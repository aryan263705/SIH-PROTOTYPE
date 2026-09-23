import React, { useState } from 'react';
import { Camera, Smartphone, Film, Play, Square, Settings, Upload, Check } from 'lucide-react';
import { configureCamera, controlCamera, updateConfig, uploadVideo } from '../services/api';

export default function CameraControl({ telemetry, onConfigChanged }) {
  const [sourceType, setSourceType] = useState(telemetry?.source_type || 'demo');
  const [mobileUrl, setMobileUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  
  // Sliders state
  const [scoreThresh, setScoreThresh] = useState(65);
  const [persistenceSecs, setPersistenceSecs] = useState(2.0);
  const [confThresh, setConfThresh] = useState(0.45);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleSourceChange = async (type) => {
    setSourceType(type);
    setLoading(true);
    try {
      const path = type === 'mobile' ? mobileUrl : (type === 'webcam' ? '0' : 'border_patrol_demo.mp4');
      await configureCamera(type, path);
      if (onConfigChanged) onConfigChanged();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleApplyMobileUrl = async () => {
    if (!mobileUrl) return;
    setLoading(true);
    try {
      await configureCamera('mobile', mobileUrl);
      if (onConfigChanged) onConfigChanged();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleStreamAction = async (action) => {
    setLoading(true);
    try {
      await controlCamera(action);
      if (onConfigChanged) onConfigChanged();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveThresholds = async () => {
    try {
      await updateConfig({
        posture_score_threshold: parseFloat(scoreThresh),
        persistence_seconds: parseFloat(persistenceSecs),
        confidence_threshold: parseFloat(confThresh)
      });
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 2500);
      if (onConfigChanged) onConfigChanged();
    } catch (err) {
      console.error(err);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await uploadVideo(file);
      await configureCamera('demo', file.name);
      setSourceType('demo');
      if (onConfigChanged) onConfigChanged();
    } catch (err) {
      console.error('Failed to upload video:', err);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
        <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
          <Camera className="w-4 h-4 text-cyan-400" />
          Camera Source & AI Parameters
        </h3>
        <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 border border-cyan-800/60 px-2 py-0.5 rounded uppercase">
          {telemetry?.camera_online ? 'CONNECTED' : 'STANDBY'}
        </span>
      </div>

      {/* Source Selector Buttons */}
      <div className="grid grid-cols-3 gap-2">
        <button
          onClick={() => handleSourceChange('demo')}
          disabled={loading}
          className={`flex flex-col items-center justify-center p-2.5 rounded-lg border text-xs font-medium transition ${
            sourceType === 'demo'
              ? 'bg-blue-600/20 border-blue-500 text-blue-300 font-semibold'
              : 'bg-slate-800/60 border-slate-700 text-slate-400 hover:text-slate-200'
          }`}
        >
          <Film className="w-4 h-4 mb-1" />
          <span>Demo Video</span>
        </button>

        <button
          onClick={() => handleSourceChange('webcam')}
          disabled={loading}
          className={`flex flex-col items-center justify-center p-2.5 rounded-lg border text-xs font-medium transition ${
            sourceType === 'webcam'
              ? 'bg-blue-600/20 border-blue-500 text-blue-300 font-semibold'
              : 'bg-slate-800/60 border-slate-700 text-slate-400 hover:text-slate-200'
          }`}
        >
          <Camera className="w-4 h-4 mb-1" />
          <span>Laptop Webcam</span>
        </button>

        <button
          onClick={() => handleSourceChange('mobile')}
          disabled={loading}
          className={`flex flex-col items-center justify-center p-2.5 rounded-lg border text-xs font-medium transition ${
            sourceType === 'mobile'
              ? 'bg-blue-600/20 border-blue-500 text-blue-300 font-semibold'
              : 'bg-slate-800/60 border-slate-700 text-slate-400 hover:text-slate-200'
          }`}
        >
          <Smartphone className="w-4 h-4 mb-1" />
          <span>Mobile Phone</span>
        </button>
      </div>

      {/* Mobile URL Input if Mobile selected */}
      {sourceType === 'mobile' && (
        <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
          <label className="text-[11px] font-mono text-slate-300 block">
            Mobile Camera Stream URL:
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="http://192.168.1.15:8080/video"
              value={mobileUrl}
              onChange={(e) => setMobileUrl(e.target.value)}
              className="flex-1 bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-hidden focus:border-cyan-500"
            />
            <button
              onClick={handleApplyMobileUrl}
              disabled={loading || !mobileUrl}
              className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded text-xs font-medium transition"
            >
              Connect
            </button>
          </div>
          <p className="text-[10px] text-slate-400">
            * Use apps like <em>IP Webcam</em> on Android or <em>Live-Reporter</em> on iOS. Ensure phone and laptop are on the same Wi-Fi.
          </p>
        </div>
      )}

      {/* Demo Video upload if Demo selected */}
      {sourceType === 'demo' && (
        <div className="flex items-center justify-between bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-xs">
          <div className="text-[11px] text-slate-400 font-mono">
            Active: <span className="text-slate-200">border_patrol_demo.mp4</span>
          </div>
          <label className="cursor-pointer inline-flex items-center gap-1.5 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded text-[11px] font-medium text-slate-300 transition">
            <Upload className="w-3 h-3" />
            {uploading ? 'Uploading...' : 'Upload Custom MP4'}
            <input
              type="file"
              accept="video/mp4"
              onChange={handleFileUpload}
              className="hidden"
            />
          </label>
        </div>
      )}

      {/* Start / Stop Stream Controls */}
      <div className="flex gap-2">
        <button
          onClick={() => handleStreamAction('start')}
          disabled={loading || telemetry?.camera_online}
          className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-emerald-600/20 border border-emerald-500/50 hover:bg-emerald-600/30 text-emerald-400 rounded-lg text-xs font-semibold uppercase tracking-wider transition disabled:opacity-40"
        >
          <Play className="w-3.5 h-3.5" /> Start Monitoring
        </button>
        <button
          onClick={() => handleStreamAction('stop')}
          disabled={loading || !telemetry?.camera_online}
          className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-red-600/20 border border-red-500/50 hover:bg-red-600/30 text-red-400 rounded-lg text-xs font-semibold uppercase tracking-wider transition disabled:opacity-40"
        >
          <Square className="w-3.5 h-3.5" /> Stop Monitoring
        </button>
      </div>

      {/* Tuning Controls */}
      <div className="border-t border-slate-800/80 pt-3 space-y-3">
        <div className="flex items-center justify-between text-xs font-bold text-slate-300 uppercase tracking-wider">
          <span className="flex items-center gap-1.5">
            <Settings className="w-3.5 h-3.5 text-cyan-400" />
            Detection & Alert Parameters
          </span>
          <button
            onClick={handleSaveThresholds}
            className="flex items-center gap-1 text-[11px] text-cyan-400 hover:text-cyan-300 font-mono"
          >
            {savedSuccess ? <span className="text-emerald-400 flex items-center gap-1"><Check className="w-3 h-3" /> Applied</span> : 'Save Parameters'}
          </button>
        </div>

        {/* Slider 1: Crawling Posture Threshold */}
        <div>
          <div className="flex justify-between text-[11px] font-mono text-slate-400 mb-1">
            <span>Posture Suspicion Trigger:</span>
            <strong className="text-cyan-400">{scoreThresh}%</strong>
          </div>
          <input
            type="range"
            min="40"
            max="90"
            step="1"
            value={scoreThresh}
            onChange={(e) => setScoreThresh(e.target.value)}
            className="w-full accent-cyan-500 h-1 bg-slate-800 rounded-lg cursor-pointer"
          />
        </div>

        {/* Slider 2: Persistence Duration */}
        <div>
          <div className="flex justify-between text-[11px] font-mono text-slate-400 mb-1">
            <span>Alert Persistence Duration:</span>
            <strong className="text-cyan-400">{persistenceSecs}s</strong>
          </div>
          <input
            type="range"
            min="1.0"
            max="5.0"
            step="0.5"
            value={persistenceSecs}
            onChange={(e) => setPersistenceSecs(e.target.value)}
            className="w-full accent-cyan-500 h-1 bg-slate-800 rounded-lg cursor-pointer"
          />
        </div>

        {/* Slider 3: Confidence Threshold */}
        <div>
          <div className="flex justify-between text-[11px] font-mono text-slate-400 mb-1">
            <span>YOLO Person Confidence:</span>
            <strong className="text-cyan-400">{Math.round(confThresh * 100)}%</strong>
          </div>
          <input
            type="range"
            min="0.25"
            max="0.80"
            step="0.05"
            value={confThresh}
            onChange={(e) => setConfThresh(e.target.value)}
            className="w-full accent-cyan-500 h-1 bg-slate-800 rounded-lg cursor-pointer"
          />
        </div>
      </div>
    </div>
  );
}
