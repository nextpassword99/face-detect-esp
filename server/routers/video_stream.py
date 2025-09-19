import asyncio
import base64
import json
import logging
import threading

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.responses import StreamingResponse

logger = logging.getLogger(__name__)
router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.esp_connections = set()
        self.android_connections = set()
        self.streaming_connections = set()
    
    def add_esp(self, websocket):
        self.esp_connections.add(websocket)
    
    def remove_esp(self, websocket):
        self.esp_connections.discard(websocket)
    
    def add_android(self, websocket):
        self.android_connections.add(websocket)
    
    def remove_android(self, websocket):
        self.android_connections.discard(websocket)
        self.streaming_connections.discard(websocket)
    
    def start_streaming(self, websocket):
        self.streaming_connections.add(websocket)
    
    def stop_streaming(self, websocket):
        self.streaming_connections.discard(websocket)
    
    async def broadcast_to_esp(self, message):
        disconnected = []
        for esp in self.esp_connections:
            try:
                await esp.send_text(message)
            except Exception:
                disconnected.append(esp)
        for esp in disconnected:
            self.remove_esp(esp)
    
    async def broadcast_to_android(self, message):
        targets = self.android_connections - self.streaming_connections
        disconnected = []
        for android in targets:
            try:
                await android.send_text(message)
            except Exception:
                disconnected.append(android)
        for android in disconnected:
            self.remove_android(android)
    
    async def broadcast_to_streaming(self, message):
        disconnected = []
        for android in self.streaming_connections:
            try:
                await android.send_text(message)
            except Exception:
                disconnected.append(android)
        for android in disconnected:
            self.remove_android(android)

class FaceDetector:
    def __init__(self):
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        if self.face_cascade.empty():
            raise RuntimeError("No se pudo cargar el clasificador de rostros")
    
    def detect_faces(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )
        return faces
    
    def draw_faces(self, frame, faces):
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
        return frame
    
    def encode_frame(self, frame, quality=70):
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return base64.b64encode(buffer).decode('utf-8')

manager = ConnectionManager()
detector = FaceDetector()

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

def process_video_frame(data):
    if "base64," in data:
        data = data.split("base64,")[1]
    
    img_bytes = base64.b64decode(data)
    nparr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if frame is None:
        return None, 0, None
    
    faces = detector.detect_faces(frame)
    num_faces = len(faces)
    processed_frame = detector.draw_faces(frame.copy(), faces)
    
    return frame, num_faces, processed_frame

@router.websocket("/ws/video")
async def video_ws(websocket: WebSocket):
    await websocket.accept()
    logger.info("Cliente de video conectado")
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                frame, num_faces, processed_frame = process_video_frame(data)
                if frame is None:
                    logger.warning("Frame no válido recibido")
                    continue
                
                logger.info(f"Detectados {num_faces} rostro(s)")
                
                stream_state.set_frame(processed_frame)
                
                response = {"num_faces": num_faces, "status": "success"}
                msg = json.dumps(response)
                
                if manager.streaming_connections:
                    encoded_frame = detector.encode_frame(frame)
                    streaming_response = {**response, "video_frame": encoded_frame}
                    await manager.broadcast_to_streaming(json.dumps(streaming_response))
                
                await manager.broadcast_to_esp(msg)
                await manager.broadcast_to_android(msg)
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
    await websocket.accept()
    manager.add_esp(websocket)
    logger.info(f"ESP conectado. Total ESPs: {len(manager.esp_connections)}")
    
    try:
        while True:
            message = await websocket.receive_text()
            logger.debug(f"Mensaje de ESP: {message}")
    except WebSocketDisconnect:
        manager.remove_esp(websocket)
        logger.info(f"ESP desconectado. Total ESPs: {len(manager.esp_connections)}")
    except Exception as e:
        logger.error(f"Error en websocket ESP: {e}")
        manager.remove_esp(websocket)

@router.websocket("/ws/android")
async def android_ws(websocket: WebSocket):
    await websocket.accept()
    manager.add_android(websocket)
    logger.info(f"Cliente Android conectado. Total Android: {len(manager.android_connections)}")
    
    try:
        while True:
            message = await websocket.receive_text()
            logger.debug(f"Mensaje de Android: {message}")
            
            try:
                data = json.loads(message)
                action = data.get("action")
                
                if action == "start_stream":
                    manager.start_streaming(websocket)
                    logger.info(f"Android iniciando streaming. Total streaming: {len(manager.streaming_connections)}")
                    await websocket.send_text(json.dumps({"status": "streaming_started"}))
                elif action == "stop_stream":
                    manager.stop_streaming(websocket)
                    logger.info(f"Android deteniendo streaming. Total streaming: {len(manager.streaming_connections)}")
                    await websocket.send_text(json.dumps({"status": "streaming_stopped"}))
                    
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        manager.remove_android(websocket)
        logger.info(f"Cliente Android desconectado. Total Android: {len(manager.android_connections)}")
    except Exception as e:
        logger.error(f"Error en websocket Android: {e}")
        manager.remove_android(websocket)

async def video_generator():
    while True:
        frame = stream_state.get_frame()
        if frame is not None:
            flag, encoded_image = cv2.imencode(".jpg", frame)
            if not flag:
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + 
                   bytearray(encoded_image) + b'\r\n')
        await asyncio.sleep(0.03)

@router.get("/stream/video")
async def video_feed():
    return StreamingResponse(video_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

