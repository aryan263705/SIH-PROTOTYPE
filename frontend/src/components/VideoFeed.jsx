import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Eye, 
  ShieldAlert, 
  AlertTriangle, 
  CheckCircle2, 
  Camera,
  Activity,
  RotateCcw,
  RefreshCw
} from 'lucide-react';
import { setVirtualBorder, setRestrictedZone } from '../services/api';

export default function VideoFeed({
  cameraSource,
  isCameraRunning,
  drawMode,
  setDrawMode,
  setPolygonPointsCount,
  borderLine,
  setBorderLine,
  roiPolygon,
  setRoiPolygon,
  telemetry
}) {
  const containerRef = useRef(null);
  const [mjpegError, setMjpegError] = useState(false);
  const [feedNonce, setFeedNonce] = useState(0);
  const prevCameraOnlineRef = useRef(false);

  const reloadFeed = useCallback(() => {
    setFeedNonce((n) => n + 1);
    setMjpegError(false);
  }, []);

  const prevSourceRef = useRef(cameraSource);
  useEffect(() => {
    if (prevSourceRef.current !== cameraSource) {
      prevSourceRef.current = cameraSource;
      reloadFeed();
    }
  }, [cameraSource, reloadFeed]);

  // Self-healing: if camera transitions to online while in error state, rebind
  useEffect(() => {
    const isNowOnline = Boolean(telemetry?.camera_online);
    if (isNowOnline && (!prevCameraOnlineRef.current && mjpegError)) {
      reloadFeed();
    }
    prevCameraOnlineRef.current = isNowOnline;
  }, [telemetry?.camera_online, mjpegError, reloadFeed]);

  // Tab switch recovery: if user returns to tab and the feed was disconnected, rebind
  useEffect(() => {
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible' && mjpegError) {
        reloadFeed();
      }
    };
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => document.removeEventListener('visibilitychange', onVisibilityChange);
  }, [mjpegError, reloadFeed]);

  const [tempBorderPoints, setTempBorderPoints] = useState([]);
  const [tempRoiPoints, setTempRoiPoints] = useState([]);

  useEffect(() => {
    setPolygonPointsCount(tempRoiPoints.length);
  }, [tempRoiPoints, setPolygonPointsCount]);

  const handleViewportClick = async (e) => {
    if (!drawMode || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;
    const normX = Math.max(0.0, Math.min(1.0, clickX / rect.width));
    const normY = Math.max(0.0, Math.min(1.0, clickY / rect.height));

    if (drawMode === 'border') {
      const nextPoints = [...tempBorderPoints, [normX, normY]];
      if (nextPoints.length === 1) {
        setTempBorderPoints(nextPoints);
      } else if (nextPoints.length >= 2) {
        const pt1 = nextPoints[0];
        const pt2 = nextPoints[1];
        setBorderLine([pt1, pt2]);
        setTempBorderPoints([]);
        setDrawMode(null);
        await setVirtualBorder(pt1, pt2);
      }
    } else if (drawMode === 'roi') {
      setTempRoiPoints([...tempRoiPoints, [normX, normY]]);
    }
  };

  const closePolygon = async () => {
    if (tempRoiPoints.length >= 3) {
      setRoiPolygon(tempRoiPoints);
      await setRestrictedZone(tempRoiPoints);
      setTempRoiPoints([]);
      setDrawMode(null);
    }
  };

  useEffect(() => {
    window.__closeSurveillancePolygon = closePolygon;
    return () => {
      delete window.__closeSurveillancePolygon;
    };
  }, [tempRoiPoints]);

  const currentThreat = telemetry?.threat_level || 'NORMAL';
  const activePersons = telemetry?.persons || [];
  const livePersons = activePersons.filter((p) => p.track_status !== 'LOST');
  const activeFps = telemetry?.fps || 0;
  const cameraOnline = Boolean(telemetry?.camera_online);
  const sourceStatus = telemetry?.source_status || 'OFFLINE';

  const getThreatBadge = () => {
    if (currentThreat === 'ALERT') {
      return (
        <div className="flex items-center gap-1.5 px-3 py-1 bg-red-950/90 border border-red-500/80 rounded-md text-red-400 font-mono text-xs font-bold uppercase tracking-wider animate-pulse shadow-md shadow-red-500/30">
          <ShieldAlert className="w-4 h-4" />
          POSSIBLE INTRUSION
        </div>
      );
    } else if (currentThreat === 'SUSPICIOUS') {
      return (
        <div className="flex items-center gap-1.5 px-3 py-1 bg-amber-950/90 border border-amber-500/70 rounded-md text-amber-400 font-mono text-xs font-bold uppercase tracking-wider">
          <AlertTriangle className="w-4 h-4" />
          SUSPICIOUS — NO ALERT YET
        </div>
      );
    }
    return (
      <div className="flex items-center gap-1.5 px-3 py-1 bg-emerald-950/80 border border-emerald-500/50 rounded-md text-emerald-400 font-mono text-xs font-semibold uppercase tracking-wider">
        <CheckCircle2 className="w-4 h-4" />
        NORMAL — NO ACTIVE THREATS
      </div>
    );
  };

  return (
    <div className="bg-slate-900/95 rounded-xl border border-slate-800 overflow-hidden shadow-2xl flex flex-col h-full">
      <div className="px-4 py-2.5 bg-slate-950 border-b border-slate-800 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Eye className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-bold text-slate-100 uppercase tracking-wider font-mono">
            LIVE SURVEILLANCE VIEWPORT
          </span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/60 text-cyan-400 border border-cyan-800/60 uppercase">
            {cameraSource === 'webcam' ? 'LAPTOP WEBCAM' : (cameraSource === 'mobile' ? 'MOBILE STREAM' : 'DEMO VIDEO')}
          </span>
          <button
            onClick={reloadFeed}
            title="Reconnect/Reload Video Feed"
            className="p-1 text-slate-400 hover:text-cyan-400 hover:bg-slate-800/80 rounded transition cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
        <div>
          {getThreatBadge()}
        </div>
      </div>

      <div 
        ref={containerRef}
        onClick={handleViewportClick}
        className={`relative flex-1 bg-black flex items-center justify-center min-h-[420px] lg:min-h-[520px] overflow-hidden select-none ${
          drawMode ? 'cursor-crosshair' : 'cursor-default'
        }`}
      >
        <div className="absolute inset-0 pointer-events-none z-20">
          <div className="absolute top-3.5 left-3.5 w-5 h-5 border-t-2 border-l-2 border-cyan-500/70" />
          <div className="absolute top-3.5 right-3.5 w-5 h-5 border-t-2 border-r-2 border-cyan-500/70" />
          <div className="absolute bottom-3.5 left-3.5 w-5 h-5 border-b-2 border-l-2 border-cyan-500/70" />
          <div className="absolute bottom-3.5 right-3.5 w-5 h-5 border-b-2 border-r-2 border-cyan-500/70" />

          <div className="absolute top-4 left-4 text-[11px] font-mono text-slate-300 bg-slate-950/70 px-2.5 py-1 rounded border border-slate-800 backdrop-blur-xs flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${cameraOnline ? 'bg-emerald-400 animate-pulse' : 'bg-red-500'}`} />
            <span>CAM_01 • {cameraOnline ? 'CAMERA ONLINE' : (sourceStatus === 'RECONNECTING' ? 'CONNECTION LOST' : 'CAMERA OFFLINE')}</span>
          </div>

          <div className="absolute top-4 right-4 text-[11px] font-mono text-slate-200 bg-slate-950/70 px-2.5 py-1 rounded border border-slate-800 backdrop-blur-xs flex items-center gap-3">
            <span>FPS: <strong className="text-cyan-400">{activeFps}</strong></span>
            <span>PERSONS: <strong className="text-emerald-400">{livePersons.length}</strong></span>
          </div>
        </div>

        <div className="w-full h-full flex items-center justify-center relative">
          {!mjpegError ? (
            <img
              src={`/api/video/feed?n=${feedNonce}`}
              alt="Live Stream Feed"
              onError={() => setMjpegError(true)}
              onLoad={() => setMjpegError(false)}
              className="w-full h-full object-contain select-none"
            />
          ) : (
            <div className="text-center p-6 max-w-md z-30">
              <div className="w-12 h-12 rounded-full bg-slate-800 border border-slate-700 text-cyan-400 flex items-center justify-center mx-auto mb-3">
                {cameraSource === 'webcam' ? <Camera className="w-6 h-6" /> : <Activity className="w-6 h-6" />}
              </div>
              <h3 className="text-sm font-semibold text-slate-200 mb-1">
                {telemetry?.camera_message || 'Stream Standby / Connecting'}
              </h3>
              <p className="text-xs text-slate-400 mb-3">
                {telemetry?.error_message || 'Connecting to camera. For mobile cameras, enter the stream URL and click CONNECT.'}
              </p>
              <button
                onClick={reloadFeed}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded text-xs font-mono font-semibold transition cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                RECONNECT FEED
              </button>
            </div>
          )}
        </div>

        <svg className="absolute inset-0 w-full h-full pointer-events-none z-10">
          <defs>
            <linearGradient id="restrictedGlow" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="rgba(239, 68, 68, 0.35)" />
              <stop offset="100%" stopColor="rgba(239, 68, 68, 0.08)" />
            </linearGradient>
          </defs>

          {(roiPolygon && roiPolygon.length >= 3) && (
            <g>
              <polygon
                points={roiPolygon.map(p => `${p[0] * 100}% ${p[1] * 100}%`).join(', ')}
                fill="url(#restrictedGlow)"
                stroke="#ef4444"
                strokeWidth="2.5"
                strokeDasharray="6,4"
              />
              {roiPolygon.map((p, idx) => (
                <circle
                  key={idx}
                  cx={`${p[0] * 100}%`}
                  cy={`${p[1] * 100}%`}
                  r="4"
                  fill="#ef4444"
                  stroke="#ffffff"
                  strokeWidth="1.5"
                />
              ))}
              <text
                x={`${(roiPolygon.reduce((acc, p) => acc + p[0], 0) / roiPolygon.length) * 100}%`}
                y={`${(roiPolygon.reduce((acc, p) => acc + p[1], 0) / roiPolygon.length) * 100}%`}
                fill="#fca5a5"
                fontSize="11"
                fontWeight="bold"
                fontFamily="monospace"
                textAnchor="middle"
              >
                [RESTRICTED ZONE]
              </text>
            </g>
          )}

          {drawMode === 'roi' && tempRoiPoints.length > 0 && (
            <g>
              {tempRoiPoints.map((p, idx) => (
                <circle
                  key={idx}
                  cx={`${p[0] * 100}%`}
                  cy={`${p[1] * 100}%`}
                  r="5"
                  fill="#38bdf8"
                  stroke="#ffffff"
                  strokeWidth="1.5"
                />
              ))}
              {tempRoiPoints.length >= 2 && (
                <polyline
                  points={tempRoiPoints.map(p => `${p[0] * 100}% ${p[1] * 100}%`).join(', ')}
                  fill="none"
                  stroke="#38bdf8"
                  strokeWidth="2"
                  strokeDasharray="4,3"
                />
              )}
            </g>
          )}

          {borderLine && (
            <g>
              <line
                x1={`${borderLine[0][0] * 100}%`}
                y1={`${borderLine[0][1] * 100}%`}
                x2={`${borderLine[1][0] * 100}%`}
                y2={`${borderLine[1][1] * 100}%`}
                stroke="#f59e0b"
                strokeWidth="3.5"
                strokeDasharray="8,5"
              />
              <text
                x={`${((borderLine[0][0] + borderLine[1][0]) / 2) * 100}%`}
                y={`${((borderLine[0][1] + borderLine[1][1]) / 2) * 100 - 1.5}%`}
                fill="#fbbf24"
                fontSize="12"
                fontWeight="bold"
                fontFamily="monospace"
                textAnchor="middle"
              >
                VIRTUAL BORDER
              </text>
            </g>
          )}

          {drawMode === 'border' && tempBorderPoints.length === 1 && (
            <circle
              cx={`${tempBorderPoints[0][0] * 100}%`}
              cy={`${tempBorderPoints[0][1] * 100}%`}
              r="6"
              fill="#fbbf24"
              stroke="#ffffff"
              strokeWidth="2"
            />
          )}
        </svg>
      </div>

      <div className="px-4 py-2 bg-slate-950 border-t border-slate-800 text-[11px] font-mono text-slate-400 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-4">
          <span>AI ENGINE: <strong className={telemetry?.ai_online ? 'text-emerald-400' : 'text-red-400'}>{telemetry?.ai_online ? 'ONLINE' : 'ERROR'}</strong></span>
          <span>TRACKING: <strong className="text-cyan-400">{telemetry?.tracking_status || 'READY'}</strong></span>
          <span>BORDER: <strong className={borderLine ? 'text-amber-400' : 'text-slate-500'}>{borderLine ? `${Math.round((telemetry?.boundary_position ?? 0.65) * 100)}%` : 'NONE'}</strong></span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${cameraOnline ? 'bg-emerald-400' : 'bg-red-400'}`} />
          <span>STATUS: {cameraOnline ? 'MONITORING ACTIVE' : (sourceStatus === 'RECONNECTING' ? 'ATTEMPTING TO RECONNECT' : 'OFFLINE')}</span>
        </div>
      </div>
    </div>
  );
}
