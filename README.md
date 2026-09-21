# VLM Business Card Lead Extraction Application

Bulk-upload business card images, extract structured leads with a **Qwen
Vision-Language Model**, review/edit them in a table, and download an Excel
lead list.

```
User
  │
  ▼
React + Vite Frontend
  │  Upload multiple images
  ▼
FastAPI Backend
  ├── Image validation
  ├── Image preprocessing
  ├── Batch processing
  ▼
Qwen Vision-Language Model
  │  Extract structured information
  ▼
Pydantic Validation → Lead JSON
  ├── Display in React table
  └── Excel generation → .xlsx Download
```

---

## 0. Important: how "Qwen VLM on free-tier AWS" actually works here

Qwen-VL's real model weights (even the smallest "3B" variant) need a GPU
with several GB of VRAM to run at usable speed. **AWS's free tier only
includes small CPU instances (t2.micro / t3.micro, 1 vCPU, ~1GB RAM)** — it
does **not** include any GPU instance, so you cannot literally load Qwen-VL
weights on a free-tier box.

To satisfy "deploy on a free-tier AWS environment" while still using the
real Qwen-VL model, this app defaults to:

- **`VLM_PROVIDER=dashscope`** — the backend calls Qwen-VL (`qwen-vl-plus`)
  through Alibaba Cloud's **DashScope API** over HTTPS. Inference happens in
  Alibaba's cloud; your EC2 box just runs lightweight FastAPI + React
  containers, which comfortably fits a `t2.micro`/`t3.micro` free-tier
  instance. DashScope has a free quota for new accounts.

If you *do* have access to a GPU machine (e.g. a paid `g4dn.xlarge`, or your
own workstation), you can switch to:

- **`VLM_PROVIDER=local`** — loads `Qwen/Qwen2.5-VL-3B-Instruct` locally via
  `transformers`. See [Section 6](#6-optional-running-qwen-vl-locally-on-a-gpu).

Everything else in the app (upload, table, Excel export, Docker, Nginx,
HTTPS) is identical either way — only `vlm.py`'s backend call changes.

---

## 1. Project structure

```
business-card-vlm/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + CORS
│   │   ├── api/routes.py        # All REST endpoints
│   │   ├── services/
│   │   │   ├── vlm.py           # Qwen-VL calls (dashscope or local)
│   │   │   ├── image.py         # Validation + preprocessing
│   │   │   └── excel.py         # .xlsx generation
│   │   ├── schemas/lead.py      # Pydantic models
│   │   └── store.py             # In-memory batch store + duplicate logic
│   ├── uploads/                 # Saved original images (per batch)
│   ├── requirements.txt
│   ├── requirements-local.txt   # only needed for VLM_PROVIDER=local
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/ (UploadZone, LeadsTable, StatsBar)
│   │   └── services/api.js
│   ├── package.json
│   └── Dockerfile
├── nginx/
│   └── nginx.conf               # Reverse proxy (/api → backend, / → frontend)
├── docker-compose.yml
└── README.md
```

---

## 2. Get a DashScope (Qwen-VL) API key

1. Create an account at https://dashscope.console.aliyun.com/ (Alibaba
   Cloud). New accounts get a free token quota.
2. Go to **API-KEY Management** and create a key.
3. Copy it — you'll put it in `backend/.env` as `DASHSCOPE_API_KEY`.

---

## 3. Run it locally (development, no Docker)

**Backend:**

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and paste your DASHSCOPE_API_KEY
uvicorn app.main:app --reload --port 8000
```

Backend is now at `http://localhost:8000`, Swagger docs at
`http://localhost:8000/docs`.

**Frontend (new terminal):**

```bash
cd frontend
npm install
npm run dev
```

Frontend is at `http://localhost:5173` (Vite dev server proxies `/api` calls
to `http://localhost:8000` — see `vite.config.js`).

Open `http://localhost:5173`, drag in some business card images, and click
**Upload & Extract Leads**.

---

## 4. Run it with Docker Compose (recommended)

```bash
cd business-card-vlm
cp backend/.env.example backend/.env
# edit backend/.env → set DASHSCOPE_API_KEY

docker compose up -d --build
```

This builds and starts three containers:

| Container       | Purpose                                   |
|-----------------|--------------------------------------------|
| `bcard-backend` | FastAPI + Qwen-VL calls                    |
| `bcard-frontend`| React build served by its own nginx        |
| `bcard-nginx`   | Public reverse proxy on ports 80/443       |

Visit `http://<server-ip>/` for the app, `http://<server-ip>/docs` for the
Swagger API docs.

Stop it with `docker compose down`. Logs: `docker compose logs -f backend`.

---

## 5. Deploy to AWS (free tier)

> **Deploying to a specific server already?** See
> [`DEPLOYMENT.md`](./DEPLOYMENT.md) for a copy-paste walkthrough covering
> getting a DashScope API key, filling in `.env`, and shipping the app to a
> live server by IP address.

### 5.1 Launch the EC2 instance

1. AWS Console → EC2 → **Launch instance**.
2. AMI: **Ubuntu Server 22.04 LTS**.
3. Instance type: **t2.micro** or **t3.micro** (free-tier eligible).
4. Create/select a key pair (for SSH).
5. Security group — allow inbound:
   - `22` (SSH) from your IP
   - `80` (HTTP) from anywhere
   - `443` (HTTPS) from anywhere
