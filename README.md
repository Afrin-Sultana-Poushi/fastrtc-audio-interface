# FastRTC Audio Backend

A FastAPI-based backend for real-time audio streaming with FastRTC integration. This backend provides WebRTC signaling, WebSocket connections, and audio processing capabilities for the FastRTC Audio Interface frontend.

## Features

- 🎤 **Real-time Audio Streaming** via WebRTC and WebSockets
- 🔄 **FastRTC Integration** for audio processing
- 📊 **Connection Management** with statistics and monitoring
- 🛡️ **CORS Support** for cross-origin requests
- 📈 **Health Monitoring** and status endpoints
- 🔧 **Configurable Settings** via environment variables

## Prerequisites

- Python 3.8+
- pip (Python package manager)

## Installation

1. **Clone or navigate to the backend directory:**
   ```bash
   cd fastrtc-backend
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create environment file (optional):**
   ```bash
   # Create .env file
   echo "HOST=0.0.0.0" > .env
   echo "PORT=8000" >> .env
   echo "MAX_STREAMS=100" >> .env
   echo "LOG_LEVEL=INFO" >> .env
   ```

## Running the Server

### Development Mode
```bash
python main.py
```

### Production Mode
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### With Custom Settings
```bash
HOST=0.0.0.0 PORT=8000 MAX_STREAMS=50 python main.py
```

## API Endpoints

### Health & Status
- `GET /` - Root endpoint with server status
- `GET /health` - Health check endpoint
- `GET /stats` - Connection and stream statistics

### WebRTC Signaling
- `POST /webrtc/offer` - Handle WebRTC offers for audio streaming

### WebSocket
- `WS /ws/audio/{client_id}` - WebSocket endpoint for real-time audio streaming

### FastRTC Management
- `GET /fastrtc/streams` - Get all FastRTC streams
- `DELETE /fastrtc/streams/{webrtc_id}` - Remove a specific stream

## WebRTC Integration

The backend supports WebRTC signaling for audio streaming:

### Offer Format
```json
{
  "sdp": "v=0\no=- ...",
  "modality": "audio",
  "mode": "send"
}
```

### Response Format
```json
{
  "status": "success",
  "sdp": "v=0\no=- ...",
  "webrtc_id": "uuid-string",
  "meta": {
    "modality": "audio",
    "mode": "send",
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

## WebSocket Protocol

### Control Messages
```json
{
  "type": "start_streaming",
  "webrtc_id": "uuid-string"
}
```

### FastRTC Messages
```json
{
  "type": "send_input",
  "webrtc_id": "uuid-string",
  "data": {}
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server host address |
| `PORT` | `8000` | Server port |
| `MAX_STREAMS` | `100` | Maximum FastRTC streams |
| `MAX_CONNECTIONS` | `100` | Maximum WebSocket connections |
| `AUDIO_BUFFER_SIZE` | `10` | Audio buffer size for processing |
| `LOG_LEVEL` | `INFO` | Logging level |
| `SECRET_KEY` | `your-secret-key-here` | Secret key for security |

### CORS Settings

The backend is configured to allow connections from:
- `http://localhost:3000` (Next.js frontend)
- `http://localhost:3001`
- `http://127.0.0.1:3000`
- `http://127.0.0.1:3001`
- `*` (all origins in development)

## FastRTC Integration

This backend integrates with FastRTC for real-time audio processing:

### Stream Management
- Automatic stream creation on WebRTC offer
- Stream lifecycle management
- Audio buffer processing
- Connection cleanup

### Message Types Supported
- `send_input` - Send input data to handlers
- `fetch_output` - Fetch output data
- `stopword` - Handle stopword detection
- `error` - Error message handling
- `warning` - Warning message handling
- `log` - Log message handling

## Development

### Project Structure
```
fastrtc-backend/
├── main.py                 # Main FastAPI application
├── fastrtc_integration.py  # FastRTC integration module
├── config.py              # Configuration settings
├── requirements.txt        # Python dependencies
├── README.md              # This file
└── .env                   # Environment variables (optional)
```

### Adding New Features

1. **New Endpoints**: Add to `main.py`
2. **FastRTC Features**: Extend `fastrtc_integration.py`
3. **Configuration**: Update `config.py`

### Testing

Test the API endpoints:

```bash
# Health check
curl http://localhost:8000/health

# Get statistics
curl http://localhost:8000/stats

# Test WebRTC offer (requires proper SDP)
curl -X POST http://localhost:8000/webrtc/offer \
  -H "Content-Type: application/json" \
  -d '{"sdp":"v=0\\no=- ...","modality":"audio","mode":"send"}'
```

## Production Deployment

### Docker (Recommended)

1. **Create Dockerfile:**
   ```dockerfile
   FROM python:3.9-slim
   
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   
   COPY . .
   EXPOSE 8000
   
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. **Build and run:**
   ```bash
   docker build -t fastrtc-backend .
   docker run -p 8000:8000 fastrtc-backend
   ```

### Environment Setup

For production, set these environment variables:
```bash
export HOST=0.0.0.0
export PORT=8000
export MAX_STREAMS=50
export LOG_LEVEL=WARNING
export SECRET_KEY=your-production-secret-key
```

## Monitoring

### Health Checks
- `/health` - Basic health status
- `/stats` - Detailed connection statistics

### Logging
The application logs:
- Connection events
- WebRTC signaling
- Audio processing
- Errors and warnings

## Troubleshooting

### Common Issues

1. **Port already in use:**
   ```bash
   # Change port
   PORT=8001 python main.py
   ```

2. **CORS errors:**
   - Check `ALLOWED_ORIGINS` in `config.py`
   - Ensure frontend URL is included

3. **WebRTC connection issues:**
   - Verify ICE servers configuration
   - Check firewall settings
   - Ensure HTTPS in production

### Debug Mode

Enable debug logging:
```bash
LOG_LEVEL=DEBUG python main.py
```

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
- Check the [FastRTC documentation](https://fastrtc.org/userguide/api/)
- Review the logs for error messages
- Test with the provided endpoints