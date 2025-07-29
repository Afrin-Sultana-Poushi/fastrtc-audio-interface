"use client";

import { useEffect, useRef, useState } from "react";

interface AudioVisualizerProps {
  audioStream: MediaStream | null;
  isRecording: boolean;
}

export default function AudioVisualizer({
  audioStream,
  isRecording,
}: AudioVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const analyserRef = useRef<AnalyserNode | null>(null);
  const dataArrayRef = useRef<Uint8Array | null>(null);
  const [audioLevel, setAudioLevel] = useState(0);
  const [visualizationType, setVisualizationType] = useState<
    "bars" | "wave" | "circles"
  >("bars");

  useEffect(() => {
    if (!audioStream || !isRecording) {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      return;
    }

    const audioContext = new (window.AudioContext ||
      (window as any).webkitAudioContext)();
    const analyser = audioContext.createAnalyser();
    const source = audioContext.createMediaStreamSource(audioStream);

    analyser.fftSize = 256;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    source.connect(analyser);
    analyserRef.current = analyser;
    dataArrayRef.current = dataArray;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const draw = () => {
      if (!analyserRef.current || !dataArrayRef.current) return;

      analyserRef.current.getByteFrequencyData(dataArrayRef.current);

      // Calculate average audio level
      const average =
        dataArrayRef.current.reduce((a, b) => a + b) /
        dataArrayRef.current.length;
      setAudioLevel(average);

      // Clear canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      switch (visualizationType) {
        case "bars":
          drawBars(ctx, canvas, dataArrayRef.current);
          break;
        case "wave":
          drawWave(ctx, canvas, dataArrayRef.current);
          break;
        case "circles":
          drawCircles(ctx, canvas, dataArrayRef.current);
          break;
      }

      animationRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      audioContext.close();
    };
  }, [audioStream, isRecording, visualizationType]);

  const drawBars = (
    ctx: CanvasRenderingContext2D,
    canvas: HTMLCanvasElement,
    dataArray: Uint8Array
  ) => {
    const barWidth = canvas.width / dataArray.length;
    const barSpacing = 2;

    for (let i = 0; i < dataArray.length; i++) {
      const barHeight = (dataArray[i] / 255) * canvas.height * 0.8;
      const x = i * (barWidth + barSpacing);
      const y = canvas.height - barHeight;

      // Create gradient based on audio level
      const gradient = ctx.createLinearGradient(0, y, 0, canvas.height);
      const intensity = dataArray[i] / 255;

      if (intensity > 0.7) {
        gradient.addColorStop(0, "#ef4444"); // Red for high intensity
        gradient.addColorStop(1, "#dc2626");
      } else if (intensity > 0.4) {
        gradient.addColorStop(0, "#f59e0b"); // Orange for medium intensity
        gradient.addColorStop(1, "#d97706");
      } else {
        gradient.addColorStop(0, "#3b82f6"); // Blue for low intensity
        gradient.addColorStop(1, "#2563eb");
      }

      ctx.fillStyle = gradient;
      ctx.fillRect(x, y, barWidth - barSpacing, barHeight);
    }
  };

  const drawWave = (
    ctx: CanvasRenderingContext2D,
    canvas: HTMLCanvasElement,
    dataArray: Uint8Array
  ) => {
    ctx.beginPath();
    ctx.strokeStyle = "#3b82f6";
    ctx.lineWidth = 2;

    const sliceWidth = canvas.width / dataArray.length;
    let x = 0;

    for (let i = 0; i < dataArray.length; i++) {
      const v = dataArray[i] / 255;
      const y = (v * canvas.height) / 2;

      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }

      x += sliceWidth;
    }

    ctx.lineTo(canvas.width, canvas.height / 2);
    ctx.stroke();
  };

  const drawCircles = (
    ctx: CanvasRenderingContext2D,
    canvas: HTMLCanvasElement,
    dataArray: Uint8Array
  ) => {
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const maxRadius = Math.min(canvas.width, canvas.height) / 2 - 10;

    for (let i = 0; i < dataArray.length; i += 4) {
      const intensity = dataArray[i] / 255;
      const radius = intensity * maxRadius;
      const angle = (i / dataArray.length) * Math.PI * 2;

      const x = centerX + Math.cos(angle) * radius;
      const y = centerY + Math.sin(angle) * radius;

      ctx.beginPath();
      ctx.arc(x, y, 2, 0, Math.PI * 2);

      if (intensity > 0.7) {
        ctx.fillStyle = "#ef4444";
      } else if (intensity > 0.4) {
        ctx.fillStyle = "#f59e0b";
      } else {
        ctx.fillStyle = "#3b82f6";
      }

      ctx.fill();
    }
  };

  // if (!isRecording) {
  //   return null;
  // }

  return (
    <div className='w-full max-w-md mx-auto mb-6'>
      <div className='bg-gray-900 rounded-lg p-4'>
        <div className='text-center mb-2'>
          <span className='text-xs text-gray-400'>Audio Level</span>
          <div className='text-sm font-mono text-green-400'>
            {Math.round(audioLevel)}%
          </div>
        </div>

        {/* Visualization Type Selector */}
        <div className='flex justify-center mb-3 space-x-2'>
          {(["bars", "wave", "circles"] as const).map((type) => (
            <button
              key={type}
              onClick={() => setVisualizationType(type)}
              className={`px-3 py-1 text-xs rounded-full transition-colors ${
                visualizationType === type
                  ? "bg-blue-500 text-white"
                  : "bg-gray-700 text-gray-300 hover:bg-gray-600"
              }`}
            >
              {type.charAt(0).toUpperCase() + type.slice(1)}
            </button>
          ))}
        </div>

        <canvas
          ref={canvasRef}
          width={300}
          height={80}
          className='w-full h-20 bg-gray-800 rounded'
        />
      </div>
    </div>
  );
}
