"""
FastRTC Integration Module

This module provides integration with FastRTC for real-time audio processing.
Based on the FastRTC documentation: https://fastrtc.org/userguide/api/
"""

import asyncio
import logging
from typing import Dict, Optional, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class FastRTCStream:
    """
    FastRTC Stream handler for real-time audio processing
    """
    
    def __init__(self, webrtc_id: str, modality: str = "audio", mode: str = "send"):
        self.webrtc_id = webrtc_id
        self.modality = modality
        self.mode = mode
        self.is_active = False
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.audio_buffer = []
        self.processing = False
        
    async def start_streaming(self):
        """Start the audio stream"""
        self.is_active = True
        self.last_activity = datetime.utcnow()
        logger.info(f"Started FastRTC stream for {self.webrtc_id}")
        
    async def stop_streaming(self):
        """Stop the audio stream"""
        self.is_active = False
        logger.info(f"Stopped FastRTC stream for {self.webrtc_id}")
        
    async def process_audio_data(self, audio_data: bytes):
        """Process incoming audio data"""
        if not self.is_active:
            return
            
        self.last_activity = datetime.utcnow()
        self.audio_buffer.append(audio_data)
        
        # Process buffer when it reaches a certain size
        if len(self.audio_buffer) >= 10 and not self.processing:
            await self._process_buffer()
            
    async def _process_buffer(self):
        """Process the audio buffer"""
        self.processing = True
        try:
            # Combine audio chunks
            combined_audio = b''.join(self.audio_buffer)
            
            # Here you would integrate with actual FastRTC processing
            # For now, we'll just log the processing
            logger.debug(f"Processing {len(combined_audio)} bytes of audio for {self.webrtc_id}")
            
            # Clear buffer after processing
            self.audio_buffer = []
            
        except Exception as e:
            logger.error(f"Error processing audio for {self.webrtc_id}: {e}")
        finally:
            self.processing = False
            
    def get_status(self) -> Dict[str, Any]:
        """Get current stream status"""
        return {
            "webrtc_id": self.webrtc_id,
            "modality": self.modality,
            "mode": self.mode,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "buffer_size": len(self.audio_buffer),
            "processing": self.processing
        }

class FastRTCManager:
    """
    Manager for multiple FastRTC streams
    """
    
    def __init__(self):
        self.streams: Dict[str, FastRTCStream] = {}
        self.max_streams = 100
        
    async def create_stream(self, webrtc_id: str, modality: str = "audio", mode: str = "send") -> FastRTCStream:
        """Create a new FastRTC stream"""
        if not webrtc_id or webrtc_id == "None":
            raise ValueError("Invalid webrtc_id: cannot be None or empty")
            
        if len(self.streams) >= self.max_streams:
            raise ValueError("Maximum number of streams reached")
            
        if webrtc_id in self.streams:
            raise ValueError(f"Stream {webrtc_id} already exists")
            
        stream = FastRTCStream(webrtc_id, modality, mode)
        self.streams[webrtc_id] = stream
        logger.info(f"Created FastRTC stream {webrtc_id}")
        return stream
        
    async def get_stream(self, webrtc_id: str) -> Optional[FastRTCStream]:
        """Get a stream by ID"""
        return self.streams.get(webrtc_id)
        
    async def remove_stream(self, webrtc_id: str):
        """Remove a stream"""
        if webrtc_id in self.streams:
            stream = self.streams[webrtc_id]
            await stream.stop_streaming()
            del self.streams[webrtc_id]
            logger.info(f"Removed FastRTC stream {webrtc_id}")
            
    async def process_audio(self, webrtc_id: str, audio_data: bytes):
        """Process audio data for a specific stream"""
        stream = await self.get_stream(webrtc_id)
        if stream:
            await stream.process_audio_data(audio_data)
        else:
            logger.warning(f"Stream {webrtc_id} not found")
            
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all streams"""
        active_streams = sum(1 for stream in self.streams.values() if stream.is_active)
        
        return {
            "total_streams": len(self.streams),
            "active_streams": active_streams,
            "max_streams": self.max_streams,
            "streams": [
                stream.get_status() for stream in self.streams.values()
            ]
        }
        
    async def cleanup_inactive_streams(self, max_inactive_minutes: int = 30):
        """Clean up streams that have been inactive for too long"""
        cutoff_time = datetime.utcnow()
        cutoff_time = cutoff_time.replace(minute=cutoff_time.minute - max_inactive_minutes)
        
        streams_to_remove = []
        for webrtc_id, stream in self.streams.items():
            if stream.last_activity < cutoff_time:
                streams_to_remove.append(webrtc_id)
                
        for webrtc_id in streams_to_remove:
            await self.remove_stream(webrtc_id)
            
        if streams_to_remove:
            logger.info(f"Cleaned up {len(streams_to_remove)} inactive streams")

# Global FastRTC manager instance
fastrtc_manager = FastRTCManager()

# Message handlers for FastRTC protocol
async def handle_fastrtc_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle FastRTC protocol messages
    Based on: https://fastrtc.org/userguide/api/
    """
    message_type = message.get("type")
    
    if message_type == "send_input":
        # Handle input data for handlers
        webrtc_id = message.get("webrtc_id")
        data = message.get("data", {})
        
        if webrtc_id:
            stream = await fastrtc_manager.get_stream(webrtc_id)
            if stream:
                # Process input data
                logger.info(f"Received input data for stream {webrtc_id}")
                return {"status": "success", "message": "Input processed"}
            else:
                return {"status": "error", "message": "Stream not found"}
                
    elif message_type == "fetch_output":
        # Handle output data requests
        webrtc_id = message.get("webrtc_id")
        
        if webrtc_id:
            stream = await fastrtc_manager.get_stream(webrtc_id)
            if stream:
                # Return output data
                return {
                    "status": "success",
                    "output": {
                        "stream_id": webrtc_id,
                        "status": stream.get_status()
                    }
                }
            else:
                return {"status": "error", "message": "Stream not found"}
                
    elif message_type == "stopword":
        # Handle stopword detection
        webrtc_id = message.get("webrtc_id")
        logger.info(f"Stopword detected for stream {webrtc_id}")
        return {"status": "success", "message": "Stopword detected"}
        
    elif message_type == "error":
        # Handle error messages
        error_message = message.get("data", "Unknown error")
        logger.error(f"FastRTC error: {error_message}")
        return {"status": "error", "message": error_message}
        
    elif message_type == "warning":
        # Handle warning messages
        warning_message = message.get("data", "Unknown warning")
        logger.warning(f"FastRTC warning: {warning_message}")
        return {"status": "warning", "message": warning_message}
        
    elif message_type == "log":
        # Handle log messages
        log_message = message.get("data", "")
        logger.info(f"FastRTC log: {log_message}")
        return {"status": "success", "message": "Log recorded"}
        
    else:
        return {"status": "error", "message": f"Unknown message type: {message_type}"}

