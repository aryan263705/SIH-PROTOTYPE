import React, { useState, useEffect, useRef } from 'react';
import VideoFeed from '../components/VideoFeed';
import StatusPanel from '../components/StatusPanel';
import OperatorToolbar from '../components/OperatorToolbar';
import AlertPanel from '../components/AlertPanel';
import EventHistory from '../components/EventHistory';
import SnapshotModal from '../components/SnapshotModal';
import { 
  fetchStatus, 
  fetchAlerts, 
  fetchEvents, 
  configureCamera, 
  controlCamera, 
  clearZones, 
  resetDemo,
  fetchConfig,
  updateConfig,
  toggleMotionRoi,
  switchModel
} from '../services/api';

export default function Dashboard() {
  const [cameraSource, setCameraSource] = useState('webcam');
  const [isCameraRunning, setIsCameraRunning] = useState(false);
  const [mobileUrl, setMobileUrl] = useState('');
  const [wsConnected, setWsConnected] = useState(false);
  
  const [drawMode, setDrawMode] = useState(null);
  const [polygonPointsCount, setPolygonPointsCount] = useState(0);
  const [borderLine, setBorderLine] = useState([[0, 0.65], [1, 0.65]]);
  const [roiPolygon, setRoiPolygon] = useState([]);
  const [boundaryPosition, setBoundaryPosition] = useState(65);

  const [telemetry, setTelemetry] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [events, setEvents] = useState([]);
  const [selectedSnapshot, setSelectedSnapshot] = useState(null);
  const eventsRef = useRef([]);

  const applyTelemetry = (statusData) => {
    if (!statusData) return;
    setTelemetry(statusData);
    if (statusData.source_type) setCameraSource(statusData.source_type);
    if (statusData.border_line) setBorderLine(statusData.border_line);
    if (typeof statusData.boundary_position === 'number') {
      setBoundaryPosition(Math.round(statusData.boundary_position * 100));
    }
    if (statusData.roi_polygon) setRoiPolygon(statusData.roi_polygon);
    setIsCameraRunning(Boolean(statusData.camera_online) || statusData.source_status === 'CONNECTING' || statusData.source_status === 'RECONNECTING');
  };

  const loadData = async () => {
    try {
      const [statusData, alertsData, eventsData] = await Promise.all([
        fetchStatus(),
        fetchAlerts(),
        fetchEvents(50)
      ]);
      applyTelemetry(statusData);
      if (alertsData) setAlerts(alertsData);
      if (eventsData) {
        eventsRef.current = eventsData;
        setEvents(eventsData);
      }
    } catch (err) {
      console.warn('Polling warning:', err);
    }
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [cfg, currentSt] = await Promise.all([
        fetchConfig(),
        fetchStatus()
      ]);
      if (cancelled) return;
      if (cfg?.border_line) setBorderLine(cfg.border_line);
      if (typeof cfg?.boundary_position === 'number') {
        setBoundaryPosition(Math.round(cfg.boundary_position * 100));
      }

      // If camera is already streaming online or connecting, do not disrupt capture session
      if (currentSt?.camera_online || currentSt?.source_status === 'CONNECTING') {
        applyTelemetry(currentSt);
      } else {
        await configureCamera('webcam', '0');
      }
      await loadData();
    })();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const socket = new WebSocket(`${proto}://${window.location.host}/ws`);

    socket.onopen = () => setWsConnected(true);
    socket.onclose = () => setWsConnected(false);
    socket.onerror = () => setWsConnected(false);
    socket.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === 'TELEMETRY' && msg.telemetry) {
          applyTelemetry(msg.telemetry);
          if (msg.recent_alerts) setAlerts(msg.recent_alerts);
        } else if (msg.type === 'ALERT' || msg.event) {
          setAlerts((prev) => [msg, ...prev.filter((a) => a.id !== msg.id)]);
          loadData();
        }
      } catch (e) {
        // ignore malformed frames
      }
    };

    const interval = setInterval(() => {
      if (socket.readyState !== WebSocket.OPEN) {
        loadData();
      } else {
        fetchEvents(50).then((eventsData) => {
          if (eventsData) setEvents(eventsData);
        });
      }
    }, 1500);

    return () => {
      socket.close();
      clearInterval(interval);
    };
  }, []);

  const handleSourceChange = async (src) => {
    setCameraSource(src);
    if (src === 'demo') {
      await configureCamera('demo', 'border_patrol_demo.mp4');
      setIsCameraRunning(true);
    } else if (src === 'mobile') {
      if (mobileUrl) {
        await configureCamera('mobile', mobileUrl);
        setIsCameraRunning(true);
      }
    } else if (src === 'webcam') {
      await configureCamera('webcam', '0');
      setIsCameraRunning(true);
    }
    loadData();
  };

  const handleToggleCamera = async () => {
    const nextState = !isCameraRunning;
    if (nextState) {
      await controlCamera('start');
    } else {
      await controlCamera('stop');
    }
    setIsCameraRunning(nextState);
    loadData();
  };

  const handleConnectMobile = async () => {
    if (!mobileUrl) return;
    setCameraSource('mobile');
    await configureCamera('mobile', mobileUrl);
    setIsCameraRunning(true);
    loadData();
  };

  const handleBoundaryChange = async (pct) => {
    setBoundaryPosition(pct);
    const pos = pct / 100;
    setBorderLine([[0, pos], [1, pos]]);
    await updateConfig({ boundary_position: pos });
  };

  const handleClosePolygon = () => {
    if (window.__closeSurveillancePolygon) {
      window.__closeSurveillancePolygon();
    }
  };

  const handleClearZones = async () => {
    setRoiPolygon([]);
    setDrawMode(null);
    await clearZones();
    loadData();
  };

  const handleResetDemo = async () => {
    setRoiPolygon([]);
    setDrawMode(null);
    setAlerts([]);
    setEvents([]);
    await resetDemo();
    loadData();
  };

  const handleToggleMotionRoi = async () => {
    try {
      const res = await toggleMotionRoi();
      if (res?.show_motion_roi !== undefined) {
        setTelemetry((prev) => prev ? { ...prev, show_motion_roi: res.show_motion_roi } : prev);
      }
    } catch (e) {
      console.error(e);
    }
    loadData();
  };

  const handleSwitchModel = async (modelName) => {
    try {
      await switchModel(modelName);
      loadData();
    } catch (e) {
      console.error('Error switching model:', e);
    }
  };

  return (
    <div className="space-y-4">
      <OperatorToolbar
        cameraSource={cameraSource}
        onSourceChange={handleSourceChange}
        isCameraRunning={isCameraRunning}
        onToggleCamera={handleToggleCamera}
        drawMode={drawMode}
        setDrawMode={setDrawMode}
        polygonPointsCount={polygonPointsCount}
        onClosePolygon={handleClosePolygon}
        onClearZones={handleClearZones}
        onResetDemo={handleResetDemo}
        mobileUrl={mobileUrl}
        setMobileUrl={setMobileUrl}
        onConnectMobile={handleConnectMobile}
        boundaryPosition={boundaryPosition}
        onBoundaryChange={handleBoundaryChange}
        wsConnected={wsConnected}
        showMotionRoi={telemetry?.show_motion_roi || false}
        onToggleMotionRoi={handleToggleMotionRoi}
        currentModel={telemetry?.model_name || 'yolov8s.pt'}
        onSwitchModel={handleSwitchModel}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <VideoFeed
            cameraSource={cameraSource}
            isCameraRunning={isCameraRunning}
            drawMode={drawMode}
            setDrawMode={setDrawMode}
            setPolygonPointsCount={setPolygonPointsCount}
            borderLine={borderLine}
            setBorderLine={setBorderLine}
            roiPolygon={roiPolygon}
            setRoiPolygon={setRoiPolygon}
            telemetry={telemetry}
          />
        </div>
        <div className="lg:col-span-1">
          <StatusPanel
            telemetry={telemetry}
            borderLine={borderLine}
            roiPolygon={roiPolygon}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-1">
          <AlertPanel
            alerts={alerts}
            onSelectSnapshot={(item) => setSelectedSnapshot(item)}
            onAlertsCleared={loadData}
          />
        </div>
        <div className="lg:col-span-2">
          <EventHistory
            events={events}
            onSelectSnapshot={(item) => setSelectedSnapshot(item)}
            onRefresh={loadData}
          />
        </div>
      </div>

      {selectedSnapshot && (
        <SnapshotModal
          snapshot={selectedSnapshot}
          onClose={() => setSelectedSnapshot(null)}
        />
      )}
    </div>
  );
}
