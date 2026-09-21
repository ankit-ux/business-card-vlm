import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from app.api.routes import router  # noqa: E402

app = FastAPI(
    title="Business Card Lead Extraction API",
    description="Upload business card images in bulk and extract structured leads using a Qwen VLM.",
    version="1.0.0",
)

origins_env = os.getenv("ALLOWED_ORIGINS", "*")
allow_origins = ["*"] if origins_env.strip() == "*" else [o.strip() for o in origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {"message": "Business Card Lead Extraction API. See /docs for Swagger UI."}
