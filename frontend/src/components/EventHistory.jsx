import React, { useState } from 'react';
import { History, Search, Image as ImageIcon, Trash2, RefreshCw, Film } from 'lucide-react';
import { clearEvents } from '../services/api';

export default function EventHistory({ events, onSelectSnapshot, onRefresh }) {
  const [filter, setFilter] = useState('');

  const filteredEvents = events.filter((ev) => {
    const q = filter.toLowerCase();
    return (
      (ev.person_id && ev.person_id.toLowerCase().includes(q)) ||
      (ev.event_type && ev.event_type.toLowerCase().includes(q)) ||
      (ev.timestamp && ev.timestamp.toLowerCase().includes(q)) ||
      (ev.status && ev.status.toLowerCase().includes(q))
    );
  });

  const handleClearHistory = async () => {
    if (window.confirm('Clear all historical security incident records?')) {
      try {
        await clearEvents();
        if (onRefresh) onRefresh();
      } catch (err) {
        console.error(err);
      }
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col gap-3">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
            Incident & Alert Audit Trail ({filteredEvents.length})
          </h3>
        </div>

        <div className="flex items-center gap-2">
          {/* Filter input */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-slate-500" />
            <input
              type="text"
              placeholder="Search ID, event, time..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded pl-8 pr-2.5 py-1 text-xs text-slate-200 font-mono focus:outline-hidden focus:border-cyan-500 w-48"
            />
          </div>

          <button
            onClick={onRefresh}
            title="Refresh history"
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleClearHistory}
            title="Clear history database"
            className="p-1.5 bg-slate-800 hover:bg-red-950/60 hover:text-red-400 text-slate-400 rounded border border-slate-700 transition"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto max-h-[300px] overflow-y-auto">
        <table className="w-full text-left text-xs font-mono border-collapse">
          <thead>
            <tr className="bg-slate-950/80 text-slate-400 border-b border-slate-800">
              <th className="py-2 px-3 font-semibold">TIMESTAMP</th>
              <th className="py-2 px-3 font-semibold">PERSON ID</th>
              <th className="py-2 px-3 font-semibold">INCIDENT TYPE</th>
              <th className="py-2 px-3 font-semibold">SCORE</th>
              <th className="py-2 px-3 font-semibold">STATUS</th>
              <th className="py-2 px-3 font-semibold text-right">EVIDENCE</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {filteredEvents.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-500">
                  No incident logs recorded yet.
                </td>
              </tr>
            ) : (
              filteredEvents.map((row) => {
                const isAlert = row.event_type?.includes('INTRUSION') || row.score >= 70;

                return (
                  <tr
                    key={row.id}
                    className="hover:bg-slate-800/40 transition group"
                  >
                    <td className="py-2.5 px-3 text-slate-300 whitespace-nowrap">
                      {row.timestamp}
                    </td>
                    <td className="py-2.5 px-3 font-bold text-cyan-400 whitespace-nowrap">
                      #{row.person_id}
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                        isAlert
                          ? 'bg-red-950/80 text-red-400 border border-red-800/50'
                          : 'bg-amber-950/80 text-amber-400 border border-amber-800/50'
                      }`}>
                        {row.event_type}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <span className={isAlert ? 'text-red-400 font-bold' : 'text-slate-300'}>
                        {row.score}%
                      </span>
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <span className="text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded text-[10px] border border-emerald-800/40">
                        {row.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-2">
                        {row.details && row.details.includes('Replay: ') && (
                          <button
                            onClick={() => onSelectSnapshot({ ...row, initialTab: 'replay' })}
                            className="inline-flex items-center gap-1 text-[11px] text-amber-400 hover:text-amber-300 hover:underline"
                            title="Play 30s event replay video"
                          >
                            <Film className="w-3.5 h-3.5" /> Replay
                          </button>
                        )}
                        {row.snapshot_path ? (
                          <button
                            onClick={() => onSelectSnapshot(row)}
                            className="inline-flex items-center gap-1 text-[11px] text-cyan-400 hover:text-cyan-300 hover:underline"
                          >
                            <ImageIcon className="w-3.5 h-3.5" /> Snapshot
                          </button>
                        ) : (
                          <span className="text-slate-600">N/A</span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
