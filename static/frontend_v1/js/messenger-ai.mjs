// AI presentation only. The existing socket/task/preferences own all policy.
export const retryAllowed = run => !!run && ['failed', 'fallback', 'succeeded'].includes(run.status);
export function mergeRun(previous, incoming) {
  if (!incoming?.user_message_id) return previous;
  if (previous?.run_id && incoming.run_id && Number(incoming.run_id) < Number(previous.run_id)) return previous;
  // A retry has no durable receipt until a newer canonical run appears.
  if (previous?.status === 'unknown' && previous.awaiting_after && Number(incoming.run_id || 0) <= previous.awaiting_after) return previous;
  if (previous?.run_id && incoming.run_id === previous.run_id && retryAllowed(previous) && ['pending', 'running'].includes(incoming.status)) return previous;
  return {user_message_id: incoming.user_message_id, status: incoming.status,
    run_id: incoming.run_id, ai_message_id: incoming.ai_message_id};
}
export function initAI({root, q, element, button, api, post, render, refresh, transmit, storage, key, showNotice, isReady}) {
  const runs = new Map(), feedback = new Map();
  let saved;
  try { saved = JSON.parse(storage(store => store.getItem(key + ':ai')) || '[]'); } catch { saved = []; }
  if (Array.isArray(saved)) for (const run of saved) if (run?.user_message_id) runs.set(Number(run.user_message_id), run);
  const persist = () => storage(store => store.setItem(key + ':ai', JSON.stringify([...runs.values()].slice(-100))));
  const absorb = incoming => {
    const id = Number(incoming.user_message_id);
    if (!id) return;
    runs.set(id, mergeRun(runs.get(id), incoming)); persist();
  };
  const labels = {pending: 'AI navbatda', running: 'AI javob tayyorlayapti…', succeeded: 'AI javobi tayyor', fallback: 'Cheklangan javob — limit yoki xizmat holatini javobdan tekshiring', failed: 'AI javobi olinmadi', unknown: 'AI holati hali tasdiqlanmadi'};
  const retryDialog = q('[data-ai-retry-dialog]');
  function askRetry(id) {
    if (!isReady() || !retryAllowed(runs.get(Number(id)))) return;
    q('[data-message-menu]').close();
    retryDialog.dataset.message = id; retryDialog.returnValue = ''; retryDialog.showModal();
  }
  retryDialog.addEventListener('close', () => {
    if (retryDialog.returnValue !== 'retry') return;
    retryDialog.returnValue = '';
    const id = Number(retryDialog.dataset.message), previous = runs.get(id);
    if (!isReady() || !retryAllowed(previous)) return;
    runs.set(id, {user_message_id: id, status: 'unknown', awaiting_after: Number(previous.run_id || 0)}); persist(); render();
    try { transmit({action: 'retry_ai_response', user_message_id: id}); }
    catch { showNotice('Qayta so‘rash tasdiqlanmadi. Tarix holatini yangilang; so‘rov takrorlanmaydi.'); }
  });
  for (const form of document.querySelectorAll('[data-ai-preference]')) {
    form.addEventListener('submit', async event => {
      event.preventDefault(); const submit = form.querySelector('[type=submit]');
      if (submit.disabled) return;
      const select = form.querySelector('select'), status = form.querySelector('[data-preference-status]');
      submit.disabled = true; select.disabled = true; status.textContent = 'Saqlanmoqda…';
      // Django's canonical preference endpoints accept form data, not JSON.
      const body = new FormData(form); body.set(select.name, select.value);
      try {
        const result = await api(form.action, {method: 'POST', body, headers: {'Accept': 'application/json'}});
        select.value = result[select.name]; status.textContent = 'Saqlandi. Keyingi xabarda ishlaydi.';
        submit.disabled = false; select.disabled = false;
        if (document.activeElement === document.body) submit.focus();
      } catch (error) { status.textContent = `${error.message} Qayta bosmang; sahifani yangilab saqlangan holatni tekshiring.`; }
    });
  }
  q('[data-new-chat]')?.addEventListener('submit', event => {
    const submit = event.currentTarget.querySelector('[type=submit]');
    if (submit.disabled) event.preventDefault(); else submit.disabled = true;
  });
  function actions(message, bubble) {
    if (message.is_deleted) return;
    const id = Number(message.id || message.message_id);
    bubble.append(button('Nusxa olish', async () => {
      try { await navigator.clipboard.writeText(message.message ?? message.text ?? ''); showNotice('Xabar nusxalandi.'); q('[data-message-menu]').close(); }
      catch { showNotice('Nusxa olinmadi. Xabar matnini belgilab nusxalang.'); }
    }));
    if (!message.is_ai) {
      if (String(message.sender_id) !== root.dataset.userId) return;
      const run = runs.get(id), panel = element('div', '', 's-mw-ai-state');
      const status = element('small', labels[run?.status] || labels.unknown); status.setAttribute('role', 'status'); panel.append(status);
      const check = button('AI holatini yangilash', () => refresh()); check.dataset.aiCheck = id;
      panel.append(check);
      if (retryAllowed(run)) { const retry = button('AI javobini qayta so‘rash', () => askRetry(id)); retry.dataset.aiRetry = id; retry.disabled = !isReady(); panel.append(retry); }
      bubble.append(panel); return;
    }
    const state = feedback.get(id) || {}, controls = element('div', '', 's-mw-actions');
    const current = state.result || message;
    for (const [rating, label, total] of [[1, 'Foydali', 'positive'], [-1, 'Foydasiz', 'negative']]) {
      const vote = button(`${label} · ${current.feedback_totals?.[total] || 0}`, async () => {
        if (feedback.get(id)?.busy) return;
        feedback.set(id, {...state, busy: true, note: 'Saqlanmoqda…'}); render();
        try {
          const result = await post(root.dataset.feedbackUrl.replace('/0/', `/${id}/`), {rating});
          feedback.set(id, {result, note: 'Baho saqlandi.'});
        } catch (error) { feedback.set(id, {busy: true, note: `${error.message} Sahifani yangilab tekshiring.`}); }
        render();
      });
      vote.dataset.aiVote = `${id}:${rating}`; vote.setAttribute('aria-pressed', String(current.feedback?.rating === rating)); vote.disabled = !!state.busy;
      controls.append(vote);
    }
    if (state.note) { const note = element('span', state.note); note.setAttribute('role', 'status'); controls.append(note); }
    bubble.append(controls);
    const promptId = Number(message.regenerate_user_message_id);
    if (promptId && retryAllowed(runs.get(promptId))) {
      const retry = button('AI javobini qayta so‘rash', () => askRetry(promptId)); retry.disabled = !isReady(); bubble.append(retry);
    }
    if (message.ai_skill_label) bubble.append(element('small', `Mashq: ${message.ai_skill_label}`, 's-mw-message-meta'));
    if (Array.isArray(message.ai_used_tools) && message.ai_used_tools.length) bubble.append(element('small', `Vositalar: ${message.ai_used_tools.join(', ')}`, 's-mw-message-meta'));
    const sources = Array.isArray(message.ai_rag_sources) ? message.ai_rag_sources : [];
    if (sources.length) {
      const details = element('details'), items = element('ul'); details.append(element('summary', 'Javob manbalari'));
      for (const source of sources.slice(0, 4)) items.append(element('li', source.label || [source.course_title, source.module_title, source.lesson_title].filter(Boolean).join(' › ')));
      details.append(items); bubble.append(details);
    }
  }
  return {
    actions,
    connectionLabel() {
      const latest = [...runs.values()].sort((a, b) => Number(b.user_message_id) - Number(a.user_message_id))[0];
      return latest && latest.status !== 'succeeded' ? labels[latest.status] : '';
    },
    hydrate(data) { for (const run of data.ai_runs || []) absorb(run); },
    event(message) {
      if (message.event_type === 'ai_status') { absorb(message); render(); return; }
      if (message.room_name) {
        const link = q(`[data-ai-room="${root.dataset.roomId}"]`);
        if (link) { link.querySelector('strong').textContent = message.room_name; link.querySelector('.s-mw-preview').textContent = message.message || message.text || ''; }
      }
      if (message.is_ai && message.regenerate_user_message_id) {
        const id = Number(message.regenerate_user_message_id), previous = runs.get(id);
        // Don't overwrite a newer explicit retry with an old message update.
        if (!previous?.awaiting_after && !retryAllowed(previous)) absorb({user_message_id: id, status: 'succeeded', run_id: previous?.run_id});
      }
    },
    payload() { return root.dataset.contextLesson ? {context_lesson_id: Number(root.dataset.contextLesson)} : {}; },
  };
}
