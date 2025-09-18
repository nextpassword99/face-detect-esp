import asyncio
import base64
import json
import logging
import threading

import cv2
import numpy as np
from fastapi import APIRouter, Response, WebSocket, WebSocketDisconnect
from starlette.responses import StreamingResponse

from server.services.connection_manager import ConnectionManager
from server.services.face_detector import FaceDetector

logger = logging.getLogger(__name__)
router = APIRouter()

esp_manager = ConnectionManager()
face_detector = FaceDetector()

class StreamState:
    def __init__(self):
        self.frame = None
        self.lock = threading.Lock()

    def set_frame(self, frame):
        with self.lock:
            self.frame = frame

    def get_frame(self):
        with self.lock:
            return self.frame

stream_state = StreamState()

@router.websocket("/ws/video")
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
                    logger.warning("Frame no valido recibido")
                    continue

                faces = face_detector.detect(frame)
                num_faces = len(faces)
                logger.info(f"Detectados {num_faces} rostro(s)")

                processed_frame = face_detector.draw_faces(frame.copy(), faces)
                stream_state.set_frame(processed_frame)

                response = {"num_faces": num_faces, "status": "success"}
                msg = json.dumps(response)

                await esp_manager.broadcast(msg)
                await websocket.send_text(msg)

            except Exception as e:
                logger.error(f"Error procesando frame: {e}")
                error_response = {"num_faces": 0, "status": "error", "message": str(e)}
                await websocket.send_text(json.dumps(error_response))

    except WebSocketDisconnect:
        logger.info("Cliente de video desconectado")
    except Exception as e:
        logger.error(f"Error en websocket de video: {e}")

@router.websocket("/ws/esp")
async def esp_ws(websocket: WebSocket):
    await esp_manager.connect(websocket)
    try:
        while True:
            message = await websocket.receive_text()
            logger.debug(f"Mensaje de ESP: {message}")
    except WebSocketDisconnect:
        esp_manager.disconnect(websocket)
        logger.info("ESP desconectado")
    except Exception as e:
        logger.error(f"Error en websocket ESP: {e}")
        if websocket in esp_manager.active_connections:
            esp_manager.disconnect(websocket)

async def video_generator():
    while True:
        frame = stream_state.get_frame()
        if frame is not None:
            (flag, encodedImage) = cv2.imencode(".jpg", frame)
            if not flag:
                continue
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
                   bytearray(encodedImage) + b'\r\n')
        await asyncio.sleep(0.03) # ~30 fps

@router.get("/stream/video")
async def video_feed():
    return StreamingResponse(video_generator(), media_type="multipart/x-mixed-replace; boundary=frame")
