"use client";

import AudioVisualizer from "@/components/AudioVisualizer";
import VolumeMeter from "@/components/VolumeMeter";
import { FastRTCConnection } from "@/lib/fastrtc";
import { Loader2, Mic, MicOff } from "lucide-react";
import { useRef, useState } from "react";

export default function Home() {
  const [isRecording, setIsRecording] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("Click to start recording");

  const fastRTCRef = useRef<FastRTCConnection | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);

  // FastRTC server configuration
  const FASTRTC_SERVER =
    process.env.NEXT_PUBLIC_FASTRTC_SERVER || "ws://localhost:8000";

  const requestMicrophonePermission = async (): Promise<boolean> => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => track.stop()); // Stop the test stream
      setHasPermission(true);
      setError(null);
      return true;
    } catch (err) {
      setHasPermission(false);
      setError(
        "Microphone permission denied. Please allow microphone access and try again."
      );
      return false;
    }
  };

  const connectToFastRTC = async (): Promise<boolean> => {
    try {
      setIsConnecting(true);
      setStatus("Connecting to FastRTC server...");

      // Get audio stream
      const audioStream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });

      audioStreamRef.current = audioStream;

      // Create FastRTC connection
      fastRTCRef.current = new FastRTCConnection(FASTRTC_SERVER);

      // Connect to FastRTC server
      const connected = await fastRTCRef.current.connect(audioStream);

      if (!connected) {
        throw new Error("Failed to establish connection");
      }

      setStatus("Connected to FastRTC server");
      setIsConnecting(false);
      return true;
    } catch (err) {
      console.error("FastRTC connection error:", err);
      setError(
        `Failed to connect to FastRTC server: ${
          err instanceof Error ? err.message : "Unknown error"
        }`
      );
      setIsConnecting(false);
      return false;
    }
  };

  const startRecording = async () => {
    if (hasPermission === false) {
      const granted = await requestMicrophonePermission();
      if (!granted) return;
    }

    if (hasPermission === null) {
      const granted = await requestMicrophonePermission();
      if (!granted) return;
    }

    setError(null);
    setStatus("Connecting...");

    const connected = await connectToFastRTC();
    if (!connected) return;

    setIsRecording(true);
    setStatus("Recording... Click to stop");
  };

  const stopRecording = () => {
    if (fastRTCRef.current) {
      fastRTCRef.current.disconnect();
      fastRTCRef.current = null;
    }

    if (audioStreamRef.current) {
      audioStreamRef.current
        .getTracks()
        .forEach((track: MediaStreamTrack) => track.stop());
      audioStreamRef.current = null;
    }

    setIsRecording(false);
    setStatus("Click to start recording");
  };

  const handleMicrophoneClick = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <div className='min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4'>
      <div className='max-w-md w-full'>
        <div className='bg-white rounded-2xl shadow-xl p-8 text-center'>
          <h1 className='text-3xl font-bold text-gray-800 mb-2'>
            FastRTC Audio
          </h1>
          <p className='text-gray-600 mb-8'>
            Real-time audio streaming interface
          </p>

          {/* Volume Meter */}
          <VolumeMeter
            audioStream={audioStreamRef.current}
            isRecording={isRecording}
          />

          {/* Audio Visualizer */}
          <AudioVisualizer
            audioStream={audioStreamRef.current}
            isRecording={isRecording}
          />

          {/* Microphone Button */}
          <div className='mb-6 flex justify-center'>
            <button
              type='button'
              aria-label='Toggle microphone'
              title='Toggle microphone'
              onClick={handleMicrophoneClick}
              disabled={isConnecting}
              className={`
                relative w-24 h-24 rounded-full flex items-center justify-center
                transition-all duration-300 ease-in-out transform hover:scale-105
                ${
                  isRecording
                    ? "bg-red-500 hover:bg-red-600 shadow-lg shadow-red-200"
                    : "bg-blue-500 hover:bg-blue-600 shadow-lg shadow-blue-200"
                }
                ${
                  isConnecting
                    ? "opacity-50 cursor-not-allowed"
                    : "cursor-pointer"
                }
              `}
            >
              {isConnecting ? (
                <Loader2 className='w-8 h-8 text-white animate-spin' />
              ) : isRecording ? (
                <MicOff className='w-8 h-8 text-white' />
              ) : (
                <Mic className='w-8 h-8 text-white' />
              )}

              {/* Recording indicator */}
              {isRecording && (
                <div className='absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full animate-pulse' />
              )}
            </button>
          </div>

          {/* Status */}
          <div className='mb-4'>
            <p
              className={`text-sm font-medium ${
                isRecording
                  ? "text-green-600"
                  : error
                  ? "text-red-600"
                  : "text-gray-600"
              }`}
            >
              {status}
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className='mb-4 p-3 bg-red-50 border border-red-200 rounded-lg'>
              <p className='text-sm text-red-600'>{error}</p>
            </div>
          )}

          {/* Permission Status */}
          {hasPermission !== null && (
            <div className='text-xs text-gray-500'>
              Microphone: {hasPermission ? "✅ Allowed" : "❌ Denied"}
            </div>
          )}

          {/* Instructions */}
          <div className='mt-6 text-xs text-gray-500'>
            <p>Click the microphone to start real-time audio streaming</p>
            <p>Audio will be sent to the FastRTC server for processing</p>
          </div>
        </div>
      </div>
    </div>
  );
}
