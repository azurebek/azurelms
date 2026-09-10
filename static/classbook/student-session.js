(() => {
  const root = document.querySelector('[data-student-session]');
  if (!root) return;
  const stateUrl = root.dataset.stateUrl;
  const sessionId = root.dataset.sessionId;
  let knownActivity = document.querySelector('.cb-active-card')?.getAttribute('href') || '';
  const refresh = async () => {
    try {
      const response = await fetch(stateUrl, {headers: {'X-Requested-With': 'XMLHttpRequest'}});
      if (!response.ok) return;
      const data = await response.json();
      if (data.current_activity_url && data.current_activity_url !== knownActivity) location.assign(data.current_activity_url);
      if (data.status !== 'open') location.reload();
    } catch (_) {}
  };
  if (window.ClassbookSocket) window.ClassbookSocket(sessionId, refresh);
  setInterval(refresh, 3000);
})();
