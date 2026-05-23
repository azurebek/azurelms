(function () {
  const panel = document.querySelector('[data-chat-room-id]');
  if (!panel) return;

  const roomId = panel.getAttribute('data-chat-room-id');
  const activeRoom = panel.getAttribute('data-active-room');
  const currentUserId = Number(panel.getAttribute('data-current-user-id'));
  const currentUserName = panel.getAttribute('data-current-user-name') || 'Siz';
  const aiToneUrl = panel.getAttribute('data-ai-tone-url');
  const aiModelUrl = panel.getAttribute('data-ai-model-url');
  const messagesArea = document.querySelector('[data-chat-messages]');
  const input = document.querySelector('[data-chat-input]');
  const sendButton = document.querySelector('[data-chat-send]');

  if (!roomId || !messagesArea || !input || !sendButton) return;

  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/chat/${roomId}/`);
  const pendingClientMessageIds = new Map();

  function scrollToBottom() {
    messagesArea.scrollTop = messagesArea.scrollHeight;
  }

  function currentTime() {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function ensureStatusBar() {
    let status = document.querySelector('[data-chat-status]');
    if (status) return status;

    status = document.createElement('div');
    status.className = 'chat-status';
    status.dataset.chatStatus = 'true';
    messagesArea.insertAdjacentElement('afterend', status);
    return status;
  }

  function setChatStatus(message, type) {
    const status = ensureStatusBar();
    status.textContent = message || '';
    status.classList.toggle('is-visible', Boolean(message));
    status.classList.toggle('is-error', type === 'error');
    status.classList.toggle('is-success', type === 'success');
  }

  function removeEmptyState() {
    const emptyState = messagesArea.querySelector('[data-empty-state]');
    if (emptyState) emptyState.remove();
  }

  function truncatePreview(text) {
    const clean = (text || '').replace(/\s+/g, ' ').trim();
    return clean.length > 44 ? `${clean.slice(0, 41)}...` : clean;
  }

  function updateSidebarRoom(payload) {
    const sidebarRoomId = payload.room_id || roomId;
    const item = document.querySelector(`[data-sidebar-room-id="${CSS.escape(String(sidebarRoomId))}"]`);
    if (!item) return;

    const name = item.querySelector('.sb-item-name');
    if (name && payload.room_name) name.textContent = payload.room_name;

    const preview = item.querySelector('.sb-item-preview');
    if (preview) preview.textContent = truncatePreview(payload.message || payload.text || '');

    const time = item.querySelector('.sb-item-time');
    if (time) time.textContent = payload.created_at || currentTime();
  }

  function appendSystemNotice(message, options) {
    removeEmptyState();
    const notice = document.createElement('div');
    notice.className = `sys-note ${options && options.type === 'error' ? 'sys-note--error' : ''}`;

    const span = document.createElement('span');
    span.textContent = message;
    notice.appendChild(span);

    if (options && options.retry && options.userMessageId) {
      const retry = document.createElement('button');
      retry.type = 'button';
      retry.className = 'sys-retry';
      retry.textContent = 'Qayta urinish';
      retry.addEventListener('click', function () {
        notice.remove();
        retryAiResponse(options.userMessageId);
      });
      span.appendChild(retry);
    }

    messagesArea.appendChild(notice);
    scrollToBottom();
  }

  function csrfToken() {
    const tokenInput = document.querySelector('[name="csrfmiddlewaretoken"]');
    if (tokenInput && tokenInput.value) return tokenInput.value;
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  function setPickerStatus(selector, message, type) {
    const status = document.querySelector(selector);
    if (!status) return;
    status.textContent = message || '';
    status.classList.toggle('is-success', type === 'success');
    status.classList.toggle('is-error', type === 'error');
  }

  function markSelectedOption(selector, attr, value) {
    document.querySelectorAll(selector).forEach(function (button) {
      const selected = button.getAttribute(attr) === value;
      button.classList.toggle('active', selected);
      const marker = button.querySelector('.ai-current');
      if (marker) marker.textContent = selected ? 'Tanlangan' : '';
    });
  }

  function optionLabel(button) {
    const label = button.querySelector('span:not(.ai-current)');
    return label ? label.textContent.trim() : '';
  }

  function initTonePicker() {
    if (!aiToneUrl) return;
    document.querySelectorAll('[data-ai-tone-option]').forEach(function (button) {
      button.addEventListener('click', async function () {
        const tone = button.getAttribute('data-ai-tone-option');
        if (!tone) return;

        setPickerStatus('[data-ai-tone-status]', 'Saqlanmoqda...');
        const body = new URLSearchParams();
        body.set('ai_tone', tone);

        try {
          const response = await fetch(aiToneUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
              'X-CSRFToken': csrfToken(),
              'X-Requested-With': 'XMLHttpRequest',
              'Accept': 'application/json',
            },
            body: body.toString(),
          });
          const payload = await response.json();
          if (!response.ok || payload.status !== 'success') {
            throw new Error(payload.message || 'Uslub saqlanmadi.');
          }
          markSelectedOption('[data-ai-tone-option]', 'data-ai-tone-option', payload.ai_tone || tone);
          panel.setAttribute('data-current-ai-tone', payload.ai_tone || tone);
          const currentLabel = document.querySelector('[data-ai-tone-current-label]');
          if (currentLabel) currentLabel.textContent = payload.label || optionLabel(button);
          setPickerStatus('[data-ai-tone-status]', 'Uslub yangilandi.', 'success');
        } catch (error) {
          setPickerStatus('[data-ai-tone-status]', error.message || 'Uslub saqlanmadi.', 'error');
        }
      });
    });
  }

  function initModelPicker() {
    if (!aiModelUrl) return;
    document.querySelectorAll('[data-ai-model-option]').forEach(function (button) {
      button.addEventListener('click', async function () {
        const model = button.getAttribute('data-ai-model-option');
        if (!model) return;

        setPickerStatus('[data-ai-model-status]', 'Saqlanmoqda...');
        const body = new URLSearchParams();
        body.set('ai_model', model);

        try {
          const response = await fetch(aiModelUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
              'X-CSRFToken': csrfToken(),
              'X-Requested-With': 'XMLHttpRequest',
              'Accept': 'application/json',
            },
            body: body.toString(),
          });
          const payload = await response.json();
          if (!response.ok || payload.status !== 'success') {
            throw new Error(payload.message || 'Model saqlanmadi.');
          }
          markSelectedOption('[data-ai-model-option]', 'data-ai-model-option', payload.ai_model || model);
          panel.setAttribute('data-current-ai-model', payload.ai_model || model);
          const currentLabel = document.querySelector('[data-ai-model-current-label]');
          if (currentLabel) currentLabel.textContent = payload.label || optionLabel(button);
          setPickerStatus('[data-ai-model-status]', 'Model yangilandi.', 'success');
        } catch (error) {
          setPickerStatus('[data-ai-model-status]', error.message || 'Model saqlanmadi.', 'error');
        }
      });
    });
  }

  function showAiTyping() {
    if (activeRoom !== 'ai' || messagesArea.querySelector('[data-ai-typing]')) return;
    removeEmptyState();

    const row = document.createElement('div');
    row.className = 'typing-row';
    row.dataset.aiTyping = 'true';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar msg-avatar--ai';
    avatar.innerHTML = '<i class="bi bi-stars"></i>';

    const bubble = document.createElement('div');
    bubble.className = 'typing-bubble';
    for (let i = 0; i < 3; i += 1) {
      const dot = document.createElement('span');
      dot.className = 'typing-dot';
      bubble.appendChild(dot);
    }

    row.appendChild(avatar);
    row.appendChild(bubble);
    messagesArea.appendChild(row);
    scrollToBottom();
  }

  function hideAiTyping() {
    const typing = messagesArea.querySelector('[data-ai-typing]');
    if (typing) typing.remove();
  }

  function createAvatar(senderId, senderName) {
    if (!senderId) {
      const avatar = document.createElement('div');
      avatar.className = 'msg-avatar msg-avatar--ai';
      avatar.innerHTML = '<i class="bi bi-stars"></i>';
      return avatar;
    }

    const avatar = document.createElement('div');
    avatar.className = activeRoom === 'tutor' ? 'msg-avatar msg-avatar--tutor' : 'msg-avatar c-lime';
    const cleanName = senderName || 'User';
    avatar.textContent = cleanName.slice(0, 2).toUpperCase();
    return avatar;
  }

  function appendMessage(payload) {
    const senderId = payload.sender_id === null || payload.sender_id === undefined ? null : Number(payload.sender_id);
    const isMine = senderId === currentUserId;
    const senderName = payload.sender_name || 'Azure AI';
    const text = payload.message || payload.text || '';

    removeEmptyState();
    if (!isMine) hideAiTyping();

    const row = document.createElement('div');
    row.className = `msg-row ${isMine ? 'me ' : ''}group-start group-last`;
    if (payload.message_id) row.dataset.messageId = payload.message_id;
    if (payload.client_message_id) row.dataset.clientMessageId = payload.client_message_id;
    if (payload.optimistic) row.classList.add('is-pending');
    if (payload.retry_text) row.dataset.retryText = payload.retry_text;

    if (!isMine) row.appendChild(createAvatar(senderId, senderName));

    const group = document.createElement('div');
    group.className = 'msg-group';

    if (!isMine && senderId) {
      const author = document.createElement('div');
      author.className = 'msg-author-name';
      author.textContent = senderName;
      group.appendChild(author);
    }

    const bubble = document.createElement('div');
    bubble.className = `bubble ${isMine ? 'bubble-me' : 'bubble-them'}`;
    bubble.textContent = text;
    group.appendChild(bubble);

    const meta = document.createElement('div');
    meta.className = 'bubble-meta';

    const time = document.createElement('span');
    time.textContent = payload.created_at || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    meta.appendChild(time);

    if (isMine) {
      const check = document.createElement('i');
      check.className = 'bi bi-check2-all check';
      meta.appendChild(check);
    }

    group.appendChild(meta);
    row.appendChild(group);
    messagesArea.appendChild(row);
    updateSidebarRoom(payload);
    scrollToBottom();
  }

  function confirmOptimisticMessage(payload) {
    const clientMessageId = payload.client_message_id;
    if (!clientMessageId || !pendingClientMessageIds.has(clientMessageId)) return false;

    pendingClientMessageIds.delete(clientMessageId);
    const row = messagesArea.querySelector(`[data-client-message-id="${CSS.escape(clientMessageId)}"]`);
    if (row) {
      row.classList.remove('is-pending');
      if (payload.message_id) row.dataset.messageId = payload.message_id;
      row.dataset.retryText = payload.message || payload.text || row.dataset.retryText || '';
      const time = row.querySelector('.bubble-meta span');
      if (time && payload.created_at) time.textContent = payload.created_at;
    }
    updateSidebarRoom(payload);
    return true;
  }

  function handleAiStatus(payload) {
    if (activeRoom !== 'ai') return;
    const status = payload.status || '';

    if (status === 'running' || status === 'pending') {
      showAiTyping();
      setChatStatus(payload.message || 'Azure AI javob tayyorlayapti...');
      return;
    }

    if (status === 'succeeded') {
      hideAiTyping();
      setChatStatus('', 'success');
      return;
    }

    if (status === 'fallback') {
      hideAiTyping();
      setChatStatus('', 'success');
      return;
    }

    if (status === 'failed') {
      hideAiTyping();
      setChatStatus(payload.message || 'AI javob bera olmadi.', 'error');
      appendSystemNotice(payload.message || 'AI javob bera olmadi.', {
        type: 'error',
        retry: true,
        userMessageId: payload.user_message_id,
      });
    }
  }

  function retryAiResponse(userMessageId) {
    if (!userMessageId) return;
    if (socket.readyState !== WebSocket.OPEN) {
      setChatStatus("Ulanish uzilgan. Sahifani yangilab qayta urinib ko'ring.", 'error');
      return;
    }

    showAiTyping();
    setChatStatus('Qayta urinilmoqda...');
    socket.send(JSON.stringify({
      action: 'retry_ai_response',
      user_message_id: userMessageId,
    }));
  }

  function sendMessage() {
    const text = input.value.trim();
    if (!text || socket.readyState !== WebSocket.OPEN) return;
    const clientMessageId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;

    pendingClientMessageIds.set(clientMessageId, { text });
    appendMessage({
      message: text,
      sender_id: currentUserId,
      sender_name: currentUserName,
      client_message_id: clientMessageId,
      created_at: currentTime(),
      optimistic: true,
      retry_text: text,
    });
    if (activeRoom === 'ai') showAiTyping();

    socket.send(JSON.stringify({
      message: text,
      client_message_id: clientMessageId,
    }));
    input.value = '';
    input.style.height = 'auto';
  }

  socket.addEventListener('open', function () {
    sendButton.disabled = false;
    setChatStatus('');
  });

  socket.addEventListener('close', function () {
    sendButton.disabled = true;
    hideAiTyping();
    setChatStatus("Ulanish uzildi. Sahifani yangilang yoki birozdan keyin qayta urinib ko'ring.", 'error');
  });

  socket.addEventListener('error', function () {
    setChatStatus('Ulanishda muammo bor.', 'error');
  });

  socket.addEventListener('message', function (event) {
    try {
      const payload = JSON.parse(event.data);
      if (payload.event_type === 'ai_status') {
        handleAiStatus(payload);
        return;
      }
      if (confirmOptimisticMessage(payload)) return;
      appendMessage(payload);
    } catch (_) {
      return;
    }
  });

  sendButton.addEventListener('click', sendMessage);
  input.addEventListener('keydown', function (event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });

  sendButton.disabled = true;
  initModelPicker();
  initTonePicker();
  scrollToBottom();
})();
