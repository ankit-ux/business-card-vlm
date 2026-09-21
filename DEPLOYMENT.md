# Deployment Guide — Server 51.20.68.136

This is a copy-paste walkthrough for getting a DashScope (Qwen-VL) API key,
configuring your `.env`, and deploying this app to your AWS instance at
**51.20.68.136**.

> Note on HTTPS: Let's Encrypt (the free HTTPS provider used in this
> project) only issues certificates for a **domain name**, not a bare IP
> address. So with just the IP `51.20.68.136` you'll have a fully working
> app over plain `http://51.20.68.136`. If you want `https://`, point a
> domain at this IP first — see [Step 6](#step-6-optional-https-once-you-have-a-domain).

---

## Step 1 — Get your Qwen-VL (DashScope) API key

1. Go to **https://dashscope.console.aliyun.com/** and sign up / log in
   (Alibaba Cloud account — email + phone verification).
2. New accounts get a free token quota for models like `qwen-vl-plus`, no
   payment method required to start.
3. In the left sidebar, go to **API-KEY Management** (sometimes labeled
   "My API-KEY" or found under your account menu → "API-KEY").
4. Click **Create new API key**.
5. Copy the key immediately — it's shown only once (`sk-xxxxxxxxxxxx...`).
6. (Optional but recommended) Under **Model Square / Model Gallery**,
   confirm `qwen-vl-plus` is enabled for your account/region — it's on by
   default for most new accounts.

Keep this key private — anyone with it can rack up usage on your account.

---

## Step 2 — Configure your `.env` file

On your local machine (inside the project you downloaded), open
`backend/.env.example`, and create your real config:

```bash
cd business-card-vlm/backend
cp .env.example .env
```

Edit `backend/.env` so it looks like this (replace the key with your real
one from Step 1):

```dotenv
# ---- VLM provider ----
VLM_PROVIDER=dashscope

# Required when VLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=sk-your_real_key_from_step_1
DASHSCOPE_MODEL=qwen-vl-plus

# Not used in dashscope mode, safe to leave as-is
LOCAL_MODEL_NAME=Qwen/Qwen2.5-VL-3B-Instruct

# Lock CORS down to your server's address instead of "*" once deployed
ALLOWED_ORIGINS=http://51.20.68.136

# Max upload size per image, MB
MAX_IMAGE_MB=10
```

Save the file. **Do not commit `.env` to git** — it's already in
`.gitignore`.

---

## Step 3 — Get the project onto the server

From your local machine, copy the whole project folder to the server
(replace `your-key.pem` with your actual EC2 SSH key):

```bash
scp -i your-key.pem -r business-card-vlm ubuntu@51.20.68.136:~/
```

(If your instance's username isn't `ubuntu`, e.g. it's `ec2-user` for
Amazon Linux, use that instead.)

Or, if you've pushed this project to a git repo, SSH in and `git clone` it
directly — either way works.

---

## Step 4 — Install Docker on the server (one-time setup)

```bash
ssh -i your-key.pem ubuntu@51.20.68.136

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

Also make sure your EC2 **Security Group** allows inbound traffic on:
- `22` (SSH) — from your IP
- `80` (HTTP) — from anywhere (`0.0.0.0/0`)
- `443` (HTTPS) — from anywhere, only needed if you do Step 6

(EC2 console → your instance → Security tab → security group → Edit
inbound rules.)

---

## Step 5 — Build and start the app

Still on the server:

```bash
cd ~/business-card-vlm
docker compose up -d --build
```

This takes a few minutes the first time (builds the React frontend and
installs backend dependencies). Check everything is running:

```bash
docker compose ps
docker compose logs -f backend    # Ctrl+C to stop watching logs
```

Now open in your browser:

- App: **http://51.20.68.136/**
- Swagger API docs: **http://51.20.68.136/docs**
- Health check: **http://51.20.68.136/api/health** → should return
  `{"status": "ok", "vlm_provider": "dashscope"}`

Try uploading a business card image — if extraction fails, run
`docker compose logs backend` and check for a DashScope error message
(usually means the API key wasn't picked up — see Troubleshooting below).

---

## Step 6 — (Optional) HTTPS, once you have a domain

If you later point a domain (e.g. `leads.yourdomain.com`) at
`51.20.68.136` via an **A record**, you can add free HTTPS:

```bash
sudo apt-get install -y certbot
docker compose stop nginx

sudo certbot certonly --standalone \
  -d leads.yourdomain.com \
  --agree-tos -m you@example.com --non-interactive

sudo cp -r /etc/letsencrypt/* nginx/certbot/conf/

nano nginx/nginx.conf
# uncomment the "server { listen 443 ssl; ... }" block at the bottom,
# replace YOUR_DOMAIN with leads.yourdomain.com

docker compose up -d nginx
```

Auto-renew twice a day:

```bash
sudo crontab -e
# add:
0 3,15 * * * certbot renew --quiet --deploy-hook "docker restart bcard-nginx"
```

Also update `ALLOWED_ORIGINS` in `backend/.env` to
`https://leads.yourdomain.com`, then `docker compose up -d --build backend`.

---

## Updating the app later

```bash
cd ~/business-card-vlm
git pull                       # or re-scp changed files
docker compose up -d --build
```

## Troubleshooting on this server

- **Can't reach http://51.20.68.136/ at all** → check the EC2 security
  group allows port 80 inbound, and `docker compose ps` shows `bcard-nginx`
  as `Up`.
- **"DASHSCOPE_API_KEY is not set" when uploading** → confirm
  `backend/.env` on the *server* (not just your laptop) has the real key,
  then `docker compose restart backend`.
- **CORS error in browser console** → make sure `ALLOWED_ORIGINS` in
  `backend/.env` exactly matches how you access the app
  (`http://51.20.68.136`, no trailing slash), then rebuild the backend.
- **413 error on upload** → already handled (`client_max_body_size 50M` in
  `nginx/nginx.conf`), but if you increase upload limits further, also
  raise `MAX_IMAGE_MB` in `.env`.
