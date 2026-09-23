import React from 'react';
import { 
  Activity, 
  Users, 
  Slash, 
  Pentagon, 
  Cpu, 
  Server, 
  Wifi, 
  CheckCircle2, 
  Circle, 
  HelpCircle,
  ShieldCheck,
  AlertTriangle,
  Zap
} from 'lucide-react';

export default function StatusPanel({ telemetry, borderLine, roiPolygon }) {
  const threatLevel = telemetry?.threat_level || 'NORMAL';
  const persons = telemetry?.persons || [];
  const livePersons = persons.filter((p) => p.track_status !== 'LOST');
  const fps = telemetry?.fps || 0;
  const activeAlertsCount = telemetry?.active_alerts_count || 0;
  const threatReason = telemetry?.threat_reason || 'No person currently detected';
  const threatScore = telemetry?.threat_score;

  const motionMetrics = telemetry?.motion_metrics || {};
  const factorBreakdown = telemetry?.factor_breakdown || [];
  const edgeHealth = telemetry?.edge_health || {};
  const bandwidth = telemetry?.telemetry_bandwidth || {};
  const tamperDetected = telemetry?.tamper_detected;
  const tamperReason = telemetry?.tamper_reason;

  return (
    <div className="flex flex-col gap-3.5 h-full">
      {/* Real-time Threat Status Banner Card */}
      <div className={`p-4 rounded-xl border shadow-lg transition-all ${
        threatLevel === 'ALERT'
          ? 'bg-red-950/60 border-red-500/80 shadow-red-500/20 animate-pulse'
          : (threatLevel === 'SUSPICIOUS'
            ? 'bg-amber-950/40 border-amber-500/60 shadow-amber-500/20'
            : (threatLevel === 'OBSERVATION'
              ? 'bg-blue-950/40 border-blue-500/60 shadow-blue-500/20'
              : 'bg-emerald-950/30 border-emerald-500/50 shadow-emerald-500/10'))
      }`}>
        <div className="flex items-center justify-between font-mono text-xs mb-1">
          <span className="font-semibold text-slate-300 uppercase">PERIMETER THREAT STATUS</span>
          <span className={`w-2.5 h-2.5 rounded-full ${
            threatLevel === 'ALERT' 
              ? 'bg-red-500 animate-ping' 
              : (threatLevel === 'SUSPICIOUS' 
                ? 'bg-amber-400' 
                : (threatLevel === 'OBSERVATION' ? 'bg-cyan-400' : 'bg-emerald-400'))
          }`} />
        </div>

        <div className="text-lg font-bold font-mono tracking-wide mb-1">
          {threatLevel === 'ALERT' ? (
            <span className="text-red-400 flex items-center gap-1.5">
              🔴 INTRUSION DETECTED
            </span>
          ) : (threatLevel === 'SUSPICIOUS' ? (
            <span className="text-amber-400 flex items-center gap-1.5">
              🟡 SUSPICIOUS ACTIVITY
            </span>
          ) : (threatLevel === 'OBSERVATION' ? (
            <span className="text-cyan-400 flex items-center gap-1.5">
              🔵 TARGET MONITORED
            </span>
          ) : (
            <span className="text-emerald-400 flex items-center gap-1.5">
              🟢 PERIMETER SECURE
            </span>
          )))}
        </div>

        <p className="text-xs text-slate-300 font-mono">
          {threatReason}
        </p>

        {tamperDetected && (
          <div className="mt-2 p-2 rounded bg-red-900/60 border border-red-500 text-xs font-mono text-white flex items-center gap-1.5 animate-pulse">
            <AlertTriangle className="w-3.5 h-3.5 text-yellow-300" />
            <span>TAMPER ALERT: {tamperReason}</span>
          </div>
        )}

        <div className="mt-2.5 flex items-center justify-between text-[11px] font-mono text-slate-400 border-t border-white/10 pt-1.5">
          <span>ACTIVE ALERTS: <strong className="text-slate-100">{activeAlertsCount}</strong></span>
          <span>
            {threatScore == null ? 'THREAT SCORE: —' : `THREAT SCORE: ${threatScore}%`}
          </span>
        </div>
      </div>

      {/* Quick Status Metrics Row */}
      <div className="grid grid-cols-2 gap-2.5">
        <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-2.5">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono mb-0.5">
            <span>PIPELINE FPS</span>
            <Activity className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="text-lg font-bold font-mono text-cyan-400">
            {fps} <span className="text-[10px] text-slate-500 font-normal">FPS</span>
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-2.5">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono mb-0.5">
            <span>TARGETS</span>
            <Users className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-lg font-bold font-mono text-emerald-400">
            {livePersons.length} <span className="text-[10px] text-slate-500 font-normal">TRACKED</span>
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-2.5">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono mb-0.5">
            <span>VIRTUAL BORDER</span>
            <Slash className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className={`text-xs font-bold font-mono ${borderLine ? 'text-amber-400' : 'text-slate-500'}`}>
            {borderLine ? 'ACTIVE (HORIZONTAL)' : 'UNARMED'}
          </div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-2.5">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono mb-0.5">
            <span>RESTRICTED ZONE</span>
            <Pentagon className="w-3.5 h-3.5 text-red-400" />
          </div>
          <div className={`text-xs font-bold font-mono ${roiPolygon?.length >= 3 ? 'text-red-400' : 'text-slate-500'}`}>
            {roiPolygon?.length >= 3 ? 'POLYGON ARMED' : 'UNARMED'}
          </div>
        </div>
      </div>

      {/* Dual-Scale Motion Gating & Edge Optimization Card */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-lg">
        <div className="flex items-center justify-between mb-2 pb-1.5 border-b border-slate-800">
          <div className="flex items-center gap-1.5">
            <Zap className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider font-mono">
              Dual-Scale Motion Gating
            </h3>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
            {motionMetrics.roi_active ? 'ROI ACTIVE' : 'IDLE GATING'}
          </span>
        </div>

        <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono mb-2">
          <div className="bg-slate-950 p-2 rounded border border-slate-800">
            <span className="text-[10px] text-slate-500 block">AI INFERENCE</span>
            <strong className="text-cyan-400 text-sm">
              {motionMetrics.ai_processing_pct ?? 0}%
            </strong>
          </div>
          <div className="bg-slate-950 p-2 rounded border border-slate-800">
            <span className="text-[10px] text-slate-500 block">FRAMES SKIPPED</span>
            <strong className="text-emerald-400 text-sm">
              {motionMetrics.frames_skipped ?? 0}
            </strong>
          </div>
          <div className="bg-slate-950 p-2 rounded border border-slate-800">
            <span className="text-[10px] text-slate-500 block">COMPUTE SAVED</span>
            <strong className="text-amber-400 text-sm">
              {motionMetrics.compute_saved_pct ?? 100}%
            </strong>
          </div>
        </div>

        <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
          <span>Frames In: <strong className="text-slate-200">{motionMetrics.frames_received ?? 0}</strong></span>
          <span>Motion Score: <strong className="text-cyan-400">{motionMetrics.motion_score ?? 0}%</strong></span>
        </div>
      </div>

      {/* Explainable Threat Reasoning Checklist Card */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-lg">
        <div className="flex items-center justify-between mb-2 pb-1.5 border-b border-slate-800">
          <div className="flex items-center gap-1.5">
            <HelpCircle className="w-4 h-4 text-amber-400" />
            <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider font-mono">
              Explainable Threat Decision
            </h3>
          </div>
          <span className="text-[10px] font-mono text-slate-400">FACTOR BREAKDOWN</span>
        </div>

        <div className="space-y-1.5 text-xs font-mono">
          {factorBreakdown.length > 0 ? (
            factorBreakdown.map((item, idx) => (
              <div
                key={idx}
                className={`flex items-center justify-between p-1.5 rounded transition ${
                  item.active
                    ? 'bg-amber-950/30 text-amber-200 border border-amber-500/30'
                    : 'text-slate-500 bg-slate-950/40'
                }`}
              >
                <div className="flex items-center gap-2">
                  {item.active ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Circle className="w-3.5 h-3.5 text-slate-600" />
                  )}
                  <span>{item.factor}</span>
                </div>
                <span className={`text-[10px] font-bold ${item.active ? 'text-amber-400' : 'text-slate-600'}`}>
                  +{item.weight}%
                </span>
              </div>
            ))
          ) : (
            <div className="text-[11px] text-slate-500 text-center py-2">
              No person detected • Threat score: 0%
            </div>
          )}
        </div>
      </div>

      {/* Edge Node Health & Low-Bandwidth Telemetry Card */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-lg">
        <div className="flex items-center justify-between mb-2 pb-1.5 border-b border-slate-800">
          <div className="flex items-center gap-1.5">
            <Server className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider font-mono">
              Edge Node Telemetry
            </h3>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
            {edgeHealth.node_label || 'SOFTWARE EDGE NODE'}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2 text-xs font-mono mb-2">
          <div className="bg-slate-950 p-2 rounded border border-slate-800">
            <span className="text-[10px] text-slate-500 block">JSON TELEMETRY</span>
            <strong className="text-cyan-400 text-sm">
              {bandwidth.telemetry_payload_kb ?? 1.8} KB
            </strong>
          </div>
          <div className="bg-slate-950 p-2 rounded border border-slate-800">
            <span className="text-[10px] text-slate-500 block">BANDWIDTH REDUCTION</span>
            <strong className="text-emerald-400 text-sm">
              {bandwidth.bandwidth_reduction_pct ?? 99.4}%
            </strong>
          </div>
        </div>

        <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
          <span>Heartbeat: <strong className="text-slate-200">{edgeHealth.last_heartbeat_ago ?? 0.1}s ago</strong></span>
          <span>Latency: <strong className="text-cyan-400">{edgeHealth.latency_ms ?? 10} ms</strong></span>
        </div>
      </div>

      {/* Real-time Target Track List */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-lg flex-1 flex flex-col">
        <div className="flex items-center justify-between mb-2.5 border-b border-slate-800/80 pb-2">
          <h3 className="text-xs font-bold text-slate-200 tracking-wider uppercase flex items-center gap-2 font-mono">
            <Users className="w-4 h-4 text-cyan-400" />
            Tracked Persons ({livePersons.length})
          </h3>
          <span className="text-[10px] font-mono text-slate-400">BYTETRACK PERSISTENCE</span>
        </div>

        {persons.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center py-6 text-center text-slate-500 text-xs font-mono">
            <span>PERSONS DETECTED: 0</span>
            <span className="mt-1 text-emerald-500/80">No active threats</span>
          </div>
        ) : (
          <div className="space-y-2.5 max-h-[260px] overflow-y-auto pr-1">
            {persons.map((p) => {
              const isAlert = (p.in_restricted && threatLevel === 'ALERT') || p.track_status === 'ALERT';
              const isWatch = p.approaching || p.is_suspicious;
              const showScore = p.track_status !== 'LOST' && (p.behavior_score || 0) > 0;

              return (
                <div
                  key={p.track_id}
                  className={`p-2.5 rounded-lg border text-xs transition-all ${
                    p.track_status === 'LOST'
                      ? 'bg-slate-900/40 border-slate-700/40 text-slate-400'
                      : isAlert
                      ? 'bg-red-950/30 border-red-500/50 text-red-200'
                      : isWatch
                      ? 'bg-amber-950/20 border-amber-500/40 text-amber-200'
                      : 'bg-slate-800/40 border-slate-700/60 text-slate-200'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5 font-mono">
                    <span className="font-bold flex items-center gap-1.5">
                      <span className={`w-2 h-2 rounded-full ${isAlert ? 'bg-red-500 animate-ping' : (p.track_status === 'LOST' ? 'bg-slate-500' : 'bg-emerald-400')}`} />
                      PERSON #{p.track_id}{p.track_status === 'LOST' ? ' (LOST)' : ''}
                    </span>
                    <span className="text-[11px] text-slate-400">
                      Conf: <strong className="text-slate-200">{p.confidence}%</strong>
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-1.5 text-[11px] font-mono mb-2">
                    <div>
                      <span className="text-slate-400">Boundary: </span>
                      <strong className={p.in_restricted ? 'text-red-400' : (p.approaching ? 'text-amber-400' : 'text-emerald-400')}>
                        {p.track_status === 'LOST' ? 'LOST' : (p.in_restricted ? 'RESTRICTED' : (p.approaching ? 'APPROACHING' : 'NORMAL'))}
                      </strong>
                    </div>
                    <div>
                      <span className="text-slate-400">State: </span>
                      <strong className={p.is_suspicious ? 'text-red-400' : 'text-slate-200'}>
                        {p.posture_label}
                      </strong>
                    </div>
                  </div>

                  {p.crossing_direction && p.track_status !== 'LOST' && (
                    <div className="text-[10px] font-mono text-slate-400 mb-1.5">
                      Direction: <strong className="text-slate-200">{p.crossing_direction}</strong>
                    </div>
                  )}

                  {showScore && (
                  <div>
                    <div className="flex justify-between text-[10px] font-mono text-slate-400 mb-0.5">
                      <span>Threat Score</span>
                      <span className={isAlert ? 'text-red-400 font-bold' : 'text-slate-300'}>
                        {p.behavior_score}%
                      </span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                      <div
                        className={`h-full transition-all duration-300 ${
                          p.behavior_score >= 65 ? 'bg-red-500' : (p.behavior_score >= 45 ? 'bg-amber-400' : 'bg-emerald-400')
                        }`}
                        style={{ width: `${Math.min(100, Math.max(5, p.behavior_score))}%` }}
                      />
                    </div>
                    {p.threat_reasons?.length > 0 && (
                      <div className="mt-1 text-[10px] text-slate-400 font-mono">
                        Reason: {p.threat_reasons.join(' + ')}
                      </div>
                    )}
                  </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
