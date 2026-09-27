const API_BASE = (import.meta.env.VITE_API_BASE_URL || window.location.origin).replace(/\/$/, '');

export async function fetchStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/status`);
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    return null;
  }
}

export async function fetchAlerts() {
  try {
    const res = await fetch(`${API_BASE}/api/alerts`);
    if (!res.ok) return [];
    return await res.json();
  } catch (err) {
    return [];
  }
}

export async function clearAlerts() {
  try {
    const res = await fetch(`${API_BASE}/api/alerts/clear`, { method: 'POST' });
    return await res.json();
  } catch (err) {
    return { status: 'error' };
  }
}

export async function fetchEvents(limit = 50) {
  try {
    const res = await fetch(`${API_BASE}/api/events?limit=${limit}`);
    if (!res.ok) return [];
    return await res.json();
  } catch (err) {
    return [];
  }
}

export async function clearEvents() {
  try {
    const res = await fetch(`${API_BASE}/api/events/clear`, { method: 'POST' });
    return await res.json();
  } catch (err) {
    return { status: 'error' };
  }
}

export async function configureCamera(sourceType, sourcePath = '') {
  try {
    const res = await fetch(`${API_BASE}/api/camera/configure`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_type: sourceType, source_path: sourcePath })
    });
    return await res.json();
  } catch (err) {
    return { status: 'error', message: err.message };
  }
}

export async function controlCamera(action) {
  try {
    const formData = new FormData();
    formData.append('action', action);
    const res = await fetch(`${API_BASE}/api/camera/control`, {
      method: 'POST',
      body: formData
    });
    return await res.json();
  } catch (err) {
    return { status: 'error', message: err.message };
  }
}

export async function fetchConfig() {
  try {
    const res = await fetch(`${API_BASE}/api/config`);
    return await res.json();
  } catch (err) {
    return {};
  }
}

export async function updateConfig(newConfig) {
  try {
    const res = await fetch(`${API_BASE}/api/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newConfig)
    });
    return await res.json();
  } catch (err) {
    return { status: 'error', message: err.message };
  }
}

export async function uploadVideo(file) {
  try {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/api/upload_video`, {
      method: 'POST',
      body: formData
    });
    return await res.json();
  } catch (err) {
    return { status: 'error', message: err.message };
  }
}

// --- Virtual Border and ROI Endpoints ---

export async function setVirtualBorder(pt1, pt2) {
  try {
    const res = await fetch(`${API_BASE}/api/zone/border`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pt1, pt2 })
    });
    return await res.json();
  } catch (err) {
    return { status: 'error', message: err.message };
  }
}

export async function setRestrictedZone(polygon) {
  try {
    const res = await fetch(`${API_BASE}/api/zone/roi`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ polygon })
    });
    return await res.json();
  } catch (err) {
    return { status: 'error', message: err.message };
  }
}

export async function clearZones() {
  try {
    const res = await fetch(`${API_BASE}/api/zone/clear`, { method: 'POST' });
    return await res.json();
  } catch (err) {
    return { status: 'error', message: err.message };
  }
}

export async function resetDemo() {
  try {
    const res = await fetch(`${API_BASE}/api/reset_demo`, { method: 'POST' });
    return await res.json();
  } catch (err) {
    return { status: 'error', message: err.message };
  }
}

export async function processBrowserFrame(blob) {
  try {
    const formData = new FormData();
    formData.append('file', blob, 'frame.jpg');
    const res = await fetch(`${API_BASE}/api/process_frame`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    return null;
  }
}

export async function toggleMotionRoi() {
  try {
    const res = await fetch(`${API_BASE}/api/debug/toggle_motion_roi`, { method: 'POST' });
    return await res.json();
  } catch (err) {
    return { status: 'error', message: err.message };
  }
}

export async function switchModel(modelName) {
  try {
    const res = await fetch(`${API_BASE}/api/model/switch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_name: modelName })
    });
    return await res.json();
  } catch (err) {
    return { status: 'error', message: err.message };
  }
}


