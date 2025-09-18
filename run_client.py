#!/usr/bin/env python3
"""
Script para ejecutar el cliente de captura de video
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.app import send_frames
import asyncio

if __name__ == "__main__":
    print("Iniciando cliente de captura de video...")
    print("Asegúrate de que el servidor esté ejecutándose en localhost:8000")
    print("Presiona Ctrl+C para detener el cliente")
    
    try:
        asyncio.run(send_frames())
    except KeyboardInterrupt:
        print("\nCliente detenido por el usuario")
    except Exception as e:
        print(f"Error: {e}")