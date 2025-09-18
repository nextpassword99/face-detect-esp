import asyncio
import websockets
import cv2
import base64

async def send_frames():
    uri = "ws://localhost:8000/ws/video"
    async with websockets.connect(uri) as websocket:
        cap = cv2.VideoCapture(0)
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame = cv2.resize(frame, (320, 240))

                _, buffer = cv2.imencode('.jpg', frame)
                jpg_as_text = base64.b64encode(buffer).decode('utf-8')

                await websocket.send("data:image/jpeg;base64," + jpg_as_text)

                response = await websocket.recv()
                print("Respuesta del servidor:", response)

                await asyncio.sleep(0.1)
        finally:
            cap.release()

asyncio.run(send_frames())
