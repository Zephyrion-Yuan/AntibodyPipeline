from fastapi import FastAPI

from app.api.router import api_router

app = FastAPI(title="Antibody Pipeline Backend")


@app.get("/health")
def healthcheck():
    return {"status": "ok"}


app.include_router(api_router)
