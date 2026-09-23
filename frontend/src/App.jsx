import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import Architecture from './pages/Architecture';
import { fetchStatus } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [telemetry, setTelemetry] = useState(null);

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const data = await fetchStatus();
        setTelemetry(data);
      } catch (e) {
        // Handled gracefully in UI
      }
    };
    checkStatus();
    const timer = setInterval(checkStatus, 2000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="min-h-screen bg-[#080c14] text-slate-100 flex flex-col selection:bg-cyan-500 selection:text-black">
      {/* Tactical Header */}
      <Header
        telemetry={telemetry}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />

      {/* Main Command Console Container */}
      <main className="flex-1 p-4 md:p-6 max-w-[1600px] w-full mx-auto">
        {activeTab === 'dashboard' ? (
          <Dashboard />
        ) : (
          <Architecture />
        )}
      </main>

      {/* Footer */}
      <footer className="py-3 px-6 border-t border-slate-900 bg-slate-950 text-slate-500 text-[11px] font-mono flex flex-col sm:flex-row items-center justify-between gap-2">
        <div>
          SMART INDIA HACKATHON • PROBLEM STATEMENT ID: <span className="text-slate-300">SIH26187</span> • TEAM: <span className="text-slate-300">AI AVENGERS</span>
        </div>
        <div className="flex items-center gap-3">
          <span>PIPELINE: <strong className="text-emerald-400">YOLOv8 + BYTETRACK</strong></span>
          <span>•</span>
          <span>SECURITY CLASSIFICATION: <strong className="text-cyan-400">RESTRICTED BORDER MONITORING</strong></span>
        </div>
      </footer>
    </div>
  );
}
