import {valueOf, dirty, blocked, makeRow, receive, rebase, answered, packDraft, acknowledgedKey, clockLabel, prepareListening} from './exam-attempt-state.mjs';

const root = document.querySelector('[data-exam-attempt]');
if (root) initialize();
function initialize() {
  const config = JSON.parse(document.getElementById('exam-attempt-config').textContent);
  const find = selector => root.querySelector(selector);
  const forms = [...root.querySelectorAll('[data-answer]')];
  const rows = {}, files = new Map(), recorders = new Map(), objectUrls = new Map();
  let state = config.state, busy = false, checking = false, leaving = false, activeRequest = null;
  let loadingMedia = null;
  const operationKey = `azurelms:v1:exam:${config.scope}:operation`;
  const draftKey = `azurelms:v1:exam:${config.scope}:${state.attempt_id}:drafts`;
  const read = key => { try { return JSON.parse(sessionStorage.getItem(key)); } catch { return null; } };
  const write = (key, value) => { try { if (value) sessionStorage.setItem(key, JSON.stringify(value)); else sessionStorage.removeItem(key); return true; } catch { tell('Bu brauzer qoralamani saqlay olmadi. Sahifani yopmang.'); return false; } };
  let pending = read(operationKey);
  const restored = read(draftKey) || {};
  const csrf = root.querySelector('[name=csrfmiddlewaretoken]')?.value;
  function tell(message) { find('[data-global-status]').textContent = message; }
  function persist() {
    const drafts = {};
    for (const [key, row] of Object.entries(rows)) if (dirty(row) || row.stale) {
      drafts[key] = packDraft(row);
    }
    write(draftKey, Object.keys(drafts).length ? drafts : null);
    write(operationKey, pending);
  }
  const closed = () => !['in_progress', 'not_started'].includes(state.status) && !find('[data-start]');
  function fill(form, value) {
    for (const input of form.elements) {
      if (input.name === 'answer_text') input.value = value.answer_text;
      if (input.name === 'flagged') input.checked = value.flagged;
      if (input.name === 'choice_id') { if (input.type === 'radio') input.checked = input.value === value.choice_id; else input.value = value.choice_id; }
      if (input.name === 'option_ids') input.checked = value.option_ids.includes(input.value);
    }
  }
  function readForm(form) {
    const data = new FormData(form), row = rows[form.dataset.answer];
    return valueOf({choice_id: data.get('choice_id'), option_ids: data.getAll('option_ids'), answer_text: data.get('answer_text'), flagged: data.has('flagged'), audio_url: row.base.audio_url});
  }
  function render() {
    const locked = Boolean(busy || pending || loadingMedia || closed());
    find('[data-clock]').textContent = state.status === 'not_started' ? 'Hali boshlanmagan' : closed() ? 'Urinish yopilgan' : clockLabel(state.remaining_seconds);
    find('[data-unknown]').hidden = !pending;
    find('[data-closed]').hidden = !closed();
    const start = find('[data-start]');
    if (start) start.querySelector('button[type=submit]').disabled = locked || !start.elements.confirmed.checked;
    const count = Object.values(state.answers).filter(answered).length;
    const total = Object.keys(state.answers).length;
    if (find('[data-counts]')) find('[data-counts]').textContent = `${count} / ${total} javob serverda saqlangan`;
    for (const form of forms) {
      const key = form.dataset.answer, row = rows[key];
      form.querySelector('fieldset').disabled = locked;
      const status = row.stale ? 'Boshqa oynada o‘zgargan — qoralama saqlandi.' : row.audioLost ? 'Audio qoralama qayta ochilganda yo‘qoldi. Faylni qayta tanlang yoki qoralamani bekor qiling.' : row.recording ? 'Ovoz yozilmoqda. Yozishni tugating.' : dirty(row) ? 'Qoralama — hali serverda saqlanmagan.' : answered(row.base) ? 'Serverda saqlangan.' : 'Javobsiz.';
      form.querySelector('[data-answer-status]').textContent = status;
      root.querySelector(`[data-map="${key}"]`).textContent = row.stale ? 'O‘zgargan' : dirty(row) ? 'Qoralama' : row.base.flagged ? 'Tekshirish' : answered(row.base) ? 'Saqlangan' : 'Javobsiz';
      form.querySelector('[data-stale]').hidden = !row.stale;
      form.querySelector('[data-server-answer]').textContent = serverText(key, row.server);
      form.querySelector('[data-rebase]').disabled = locked;
      form.querySelector('[type=submit]').disabled = locked || row.stale || row.recording || row.audioLost || !dirty(row);
      const audio = form.querySelector('[data-saved-audio]');
      if (audio) {
        audio.hidden = !row.server.audio_url;
        if (row.server.audio_url && audio.getAttribute('src') !== row.server.audio_url) audio.src = row.server.audio_url;
        form.querySelector('[data-discard-audio]').hidden = !(row.file || row.audioLost);
      }
    }
    for (const panel of root.querySelectorAll('[data-listening]')) {
      const section = state.sections.find(item => String(item.id) === panel.dataset.listening);
      panel.querySelector('[data-listen]').disabled = locked || !section?.media_url || section.plays_left === 0;
      if (section) panel.querySelector('[data-listen-count]').textContent = `Tinglangan: ${section.plays_used}. ` + (section.plays_left === null ? 'Tinglash cheklanmagan.' : `Qolgan: ${section.plays_left}.`);
    }
    const prepare = find('[data-prepare]');
    if (prepare) {
      prepare.disabled = blocked(rows, pending, busy || loadingMedia, closed());
      find('[data-submit-hint]').textContent = prepare.disabled ? 'Avval qoralama va noma’lum holatlarni hal qiling.' : `${total - count} ta javobsiz savol bor. Saqlangan javoblarni topshirishingiz mumkin.`;
      find('[data-submit-summary]').textContent = `${count} ta javob saqlangan, ${total - count} ta savol javobsiz.`;
    }
  }
  function serverText(key, saved) {
    if (!saved) return '';
    const question = state.sections.flatMap(section => section.questions).find(item => item.key === key);
    const choices = (question?.choices || []).filter(choice => String(choice.id) === saved.choice_id || saved.option_ids.includes(String(choice.id))).map(choice => choice.text);
    return [...choices, saved.answer_text, saved.audio_url ? 'Audio yozuv bor.' : '', saved.flagged ? 'Keyin tekshirish uchun belgilangan.' : ''].filter(Boolean).join('\n') || 'Javobsiz';
  }
  function accept(next, receipt = null, operation = pending) {
    const ack = acknowledgedKey(operation, receipt, next);
    const sameAttempt = next.attempt_id === state.attempt_id;
    state = next;
    if (sameAttempt) for (const form of forms) {
      const key = form.dataset.answer, saved = next.answers[key];
      if (!saved) continue;
      const row = rows[key];
      const wasDirty = dirty(row);
      receive(row, saved, key === ack);
      if (!wasDirty || key === ack) fill(form, row.draft);
      if (key === ack) clearAudio(form);
    }
    if (receipt?.id === operation?.operation_id) pending = null;
    if (!sameAttempt && next.status === 'in_progress') {
      pending = null; persist(); leaving = true; location.reload(); return;
    }
    if (closed()) {
      loadingMedia?.abort();
      for (const recorder of recorders.values()) if (recorder.state !== 'inactive') recorder.stop();
      for (const audio of root.querySelectorAll('audio')) audio.pause();
      find('#exam-submit-dialog')?.close();
    }
    persist(); render();
  }
  async function fetchJSON(url, options) {
    const response = await fetch(url, {credentials: 'same-origin', cache: 'no-store', ...options});
    if (!response.headers.get('content-type')?.includes('application/json')) throw new Error('unconfirmed');
    const data = await response.json();
    if (response.status >= 500) throw new Error('unconfirmed');
    return {response, data};
  }
  async function action(command, payload = {}, file = null) {
    if (busy || pending || loadingMedia || closed()) return;
    if (Object.values(rows).some(row => row.recording)) { tell('Avval ovoz yozishni tugating.'); return; }
    const operation = {command, operation_id: crypto.randomUUID(), operation_epoch: state.operation_epoch, attempt_id: state.attempt_id, ...payload};
    pending = {command, operation_id: operation.operation_id, operation_epoch: operation.operation_epoch, attempt_id: operation.attempt_id, key: operation.key, version: operation.version};
    if (!write(operationKey, pending)) { pending = null; tell('Amalni tiklash yozuvi saqlanmadi. So‘rov yuborilmadi; brauzer xotirasini tekshiring.'); return; }
    const controller = new AbortController(); activeRequest = controller;
    busy = true; persist(); render(); tell('Server javobi kutilmoqda…');
    let body = JSON.stringify(operation), headers = {'X-CSRFToken': csrf, 'Content-Type': 'application/json'};
    if (file) { body = new FormData(); body.set('payload', JSON.stringify(operation)); body.set('audio', file, file.name || 'recording.webm'); delete headers['Content-Type']; }
    try {
      const {response, data} = await fetchJSON(config.url, {method: 'POST', body, headers, signal: controller.signal});
      // An explicit reconciliation may already have closed this in-flight action.
      if (pending?.operation_id !== operation.operation_id) return;
      if (response.ok && data.receipt?.id === operation.operation_id) {
        accept(data.state, data.receipt, operation);
        tell(command === 'save' ? 'Javob serverda saqlandi.' : command === 'submit' ? 'Javoblar topshirildi.' : 'Amal tasdiqlandi.');
        return data;
      }
      if (response.ok) throw new Error('unconfirmed');
      pending = null;
      if (data.state) accept(data.state);
      tell(data.error || 'So‘rov qabul qilinmadi. Qoralama saqlandi.');
      find('#exam-submit-dialog')?.close();
    } catch {
      if (pending?.operation_id === operation.operation_id) tell('Aloqa uzildi yoki tasdiq kelmadi. Qayta yubormang; noma’lum amalni tekshiring.');
    } finally { if (activeRequest === controller) activeRequest = null; busy = false; persist(); render(); }
  }
  async function refresh(reconcile = false) {
    if (checking) return;
    checking = true;
    try {
      const operation = pending;
      const options = reconcile && operation ? {method: 'POST', headers: {'X-CSRFToken': csrf, 'Content-Type': 'application/json'}, body: JSON.stringify({command: 'reconcile', operation_id: operation.operation_id, operation_epoch: operation.operation_epoch})} : {};
      const url = options.method ? config.url : config.url + (operation ? `?operation=${encodeURIComponent(operation.operation_id)}` : '');
      const {response, data} = await fetchJSON(url, options);
      if (!response.ok) { tell(data.error || 'Holatni tekshirib bo‘lmadi.'); return; }
      accept(data.state, data.receipt, operation);
      if (operation && data.receipt?.id === operation.operation_id) activeRequest?.abort();
      tell(data.receipt?.command === 'cancelled' ? 'Amal bajarilmagan; kechikkan so‘rov yopildi. Qoralamangizni qayta ko‘rib saqlashingiz mumkin.' : pending ? 'Amal tasdig‘i hali topilmadi. Noma’lum amalni tekshirib yoping.' : 'Server holati yangilandi.');
    } catch { tell('Server bilan aloqa yo‘q. Qoralama va noma’lum amal saqlandi.'); }
    finally { checking = false; render(); }
  }
  function clearAudio(form) {
    const key = form.dataset.answer, row = rows[key];
    files.delete(key); row.file = false; row.audioLost = false;
    if (objectUrls.has(key)) URL.revokeObjectURL(objectUrls.get(key));
    objectUrls.delete(key);
    const audio = form.querySelector('[data-draft-audio]');
    if (audio) { audio.pause(); audio.removeAttribute('src'); audio.hidden = true; form.elements.audio.value = ''; }
  }
  function chooseAudio(form, file) {
    clearAudio(form);
    const key = form.dataset.answer;
    if (file) {
      files.set(key, file); rows[key].file = true;
      const url = URL.createObjectURL(file); objectUrls.set(key, url);
      const audio = form.querySelector('[data-draft-audio]'); audio.src = url; audio.hidden = false;
    }
    persist(); render();
  }
  for (const form of forms) {
    const key = form.dataset.answer;
    rows[key] = makeRow(state.answers[key], restored[key]); fill(form, rows[key].draft);
    form.addEventListener('input', event => {
      if (event.target.type === 'file') return;
      rows[key].draft = readForm(form); persist(); render();
    });
    form.addEventListener('submit', event => {
      event.preventDefault(); const row = rows[key];
      if (row.stale || row.recording || row.audioLost || !dirty(row)) return;
      action('save', {key, version: row.base.version, value: row.draft}, files.get(key));
    });
    form.querySelector('[data-rebase]').addEventListener('click', () => { rebase(rows[key]); persist(); render(); });
    form.querySelector('[name=audio]')?.addEventListener('change', event => chooseAudio(form, event.target.files[0]));
    form.querySelector('[data-discard-audio]')?.addEventListener('click', () => { clearAudio(form); persist(); render(); });
    const record = form.querySelector('[data-record]');
    if (record) {
      const stop = form.querySelector('[data-stop]'), status = form.querySelector('[data-audio-status]');
      record.addEventListener('click', async () => {
        if (busy || pending || loadingMedia || rows[key].recording) return;
        if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) { status.textContent = 'Bu brauzerda mikrofon qo‘llanmaydi. Audio fayl tanlang.'; return; }
        rows[key].recording = true; record.disabled = true; persist(); render();
        let stream;
        try {
          stream = await navigator.mediaDevices.getUserMedia({audio: true});
          if (closed() || pending || busy) { stream.getTracks().forEach(track => track.stop()); rows[key].recording = false; render(); return; }
          const chunks = [], recorder = new MediaRecorder(stream); recorders.set(key, recorder);
          recorder.addEventListener('dataavailable', event => { if (event.data.size) chunks.push(event.data); });
          recorder.addEventListener('stop', () => {
            stream.getTracks().forEach(track => track.stop()); rows[key].recording = false;
            recorders.delete(key); record.disabled = false; stop.hidden = true;
            const type = recorder.mimeType || 'audio/webm';
            chooseAudio(form, new File(chunks, type.includes('mp4') ? 'recording.m4a' : type.includes('ogg') ? 'recording.ogg' : 'recording.webm', {type}));
            status.textContent = 'Yozuv tayyor. Tinglab tekshiring, keyin alohida saqlang.';
          });
          recorder.addEventListener('error', () => { status.textContent = 'Yozuvda xato. Tayyor audioni tekshiring yoki qayta yozing.'; if (recorder.state !== 'inactive') recorder.stop(); });
          recorder.start(); stop.hidden = false; status.textContent = 'Ovoz yozilmoqda…';
        } catch { stream?.getTracks().forEach(track => track.stop()); rows[key].recording = false; record.disabled = false; status.textContent = 'Mikrofonga ruxsat berilmadi yoki qurilma band. Audio fayl tanlashingiz mumkin.'; persist(); render(); }
      });
      stop.addEventListener('click', () => { const recorder = recorders.get(key); if (recorder?.state !== 'inactive') recorder?.stop(); });
    }
  }
  for (const panel of root.querySelectorAll('[data-listening]')) {
    const player = panel.querySelector('audio'), pause = panel.querySelector('[data-pause]'), status = panel.querySelector('[data-media-status]');
    let preloadController = null, charged = false;
    panel.querySelector('[data-listen]').addEventListener('click', async () => {
      if (busy || pending || loadingMedia || closed()) return;
      if (Object.values(rows).some(row => row.recording)) { tell('Avval ovoz yozishni tugating.'); return; }
      const section = state.sections.find(item => String(item.id) === panel.dataset.listening);
      if (!section?.media_url) return;
      const controller = new AbortController();
      preloadController = loadingMedia = controller; charged = false;
      pause.disabled = false; pause.textContent = 'Yuklashni bekor qilish';
      status.textContent = 'Audio tekshirilmoqda. Hali limit sarflanmadi.'; render();
      try { await prepareListening(player, section.media_url, controller.signal); }
      catch { status.textContent = controller.signal.aborted ? 'Yuklash bekor qilindi. Limit sarflanmadi.' : 'Audio yuklanmadi. Limit sarflanmadi; ustozga xabar bering.'; return; }
      finally { loadingMedia = preloadController = null; pause.disabled = true; pause.textContent = 'Pauza'; render(); }
      if (controller.signal.aborted || closed()) return;
      const data = await action('listen', {section_id: Number(panel.dataset.listening), media_url: section.media_url});
      if (!data) return;
      charged = true; player.currentTime = 0;
      try { await player.play(); pause.disabled = false; pause.textContent = 'Pauza'; status.textContent = 'Tinglanmoqda. Bu boshlash limitdan hisoblandi.'; }
      catch { status.textContent = 'Audio boshlanmadi, urinish hisoblandi. Davom ettirishni bosing.'; pause.disabled = false; pause.textContent = 'Davom ettirish'; }
    });
    pause.addEventListener('click', async () => {
      if (preloadController) { preloadController.abort(); return; }
      if (closed() || player.ended) return;
      if (player.paused) { try { await player.play(); pause.textContent = 'Pauza'; } catch { status.textContent = 'Audio ochilmadi. Holatni tekshiring.'; } }
      else { player.pause(); pause.textContent = 'Davom ettirish'; }
    });
    player.addEventListener('ended', () => { pause.disabled = true; status.textContent = 'Tinglash tugadi. Qayta boshlash yana limitdan hisoblanadi.'; });
    player.addEventListener('error', () => { if (charged) status.textContent = 'Audio uzildi. Tinglash urinishi hisoblangan; avtomatik qaytarilmaydi.'; });
  }
  const start = find('[data-start]');
  start?.addEventListener('change', render);
  start?.addEventListener('submit', event => { event.preventDefault(); action('start', {confirmed: start.elements.confirmed.checked}); });
  const dialog = find('#exam-submit-dialog');
  find('[data-prepare]')?.addEventListener('click', () => {
    if (blocked(rows, pending, busy || loadingMedia, closed())) return;
    dialog.querySelector('[name=confirmed]').checked = false; dialog.showModal();
  });
  for (const button of root.querySelectorAll('[data-dialog-close]')) button.addEventListener('click', () => dialog.close());
  find('[data-submit]')?.addEventListener('submit', event => {
    event.preventDefault();
    if (blocked(rows, pending, busy || loadingMedia, closed())) { dialog.close(); return; }
    action('submit', {version: state.revision, confirmed: event.target.elements.confirmed.checked});
  });
  find('[data-refresh]').addEventListener('click', () => refresh());
  find('[data-reconcile]').addEventListener('click', () => refresh(true));
  window.addEventListener('beforeunload', event => {
    if (!leaving && (pending || busy || Object.values(rows).some(dirty))) { persist(); event.preventDefault(); event.returnValue = ''; }
  });
  window.addEventListener('pagehide', () => { loadingMedia?.abort(); for (const recorder of recorders.values()) if (recorder.state !== 'inactive') recorder.stop(); });
  persist(); render();
  if (pending) refresh();
}
