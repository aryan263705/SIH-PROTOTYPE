import React from 'react';
import { 
  Camera, 
  Tv, 
  Cpu, 
  Crosshair, 
  Activity, 
  AlertTriangle, 
  Camera as SnapshotIcon, 
  LayoutDashboard, 
  ArrowRight, 
  CheckCircle,
  Database,
  Zap,
  Scan,
  Shield,
  Server,
  Film
} from 'lucide-react';

const pipelineStages = [
  {
    step: "01",
    title: "Video Ingestion",
    tech: "Mobile IP Cam / Webcam / MP4",
    icon: Camera,
    color: "cyan",
    desc: "Ingests RTSP/HTTP streams from mobile phones, laptop webcams, or existing CCTV camera hardware via non-blocking threaded capture with automatic reconnect."
  },
  {
    step: "02",
    title: "Dual-Scale Motion Gating",
    tech: "Fast Frame Diff + Slow Background Model",
    icon: Zap,
    color: "amber",
    desc: "Saves >90% edge compute by evaluating dual temporal layers (fast instantaneous shifts + slow background model). Skips expensive YOLO forward pass on static scenes."
  },
  {
    step: "03",
    title: "Dynamic Motion ROI",
    tech: "Contour Bounding with 20% Margin",
    icon: Scan,
    color: "blue",
    desc: "Identifies moving cluster contours to isolate candidate regions of interest, keeping AI focused while mapping bounding coordinates back to the full frame."
  },
  {
    step: "04",
    title: "Person Detection",
    tech: "Ultralytics YOLOv8n (Class 0)",
    icon: Cpu,
    color: "purple",
    desc: "Runs lightweight nano neural network filtered strictly to Class 0 ('person') to maximize processing throughput on edge / laptop hardware (>25 FPS)."
  },
  {
    step: "05",
    title: "Persistent Tracking",
    tech: "ByteTrack (Kalman Filter)",
    icon: Crosshair,
    color: "emerald",
    desc: "Associates detections across consecutive frames to maintain persistent Target IDs (#01, #02) across momentary occlusions without identity swaps."
  },
  {
    step: "06",
    title: "Ultra-Slow Crawler Analysis",
    tech: "3–8s Trajectory & Aspect Ratio Inversion",
    icon: Activity,
    color: "rose",
    desc: "Defeats low-velocity evasion tactics by maintaining long-term position history, detecting persistent creeping (>20px displacement) with low-posture silhouettes (AR >= 0.75)."
  },
  {
    step: "07",
    title: "Virtual Border Intelligence",
    tech: "Directional Line Crossing & Polygon ROI",
    icon: Shield,
    color: "amber",
    desc: "Tracks state transitions (OUTSIDE -> APPROACHING -> CROSSING -> INSIDE -> LEFT ZONE). Only true crossings in the monitored direction enter verification."
  },
  {
    step: "08",
    title: "Explainable Threat Decision",
    tech: "2.0s Temporal Persistence Window",
    icon: AlertTriangle,
    color: "red",
    desc: "Eliminates false alarms with 2.0s persistence verification. Generates a transparent rule-based Threat Score showing exact contributing factors."
  },
  {
    step: "09",
    title: "Forensic Evidence & Replay",
    tech: "Overlaid Snapshot + 30s MP4 Buffer",
    icon: Film,
    color: "indigo",
    desc: "Captures instant evidence snapshot and automatically compiles a standalone 30s forensic MP4 clip (8s before event + 4s after) from rolling memory."
  },
  {
    step: "10",
    title: "Low-Bandwidth Telemetry",
    tech: "Edge-Local Processing (<2 KB Payload)",
    icon: Server,
    color: "emerald",
    desc: "Edge node processes heavy video locally and sends only lightweight JSON metadata and evidence snapshots upstream, achieving >99% bandwidth savings."
  }
];

export default function Architecture() {
  return (
    <div className="max-w-6xl mx-auto space-y-8 p-2">
      {/* Page Header */}
      <div className="text-center space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 text-xs font-mono">
          <CheckCircle className="w-3.5 h-3.5" /> SIH26187 EDGE-AI ARCHITECTURE SPECIFICATION
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-100 uppercase font-mono">
          AI-Powered Border Video Analytics Pipeline
        </h2>
        <p className="text-sm text-slate-400 max-w-2xl mx-auto">
          We do not replace the existing camera — we make it intelligent. Raw video is processed near the source with dual-scale gating, persistent tracking, slow-crawler heuristics, and lightweight telemetry.
        </p>
      </div>

      {/* Interactive 10-Stage Pipeline Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3.5">
        {pipelineStages.map((stage, idx) => {
          const Icon = stage.icon;
          return (
            <div
              key={stage.step}
              className="relative bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl flex flex-col justify-between hover:border-slate-700 transition"
            >
              <div>
                {/* Stage Header */}
                <div className="flex items-center justify-between mb-2.5">
                  <span className="text-[11px] font-mono font-bold text-cyan-400 px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-900">
                    STAGE {stage.step}
                  </span>
                  <div className="w-7 h-7 rounded-lg bg-slate-800 flex items-center justify-center text-slate-200">
                    <Icon className="w-3.5 h-3.5 text-cyan-400" />
                  </div>
                </div>

                <h3 className="text-xs font-bold text-slate-100 mb-1 font-mono">
                  {stage.title}
                </h3>
                <div className="text-[10px] font-mono text-cyan-400 mb-2">
                  {stage.tech}
                </div>

                <p className="text-[11px] text-slate-400 leading-relaxed font-sans">
                  {stage.desc}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Core Innovation Highlights */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-2">
          <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider font-mono flex items-center gap-2">
            <Zap className="w-4 h-4 text-cyan-400" />
            1. Dual-Scale Motion Gating
          </h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            Running deep neural networks on empty desert or border scenes burns unnecessary power. Our fast frame-diff + slow background accumulator skips 90%+ of empty frames while keeping tracking awake whenever movement occurs.
          </p>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-2">
          <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider font-mono flex items-center gap-2">
            <Activity className="w-4 h-4 text-rose-400" />
            2. Anti-Evasion Slow Crawler Heuristic
          </h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            Traditional motion sensors miss targets crawling at &lt;15 px/s. By maintaining a 3–8s trajectory window, the edge node validates cumulative creeping displacement and wide aspect ratio silhouettes (W/H &ge; 0.75).
          </p>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-2">
          <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider font-mono flex items-center gap-2">
            <Server className="w-4 h-4 text-emerald-400" />
            3. Event-Driven Low-Bandwidth Telemetry
          </h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            Continuous 1080p streaming overwhelms tactical radio and cellular links. Our edge node transmits only lightweight JSON telemetry packets (~1.8 KB) and forensic evidence snapshots (~14 KB), saving 99.4% network bandwidth.
          </p>
        </div>
      </div>
    </div>
  );
}
