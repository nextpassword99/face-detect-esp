import logging

from fastapi import FastAPI

from server.routers import video_stream

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Face Detection Server",
    version="1.0.1",
    description="Servidor para detectar rostros desde un stream de video y distribuirlo."
)


@app.get("/")
async def root():
    return {"message": "Servidor de deteccion de rostros funcionando"}

app.include_router(video_stream.router)
