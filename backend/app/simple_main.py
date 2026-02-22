"""Minimal FastAPI app for testing deployment."""
from fastapi import FastAPI
import os

app = FastAPI(title="ZNAYKA - Minimal")

@app.get("/")
async def root():
    return {"name": "ZNAYKA", "status": "ok"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
