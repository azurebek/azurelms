(() => {
  const ACCESS_REVOKED_CLOSE_CODE = 4403;
  const MAX_RECONNECT_ATTEMPTS = 8;
  const RECONNECT_MAX_DELAY = 10000;

  window.ClassbookSocket = function ClassbookSocket(sessionId, onEvent) {
    let socket = null;
    let attempts = 0;
    let stopped = false;
    let timer = null;

    const connect = () => {
      if (stopped || !navigator.onLine) return;
      const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
      try { socket = new WebSocket(`${scheme}://${location.host}/ws/classbook/${sessionId}/`); }
      catch (_) { scheduleReconnect(); return; }
      socket.onopen = () => { attempts = 0; };
      socket.onmessage = (event) => {
        try { onEvent(JSON.parse(event.data)); } catch (_) {}
      };
      socket.onclose = (event) => {
        if (event.code === ACCESS_REVOKED_CLOSE_CODE) { stopped = true; return; }
        scheduleReconnect();
      };
      socket.onerror = () => { try { socket.close(); } catch (_) {} };
    };
    const scheduleReconnect = () => {
      if (stopped || attempts >= MAX_RECONNECT_ATTEMPTS || timer) return;
      const delay = Math.min(RECONNECT_MAX_DELAY, 500 * (2 ** attempts++));
      timer = setTimeout(() => { timer = null; connect(); }, delay);
    };
    const wake = () => {
      if (stopped || (socket && socket.readyState === WebSocket.OPEN)) return;
      attempts = 0;
      clearTimeout(timer); timer = null; connect();
    };
    window.addEventListener('online', wake);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) wake(); });
    connect();
    return {stop: () => { stopped = true; clearTimeout(timer); try { socket?.close(); } catch (_) {} }};
  };
})();
