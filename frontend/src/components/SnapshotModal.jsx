const API_BASE = (import.meta.env.VITE_API_BASE_URL || window.location.origin).replace(/\/$/, '');

import React, { useState } from 'react';
import { X, ShieldAlert, Calendar, Clock, User, Award, Film, Image as ImageIcon, Video } from 'lucide-react';

export default function SnapshotModal({ snapshot, onClose }) {
  if (!snapshot) return null;

  // Extract replay path if available
  let replayPath = snapshot.replay || null;
  if (!replayPath && snapshot.details && snapshot.details.includes('Replay: ')) {
    replayPath = snapshot.details.split('Replay: ')[1].split(' | ')[0].trim();
  }

  const resolveMediaPath = (raw) => {
    if (!raw) return null;
    let s = String(raw).trim();
    s = s.replace(/^\/?snapshots\//, '').replace(/^\//, '');
    return `${API_BASE}/snapshots/${s}`;
  };

  const snapshotSrc = resolveMediaPath(snapshot.snapshot || snapshot.snapshot_path);
  const videoSrc = resolveMediaPath(replayPath);

  const [activeTab, setActiveTab] = useState(replayPath && snapshot.initialTab === 'replay' ? 'replay' : 'snapshot');
  const [videoError, setVideoError] = useState(false);
  const [imageError, setImageError] = useState(false);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-3xl w-full overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-3.5 bg-slate-950 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <ShieldAlert className="w-5 h-5 text-red-500" />
            <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider font-mono">
              EVIDENCE INSPECTION: {snapshot.alert_type || snapshot.event_type || 'INCIDENT'}
            </h2>
          </div>

          <div className="flex items-center gap-2">
            {/* View Switcher Tabs */}
            <div className="flex bg-slate-900 p-0.5 rounded-lg border border-slate-800 text-xs font-mono">
              <button
                onClick={() => setActiveTab('snapshot')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition ${
                  activeTab === 'snapshot'
                    ? 'bg-blue-600 text-white font-bold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <ImageIcon className="w-3.5 h-3.5" /> Snapshot
              </button>
              {videoSrc ? (
                <button
                  onClick={() => {
                    setActiveTab('replay');
                    setVideoError(false);
                  }}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition ${
                    activeTab === 'replay'
                      ? 'bg-cyan-600 text-white font-bold'
                      : 'text-cyan-400 hover:text-white'
                  }`}
                >
                  <Film className="w-3.5 h-3.5" /> Event Replay
                </button>
              ) : (
                <span className="px-2 py-1 text-[10px] text-slate-600 font-mono flex items-center gap-1">
                  <Film className="w-3 h-3" /> No Replay
                </span>
              )}
            </div>

            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-100 p-1 rounded-md hover:bg-slate-800 transition ml-2"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Media Viewer Area */}
        <div className="relative bg-black flex-1 flex items-center justify-center min-h-[320px] max-h-[500px] overflow-hidden p-2">
          {activeTab === 'replay' && videoSrc ? (
            <div className="w-full h-full flex flex-col items-center justify-center relative">
              <video
                key={videoSrc}
                src={videoSrc}
                controls
                autoPlay
                loop
                playsInline
                onError={() => setVideoError(true)}
                className="w-full h-full object-contain rounded border border-slate-800"
              >
                Your browser does not support HTML5 video playback.
              </video>
              {videoError && (
                <div className="absolute inset-0 bg-slate-950/95 flex flex-col items-center justify-center p-4 text-center">
                  <Film className="w-8 h-8 text-amber-400 mb-2" />
                  <p className="text-xs text-slate-200 font-mono mb-1">HTML5 Video Playback Notice</p>
                  <p className="text-[11px] text-slate-400 font-mono mb-3">Browser cannot directly decode this clip.</p>
                  <a
                    href={videoSrc}
                    download
                    className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded text-xs font-mono font-semibold transition"
                  >
                    DOWNLOAD RAW MP4
                  </a>
                </div>
              )}
            </div>
          ) : (
            <div className="w-full h-full flex items-center justify-center relative">
              {snapshotSrc && !imageError ? (
                <img
                  key={snapshotSrc}
                  src={snapshotSrc}
                  alt="Forensic Evidence Capture"
                  onError={() => setImageError(true)}
                  className="w-full h-full object-contain rounded border border-slate-800"
                />
              ) : (
                <div className="text-center p-6">
                  <ImageIcon className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                  <p className="text-xs text-slate-400 font-mono">No snapshot image available for this event record.</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Evidence Telemetry Details Footer */}
        <div className="p-4 bg-slate-950/90 border-t border-slate-800 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
          <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
            <span className="text-slate-400 flex items-center gap-1 text-[11px] mb-0.5">
              <User className="w-3 h-3 text-cyan-400" /> TARGET ID
            </span>
            <strong className="text-slate-200 text-sm">#{snapshot.person_id}</strong>
            {snapshot.confidence && (
              <span className="text-[11px] text-cyan-400 ml-1.5 font-bold">({snapshot.confidence}%)</span>
            )}
          </div>

          <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
            <span className="text-slate-400 flex items-center gap-1 text-[11px] mb-0.5">
              <Award className="w-3 h-3 text-red-400" /> THREAT SCORE
            </span>
            <strong className="text-red-400 text-sm">{snapshot.behavior_score || snapshot.score}%</strong>
          </div>

          <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
            <span className="text-slate-400 flex items-center gap-1 text-[11px] mb-0.5">
              <Clock className="w-3 h-3 text-amber-400" /> TIMESTAMP
            </span>
            <strong className="text-slate-200">{snapshot.timestamp}</strong>
          </div>

          <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
            <span className="text-slate-400 flex items-center gap-1 text-[11px] mb-0.5">
              <Calendar className="w-3 h-3 text-emerald-400" /> STATUS
            </span>
            <strong className="text-emerald-400">{snapshot.status || 'LOGGED'}</strong>
          </div>

          {(snapshot.reason || snapshot.direction || snapshot.details) && (
            <div className="col-span-2 sm:col-span-4 bg-slate-900 p-2.5 rounded border border-slate-800 text-[11px] text-slate-300">
              {snapshot.reason && <div>Reason: <strong className="text-slate-100">{snapshot.reason}</strong></div>}
              {snapshot.direction && <div>Direction: <strong className="text-slate-100">{snapshot.direction}</strong></div>}
              {snapshot.persistence_seconds != null && <div>Persistence: <strong className="text-slate-100">{snapshot.persistence_seconds}s</strong></div>}
              {replayPath && (
                <div className="text-[10px] text-cyan-400 font-mono mt-1">
                  Replay Video: {replayPath}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
