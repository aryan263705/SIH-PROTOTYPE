const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'https://sih-prototype-backend.onrender.com').replace(/\/$/, '');

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
  const browserCameraActiveRef = useRef(false);

  const applyTelemetry = (statusData) => {
    if (!statusData) return;
    if (browserCameraActiveRef.current && statusData.source_type === 'webcam') return;
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

      // On a deployed site, the laptop webcam belongs to the browser, not the cloud backend.
      // Do not ask the remote server to open cv2.VideoCapture(0).
      if (currentSt?.source_type && currentSt.source_type !== 'webcam') {
        applyTelemetry(currentSt);
      }
      await loadData();
    })();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const socketBase = new URL(API_BASE);
    const socketHost = socketBase.host;
    const socket = new WebSocket(`${proto}://${socketHost}/ws`);

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
      browserCameraActiveRef.current = false;
      await configureCamera('demo', 'border_patrol_demo.mp4');
      setIsCameraRunning(true);
    } else if (src === 'mobile') {
      browserCameraActiveRef.current = false;
      if (mobileUrl) {
        await configureCamera('mobile', mobileUrl);
        setIsCameraRunning(true);
      }
    } else if (src === 'webcam') {
      browserCameraActiveRef.current = true;
      setIsCameraRunning(true);
    }
    loadData();
  };

  const handleToggleCamera = async () => {
    const nextState = !isCameraRunning;
    if (cameraSource === 'webcam') {
      browserCameraActiveRef.current = nextState;
      setIsCameraRunning(nextState);
      if (!nextState) {
        setTelemetry((prev) => prev ? {
          ...prev,
          camera_online: false,
          source_status: 'OFFLINE',
          camera_message: 'CAMERA OFFLINE'
        } : prev);
      }
    } else {
      if (nextState) {
        await controlCamera('start');
      } else {
        await controlCamera('stop');
      }
      setIsCameraRunning(nextState);
      loadData();
    }
  };

  const handleBrowserTelemetry = (browserData) => {
    browserCameraActiveRef.current = true;
    setTelemetry((prev) => ({
      ...(prev || {}),
      ...browserData,
      source_type: 'webcam',
      source_status: browserData.source_status || 'ONLINE',
      camera_online: Boolean(browserData.camera_online),
      ai_online: browserData.ai_online !== false
    }));
    if (browserData.border_line) setBorderLine(browserData.border_line);
    if (browserData.roi_polygon) setRoiPolygon(browserData.roi_polygon);
    if (browserData.new_alerts?.length) {
      setAlerts((prev) => [...browserData.new_alerts, ...prev]);
    }
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
            onBrowserTelemetry={handleBrowserTelemetry}
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
