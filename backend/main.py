from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Optional
import json
import asyncio
import logging
from datetime import datetime
import uuid

# Import FastRTC integration
from fastrtc_integration import fastrtc_manager, handle_fastrtc_message, create_webrtc_answer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FastRTC Audio Backend",
    description="Real-time audio streaming backend with FastRTC integration",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connection management
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.connection_metadata[client_id] = {
            "connected_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "audio_streaming": False
        }
        logger.info(f"Client {client_id} connected")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.connection_metadata:
            del self.connection_metadata[client_id]
        logger.info(f"Client {client_id} disconnected")

    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)

    async def broadcast(self, message: str, exclude_client: str = None):
        for client_id, connection in self.active_connections.items():
            if client_id != exclude_client:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {client_id}: {e}")

    def get_connection_count(self) -> int:
        return len(self.active_connections)

manager = ConnectionManager()

# Pydantic models
class WebRTCOffer(BaseModel):
    sdp: str
    modality: str = "audio"
    mode: str = "send"

class WebRTCAnswer(BaseModel):
    status: str
    sdp: Optional[str] = None
    webrtc_id: Optional[str] = None
    meta: Optional[Dict] = None

class AudioMessage(BaseModel):
    type: str
    data: str
    timestamp: Optional[datetime] = None

# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": "FastRTC Audio Backend",
        "status": "running",
        "connections": manager.get_connection_count(),
        "fastrtc_stats": fastrtc_manager.get_stats(),
        "timestamp": datetime.utcnow().isoformat()
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "connections": manager.get_connection_count(),
        "fastrtc_streams": fastrtc_manager.get_stats(),
        "timestamp": datetime.utcnow().isoformat()
    }

# WebRTC signaling endpoint
@app.post("/webrtc/offer")
async def webrtc_offer(offer: WebRTCOffer):
    """
    Handle WebRTC offer for audio streaming with FastRTC integration
    """
    try:
        # Validate modality and mode
        if offer.modality not in ["audio", "video", "audio-video"]:
            raise HTTPException(status_code=400, detail="Invalid modality")
        
        if offer.mode not in ["send", "receive", "send-receive"]:
            raise HTTPException(status_code=400, detail="Invalid mode")
        
        # Check FastRTC stream limits
        fastrtc_stats = fastrtc_manager.get_stats()
        if fastrtc_stats["total_streams"] >= fastrtc_stats["max_streams"]:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "failed",
                    "meta": {
                        "error": "concurrency_limit_reached",
                        "limit": fastrtc_stats["max_streams"]
                    }
                }
            )
        
        # Create FastRTC stream and WebRTC answer
        offer_data = {
            "sdp": offer.sdp,
            "modality": offer.modality,
            "mode": offer.mode
        }
        
        try:
            answer = await create_webrtc_answer(offer_data)
        except ValueError as e:
            logger.error(f"FastRTC stream creation error: {e}")
            return JSONResponse(
                status_code=200,
                content={
                    "status": "failed",
                    "meta": {
                        "error": "stream_creation_failed",
                        "message": str(e)
                    }
                }
            )
        
        logger.info(f"WebRTC offer accepted for {answer['webrtc_id']}")
        
        return WebRTCAnswer(
            status=answer["status"],
            sdp=answer["sdp"],
            webrtc_id=answer["webrtc_id"],
            meta=answer["meta"]
        )
        
    except Exception as e:
        logger.error(f"Error processing WebRTC offer: {e}")
        return JSONResponse(
            status_code=200,
            content={
                "status": "failed",
                "meta": {
                    "error": "internal_server_error",
                    "message": str(e)
                }
            }
        )

