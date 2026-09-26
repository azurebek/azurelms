(() => {
  'use strict';
  // No grade/access decisions here. Only server acknowledgement and UI state.
  function answerFlow({send, read, changed, online}) {
    const state = {busy:false, unknown:false, submitted:false, blocked:true, message:''};
    let reading = false;
    const emit = () => changed({...state});
    const refresh = async () => {
      if (reading) return;
      reading = true;
      try {
        const data = await read();
        if (typeof data.submitted !== 'boolean' || typeof data.enabled !== 'boolean' || typeof data.expired !== 'boolean' || !['open', 'closed', 'revealed'].includes(data.status) || !['open', 'closed'].includes(data.session_status)) throw Error('Invalid state');
        if (data.submitted === true) { state.submitted = true; state.unknown = false; state.message = 'Serverda javobingiz qabul qilingan. Natijani ustoz ochadi.'; }
        state.blocked = data.enabled !== true || data.status !== 'open' || data.session_status !== 'open' || data.expired === true;
        if (state.unknown && !state.submitted) state.message = 'Yuborish natijasi noma’lum. Qayta yubormang; holatni tekshiring. Qoralama shu sahifada qoladi.';
        else if (state.blocked && !state.submitted) state.message = 'Mashq javob qabul qilmayapti. Qoralama shu sahifada qoladi.';
        if (data.status === 'revealed') state.message = 'Natija e’lon qilindi. Uni quyidagi havola orqali oching.';
        emit();
        return data;
      } catch (_) { state.blocked = true; emit(); throw _; }
      finally { reading = false; }
    };
    const submit = async answer => {
      if (state.busy || state.unknown || state.submitted || state.blocked) return;
      if (!online()) { state.message = 'Aloqa yo‘q. Javob yuborilmadi; qoralama saqlanib turibdi.'; emit(); return; }
      state.busy = true; state.message = 'Javob yuborilmoqda…'; emit();
      try {
        const data = await send(answer);
        if (typeof data.ok !== 'boolean' || typeof data.message !== 'string') throw Error('Invalid acknowledgement');
        if (data.ok === true) { state.submitted = true; state.unknown = false; }
        if (!state.submitted || data.ok === true) state.message = data.message;
        if (data.code && !['submitted', 'already_submitted', 'invalid_answer'].includes(data.code)) state.blocked = true;
      } catch (_) {
        if (!state.submitted) { state.unknown = true; state.message = 'Yuborish natijasi noma’lum. Qayta yubormang; holatni tekshiring.'; }
      } finally { state.busy = false; emit(); }
    };
    return {state, refresh, submit};
  }

  function renderExercise(document, renderer, exercise) {
    const node = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; };
    const kind = exercise.kind, config = exercise.config;
    const inputs = [];
    let order = [];
    const select = (id, options) => {
      const input = node('select', 'c-field'); input.name = id; input.required = true;
      const blank = node('option', '', 'Tanlang'); blank.value = ''; input.append(blank);
      for (const item of options) { const option = node('option', '', item.text); option.value = item.id; input.append(option); }
      inputs.push(input); return input;
    };
    if (['single_choice', 'multiple_choice', 'true_false', 'poll'].includes(kind)) {
      for (const item of config.options) {
        const label = node('label', 'c-choice'), input = node('input');
        input.type = kind === 'multiple_choice' ? 'checkbox' : 'radio'; input.name = 'answer'; input.value = item.id;
        if (input.type === 'radio') input.required = true;
        inputs.push(input); label.append(input, node('span', '', item.text)); renderer.append(label);
      }
    } else if (['short_answer', 'fill_blank'].includes(kind)) {
      const label = node('label', 'f-classbook-form', 'Javob matni');
      const input = node('textarea', 'c-field'); input.name = 'answer'; input.required = true;
      input.maxLength = 2000; input.rows = 3; input.autocomplete = 'off'; inputs.push(input); label.append(input); renderer.append(label);
    } else if (['matching', 'categorization'].includes(kind)) {
      const rows = kind === 'matching' ? config.left : config.items;
      const options = kind === 'matching' ? config.right : config.categories;
      for (const item of rows) { const label = node('label', 'f-classbook-map'); label.append(node('span', '', item.text), select(item.id, options)); renderer.append(label); }
    } else if (['ordering', 'unscramble'].includes(kind)) {
      order = config.items.map(item => item.id);
      const draw = (focusIndex, direction) => {
        renderer.replaceChildren();
        order.forEach((id, index) => {
          const item = config.items.find(item => item.id === id), row = node('div', 'f-classbook-order');
          row.append(node('b', '', String(index + 1)), node('span', '', item.text));
          const controls = node('span', 'f-classbook-order-controls');
          for (const [delta, symbol, label] of [[-1, '↑', 'yuqoriga'], [1, '↓', 'pastga']]) {
            const button = node('button', 'c-icon-button', symbol); button.type = 'button';
            button.setAttribute('aria-label', `${item.text}: ${label}`);
            button.disabled = index + delta < 0 || index + delta >= order.length;
            button.addEventListener('click', () => {
              [order[index], order[index + delta]] = [order[index + delta], order[index]];
              draw(index + delta, delta);
              renderer.dispatchEvent(new Event('change', {bubbles:true}));
            });
            controls.append(button);
            if (index === focusIndex && delta === direction) queueMicrotask(() => {
              if (!button.disabled) button.focus(); else controls.querySelector('button:not(:disabled)')?.focus();
            });
          }
          row.append(controls); renderer.append(row);
        });
      };
      draw();
    } else { throw Error('Unsupported exercise'); }
    return () => {
      if (['single_choice', 'true_false', 'poll'].includes(kind)) return inputs.find(input => input.checked)?.value || null;
      if (kind === 'multiple_choice') return inputs.filter(input => input.checked).map(input => input.value);
      if (['short_answer', 'fill_blank'].includes(kind)) return inputs[0].value;
      if (['matching', 'categorization'].includes(kind)) return Object.fromEntries(inputs.map(input => [input.name, input.value]));
      return [...order];
    };
  }
  if (typeof module !== 'undefined') module.exports = {answerFlow, renderExercise};
  if (typeof document === 'undefined') return;
  const root = document.querySelector('[data-classbook-live]');
  if (!root) return;
  const $ = selector => root.querySelector(selector);
  const status = $('[data-live-status]'), reload = $('[data-live-reload]');
  const mode = root.dataset.classbookLive;
  const request = async (url, options = {}) => {
    const controller = new AbortController();
    // Transport timeout, not an owner-configurable lesson duration.
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(url, {...options, signal:controller.signal, credentials:'same-origin', cache:'no-store', headers:{'X-Classbook-V1':'1', ...options.headers}});
      if (response.redirected || response.status >= 500 || [401, 403, 404].includes(response.status)) throw Error('Unavailable');
      const data = await response.json();
      if (typeof data !== 'object' || data === null || Array.isArray(data)) throw Error('Invalid response');
      if (!options.method && !response.ok) throw Error('Unavailable');
      return data;
    } finally { clearTimeout(timeout); }
  };
  const read = () => request(root.dataset.stateUrl);
  let flow = null, dirty = false, collecting = null, activityEnded = false;
  if (mode === 'activity') {
    const exercise = JSON.parse(document.getElementById('classbook-live-payload').textContent);
    const form = $('[data-live-answer]'), fields = $('[data-live-fields]'), button = $('[data-live-submit]');
    flow = answerFlow({read, online:() => navigator.onLine !== false,
      send:answer => request(root.dataset.submitUrl, {method:'POST', headers:{'Content-Type':'application/json', 'X-CSRFToken':form.querySelector('[name=csrfmiddlewaretoken]').value}, body:JSON.stringify({answer, revision:exercise.revision})}),
      changed:state => {
        $('[data-answer-status]').textContent = state.message;
        if (button) button.disabled = state.busy || state.unknown || state.submitted || state.blocked;
        if (fields) fields.disabled = state.busy || state.unknown || state.submitted;
        if (form) form.setAttribute('aria-busy', String(state.busy));
        if (state.submitted) dirty = false;
      }});
    flow.state.submitted = root.dataset.submitted === '1';
    if (form) {
      try { collecting = renderExercise(document, $('[data-live-renderer]'), exercise); }
      catch (_) { $('[data-answer-status]').textContent = 'Mashq formasi ochilmadi. Sahifani qayta oching.'; return; }
      form.addEventListener('input', () => {dirty = true;});
      form.addEventListener('change', () => {dirty = true;});
      form.addEventListener('submit', event => {event.preventDefault(); dirty = true; flow.submit(collecting());});
    }
    const deadline = Date.parse(exercise.closes_at);
    const tick = () => {
      const left = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      $('[data-live-timer]').textContent = activityEnded ? 'Yakunlangan' : Number.isFinite(left) ? `${Math.floor(left / 60)}:${String(left % 60).padStart(2, '0')}` : 'Server vaqti';
      // Local clock is indicative; only server state blocks acceptance.
    };
    tick(); setInterval(tick, 1000);
    window.addEventListener('beforeunload', event => {
      if (dirty || flow.state.busy || flow.state.unknown) {event.preventDefault(); event.returnValue = '';}
    });
  }
  let busy = false, lastActivities = '', lastRanking = '';
  const refresh = async () => {
    if (busy) return;
    busy = true;
    try {
      const data = flow ? await flow.refresh() : await read();
      if (!data) return;
      status.textContent = data.enabled ? 'Server holati tekshirildi.' : 'Yangi ko‘rinish o‘chirilgan. Sahifani qayta oching.';
      if (!data.enabled) reload.hidden = false;
      if (mode === 'activity') {
        activityEnded = data.status !== 'open' || data.session_status !== 'open';
        $('[data-live-result]').hidden = data.status !== 'revealed';
      } else if (mode === 'teacher') {
        $('[data-attendance-count]').textContent = data.attendance_count;
        $('[data-delivery-pending]').textContent = data.deliveries.queued || 0;
        $('[data-delivery-failed]').textContent = data.deliveries.failed || 0;
        for (const activity of data.activities) {
          const row = root.querySelector(`[data-activity-row="${activity.id}"]`);
          if (row) row.querySelector('[data-response-count]').textContent = activity.responses;
        }
        const ranking = JSON.stringify(data.leaderboard);
        if (ranking !== lastRanking) {
          const list = $('[data-live-leaderboard]'); list.replaceChildren();
          for (const row of data.leaderboard) {
            const li = document.createElement('li'), name = document.createElement('strong'), score = document.createElement('span');
            name.textContent = `${row.rank}. ${row.name}`; score.textContent = `${row.score} ball`;
            li.append(name, score); list.append(li);
          }
          if (!data.leaderboard.length) {const li = document.createElement('li'); li.textContent = 'Hali natija yo‘q.'; list.append(li);}
          lastRanking = ranking;
        }
        if (data.revision !== root.dataset.revision || !data.enabled) {
          reload.hidden = false; status.textContent = 'Dars holati o‘zgargan. Amaldan oldin joriy sahifani qayta oching.';
          root.querySelectorAll('[data-live-action] button[type=submit]').forEach(button => {button.disabled = true;});
        }
      } else if (mode === 'session') {
        $('[data-session-heading]').textContent = data.status === 'open' ? 'Dars davom etmoqda' : 'Dars yakunlandi';
        const list = $('[data-live-activities]'), signature = JSON.stringify(data.activities);
        if (signature !== lastActivities) {
          if (list.contains(document.activeElement)) {reload.hidden = false; return;}
          list.replaceChildren();
          for (const item of data.activities) {
            const li = document.createElement('li'), title = document.createElement('strong'), link = document.createElement('a');
            title.textContent = item.title; link.textContent = item.status === 'open' ? 'Mashqni ochish' : 'Natijani ko‘rish';
            link.className = 'c-button c-button--secondary'; link.href = item.url;
            li.append(title, link); list.append(li);
          }
          if (!data.activities.length) {const li = document.createElement('li'); li.textContent = 'Ustoz keyingi mashqni ochishini kuting.'; list.append(li);}
          lastActivities = signature;
        }
      }
    } catch (_) {status.textContent = 'Holat olinmadi. Aloqa yoki kirishni tekshiring; avtomatik yuborish yo‘q.';}
    finally {busy = false;}
  };
  $('[data-live-refresh]').addEventListener('click', refresh);
  window.addEventListener('online', refresh);
  window.addEventListener('pageshow', refresh);
  document.addEventListener('visibilitychange', () => {if (!document.hidden) refresh();});
  if (window.ClassbookSocket) window.ClassbookSocket(root.dataset.sessionId, refresh);
  // Existing canonical polling cadence; no new owner timing policy.
  setInterval(() => {if (!document.hidden) refresh();}, mode === 'teacher' ? 10000 : 3000);
  refresh();
})();
