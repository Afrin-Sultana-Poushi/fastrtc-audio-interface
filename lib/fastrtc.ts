export interface FastRTCMessage {
  type:
    | "send_input"
    | "fetch_output"
    | "stopword"
    | "error"
    | "warning"
    | "log";
  data: string | object;
}

export interface FastRTCOffer {
  sdp: string;
  modality: "audio" | "video" | "audio-video";
  mode: "send" | "receive" | "send-receive";
}

export interface FastRTCResponse {
  status: "success" | "failed";
  sdp?: string;
  webrtc_id?: string;
  meta?: {
    error?: string;
    limit?: number;
  };
}

export class FastRTCConnection {
  private peerConnection: RTCPeerConnection | null = null;
  private webrtcId: string | null = null;
  private serverUrl: string;
  private websocket: WebSocket | null = null;
  private clientId: string | null = null;

  constructor(serverUrl: string = "ws://localhost:8000") {
    this.serverUrl = serverUrl;
  }

  async connect(audioStream: MediaStream): Promise<boolean> {
    try {
      // Create WebRTC connection with proper configuration
      this.peerConnection = new RTCPeerConnection({
        iceServers: [
          { urls: "stun:stun.l.google.com:19302" },
          { urls: "stun:stun1.l.google.com:19302" },
        ],
        iceCandidatePoolSize: 10,
      });

      // Add audio track to peer connection
      audioStream.getTracks().forEach((track) => {
        this.peerConnection!.addTrack(track, audioStream);
      });

      // Set up WebRTC event handlers
      this.peerConnection.onicecandidate = (event) => {
        if (event.candidate) {
          console.log("ICE candidate:", event.candidate);
        }
      };

      this.peerConnection.onconnectionstatechange = () => {
        console.log("Connection state:", this.peerConnection?.connectionState);
      };

      this.peerConnection.oniceconnectionstatechange = () => {
        console.log(
          "ICE connection state:",
          this.peerConnection?.iceConnectionState
        );
      };

      // Create offer with proper constraints
      const offer = await this.peerConnection.createOffer({
        offerToReceiveAudio: true,
        offerToReceiveVideo: false,
      });

      await this.peerConnection.setLocalDescription(offer);

      // Send offer to FastRTC server
      const httpUrl = this.serverUrl
        .replace("ws://", "http://")
        .replace("wss://", "https://");
      const response = await fetch(`${httpUrl}/webrtc/offer`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          sdp: offer.sdp,
          modality: "audio",
          mode: "send-receive", // Changed to send-receive for bidirectional audio
        } as FastRTCOffer),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result: FastRTCResponse = await response.json();

      if (result.status === "failed") {
        throw new Error(result.meta?.error || "Connection failed");
      }

      if (!result.sdp) {
        throw new Error("No SDP received from server");
      }

      // Set remote description with proper error handling
      try {
        console.log("Setting remote description with SDP:", result.sdp);
        console.log("SDP length:", result.sdp.length);
        console.log("SDP lines:", result.sdp.split("\n").length);

        await this.peerConnection.setRemoteDescription(
          new RTCSessionDescription({
            type: "answer",
            sdp: result.sdp,
          })
        );
        console.log("Remote description set successfully");
      } catch (sdpError: unknown) {
        console.error("SDP parsing error:", sdpError);
        console.log("Received SDP:", result.sdp);
        if (sdpError instanceof Error) {
          console.log("SDP error details:", {
            name: sdpError.name,
            message: sdpError.message,
            stack: sdpError.stack,
          });
        }
        throw new Error(`Failed to parse SDP: ${sdpError}`);
      }

      this.webrtcId = result.webrtc_id || null;

      // Set up WebSocket connection for audio streaming
      await this.setupWebSocket();

      return true;
    } catch (err) {
      console.error("FastRTC connection error:", err);
      this.disconnect();
      return false;
    }
  }

  private async setupWebSocket(): Promise<void> {
    try {
      this.clientId = `client-${Date.now()}`;
      const wsUrl = `${this.serverUrl}/ws/audio/${this.clientId}`;

      this.websocket = new WebSocket(wsUrl);

      this.websocket.onopen = () => {
        console.log("WebSocket connected for audio streaming");
        // Send start streaming message
        if (this.websocket && this.webrtcId) {
          this.websocket.send(
            JSON.stringify({
              type: "start_streaming",
              webrtc_id: this.webrtcId,
            })
          );
        }
      };

      this.websocket.onmessage = (event: MessageEvent) => {
        try {
          const message = JSON.parse(event.data) as FastRTCMessage;
          console.log("WebSocket message received:", message);

          // Handle different message types according to FastRTC API
          switch (message.type) {
            case "send_input":
              console.log("Input data received:", message.data);
              break;
            case "fetch_output":
              console.log("Output data received:", message.data);
              break;
            case "stopword":
              console.log("Stopword detected:", message.data);
              break;
            case "error":
              console.error("FastRTC error:", message.data);
              break;
            case "warning":
              console.warn("FastRTC warning:", message.data);
              break;
            case "log":
              console.log("FastRTC log:", message.data);
              break;
            default:
              console.log("Unknown message type:", message.type);
          }
        } catch (err) {
          console.error("Error parsing WebSocket message:", err);
        }
      };

      this.websocket.onerror = (error: Event) => {
        console.error("WebSocket error:", error);
      };

      this.websocket.onclose = () => {
        console.log("WebSocket connection closed");
      };
    } catch (err) {
      console.error("Failed to setup WebSocket:", err);
      throw err;
    }
  }

  disconnect() {
    if (this.websocket) {
      this.websocket.close();
      this.websocket = null;
    }
    if (this.peerConnection) {
      this.peerConnection.close();
      this.peerConnection = null;
    }
    this.webrtcId = null;
    this.clientId = null;
  }

  getWebrtcId(): string | null {
    return this.webrtcId;
  }

  isConnected(): boolean {
    return (
      this.peerConnection !== null &&
      this.peerConnection.connectionState === "connected"
    );
  }

  sendAudioData(audioData: ArrayBuffer): boolean {
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      this.websocket.send(audioData);
      return true;
    }
    return false;
  }

  sendMessage(message: FastRTCMessage): boolean {
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      this.websocket.send(JSON.stringify(message));
      return true;
    }
    return false;
  }
}
