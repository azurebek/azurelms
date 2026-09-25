const root = document.querySelector('[data-chat-root]');
if (root) {
  // The template supplies a manifest-hashed module URL (also in production).
  const {prefix, draftKey, parseDraft, canSend, confirms, mergeMessages, composeShortcut} = await import(root.dataset.stateUrl);
  const q = selector => document.querySelector(selector);
  const room = root.dataset.roomId, user = root.dataset.userId;
  const history = q('[data-history]'), list = q('[data-messages]'), notice = q('[data-notice]');
  const composer = q('[data-composer]'), input = q('#chat-message'), file = q('[data-file]');
  const latest = q('[data-latest]'), older = q('[data-older]');
  let socket, retryTimer, ackTimer, attempts = 0, stopped = false, loaded = false, blocked = false;
  let messages = [], cursor = null, historyBusy = false, eventBuffer = [], historyVersion = 0;
  let storageOK = true, mutationBusy = false;
  const key = draftKey(root.dataset.scope, room);
  const storage = fn => { try { return fn(sessionStorage); } catch { storageOK = false; return null; } };
  storage(store => {
    for (let i = store.length - 1; i >= 0; i--) {
      const name = store.key(i);
      if (name.startsWith(prefix) && !name.startsWith(prefix + root.dataset.scope + ':')) store.removeItem(name);
    }
  });
  const draft = parseDraft(storage(store => store.getItem(key)));
  const save = () => {
    if (input) draft.text = input.value;
    storage(store => store.setItem(key, JSON.stringify(draft)));
    if (q('[data-draft-status]')) q('[data-draft-status]').textContent = storageOK ? 'Enter — yangi qator · matn shu tabda saqlanadi' : 'Matnni nusxalang: brauzer qoralamani saqlay olmadi.';
  };
  const element = (tag, text, className) => {
    const node = document.createElement(tag); node.textContent = text || '';
    if (className) node.className = className;
    return node;
  };
  const button = (text, action) => {
    const node = element('button', text, 'c-button c-button--secondary'); node.type = 'button';
    node.addEventListener('click', action); return node;
  };
  const showNotice = (text = '', action = null, label = '') => {
    notice.replaceChildren(element('span', text)); notice.hidden = !text;
    if (action) notice.append(button(label, action));
  };
  const csrf = () => composer.querySelector('[name=csrfmiddlewaretoken]').value;
  const api = async (url, options = {}) => {
    const response = await fetch(url, {credentials: 'same-origin', cache: 'no-store', signal: AbortSignal.timeout(20000), ...options});
    if (response.redirected || [401, 403].includes(response.status)) {
      blocked = true; socket?.close(); update();
      throw Object.assign(new Error('Kirish muddati yoki ruxsat yakunlandi. Sahifani yangilang.'), {definite: true});
    }
    let data;
    try { data = await response.json(); } catch { throw new Error('Server javobi tasdiqlanmadi.'); }
    if (!response.ok || data.status !== 'success') throw Object.assign(new Error(typeof data.message === 'string' ? data.message : 'Amal bajarilmadi.'), {definite: response.status >= 400 && response.status < 500});
    return data;
  };
  const post = (url, data) => api(url, {method: 'POST', headers: {'X-CSRFToken': csrf(), 'Content-Type': 'application/json'}, body: JSON.stringify(data)});
  function update() {
    if (!composer) return;
    const ready = socket?.readyState === WebSocket.OPEN;
    const locked = !!(blocked || draft.pending);
    input.disabled = blocked;
    input.readOnly = locked;
    q('[data-attach]').disabled = !ready || !loaded || locked;
    q('[data-file-clear]').disabled = locked;
    composer.querySelector('[type=submit]').disabled = !canSend({connected: ready, loaded, blocked, pending: draft.pending, text: input.value, file: file.files[0]});
    q('[data-connection]').textContent = blocked ? 'Kirish huquqi yakunlangan' : ready && loaded ? 'Ulangan' : 'Ulanish kutilmoqda';
  }
  function unknown() {
    showNotice('Yuborish tasdiqlanmadi. Tarixni tekshiring; qayta yuborilmaydi.', () => {
      q('[data-unknown-dialog] input').checked = false;
      q('[data-unknown-dialog]').showModal();
    }, 'Holatni ko‘rish');
    update();
  }
  const atBottom = () => history.scrollHeight - history.scrollTop - history.clientHeight < 64;
  const bottom = () => { history.scrollTop = history.scrollHeight; latest.hidden = true; };
  const resize = () => { if (input) { input.style.height = 'auto'; input.style.height = input.scrollHeight + 'px'; } };
  const viewport = () => { document.documentElement.style.setProperty('--mw-viewport', `${window.visualViewport?.height || window.innerHeight}px`); resize(); };
  window.visualViewport?.addEventListener('resize', viewport); window.addEventListener('resize', viewport); viewport();
  const roomView = () => { root.dataset.view = location.hash === '#rooms' ? 'rooms' : 'chat'; };
  window.addEventListener('hashchange', () => { roomView(); (root.dataset.view === 'rooms' ? q('#rooms-title') : q('#chat-title')).focus(); });
  q('#chat-title').tabIndex = -1; roomView();
  q('#room-search').addEventListener('input', event => {
    let count = 0;
    root.querySelectorAll('[data-room-link]').forEach(link => { link.hidden = !link.textContent.toLocaleLowerCase().includes(event.target.value.toLocaleLowerCase()); if (!link.hidden) count++; });
    q('[data-no-results]').hidden = count > 0;
  });
  document.querySelectorAll('[data-close]').forEach(node => node.addEventListener('click', () => { if (!mutationBusy) node.closest('dialog').close(); }));
  q('[data-info]')?.addEventListener('click', () => q('[data-info-dialog]').showModal());
  latest.addEventListener('click', bottom);
  history.addEventListener('scroll', () => { latest.hidden = atBottom(); storage(store => store.setItem(key + ':scroll', String(history.scrollTop))); });
  function render() {
    const stick = atBottom(), top = history.scrollTop;
    list.replaceChildren();
    if (!messages.length) list.append(element('li', 'Hali xabar yo‘q. Suhbatni boshlashingiz mumkin.', 's-mw-empty'));
    for (const m of messages) {
      const item = element('li', '', 's-mw-message'), id = m.id || m.message_id;
      item.dataset.messageId = id;
      if (String(m.sender_id) === user && !m.is_ai) item.dataset.own = '';
      const bubble = element('div', '', 's-mw-bubble');
      bubble.append(element('strong', m.sender_name, 's-mw-author'), element('p', m.message ?? m.text));
      if (m.attachment && !m.is_deleted) {
        // Server private-media URL only; never render an untrusted arbitrary URL.
        const url = new URL(m.attachment.url, location.origin);
        if (url.origin === location.origin && url.pathname.startsWith('/messenger/attachment/')) {
          const link = element('a', `${m.attachment.name} · ${m.attachment.size_label || 'Fayl'}`, 'c-text-link');
          link.href = url.href; link.target = '_blank'; link.rel = 'noopener'; bubble.append(link);
        }
      }
      bubble.append(element('small', `${m.created_at || ''}${m.edited_at ? ' · tahrirlangan' : ''}`, 's-mw-message-meta'));
      if (String(m.sender_id) === user && !m.is_ai && !m.is_deleted) {
        const actions = element('div', '', 's-mw-actions');
        actions.append(button('Tahrirlash', () => manage(id, 'edit')), button('O‘chirish', () => manage(id, 'delete')));
        bubble.append(actions);
      }
      item.append(bubble); list.append(item);
    }
    if (stick) bottom(); else { history.scrollTop = top; latest.hidden = false; }
  }
  async function refresh(earlier = false) {
    if (!room || historyBusy || blocked) return;
    historyBusy = true; older.disabled = true;
    const version = ++historyVersion, previousHeight = history.scrollHeight, previousTop = history.scrollTop;
    if (!earlier) eventBuffer = [];
    try {
      const data = await api(root.dataset.historyUrl + (earlier ? `?before=${cursor}` : ''));
      if (version !== historyVersion || blocked) return;
      messages = mergeMessages(earlier ? messages : [], data.messages);
      messages = mergeMessages(messages, eventBuffer); eventBuffer = [];
      cursor = data.before; older.hidden = !data.has_more;
      const first = !loaded;
      const savedScroll = first ? storage(store => store.getItem(key + ':scroll')) : null;
      loaded = true; render();
      if (earlier) history.scrollTop = previousTop + history.scrollHeight - previousHeight;
      else if (first) {
        if (savedScroll !== null) history.scrollTop = Number(savedScroll); else bottom();
      }
      if (draft.pending) unknown(); else showNotice();
    } catch (error) { showNotice(error.message || 'Tarixni yuklab bo‘lmadi.', () => { if (blocked) location.reload(); else refresh(); }, 'Yangilash'); }
    finally { historyBusy = false; older.disabled = false; update(); }
  }
  older.addEventListener('click', () => refresh(true));
  function connect() {
    if (stopped || blocked || !room || socket?.readyState === WebSocket.OPEN || socket?.readyState === WebSocket.CONNECTING) return;
    clearTimeout(retryTimer);
    socket = new WebSocket(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws/chat/${room}/`);
    socket.addEventListener('open', () => { attempts = 0; refresh(); update(); });
    socket.addEventListener('message', event => {
      let m; try { m = JSON.parse(event.data); } catch { return; }
      if (m.type === 'access_revoked') { blocked = true; showNotice(m.message); socket.close(); update(); return; }
      if (m.event_type === 'ai_status') {
        // Existing @azure mentions may produce status events even in human rooms.
        if (!draft.pending) showNotice(m.message || (m.status === 'failed' ? 'AI javobi olinmadi. Azure AI bo‘limini tekshiring.' : ''));
        return;
      }
      if (m.room_id && String(m.room_id) !== room) return;
      if (!(m.id || m.message_id)) return;
      if (historyBusy) eventBuffer.push(m);
      messages = mergeMessages(messages, [m]); render();
      if (confirms(draft.pending, m, user, room)) {
        clearTimeout(ackTimer); draft.pending = null; input.value = ''; save(); resize(); showNotice(); bottom();
      }
      update();
    });
    socket.addEventListener('close', event => {
      if (event.code === 4403) blocked = true;
      loaded = false; update();
      if (stopped) return;
      if (blocked) { showNotice('Suhbatga kirish huquqi yakunlandi. Sahifani yangilang.'); return; }
      if (draft.pending) unknown();
      else showNotice('Aloqa uzildi. Matn saqlanadi; xabar o‘zicha yuborilmaydi.', () => { attempts = 0; connect(); }, 'Qayta ulanish');
      if (attempts < 6) retryTimer = setTimeout(connect, Math.min(1000 * 2 ** attempts++, 30000));
    });
    socket.addEventListener('error', () => update());
  }
  if (composer) {
    input.value = draft.text; input.disabled = false; resize(); save(); update(); refresh(); connect();
    if (draft.pending) unknown();
    input.addEventListener('input', () => { resize(); save(); update(); });
    input.addEventListener('keydown', event => { if (composeShortcut(event)) { event.preventDefault(); composer.requestSubmit(); } });
    q('[data-attach]').addEventListener('click', () => file.click());
    const fileChange = () => {
      q('[data-file-row]').hidden = !file.files.length;
      q('[data-file-name]').textContent = file.files[0] ? `${file.files[0].name} · Izoh 1000 belgigacha. Fayl reload’da tiklanmaydi.` : '';
      input.maxLength = file.files.length ? 1000 : 4000; update();
    };
    file.addEventListener('change', fileChange);
    q('[data-file-clear]').addEventListener('click', () => { file.value = ''; fileChange(); });
    composer.addEventListener('submit', async event => {
      event.preventDefault();
      if (!canSend({connected: socket?.readyState === WebSocket.OPEN, loaded, blocked, pending: draft.pending, text: input.value, file: file.files[0]})) return;
      if (file.files.length && input.value.length > 1000) { showNotice('Fayl izohini 1000 belgigacha qisqartiring. Matningiz saqlandi.'); return; }
      draft.pending = {id: crypto.randomUUID(), kind: file.files.length ? 'file' : 'text'}; save(); update();
      showNotice('Yuborilmoqda… Tasdiq kutilmoqda.');
      if (!file.files.length) {
        try { socket.send(JSON.stringify({action: 'message', message: input.value.trim(), client_message_id: draft.pending.id})); ackTimer = setTimeout(unknown, 15000); }
        catch { unknown(); }
      } else {
        const form = new FormData(); form.set('room_id', room); form.set('text', input.value); form.set('file', file.files[0]);
        try {
          const result = await api(root.dataset.uploadUrl, {method: 'POST', headers: {'X-CSRFToken': csrf()}, body: form});
          messages = mergeMessages(messages, [result.message]); render(); draft.pending = null;
          input.value = ''; file.value = ''; fileChange(); save(); resize(); showNotice(); bottom();
        } catch (error) {
          if (error.definite) { draft.pending = null; save(); showNotice(error.message); } else unknown();
        }
        update();
      }
    });
    q('[data-unknown-dialog]').addEventListener('close', () => {
      const dialog = q('[data-unknown-dialog]');
      if (dialog.returnValue !== 'discard') return;
      dialog.returnValue = ''; clearTimeout(ackTimer); draft.pending = null; input.value = ''; file.value = ''; fileChange(); save(); resize(); showNotice(); update(); input.focus();
    });
    q('[data-pin]').addEventListener('click', async event => {
      const node = event.currentTarget; node.disabled = true;
      try { const result = await post(root.dataset.pinUrl, {}); node.textContent = result.is_pinned ? 'Mahkamlashni bekor qilish' : 'Suhbatni mahkamlash'; q('[data-pin-status]').textContent = 'Saqlandi.'; node.disabled = false; }
      catch (error) { q('[data-pin-status]').textContent = `${error.message} Qayta bosmang; sahifani yangilab holatni tekshiring.`; }
    });
  }
  async function manage(id, kind) {
    if (blocked || mutationBusy) return;
    try {
      const data = await api(root.dataset.historyUrl + `?message=${id}`), message = data.messages[0];
      if (!message.can_edit) { showNotice('Bu xabarni o‘zgartirib bo‘lmaydi.'); refresh(); return; }
      const dialog = q(`[data-${kind}-dialog]`), form = dialog.querySelector('form'), status = q(`[data-${kind}-status]`);
      const recordKey = String(id), saved = draft.edits[recordKey];
      form.dataset.id = id; form.dataset.revision = message.revision;
      status.replaceChildren(); form.querySelector('[type=submit]').disabled = false;
      if (kind === 'edit') q('#edit-text').value = saved?.text ?? message.text;
      else { q('[data-delete-preview]').textContent = message.text; form.querySelector('input').checked = false; }
      if (saved && (saved.pending || saved.revision !== message.revision)) {
        form.querySelector('[type=submit]').disabled = true;
        status.append(element('span', 'Oldingi tahrir holati o‘zgargan yoki tasdiqlanmagan. Matn avtomatik yozilmaydi. '), button('Serverdagi matndan boshlash', () => {
          delete draft.edits[recordKey]; save(); dialog.close(); manage(id, kind);
        }));
      }
      dialog.showModal();
      if (kind === 'edit') q('#edit-text').focus();
    } catch (error) { showNotice(error.message); }
  }
  for (const kind of ['edit', 'delete']) {
    const form = q(`[data-${kind}-form]`), dialog = form.closest('dialog');
    dialog.addEventListener('close', () => history.focus());
    dialog.addEventListener('cancel', event => { if (mutationBusy) event.preventDefault(); });
    if (kind === 'edit') q('#edit-text').addEventListener('input', () => {
      draft.edits[form.dataset.id] = {text: q('#edit-text').value, revision: form.dataset.revision}; save();
    });
    form.addEventListener('submit', async event => {
      event.preventDefault(); if (mutationBusy || form.querySelector('[type=submit]').disabled) return;
      mutationBusy = true; form.querySelector('[type=submit]').disabled = true;
      const id = form.dataset.id, text = q('#edit-text').value, revision = form.dataset.revision;
      draft.edits[id] = {text, revision, pending: true}; save();
      try {
        const result = await post(root.dataset[kind + 'Url'].replace('/0/', `/${id}/`), {text, revision});
        messages = mergeMessages(messages, [result.message]); render(); delete draft.edits[id]; save(); dialog.close();
      } catch (error) {
        q(`[data-${kind}-status]`).textContent = `${error.message} Matn saqlandi. Oynani yopib xabarni qayta oching; avtomatik qayta yozilmaydi.`;
      } finally { mutationBusy = false; }
    });
  }
  window.addEventListener('beforeunload', event => {
    if (mutationBusy || file?.files.length || (!storageOK && (input?.value || draft.pending || Object.keys(draft.edits).length))) { event.preventDefault(); event.returnValue = ''; }
  });
  window.addEventListener('pagehide', () => { stopped = true; clearTimeout(retryTimer); clearTimeout(ackTimer); socket?.close(); });
  window.addEventListener('pageshow', event => { if (event.persisted) location.reload(); });
}
