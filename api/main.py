"""Clinical Knowledge Graph — Evaluator API."""

from fastapi import FastAPI

app = FastAPI(title="CKG API", version="0.1.0")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/version")
def version():
    return {"version": "0.1.0"}
