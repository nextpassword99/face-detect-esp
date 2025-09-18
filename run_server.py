#!/usr/bin/env python3
"""
Script para ejecutar el servidor de detección de rostros
"""
import uvicorn
from server.app import app

if __name__ == "__main__":
    print("Iniciando servidor de detección de rostros...")
    print("Servidor disponible en: http://localhost:8000")
    print("WebSocket para video: ws://localhost:8000/ws/video")
    print("WebSocket para ESP: ws://localhost:8000/ws/esp")
    print("Presiona Ctrl+C para detener el servidor")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info",
        reload=False
    )