# WebSocket endpoint for real-time audio streaming
@app.websocket("/ws/audio/{client_id}")
async def websocket_audio_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time audio streaming with FastRTC integration
    """
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # Receive audio data or control messages
            data = await websocket.receive()
            
            if "text" in data:
                # Handle text messages (control messages or FastRTC messages)
                message = data["text"]
                try:
                    parsed_message = json.loads(message)
                    
                    # Check if it's a FastRTC message
                    if parsed_message.get("type") in ["send_input", "fetch_output", "stopword", "error", "warning", "log"]:
                        # Handle FastRTC message
                        response = await handle_fastrtc_message(parsed_message)
                        await manager.send_personal_message(json.dumps(response), client_id)
                    else:
                        # Handle regular control message
                        await handle_control_message(client_id, parsed_message)
                        
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from client {client_id}")
                    
            elif "bytes" in data:
                # Handle binary audio data
                audio_data = data["bytes"]
                await handle_audio_data(client_id, audio_data)
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(f"WebSocket disconnected for client {client_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket connection for client {client_id}: {e}")
        manager.disconnect(client_id)

async def handle_control_message(client_id: str, message: Dict):
    """
    Handle control messages from clients
    """
    message_type = message.get("type")
    
    if message_type == "start_streaming":
        manager.connection_metadata[client_id]["audio_streaming"] = True
        
        # Start FastRTC stream if webrtc_id is provided
        webrtc_id = message.get("webrtc_id")
        if webrtc_id:
            stream = await fastrtc_manager.get_stream(webrtc_id)
            if stream:
                await stream.start_streaming()
        
        await manager.send_personal_message(
            json.dumps({
                "type": "streaming_started",
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat()
            }),
            client_id
        )
        logger.info(f"Audio streaming started for client {client_id}")
        
    elif message_type == "stop_streaming":
        manager.connection_metadata[client_id]["audio_streaming"] = False
        
        # Stop FastRTC stream if webrtc_id is provided
        webrtc_id = message.get("webrtc_id")
        if webrtc_id:
            stream = await fastrtc_manager.get_stream(webrtc_id)
            if stream:
                await stream.stop_streaming()
        
        await manager.send_personal_message(
            json.dumps({
                "type": "streaming_stopped",
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat()
            }),
            client_id
        )
        logger.info(f"Audio streaming stopped for client {client_id}")
        
    elif message_type == "ping":
        await manager.send_personal_message(
            json.dumps({
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            }),
            client_id
        )
        
    else:
        logger.warning(f"Unknown message type from client {client_id}: {message_type}")

async def handle_audio_data(client_id: str, audio_data: bytes):
    """
    Handle incoming audio data with FastRTC integration
    """
    # Update last activity
    if client_id in manager.connection_metadata:
        manager.connection_metadata[client_id]["last_activity"] = datetime.utcnow()
    
    # Process audio data with FastRTC
    # You can implement logic to determine which stream to use
    # For now, we'll process with all active streams
    fastrtc_stats = fastrtc_manager.get_stats()
    for stream_info in fastrtc_stats["streams"]:
        if stream_info["is_active"]:
            await fastrtc_manager.process_audio(stream_info["webrtc_id"], audio_data)
    
    logger.debug(f"Received {len(audio_data)} bytes of audio data from client {client_id}")

# Get connection statistics
@app.get("/stats")
async def get_stats():
    """
    Get current connection statistics including FastRTC streams
    """
    active_streams = sum(
        1 for metadata in manager.connection_metadata.values()
        if metadata.get("audio_streaming", False)
    )
    
    return {
        "websocket_connections": {
            "total_connections": manager.get_connection_count(),
            "active_streams": active_streams,
            "connections": [
                {
                    "client_id": client_id,
                    "connected_at": metadata["connected_at"].isoformat(),
                    "last_activity": metadata["last_activity"].isoformat(),
                    "audio_streaming": metadata["audio_streaming"]
                }
                for client_id, metadata in manager.connection_metadata.items()
            ]
        },
        "fastrtc_streams": fastrtc_manager.get_stats()
    }

# FastRTC specific endpoints
@app.get("/fastrtc/streams")
async def get_fastrtc_streams():
    """
    Get all FastRTC streams
    """
    return fastrtc_manager.get_stats()

@app.delete("/fastrtc/streams/{webrtc_id}")
async def remove_fastrtc_stream(webrtc_id: str):
    """
    Remove a FastRTC stream
    """
    try:
        await fastrtc_manager.remove_stream(webrtc_id)
        return {"status": "success", "message": f"Stream {webrtc_id} removed"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Stream {webrtc_id} not found")

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception handler: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "An internal server error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 