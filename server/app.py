from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import numpy as np
import face_recognition
import base64
import json
import cv2

app = FastAPI()

esp_connections = set()


@app.websocket("/ws/video")
async def video_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()

            if "base64," in data:
                data = data.split("base64,")[1]

            img_bytes = base64.b64decode(data)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                continue

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(rgb_frame)
            num_faces = len(face_locations)

            print(f"Detectados {num_faces} rostro(s)")

            # Enviar a ESPs
            msg = json.dumps({"num_faces": num_faces})
            for esp in list(esp_connections):
                try:
                    await esp.send_text(msg)
                except:
                    esp_connections.remove(esp)

            await websocket.send_text(msg)

    except WebSocketDisconnect:
        print("Cliente de video desconectado")


@app.websocket("/ws/esp")
async def esp_ws(websocket: WebSocket):
    await websocket.accept()
    esp_connections.add(websocket)
    try:
        while True:
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        esp_connections.remove(websocket)
