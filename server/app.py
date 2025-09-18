from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import numpy as np
import base64
import json
import cv2
import logging
import os


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Face Detection Server", version="1.0.0")


esp_connections = set()


face_cascade_path = cv2.data.haarcascades + \
    'haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(face_cascade_path)

if face_cascade.empty():
    logger.error("Error: No se pudo cargar el clasificador de rostros")
    raise Exception("No se pudo cargar el clasificador de rostros")


@app.get("/")
async def root():
    return {"message": "Servidor de detección de rostros funcionando"}


@app.websocket("/ws/video")
async def video_ws(websocket: WebSocket):
    await websocket.accept()
    logger.info("Cliente de video conectado")

    try:
        while True:
            data = await websocket.receive_text()

            if "base64," in data:
                data = data.split("base64,")[1]

            try:

                img_bytes = base64.b64decode(data)
                nparr = np.frombuffer(img_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if frame is None:
                    logger.warning("Frame no válido recibido")
                    continue

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                faces = face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(30, 30),
                    flags=cv2.CASCADE_SCALE_IMAGE
                )

                num_faces = len(faces)

                logger.info(f"Detectados {num_faces} rostro(s)")

                response = {"num_faces": num_faces, "status": "success"}
                msg = json.dumps(response)

                disconnected_esps = []
                for esp in esp_connections:
                    try:
                        await esp.send_text(msg)
                    except Exception as e:
                        logger.warning(f"Error enviando a ESP: {e}")
                        disconnected_esps.append(esp)

                for esp in disconnected_esps:
                    esp_connections.discard(esp)

                await websocket.send_text(msg)

            except Exception as e:
                logger.error(f"Error procesando frame: {e}")
                error_response = {"num_faces": 0,
                                  "status": "error", "message": str(e)}
                await websocket.send_text(json.dumps(error_response))

    except WebSocketDisconnect:
        logger.info("Cliente de video desconectado")
    except Exception as e:
        logger.error(f"Error en websocket de video: {e}")


@app.websocket("/ws/esp")
async def esp_ws(websocket: WebSocket):
    await websocket.accept()
    esp_connections.add(websocket)
    logger.info(f"ESP conectado. Total ESPs: {len(esp_connections)}")

    try:
        while True:

            message = await websocket.receive_text()
            logger.debug(f"Mensaje de ESP: {message}")
    except WebSocketDisconnect:
        esp_connections.discard(websocket)
        logger.info(f"ESP desconectado. Total ESPs: {len(esp_connections)}")
    except Exception as e:
        logger.error(f"Error en websocket ESP: {e}")
        esp_connections.discard(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
