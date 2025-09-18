import logging

import cv2

from server.config import CASCADE_PATH

logger = logging.getLogger(__name__)


class FaceDetector:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
        if self.face_cascade.empty():
            logger.error("Error: No se pudo cargar el clasificador de rostros")
            raise Exception("No se pudo cargar el clasificador de rostros")

    def detect(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        return faces

    def draw_faces(self, frame, faces):
        num_faces = len(faces)
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)

        text = f"Rostros: {num_faces}"
        cv2.putText(frame, text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        return frame
