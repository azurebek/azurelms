(() => {
  const root = document.querySelector('[data-teacher-session]');
  if (!root) return;
  const stateUrl = root.dataset.stateUrl;
  const sessionId = root.dataset.sessionId;
  let lastCurrent = null;

  const render = (data) => {
    const attendance = root.querySelector('[data-attendance-count]');
    if (attendance) attendance.textContent = data.attendance_count;
    const pending = root.querySelector('[data-delivery-pending]');
    if (pending) pending.textContent = data.deliveries.queued || 0;
    data.activities.forEach((activity) => {
      const row = root.querySelector(`[data-activity-row="${activity.id}"]`);
      const count = row && row.querySelector('[data-response-count]');
      if (count) count.textContent = activity.responses;
    });
    if (lastCurrent !== null && lastCurrent !== data.current_activity_id) location.reload();
    lastCurrent = data.current_activity_id;
  };
  const refresh = async () => {
    try { const response = await fetch(stateUrl, {headers: {'X-Requested-With': 'XMLHttpRequest'}}); if (response.ok) render(await response.json()); } catch (_) {}
  };
  refresh();
  if (window.ClassbookSocket) window.ClassbookSocket(sessionId, refresh);
  setInterval(refresh, 10000);
})();
