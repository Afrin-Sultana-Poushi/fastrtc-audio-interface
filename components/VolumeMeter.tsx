"use client";

import { useEffect, useRef, useState } from "react";

interface VolumeMeterProps {
  audioStream: MediaStream | null;
  isRecording: boolean;
}

export default function VolumeMeter({
  audioStream,
  isRecording,
}: VolumeMeterProps) {
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number>();
  const [volume, setVolume] = useState(0);

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

    const updateVolume = () => {
      if (!analyserRef.current) return;

      analyserRef.current.getByteFrequencyData(dataArray);
      const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
      setVolume(average);

      animationRef.current = requestAnimationFrame(updateVolume);
    };

    updateVolume();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      audioContext.close();
    };
  }, [audioStream, isRecording]);

  if (!isRecording) {
    return null;
  }

  const radius = 30;
  const circumference = 2 * Math.PI * radius;
  const strokeDasharray = circumference;
  const strokeDashoffset = circumference - (volume / 255) * circumference;

  const getVolumeColor = (level: number) => {
    if (level > 200) return "#ef4444"; // Red for high volume
    if (level > 150) return "#f59e0b"; // Orange for medium volume
    if (level > 100) return "#10b981"; // Green for good volume
    return "#3b82f6"; // Blue for low volume
  };

  return (
    <div className='flex items-center justify-center mb-4'>
      <div className='relative'>
        <svg className='w-20 h-20 transform -rotate-90'>
          {/* Background circle */}
          <circle
            cx='40'
            cy='40'
            r={radius}
            stroke='#374151'
            strokeWidth='4'
            fill='transparent'
          />
          {/* Progress circle */}
          <circle
            cx='40'
            cy='40'
            r={radius}
            stroke={getVolumeColor(volume)}
            strokeWidth='4'
            fill='transparent'
            strokeDasharray={strokeDasharray}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap='round'
            className='transition-all duration-100'
          />
        </svg>
        <div className='absolute inset-0 flex items-center justify-center'>
          <span className='text-xs font-mono text-gray-300'>
            {Math.round((volume / 255) * 100)}%
          </span>
        </div>
      </div>
    </div>
  );
}
