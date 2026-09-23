import React, { useState } from 'react';
import { 
  Camera, 
  Smartphone, 
  Film, 
  Play, 
  Square, 
  Slash, 
  Pentagon, 
  Trash2, 
  RotateCcw,
  Check,
  AlertCircle,
  Scan
} from 'lucide-react';
import { clearZones, resetDemo, configureCamera } from '../services/api';

export default function OperatorToolbar({
  cameraSource,
  onSourceChange,
  isCameraRunning,
  onToggleCamera,
  drawMode,
  setDrawMode,
  polygonPointsCount,
  onClosePolygon,
  onClearZones,
  onResetDemo,
  mobileUrl,
  setMobileUrl,
  onConnectMobile,
  boundaryPosition = 65,
  onBoundaryChange,
  wsConnected,
  showMotionRoi = false,
  onToggleMotionRoi,
  currentModel = 'yolov8s.pt',
  onSwitchModel
}) {
  const [showMobileInput, setShowMobileInput] = useState(false);

  const handleSourceSelect = (e) => {
    const src = e.target.value;
    onSourceChange(src);
    if (src === 'mobile') {
      setShowMobileInput(true);
    } else {
      setShowMobileInput(false);
    }
  };

  return (
    <div className="bg-slate-900/95 border border-slate-800 rounded-xl p-3.5 shadow-xl space-y-3">
      {/* Top Controls Row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Source Dropdown, Model Dropdown & Start/Stop */}
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
            <span className="text-[11px] font-mono text-slate-400 uppercase font-semibold">SOURCE:</span>
            <select
              value={cameraSource}
              onChange={handleSourceSelect}
              className="bg-transparent text-xs font-mono font-bold text-cyan-400 focus:outline-hidden cursor-pointer"
            >
              <option value="webcam" className="bg-slate-900 text-slate-200">Laptop Webcam (Live)</option>
              <option value="mobile" className="bg-slate-900 text-slate-200">Mobile Camera (IP Stream)</option>
              <option value="demo" className="bg-slate-900 text-slate-200">Video File (Demo Mode)</option>
            </select>
          </div>

          <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
            <span className="text-[11px] font-mono text-slate-400 uppercase font-semibold">AI MODEL:</span>
            <select
              value={currentModel}
              onChange={(e) => onSwitchModel && onSwitchModel(e.target.value)}
              className="bg-transparent text-xs font-mono font-bold text-amber-400 focus:outline-hidden cursor-pointer"
            >
              <option value="yolov8s.pt" className="bg-slate-900 text-slate-200">High Accuracy (YOLOv8s • 91%+)</option>
              <option value="yolov8n.pt" className="bg-slate-900 text-slate-200">Max Speed (YOLOv8n • Fast)</option>
            </select>
          </div>

          <button
            onClick={onToggleCamera}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-mono font-bold uppercase transition ${
              isCameraRunning
                ? 'bg-red-950/80 border border-red-500/60 text-red-400 hover:bg-red-900/50'
                : 'bg-emerald-950/80 border border-emerald-500/60 text-emerald-400 hover:bg-emerald-900/50'
            }`}
          >
            {isCameraRunning ? <Square className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            {isCameraRunning ? 'STOP CAMERA' : 'START CAMERA'}
          </button>
        </div>

        {/* Tactical Border & Zone Defining Toolbar */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Define Virtual Border Button */}
          <button
            onClick={() => setDrawMode(drawMode === 'border' ? null : 'border')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-bold uppercase border transition ${
              drawMode === 'border'
                ? 'bg-amber-500/20 border-amber-400 text-amber-300 ring-2 ring-amber-500/30'
                : 'bg-slate-800/80 border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800'
            }`}
            title="Click 2 points on video to create a Virtual Border Line"
          >
            <Slash className="w-3.5 h-3.5 text-amber-400" />
            DEFINE BORDER
          </button>

          {/* Define ROI Polygon Button */}
          <button
            onClick={() => setDrawMode(drawMode === 'roi' ? null : 'roi')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-bold uppercase border transition ${
              drawMode === 'roi'
                ? 'bg-red-500/20 border-red-400 text-red-300 ring-2 ring-red-500/30'
                : 'bg-slate-800/80 border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800'
            }`}
            title="Click multiple points on video to draw a polygon Restricted Zone"
          >
            <Pentagon className="w-3.5 h-3.5 text-red-400" />
            DEFINE RESTRICTED ZONE
          </button>

          {/* Toggle Show Motion ROI Debug Box */}
          <button
            onClick={onToggleMotionRoi}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-bold uppercase border transition ${
              showMotionRoi
                ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 ring-2 ring-cyan-500/30'
                : 'bg-slate-800/80 border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800'
            }`}
            title="Toggle visual bounding box around moving Region-of-Interest (Edge Optimization)"
          >
            <Scan className="w-3.5 h-3.5 text-cyan-400" />
            SHOW MOTION ROI {showMotionRoi ? '● ON' : '○ OFF'}
          </button>

          {/* Close Polygon Button (only when drawing ROI) */}
          {drawMode === 'roi' && polygonPointsCount >= 3 && (
            <button
              onClick={onClosePolygon}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-bold uppercase bg-emerald-600 hover:bg-emerald-500 text-white animate-pulse transition"
            >
              <Check className="w-3.5 h-3.5" /> CLOSE ZONE ({polygonPointsCount} PTS)
            </button>
          )}

          {/* Clear Zones */}
          <button
            onClick={onClearZones}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium border border-slate-800 bg-slate-950 text-slate-400 hover:text-red-400 hover:border-red-900 transition"
            title="Clear active border line and ROI polygon"
          >
            <Trash2 className="w-3.5 h-3.5" /> CLEAR ZONES
          </button>

          {/* Reset Demo */}
          <button
            onClick={onResetDemo}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium border border-slate-800 bg-slate-950 text-slate-400 hover:text-cyan-400 hover:border-cyan-900 transition"
            title="Reset active zones, alerts, and incident history for fresh demonstration"
          >
            <RotateCcw className="w-3.5 h-3.5" /> RESET DEMO
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 bg-slate-950 px-3 py-2 rounded-lg border border-slate-800">
        <span className="text-[11px] font-mono text-slate-400 uppercase font-semibold">Boundary Position:</span>
        <input
          type="range"
          min="20"
          max="85"
          value={boundaryPosition}
          onChange={(e) => onBoundaryChange && onBoundaryChange(Number(e.target.value))}
          className="flex-1 min-w-[160px] accent-amber-400"
        />
        <span className="text-xs font-mono font-bold text-amber-400 w-10">{boundaryPosition}%</span>
        <span className="text-[10px] font-mono text-slate-500">
          Horizontal virtual border • monitored TOP → BOTTOM
        </span>
        {typeof wsConnected === 'boolean' && (
          <span className={`text-[10px] font-mono ${wsConnected ? 'text-emerald-400' : 'text-slate-500'}`}>
            LIVE WS: {wsConnected ? 'ON' : 'POLL'}
          </span>
        )}
      </div>

      {cameraSource === 'mobile' && (
        <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 flex flex-col sm:flex-row items-center gap-3">
          <div className="flex items-center gap-2 text-xs font-mono text-slate-300 whitespace-nowrap">
            <Smartphone className="w-4 h-4 text-cyan-400" />
            <span>Mobile Camera Stream URL:</span>
          </div>
          <div className="flex flex-1 w-full gap-2">
            <input
              type="text"
              placeholder="http://192.168.1.15:8080/video"
              value={mobileUrl}
              onChange={(e) => setMobileUrl(e.target.value)}
              className="flex-1 bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-hidden focus:border-cyan-500"
            />
            <button
              onClick={onConnectMobile}
              className="px-4 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded text-xs font-mono font-bold uppercase transition"
            >
              CONNECT
            </button>
          </div>
        </div>
      )}

      {/* Active Drawing Mode Guidance Prompt */}
      {drawMode && (
        <div className="bg-amber-950/40 border border-amber-500/50 px-3.5 py-2 rounded-lg flex items-center justify-between text-xs font-mono text-amber-300 animate-in fade-in">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-400" />
            <span>
              {drawMode === 'border'
                ? 'MODE: DEFINE VIRTUAL BORDER — Click two points on the surveillance video to create the boundary line.'
                : `MODE: DEFINE RESTRICTED ZONE — Click points to outline polygon (${polygonPointsCount} points so far). Click [CLOSE ZONE] when finished.`}
            </span>
          </div>
          <button
            onClick={() => setDrawMode(null)}
            className="text-[11px] text-slate-400 hover:text-slate-200 uppercase underline"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
