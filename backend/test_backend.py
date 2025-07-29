#!/usr/bin/env python3
"""
Test script for FastRTC Backend
"""

import asyncio
import aiohttp
import json
import websockets
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Backend URL
BACKEND_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"

async def test_health_endpoint():
    """Test the health endpoint"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BACKEND_URL}/health") as response:
            data = await response.json()
            logger.info(f"Health check: {data}")
            return response.status == 200

async def test_stats_endpoint():
    """Test the stats endpoint"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BACKEND_URL}/stats") as response:
            data = await response.json()
            logger.info(f"Stats: {data}")
            return response.status == 200

async def test_webrtc_offer():
    """Test WebRTC offer endpoint"""
    offer_data = {
        "sdp": "v=0\r\no=- 1234567890 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\na=group:BUNDLE audio\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\nc=IN IP4 0.0.0.0\r\na=mid:audio\r\na=sendrecv\r\na=rtpmap:111 opus/48000/2\r\na=fmtp:111 minptime=10;useinbandfec=1\r\n",
        "modality": "audio",
        "mode": "send"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/webrtc/offer",
            json=offer_data
        ) as response:
            data = await response.json()
            logger.info(f"WebRTC offer response: {data}")
            return response.status == 200 and data.get("status") == "success"

async def test_websocket_connection():
    """Test WebSocket connection"""
    client_id = "test-client-123"
    ws_url = f"{WS_URL}/ws/audio/{client_id}"
    
    try:
        async with websockets.connect(ws_url) as websocket:
            # Send a ping message
            ping_message = {
                "type": "ping",
                "timestamp": "2024-01-01T00:00:00Z"
            }
            await websocket.send(json.dumps(ping_message))
            
            # Wait for pong response
            response = await websocket.recv()
            data = json.loads(response)
            logger.info(f"WebSocket response: {data}")
            
            return data.get("type") == "pong"
            
    except Exception as e:
        logger.error(f"WebSocket test failed: {e}")
        return False

async def test_fastrtc_streams():
    """Test FastRTC streams endpoint"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BACKEND_URL}/fastrtc/streams") as response:
            data = await response.json()
            logger.info(f"FastRTC streams: {data}")
            return response.status == 200

async def run_all_tests():
    """Run all tests"""
    logger.info("Starting FastRTC Backend tests...")
    
    tests = [
        ("Health Endpoint", test_health_endpoint),
        ("Stats Endpoint", test_stats_endpoint),
        ("WebRTC Offer", test_webrtc_offer),
        ("WebSocket Connection", test_websocket_connection),
        ("FastRTC Streams", test_fastrtc_streams),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            logger.info(f"Running test: {test_name}")
            result = await test_func()
            results.append((test_name, result))
            logger.info(f"Test {test_name}: {'PASS' if result else 'FAIL'}")
        except Exception as e:
            logger.error(f"Test {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    logger.info("\n" + "="*50)
    logger.info("TEST SUMMARY")
    logger.info("="*50)
    
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nPassed: {passed}/{len(results)}")
    
    if passed == len(results):
        logger.info("🎉 All tests passed!")
    else:
        logger.error("❌ Some tests failed!")
    
    return passed == len(results)

if __name__ == "__main__":
    # Run tests
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1) 