# Utility functions
async def create_webrtc_offer(modality: str = "audio", mode: str = "send") -> Dict[str, Any]:
    """
    Create a WebRTC offer for FastRTC
    """
    import uuid
    
    webrtc_id = str(uuid.uuid4())
    
    # Create basic SDP offer that works with WebRTC
    sdp_offer = f"""
v=0
o=- {webrtc_id} 2 IN IP4 127.0.0.1
s=-
t=0 0
a=group:BUNDLE audio
a=extmap-allow-mixed
a=msid-semantic: WMS
m=audio 9 UDP/TLS/RTP/SAVPF 111
c=IN IP4 0.0.0.0
a=mid:audio
a=sendrecv
a=rtpmap:111 opus/48000/2
a=fmtp:111 minptime=10;useinbandfec=1
a=ssrc:1 cname:fastrtc-audio
a=ssrc:1 msid:fastrtc-audio audio
a=ssrc:1 mslabel:fastrtc-audio
a=label:audio
a=rtcp-mux
    """.strip()
    
    logger.info(f"Generated SDP offer: {sdp_offer}")
    return {
        "sdp": sdp_offer,
        "modality": modality,
        "mode": mode,
        "webrtc_id": webrtc_id
    }

async def create_webrtc_answer(offer: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a WebRTC answer for FastRTC
    """
    import uuid
    
    # Generate a new webrtc_id since the offer doesn't contain one
    webrtc_id = str(uuid.uuid4())
    modality = offer.get("modality", "audio")
    mode = offer.get("mode", "send")
    
    # Create stream
    await fastrtc_manager.create_stream(webrtc_id, modality, mode)
    
    # Create basic SDP answer that works with WebRTC
    sdp_answer = f"""
v=0
o=- {webrtc_id} 2 IN IP4 127.0.0.1
s=-
t=0 0
a=group:BUNDLE audio
a=extmap-allow-mixed
a=msid-semantic: WMS
m=audio 9 UDP/TLS/RTP/SAVPF 111
c=IN IP4 0.0.0.0
a=mid:audio
a=sendrecv
a=rtpmap:111 opus/48000/2
a=fmtp:111 minptime=10;useinbandfec=1
a=ssrc:1 cname:fastrtc-audio
a=ssrc:1 msid:fastrtc-audio audio
a=ssrc:1 mslabel:fastrtc-audio
a=label:audio
a=rtcp-mux
    """.strip()
    
    logger.info(f"Generated SDP answer: {sdp_answer}")
    return {
        "status": "success",
        "sdp": sdp_answer,
        "webrtc_id": webrtc_id,
        "meta": {
            "modality": modality,
            "mode": mode,
            "created_at": datetime.utcnow().isoformat()
        }
    } 