6. Launch, and note the instance's **public IP** (or allocate an Elastic IP
   so it doesn't change on reboot).

### 5.2 Install Docker on the instance

```bash
ssh -i your-key.pem ubuntu@<PUBLIC_IP>

sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

sudo usermod -aG docker $USER
newgrp docker
```

### 5.3 Deploy the app

```bash
git clone <your-repo-url> business-card-vlm
cd business-card-vlm
cp backend/.env.example backend/.env
nano backend/.env      # paste DASHSCOPE_API_KEY, set ALLOWED_ORIGINS to your domain later

docker compose up -d --build
```

Visit `http://<PUBLIC_IP>/` — the app should be live.

### 5.4 Point a domain at it (optional but needed for HTTPS)

Create an **A record** at your DNS provider (Route 53, Namecheap, etc.)
pointing your domain/subdomain to the EC2 public IP.

### 5.5 Enable HTTPS with Let's Encrypt (certbot)

```bash
sudo apt-get install -y certbot

# stop nginx's port 80 temporarily so certbot's standalone server can bind it
docker compose stop nginx

sudo certbot certonly --standalone -d yourdomain.com --agree-tos -m you@example.com --non-interactive

# copy certs into the volume nginx already mounts
sudo cp -r /etc/letsencrypt/* nginx/certbot/conf/

# edit nginx/nginx.conf: uncomment the "server { listen 443 ssl; ... }" block
# at the bottom and replace YOUR_DOMAIN with yourdomain.com
nano nginx/nginx.conf

docker compose up -d nginx
```

Set up auto-renewal (runs twice daily, renews only when needed, then
reloads nginx):

```bash
sudo crontab -e
# add this line:
0 3,15 * * * certbot renew --quiet --deploy-hook "docker restart bcard-nginx"
```

Your app is now live at `https://yourdomain.com`, with Swagger docs at
`https://yourdomain.com/docs`.

---

## 6. (Optional) Running Qwen-VL locally on a GPU

If you have a GPU instance/workstation and want to run the model weights
yourself instead of calling the DashScope API:

```bash
cd backend
pip install -r requirements-local.txt
```

In `backend/.env`:

```
VLM_PROVIDER=local
LOCAL_MODEL_NAME=Qwen/Qwen2.5-VL-3B-Instruct
```

The model downloads automatically (several GB) on first request and is
cached in-process afterwards. A `g4dn.xlarge` (16GB VRAM T4 GPU, **not**
free tier) comfortably runs the 3B model.

---

## 7. API reference

Interactive Swagger docs are auto-generated by FastAPI at **`/docs`**
(and machine-readable OpenAPI schema at `/openapi.json`).

| Method | Path                              | Description                          |
|--------|------------------------------------|---------------------------------------|
| POST   | `/api/upload`                     | Upload one or more images, extract leads |
| GET    | `/api/leads/{batch_id}`           | Get all leads + stats for a batch     |
| PATCH  | `/api/leads/{batch_id}/{lead_id}` | Edit a lead's fields                  |
| POST   | `/api/leads/{batch_id}/retry/{lead_id}` | Re-run extraction on a failed card |
| DELETE | `/api/leads/{batch_id}`           | Delete a batch and its saved images   |
| GET    | `/api/leads/{batch_id}/export`    | Download leads as `.xlsx`             |
| GET    | `/api/health`                     | Health check                          |

---

## 8. Feature checklist

- [x] Drag-and-drop bulk upload (`react-dropzone`)
- [x] Multiple image selection
- [x] Upload progress bar
- [x] Per-card status (success / failed / duplicate)
- [x] Qwen-VL extraction (DashScope API or local transformers)
- [x] Pydantic-validated structured JSON output
- [x] Editable lead table (inline edit → PATCH)
- [x] Failed-image retry
- [x] Duplicate detection (by normalized email/phone)
- [x] Excel (.xlsx) download, styled header + autosized columns
- [x] Reset/delete batch
- [x] Processing statistics bar
- [x] Responsive Tailwind UI
- [x] Swagger/OpenAPI docs at `/docs`
- [x] Full Docker Compose deployment (backend + frontend + nginx)
- [x] HTTPS via Let's Encrypt/certbot (see §5.5)

---

## 9. Troubleshooting

- **413 Request Entity Too Large** on upload → increase
  `client_max_body_size` in `nginx/nginx.conf` (already set to 50M).
- **CORS errors** in the browser console → set `ALLOWED_ORIGINS` in
  `backend/.env` to your exact frontend origin (or leave `*` for testing).
- **"DASHSCOPE_API_KEY is not set"** error on upload → check
  `backend/.env` is populated and the backend container was restarted
  (`docker compose restart backend`) after editing it.
- **Model returns non-JSON / extraction fails often** → business card
  photos with heavy glare/blur reduce accuracy; the app's "Retry" button
  re-runs extraction, and fields are always editable in the table.
- **Out of memory running `VLM_PROVIDER=local`** → you need a GPU; on CPU
  this will be extremely slow or crash — use `dashscope` mode instead.
