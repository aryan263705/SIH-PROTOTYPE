import React from 'react';
import { AlertCircle, ShieldAlert, Image as ImageIcon, Trash2, Clock, Film } from 'lucide-react';
import { clearAlerts } from '../services/api';

export default function AlertPanel({ alerts, onSelectSnapshot, onAlertsCleared }) {
  const handleClear = async () => {
    try {
      await clearAlerts();
      if (onAlertsCleared) onAlertsCleared();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2.5 mb-3">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-red-500" />
          <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
            Live Alert Ticker ({alerts.length})
          </h3>
        </div>
        {alerts.length > 0 && (
          <button
            onClick={handleClear}
            className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-red-400 font-mono transition"
            title="Acknowledge and clear active alerts"
          >
            <Trash2 className="w-3 h-3" /> Acknowledge All
          </button>
        )}
      </div>

      {/* Alert Feed */}
      {alerts.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center py-8 text-center text-slate-500 font-mono text-xs">
          <AlertCircle className="w-8 h-8 mb-2 text-slate-600 stroke-[1.5]" />
          <span>Perimeter Secure. No Active Violations.</span>
        </div>
      ) : (
        <div className="space-y-2.5 overflow-y-auto max-h-[320px] pr-1 flex-1">
          {alerts.map((item, idx) => {
            const isCritical = item.severity === 'CRITICAL' || item.alert_type?.includes('INTRUSION');

            return (
              <div
                key={item.id || idx}
                onClick={() => onSelectSnapshot(item)}
                className={`p-3 rounded-lg border transition-all cursor-pointer hover:scale-[1.01] ${
                  isCritical
                    ? 'bg-red-950/40 border-red-500/60 hover:bg-red-950/60 text-red-200'
                    : 'bg-amber-950/30 border-amber-500/50 hover:bg-amber-950/50 text-amber-200'
                }`}
              >
                <div className="flex items-center justify-between font-mono mb-1.5">
                  <span className="font-bold flex items-center gap-1.5 text-xs">
                    {isCritical ? '🚨' : '⚠️'} {item.alert_type}
                  </span>
                  <span className="text-[11px] text-slate-400 flex items-center gap-1">
                    <Clock className="w-3 h-3" /> {item.timestamp}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px] font-mono mb-2">
                  <div>
                    <span className="text-slate-400">Target: </span>
                    <strong className="text-slate-100">#{item.person_id}</strong>
                    {item.confidence && (
                      <span className="text-[10px] text-slate-400 ml-1">({item.confidence}%)</span>
                    )}
                  </div>
                  <div>
                    <span className="text-slate-400">Score: </span>
                    <strong className={isCritical ? 'text-red-400' : 'text-amber-400'}>
                      {item.behavior_score ?? item.score}%
                    </strong>
                  </div>
                </div>

                <div className="text-[10px] font-mono text-slate-300 mb-1.5 space-y-0.5">
                  {item.reason && <div>Reason: <strong className="text-slate-100">{item.reason}</strong></div>}
                  {item.direction && <div>Direction: <strong className="text-slate-100">{item.direction}</strong></div>}
                </div>

                <div className="flex items-center justify-between text-[10px] font-mono border-t border-white/10 pt-1.5">
                  <span className="text-slate-400">
                    Persistence: {item.persistence_seconds ?? '—'}s
                  </span>
                  <div className="flex items-center gap-2.5">
                    {item.replay && (
                      <span
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectSnapshot({ ...item, initialTab: 'replay' });
                        }}
                        className="inline-flex items-center gap-1 text-amber-400 font-semibold hover:underline cursor-pointer"
                        title="Watch 30s forensic rolling event replay video"
                      >
                        <Film className="w-3 h-3" /> Replay
                      </span>
                    )}
                    <span className="inline-flex items-center gap-1 text-cyan-400 font-semibold hover:underline">
                      <ImageIcon className="w-3 h-3" /> Snapshot
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
