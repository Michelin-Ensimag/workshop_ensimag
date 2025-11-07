"""
Application FastAPI pour le backend pilote avec interface Leaflet
"""

import asyncio
import json
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from kafka_service import KafkaPilotService

# Créer l'instance FastAPI
app = FastAPI(title="Backend Pilot", description="Pilot application with Kafka and Leaflet map")

# Configurer les templates et fichiers statiques
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Instance du service Kafka
kafka_service = KafkaPilotService()

# Liste des connexions WebSocket actives
active_connections: List[WebSocket] = []


class ConnectionManager:
    """Gestionnaire des connexions WebSocket"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        """Diffuse un message à toutes les connexions actives"""
        for connection in self.active_connections.copy():
            try:
                await connection.send_text(message)
            except:
                # Connexion fermée, la retirer de la liste
                self.active_connections.remove(connection)

    async def broadcast_json(self, data: dict):
        """Diffuse un message JSON à toutes les connexions actives"""
        message = json.dumps(data)
        await self.broadcast(message)


# Instance du gestionnaire de connexions
manager = ConnectionManager()


async def instruction_callback(instruction_data: dict):
    """Callback appelé quand une nouvelle instruction est reçue"""
    message = {
        "type": "instruction",
        "data": instruction_data
    }
    await manager.broadcast_json(message)


async def log_callback(message: str):
    """Callback pour les logs"""
    log_message = {
        "type": "log",
        "message": message
    }
    await manager.broadcast_json(log_message)


# Configurer les callbacks
kafka_service.set_instruction_callback(instruction_callback)

# Configure logger with error handling
async def safe_log_callback(msg):
    try:
        await log_callback(msg)
    except Exception as e:
        print(f"Error in log callback: {e}")

kafka_service.set_logger(safe_log_callback)


@app.get("/", response_class=HTMLResponse)
async def get_homepage(request: Request):
    """Page d'accueil avec la carte Leaflet"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/status")
async def get_status():
    """Retourne le statut actuel du service"""
    return kafka_service.get_stats()


@app.post("/api/start-race")
async def start_race():
    """Démarre la course en envoyant le checkpoint ready"""
    try:
        # Timeout de 15 secondes pour éviter que l'API reste bloquée
        success = await asyncio.wait_for(
            kafka_service.send_ready_checkpoint(), 
            timeout=15.0
        )
        return {"success": success, "message": "Race started" if success else "Failed to start race"}
    except asyncio.TimeoutError:
        return {"success": False, "message": "Race start timeout - check Kafka connectivity"}
    except Exception as e:
        return {"success": False, "message": f"Race start error: {str(e)}"}


@app.post("/api/stop")
async def stop_service():
    """Arrête le service"""
    kafka_service.stop_consumption()
    return {"success": True, "message": "Service stopped"}


@app.post("/api/reset")
async def reset_service():
    """Remet à zéro le service"""
    kafka_service.reset()
    return {"success": True, "message": "Service reset"}


@app.get("/api/test-connectivity")
async def test_connectivity():
    """Teste la connectivité Kafka"""
    success = kafka_service.test_connectivity()
    return {"success": success, "message": "Connectivity test " + ("passed" if success else "failed")}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket pour la communication temps réel"""
    await manager.connect(websocket)
    
    # Envoyer le statut initial
    initial_status = {
        "type": "status",
        "data": kafka_service.get_stats()
    }
    await manager.send_personal_message(json.dumps(initial_status), websocket)
    
    try:
        while True:
            # Écouter les messages du client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                # Répondre au ping avec le statut
                response = {
                    "type": "pong",
                    "data": kafka_service.get_stats()
                }
                await manager.send_personal_message(json.dumps(response), websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage de l'application"""
    print("🚀 Backend Pilot starting...")
    print("📊 Testing Kafka connectivity...")
    
    # Test de connectivité en arrière-plan
    asyncio.create_task(test_kafka_connectivity())


@app.on_event("shutdown")
async def shutdown_event():
    """Nettoyage à l'arrêt de l'application"""
    print("🛑 Backend Pilot shutting down...")
    kafka_service.stop_consumption()


async def test_kafka_connectivity():
    """Test de connectivité Kafka en arrière-plan"""
    try:
        await asyncio.sleep(1)  # Laisser le temps au service de s'initialiser
        success = kafka_service.test_connectivity()
        if success:
            await log_callback("✅ Kafka connectivity test passed")
        else:
            await log_callback("❌ Kafka connectivity test failed")
    except Exception as e:
        await log_callback(f"❌ Connectivity test error: {str(e)}")


if __name__ == "__main__":
    # Configuration pour le développement
    import os
    from config import GLOBAL_CONFIG
    
    port = int(GLOBAL_CONFIG.get('DEFAULT', 'frontend_port', fallback='8000'))
    
    print(f"🚁 Starting Backend Pilot on port {port}")
    print(f"🌐 Open http://localhost:{port} in your browser")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )