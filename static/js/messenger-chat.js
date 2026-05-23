(function () {
  const panel = document.querySelector('[data-chat-room-id]');
  if (!panel) return;

  const roomId = panel.getAttribute('data-chat-room-id');
  const activeRoom = panel.getAttribute('data-active-room');
  const currentUserId = Number(panel.getAttribute('data-current-user-id'));
  const currentUserName = panel.getAttribute('data-current-user-name') || 'Siz';
  const messagesArea = document.querySelector('[data-chat-messages]');
  const input = document.querySelector('[data-chat-input]');
  const sendButton = document.querySelector('[data-chat-send]');

  if (!roomId || !messagesArea || !input || !sendButton) return;

  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/chat/${roomId}/`);
  const pendingClientMessageIds = new Set();

  function scrollToBottom() {
    messagesArea.scrollTop = messagesArea.scrollHeight;
  }

  function currentTime() {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function removeEmptyState() {
    const emptyState = messagesArea.querySelector('[data-empty-state]');
    if (emptyState) emptyState.remove();
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
      const time = row.querySelector('.bubble-meta span');
      if (time && payload.created_at) time.textContent = payload.created_at;
    }
    return true;
  }

  function sendMessage() {
    const text = input.value.trim();
    if (!text || socket.readyState !== WebSocket.OPEN) return;
    const clientMessageId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;

    pendingClientMessageIds.add(clientMessageId);
    appendMessage({
      message: text,
      sender_id: currentUserId,
      sender_name: currentUserName,
      client_message_id: clientMessageId,
      created_at: currentTime(),
      optimistic: true,
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
  });

  socket.addEventListener('close', function () {
    sendButton.disabled = true;
  });

  socket.addEventListener('message', function (event) {
    try {
      const payload = JSON.parse(event.data);
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
  scrollToBottom();
})();
