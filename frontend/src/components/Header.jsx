import React from 'react';
import { Shield, Radio, Activity, Cpu, Layers, LayoutDashboard, Server } from 'lucide-react';

export default function Header({ telemetry, activeTab, setActiveTab }) {
  const isCameraOnline = telemetry?.camera_online;
  const isAiOnline = telemetry?.ai_online;
  const trackingStatus = telemetry?.tracking_status || (telemetry?.tracking_active ? 'TRACKING' : 'READY');
  const isTracking = trackingStatus === 'TRACKING';
  const isEdgeOnline = telemetry?.edge_health?.status === 'ONLINE' || true;

  return (
    <header className="bg-slate-950 border-b border-slate-800/80 px-6 py-3.5 sticky top-0 z-40 shadow-lg">
      <div className="flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Title and Badge */}
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-lg bg-red-600/10 border border-red-500/30 flex items-center justify-center text-red-500 shadow-sm shadow-red-500/20">
            <Shield className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-wider text-slate-100 uppercase">
                AI Border Surveillance
              </h1>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                SIH26187 • AI AVENGERS
              </span>
            </div>
            <p className="text-xs text-slate-400 tracking-wide">
              Intelligent Video Analytics for Existing CCTV Infrastructure
            </p>
          </div>
        </div>

        {/* Live System Indicators */}
        <div className="flex items-center gap-3 md:gap-4 text-xs font-mono flex-wrap justify-center">
          {/* Camera indicator */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-slate-900/90 border border-slate-800">
            <span className={`w-2 h-2 rounded-full ${isCameraOnline ? 'bg-emerald-400 animate-pulse shadow-sm shadow-emerald-400' : 'bg-red-500'}`} />
            <Radio className="w-3.5 h-3.5 text-slate-400" />
            <span className={isCameraOnline ? 'text-emerald-400 font-semibold' : 'text-slate-400'}>
              CAMERA {isCameraOnline ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>

          {/* AI Engine indicator */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-slate-900/90 border border-slate-800">
            <span className={`w-2 h-2 rounded-full ${isAiOnline ? 'bg-emerald-400 shadow-sm shadow-emerald-400' : 'bg-red-500'}`} />
            <Cpu className="w-3.5 h-3.5 text-slate-400" />
            <span className={isAiOnline ? 'text-emerald-400 font-semibold' : 'text-slate-400'}>
              AI ENGINE {isAiOnline ? 'ONLINE' : 'ERROR'}
            </span>
          </div>

          {/* Tracking indicator */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-slate-900/90 border border-slate-800">
            <span className={`w-2 h-2 rounded-full ${isTracking ? 'bg-emerald-400 shadow-sm shadow-emerald-400' : 'bg-amber-500'}`} />
            <Activity className="w-3.5 h-3.5 text-slate-400" />
            <span className={isTracking ? 'text-emerald-400 font-semibold' : 'text-slate-400'}>
              TRACKING {isTracking ? 'ACTIVE' : 'READY'}
            </span>
          </div>

          {/* Edge Node indicator */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-slate-900/90 border border-slate-800" title="Edge Compute Node (Software Heartbeat)">
            <span className={`w-2 h-2 rounded-full ${isEdgeOnline ? 'bg-cyan-400 shadow-sm shadow-cyan-400 animate-pulse' : 'bg-red-500'}`} />
            <Server className="w-3.5 h-3.5 text-cyan-400" />
            <span className={isEdgeOnline ? 'text-cyan-400 font-semibold' : 'text-slate-400'}>
              EDGE NODE {isEdgeOnline ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-1.5 bg-slate-900 p-1 rounded-lg border border-slate-800">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'dashboard'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <LayoutDashboard className="w-3.5 h-3.5" />
            Command Center
          </button>
          <button
            onClick={() => setActiveTab('architecture')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'architecture'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            Architecture
          </button>
        </div>
      </div>
    </header>
  );
}
