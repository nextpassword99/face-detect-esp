import asyncio
import websockets
import cv2
import base64
import json


async def send_frames():
    uri = "ws://localhost:8000/ws/video"

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: No se puede acceder a la cámara")
        return

    try:
        async with websockets.connect(uri) as websocket:
            print("Conectado al servidor")

            try:
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        print("Error al capturar frame")
                        break

                    frame = cv2.resize(frame, (320, 240))

                    _, buffer = cv2.imencode(
                        '.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    jpg_as_text = base64.b64encode(buffer).decode('utf-8')

                    await websocket.send("data:image/jpeg;base64," + jpg_as_text)

                    response = await websocket.recv()
                    try:
                        data = json.loads(response)
                        num_faces = data.get('num_faces', 0)
                        print(f"Rostros detectados: {num_faces}")
                    except json.JSONDecodeError:
                        print("Respuesta del servidor:", response)

                    await asyncio.sleep(0.1)

            except websockets.exceptions.ConnectionClosed:
                print("Conexión cerrada por el servidor")
            except KeyboardInterrupt:
                print("Interrumpido por el usuario")

    except Exception as e:
        print(f"Error de conexión: {e}")
    finally:
        cap.release()
        print("Cámara liberada")

if __name__ == "__main__":
    asyncio.run(send_frames())
