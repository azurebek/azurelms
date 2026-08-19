(function () {
  const panel = document.querySelector('[data-chat-room-id]');
  if (!panel) return;

  const roomId = panel.getAttribute('data-chat-room-id');
  const activeRoom = panel.getAttribute('data-active-room');
  const aiAvatarUrl = panel.getAttribute('data-ai-avatar-url') || '';
  function aiAvatarMarkup() {
    return aiAvatarUrl
      ? '<img class="ai-avatar-img" src="' + aiAvatarUrl + '" alt="Azure AI" draggable="false">'
      : '<i class="bi bi-stars"></i>';
  }
  const currentUserId = Number(panel.getAttribute('data-current-user-id'));
  const currentUserName = panel.getAttribute('data-current-user-name') || 'Siz';
  const contextLessonId = panel.getAttribute('data-context-lesson-id') || '';
  const aiToneUrl = panel.getAttribute('data-ai-tone-url');
  const aiModelUrl = panel.getAttribute('data-ai-model-url');
  const aiSkillUrl = panel.getAttribute('data-ai-skill-url');
  const aiFeedbackUrlTemplate = panel.getAttribute('data-ai-feedback-url-template');
  let selectedAiSkill = panel.getAttribute('data-current-ai-skill') || 'auto';
  const messagesArea = document.querySelector('[data-chat-messages]');
  const input = document.querySelector('[data-chat-input]');
  const sendButton = document.querySelector('[data-chat-send]');
  const uploadInput = document.querySelector('[data-upload-input]');

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

  function aiFeedbackUrl(messageId) {
    const safeId = encodeURIComponent(String(messageId));
    if (aiFeedbackUrlTemplate) {
      return aiFeedbackUrlTemplate.replace('/0/', `/${safeId}/`);
    }
    return `/messenger/api/ai-feedback/${safeId}/`;
  }

  function messageEditUrl(messageId) {
    return `/messenger/api/messages/${encodeURIComponent(String(messageId))}/edit/`;
  }

  function messageDeleteUrl(messageId) {
    return `/messenger/api/messages/${encodeURIComponent(String(messageId))}/delete/`;
  }

  function isMessageDeleted(payload) {
    return payload && (payload.is_deleted === true || payload.is_deleted === 'true');
  }

  function normalizeFeedbackTotals(totals) {
    return {
      positive: Number(totals && totals.positive) || 0,
      negative: Number(totals && totals.negative) || 0,
    };
  }

  function normalizeUserRating(feedback) {
    if (!feedback || feedback.rating === null || feedback.rating === undefined) return null;
    const rating = Number(feedback.rating);
    return rating === 1 || rating === -1 ? rating : null;
  }

  function updateFeedbackControls(container, feedback, totals) {
    if (!container) return;
    const userRating = normalizeUserRating(feedback);
    const counts = normalizeFeedbackTotals(totals);
    container.dataset.userRating = userRating === null ? '' : String(userRating);

    const positive = container.querySelector('[data-feedback-positive]');
    const negative = container.querySelector('[data-feedback-negative]');
    if (positive) positive.textContent = String(counts.positive);
    if (negative) negative.textContent = String(counts.negative);

    container.querySelectorAll('[data-feedback-rating]').forEach(function (button) {
      const rating = Number(button.getAttribute('data-feedback-rating'));
      button.classList.toggle('active', rating === userRating);
    });
  }

  function createFeedbackControls(payload) {
    const controls = document.createElement('div');
    controls.className = 'message-feedback';
    controls.dataset.aiFeedback = 'true';
    controls.dataset.messageId = payload.message_id || payload.id || '';

    const skillMeta = createAiSkillMeta(payload);
    if (skillMeta) controls.appendChild(skillMeta);
    const sourceMeta = createAiSourceMeta(payload);
    if (sourceMeta) controls.appendChild(sourceMeta);

    const positive = document.createElement('button');
    positive.type = 'button';
    positive.className = 'feedback-btn';
    positive.setAttribute('data-feedback-rating', '1');
    positive.setAttribute('aria-label', 'Yaxshi javob');
    positive.title = 'Yaxshi javob';
    positive.innerHTML = '<i class="bi bi-hand-thumbs-up"></i><span data-feedback-positive>0</span>';

    const negative = document.createElement('button');
    negative.type = 'button';
    negative.className = 'feedback-btn';
    negative.setAttribute('data-feedback-rating', '-1');
    negative.setAttribute('aria-label', 'Foydasiz javob');
    negative.title = 'Foydasiz javob';
    negative.innerHTML = '<i class="bi bi-hand-thumbs-down"></i><span data-feedback-negative>0</span>';

    const status = document.createElement('span');
    status.className = 'feedback-status';
    status.dataset.feedbackStatus = 'true';

    controls.appendChild(positive);
    controls.appendChild(negative);

    const copy = document.createElement('button');
    copy.type = 'button';
    copy.className = 'feedback-btn feedback-btn--icon';
    copy.setAttribute('data-copy-message', 'true');
    copy.setAttribute('aria-label', 'Nusxa olish');
    copy.title = 'Nusxa olish';
    copy.innerHTML = '<i class="bi bi-copy"></i>';
    controls.appendChild(copy);

    const regenerateUserMessageId = payload.regenerate_user_message_id || payload.user_message_id;
    if (regenerateUserMessageId) {
      const regenerate = document.createElement('button');
      regenerate.type = 'button';
      regenerate.className = 'feedback-btn feedback-btn--icon';
      regenerate.setAttribute('data-regenerate-message', 'true');
      regenerate.setAttribute('data-user-message-id', regenerateUserMessageId);
      regenerate.setAttribute('aria-label', 'Qayta generatsiya qilish');
      regenerate.title = 'Qayta generatsiya qilish';
      regenerate.innerHTML = '<i class="bi bi-arrow-clockwise"></i>';
      controls.appendChild(regenerate);
    }

    controls.appendChild(status);
    updateFeedbackControls(controls, payload.feedback, payload.feedback_totals);
    return controls;
  }

  function createAiSkillMeta(payload) {
    if (!payload.ai_skill_label && !payload.ai_skill_slug) return null;

    const meta = document.createElement('span');
    meta.className = 'feedback-btn feedback-btn--icon feedback-btn--skill';
    meta.tabIndex = 0;
    meta.setAttribute('role', 'img');

    const icon = document.createElement('i');
    icon.className = 'bi bi-stars';
    meta.appendChild(icon);

    const label = payload.ai_skill_label || payload.ai_skill_slug || 'AI skill';
    let title = `Skill: ${label}`;
    if (Array.isArray(payload.ai_used_tools) && payload.ai_used_tools.length) {
      title += ` | Tools: ${payload.ai_used_tools.join(', ')}`;
    }
    meta.title = title;
    meta.setAttribute('aria-label', title);

    return meta;
  }

  function createAiSourceMeta(payload) {
    const sources = Array.isArray(payload.ai_rag_sources) ? payload.ai_rag_sources : [];
    if (!sources.length) return null;

    const meta = document.createElement('span');
    meta.className = 'feedback-btn feedback-btn--icon feedback-btn--source';
    meta.tabIndex = 0;
    meta.setAttribute('role', 'img');

    const icon = document.createElement('i');
    icon.className = 'bi bi-journal-text';
    meta.appendChild(icon);

    const sourceLines = sources.slice(0, 4).map(function (source) {
      const number = source.number || '?';
      const label = source.label || [source.course_title, source.module_title, source.lesson_title].filter(Boolean).join(' > ');
      return `Manba ${number}: ${label || 'RAG chunk'}`;
    });
    const title = `RAG manbalar\n${sourceLines.join('\n')}`;
    meta.title = title;
    meta.setAttribute('aria-label', title);
    return meta;
  }

  function createAttachmentNode(attachment, isMine) {
    if (!attachment || !attachment.url) return null;
    const file = document.createElement('a');
    file.className = `bubble-file ${attachment.is_image ? 'bubble-file--image' : ''}`;
    file.href = attachment.url;
    file.target = '_blank';
    file.rel = 'noopener';

    if (attachment.is_image) {
      const preview = document.createElement('img');
      preview.src = attachment.url;
      preview.alt = attachment.name || '';
      preview.loading = 'lazy';
      preview.style.cssText = 'max-width:220px;max-height:180px;border-radius:10px;display:block;margin-bottom:6px;';
      file.appendChild(preview);
    } else {
      const iconWrap = document.createElement('span');
      iconWrap.className = 'bubble-file-icon';
      const icon = document.createElement('i');
      icon.className = 'bi bi-file-earmark';
      iconWrap.appendChild(icon);
      file.appendChild(iconWrap);
    }

    const info = document.createElement('span');
    info.className = 'bubble-file-info';

    const name = document.createElement('span');
    name.className = 'bubble-file-name';
    name.textContent = attachment.name || 'Fayl';

    const size = document.createElement('span');
    size.className = 'bubble-file-size';
    size.textContent = attachment.size_label || '';

    info.appendChild(name);
    info.appendChild(size);
    file.appendChild(info);
    if (isMine) file.classList.add('bubble-file--me');
    return file;
  }

  function createMessageActions(messageId) {
    if (!messageId) return null;
    const actions = document.createElement('div');
    actions.className = 'msg-actions';
    actions.dataset.messageActions = 'true';
    actions.dataset.messageId = messageId;

    const edit = document.createElement('button');
    edit.type = 'button';
    edit.className = 'message-action-btn';
    edit.setAttribute('data-edit-message', 'true');
    edit.setAttribute('aria-label', 'Tahrirlash');
    edit.title = 'Tahrirlash';
    edit.innerHTML = '<i class="bi bi-pencil"></i>';

    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'message-action-btn danger';
    remove.setAttribute('data-delete-message', 'true');
    remove.setAttribute('aria-label', "O'chirish");
    remove.title = "O'chirish";
    remove.innerHTML = '<i class="bi bi-trash"></i>';

    actions.appendChild(edit);
    actions.appendChild(remove);
    return actions;
  }

  async function submitFeedback(button) {
    const controls = button.closest('[data-ai-feedback]');
    if (!controls || !controls.dataset.messageId) return;
    const rating = Number(button.getAttribute('data-feedback-rating'));
    if (rating !== 1 && rating !== -1) return;

    const status = controls.querySelector('[data-feedback-status]');
    const buttons = controls.querySelectorAll('[data-feedback-rating]');
    buttons.forEach(function (item) { item.disabled = true; });
    controls.classList.add('is-saving');
    if (status) status.textContent = 'Saqlanmoqda...';

    try {
      const response = await fetch(aiFeedbackUrl(controls.dataset.messageId), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ rating: rating, comment: '' }),
      });
      const payload = await response.json();
      if (!response.ok || payload.status !== 'success') {
        throw new Error(payload.message || 'Feedback saqlanmadi.');
      }
      controls.classList.remove('has-error');
      updateFeedbackControls(controls, payload.feedback, payload.feedback_totals);
      if (status) status.textContent = 'Saqlandi';
      window.setTimeout(function () {
        if (status) status.textContent = '';
      }, 1600);
    } catch (error) {
      if (status) status.textContent = error.message || 'Saqlanmadi';
      controls.classList.add('has-error');
    } finally {
      controls.classList.remove('is-saving');
      buttons.forEach(function (item) { item.disabled = false; });
    }
  }

  function messageTextForAction(button) {
    const group = button.closest('.msg-group');
    const bubble = group ? group.querySelector('.bubble') : null;
    return bubble ? (bubble.innerText || bubble.textContent || '').trim() : '';
  }

  function fallbackCopyText(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    textarea.remove();
  }

  async function copyMessage(button) {
    const controls = button.closest('[data-ai-feedback]');
    const status = controls ? controls.querySelector('[data-feedback-status]') : null;
    const text = messageTextForAction(button);
    if (!text) return;

    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        fallbackCopyText(text);
      }
      if (status) status.textContent = 'Nusxalandi';
      window.setTimeout(function () {
        if (status) status.textContent = '';
      }, 1400);
    } catch (_) {
      if (status) status.textContent = 'Nusxa olinmadi';
      if (controls) controls.classList.add('has-error');
    }
  }

  function regenerateMessage(button) {
    const controls = button.closest('[data-ai-feedback]');
    const status = controls ? controls.querySelector('[data-feedback-status]') : null;
    const userMessageId = button.getAttribute('data-user-message-id');
    if (!userMessageId) return;
    if (status) status.textContent = 'Qayta...';
    retryAiResponse(userMessageId);
  }

  function initComposerMenus() {
    const pickers = Array.prototype.slice.call(document.querySelectorAll('[data-composer-picker]'));
    if (!pickers.length) return;

    function setOpen(picker, open) {
      picker.classList.toggle('is-open', open);
      const toggle = picker.querySelector('[data-picker-toggle]');
      if (toggle) toggle.setAttribute('aria-expanded', String(open));
      if (open) keepInsideViewport(picker);
    }

    /* Menyu chipga bog'langan, chip esa qatorning istalgan joyida bo'lishi
       mumkin — keng ekranda o'ng chetdan, tor ekranda chap chetdan chiqib
       ketadi. CSS buni o'zi hal qila olmaydi: joyni o'lchash kerak.
       Ikkala chet ham bitta hisobda qisiladi. */
    function keepInsideViewport(picker) {
      const menu = picker.querySelector('[data-picker-menu]');
      if (!menu) return;

      const margin = 8;
      menu.classList.remove('is-flipped');
      menu.style.left = '';

      const pickerLeft = picker.getBoundingClientRect().left;
      const maxLeft = Math.max(margin, window.innerWidth - margin - menu.offsetWidth);
      const wantedLeft = Math.min(Math.max(margin, pickerLeft), maxLeft);

      menu.style.left = Math.round(wantedLeft - pickerLeft) + 'px';
      if (wantedLeft < pickerLeft) menu.classList.add('is-flipped');
    }
    function closeAll(except) {
      pickers.forEach(function (picker) {
        if (picker !== except) setOpen(picker, false);
      });
    }

    pickers.forEach(function (picker) {
      const toggle = picker.querySelector('[data-picker-toggle]');
      const menu = picker.querySelector('[data-picker-menu]');
      if (toggle) {
        toggle.addEventListener('click', function (event) {
          event.stopPropagation();
          const willOpen = !picker.classList.contains('is-open');
          closeAll(picker);
          setOpen(picker, willOpen);
        });
      }
      // Menyu ichidagi bosish tashqi yopuvchiga yetib bormaydi.
      if (menu) menu.addEventListener('click', function (event) { event.stopPropagation(); });
    });

    document.addEventListener('click', function () { closeAll(null); });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') closeAll(null);
    });

    // Joy ochilish paytida hisoblanadi; telefon burilsa yoki oyna o'lchami
    // o'zgarsa ochiq menyu eski hisob bilan ekrandan chiqib qoladi.
    window.addEventListener('resize', function () {
      pickers.forEach(function (picker) {
        if (picker.classList.contains('is-open')) keepInsideViewport(picker);
      });
    });
  }

  /* Muvaffaqiyatli tanlovdan keyin menyu yopiladi: natija chipning o'zida
     ko'rinadi. Xato bo'lsa ochiq qoladi, aks holda qizil xabar ko'rinmaydi. */
  function closePickerFor(element) {
    const picker = element.closest('[data-composer-picker]');
    if (!picker) return;
    picker.classList.remove('is-open');
    const toggle = picker.querySelector('[data-picker-toggle]');
    if (toggle) toggle.setAttribute('aria-expanded', 'false');
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
          // Shablondagi `|cut:"Gemini "` bilan bir xil qoida — chipda vendor
          // prefiksi shart emas, to'liq nom menyuda turadi.
          if (currentLabel) currentLabel.textContent = (payload.label || optionLabel(button)).replace(/^Gemini\s+/, '');
          setPickerStatus('[data-ai-model-status]', 'Model yangilandi.', 'success');
          closePickerFor(button);
        } catch (error) {
          setPickerStatus('[data-ai-model-status]', error.message || 'Model saqlanmadi.', 'error');
        }
      });
    });
  }

  function initSkillPicker() {
    document.querySelectorAll('[data-ai-skill-option]').forEach(function (button) {
      button.addEventListener('click', async function () {
        const skill = button.getAttribute('data-ai-skill-option') || 'auto';

        // Endpoint bo'lmasa ham tanlov shu sahifada ishlashi kerak (eski kontrakt).
        if (!aiSkillUrl) {
          applySkill(skill, button);
          setPickerStatus('[data-ai-skill-status]', 'Keyingi xabarda ishlaydi.', 'success');
          closePickerFor(button);
          return;
        }

        setPickerStatus('[data-ai-skill-status]', 'Saqlanmoqda...');
        const body = new URLSearchParams();
        body.set('ai_skill', skill);

        try {
          const response = await fetch(aiSkillUrl, {
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
            throw new Error(payload.message || 'Skill saqlanmadi.');
          }
          applySkill(payload.ai_skill || skill, button, payload.label);
          setPickerStatus('[data-ai-skill-status]', 'Skill yangilandi.', 'success');
          closePickerFor(button);
        } catch (error) {
          setPickerStatus('[data-ai-skill-status]', error.message || 'Skill saqlanmadi.', 'error');
        }
      });
    });
  }

  function applySkill(skill, button, label) {
    selectedAiSkill = skill;
    panel.setAttribute('data-current-ai-skill', skill);
    markSelectedOption('[data-ai-skill-option]', 'data-ai-skill-option', skill);
    const currentLabel = document.querySelector('[data-ai-skill-current-label]');
    if (currentLabel) currentLabel.textContent = label || optionLabel(button) || 'Avto';
  }

  function showAiTyping() {
    if (activeRoom !== 'ai' || messagesArea.querySelector('[data-ai-typing]')) return;
    removeEmptyState();

    const row = document.createElement('div');
    row.className = 'typing-row';
    row.dataset.aiTyping = 'true';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar msg-avatar--ai';
    avatar.innerHTML = aiAvatarMarkup();

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
      avatar.innerHTML = aiAvatarMarkup();
      return avatar;
    }

    const avatar = document.createElement('div');
    avatar.className = activeRoom === 'tutor' ? 'msg-avatar msg-avatar--tutor' : 'msg-avatar c-lime';
    const cleanName = senderName || 'User';
    avatar.textContent = cleanName.slice(0, 2).toUpperCase();
    return avatar;
  }

  function isFeedbackEligibleAiMessage(payload, senderId, isMine) {
    if (isMine) return false;
    if (payload.is_ai === true || payload.is_ai === 'true') return true;
    return activeRoom === 'ai' && senderId === null;
  }

  function appendMessage(payload) {
    const senderId = payload.sender_id === null || payload.sender_id === undefined ? null : Number(payload.sender_id);
    const isMine = senderId === currentUserId;
    const isAiMessage = isFeedbackEligibleAiMessage(payload, senderId, isMine);
    const senderName = payload.sender_name || 'Azure AI';
    const text = payload.message || payload.text || '';
    const isDeleted = isMessageDeleted(payload);

    removeEmptyState();
    if (!isMine) hideAiTyping();

    const row = document.createElement('div');
    row.className = `msg-row ${isMine ? 'me ' : ''}group-start group-last`;
    if (payload.message_id) row.dataset.messageId = payload.message_id;
    if (payload.client_message_id) row.dataset.clientMessageId = payload.client_message_id;
    if (payload.optimistic) row.classList.add('is-pending');
    if (payload.retry_text) row.dataset.retryText = payload.retry_text;
    if (isAiMessage) row.dataset.isAi = 'true';
    if (isDeleted) row.classList.add('is-deleted');

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
    bubble.className = `bubble ${isMine ? 'bubble-me' : 'bubble-them'} ${isDeleted ? 'bubble-deleted' : ''}`;
    bubble.dataset.messageText = 'true';
    bubble.textContent = text;
    group.appendChild(bubble);

    const attachment = createAttachmentNode(payload.attachment, isMine);
    if (attachment) group.appendChild(attachment);

    const meta = document.createElement('div');
    meta.className = 'bubble-meta';

    const time = document.createElement('span');
    time.textContent = `${payload.created_at || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}${payload.edited_at ? ' - tahrirlangan' : ''}`;
    meta.appendChild(time);

    if (isMine) {
      const check = document.createElement('i');
      check.className = 'bi bi-check2-all check';
      meta.appendChild(check);
    }

    group.appendChild(meta);
    if (isAiMessage) {
      group.appendChild(createFeedbackControls(payload));
    } else if (isMine && !payload.optimistic && !isDeleted) {
      group.appendChild(createMessageActions(payload.message_id || payload.id));
    }
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
      const group = row.querySelector('.msg-group');
      if (group && payload.message_id && !group.querySelector('[data-message-actions]')) {
        group.appendChild(createMessageActions(payload.message_id));
      }
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

  function updateRenderedMessage(payload) {
    const messageId = payload.message_id || payload.id;
    if (!messageId) return;
    const row = messagesArea.querySelector(`[data-message-id="${CSS.escape(String(messageId))}"]`);
    if (!row) return;
    const deleted = isMessageDeleted(payload);
    const bubble = row.querySelector('[data-message-text]');
    if (bubble) {
      bubble.textContent = payload.message || payload.text || '';
      bubble.classList.toggle('bubble-deleted', deleted);
    }
    row.classList.toggle('is-deleted', deleted);

    const metaTime = row.querySelector('.bubble-meta span');
    if (metaTime && payload.created_at) {
      metaTime.textContent = `${payload.created_at}${payload.edited_at ? ' - tahrirlangan' : ''}`;
    }
    if (deleted) {
      row.querySelector('[data-message-actions]')?.remove();
      row.querySelector('.bubble-file')?.remove();
    }
    updateSidebarRoom(payload);
  }

  async function editOwnMessage(button) {
    const row = button.closest('[data-message-id]');
    const messageId = row ? row.dataset.messageId : '';
    const bubble = row ? row.querySelector('[data-message-text]') : null;
    if (!messageId || !bubble) return;
    const current = (bubble.innerText || bubble.textContent || '').trim();
    const next = window.prompt('Xabarni tahrirlang', current);
    if (next === null) return;
    const text = next.trim();
    if (!text) {
      setChatStatus("Xabar bo'sh bo'lmasin.", 'error');
      return;
    }

    try {
      const response = await fetch(messageEditUrl(messageId), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ text }),
      });
      const payload = await response.json();
      if (!response.ok || payload.status !== 'success') throw new Error(payload.message || 'Tahrirlanmadi');
      updateRenderedMessage(payload.message);
      setChatStatus('Xabar tahrirlandi.', 'success');
      window.setTimeout(() => setChatStatus(''), 1200);
    } catch (error) {
      setChatStatus(error.message || 'Tahrirlanmadi', 'error');
    }
  }

  async function deleteOwnMessage(button) {
    const row = button.closest('[data-message-id]');
    const messageId = row ? row.dataset.messageId : '';
    if (!messageId || !window.confirm("Xabar o'chirilsinmi?")) return;

    try {
      const response = await fetch(messageDeleteUrl(messageId), {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'application/json',
        },
      });
      const payload = await response.json();
      if (!response.ok || payload.status !== 'success') throw new Error(payload.message || "O'chirilmadi");
      updateRenderedMessage(payload.message);
      setChatStatus("Xabar o'chirildi.", 'success');
      window.setTimeout(() => setChatStatus(''), 1200);
    } catch (error) {
      setChatStatus(error.message || "O'chirilmadi", 'error');
    }
  }

  async function uploadAttachment(file) {
    if (!file) return;
    const form = new FormData();
    form.append('room_id', roomId);
    form.append('file', file);
    const caption = input.value.trim();
    if (caption) form.append('text', caption);

    setChatStatus('Fayl yuklanmoqda...');
    try {
      const response = await fetch('/messenger/api/messages/upload/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'application/json',
        },
        body: form,
      });
      const payload = await response.json();
      if (!response.ok || payload.status !== 'success') throw new Error(payload.message || 'Fayl yuklanmadi');
      input.value = '';
      input.style.height = 'auto';
      if (socket.readyState !== WebSocket.OPEN && payload.message) {
        appendMessage(payload.message);
      }
      setChatStatus('Fayl yuborildi.', 'success');
      window.setTimeout(() => setChatStatus(''), 1200);
    } catch (error) {
      setChatStatus(error.message || 'Fayl yuklanmadi', 'error');
    }
  }

  function initUpload() {
    if (!uploadInput) return;
    document.querySelectorAll('[data-upload-trigger]').forEach(function (button) {
      button.addEventListener('click', function () {
        const accept = button.getAttribute('data-upload-accept') || '';
        uploadInput.setAttribute('accept', accept);
        uploadInput.click();
      });
    });
    uploadInput.addEventListener('change', function () {
      const file = uploadInput.files && uploadInput.files[0];
      uploadInput.value = '';
      uploadAttachment(file);
    });
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

    const payload = {
      message: text,
      client_message_id: clientMessageId,
      ai_skill: selectedAiSkill || 'auto',
    };
    if (activeRoom === 'ai' && contextLessonId) {
      payload.context_lesson_id = contextLessonId;
    }
    socket.send(JSON.stringify(payload));
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
      if (payload.event_type === 'message_edited' || payload.event_type === 'message_deleted' || payload.event_type === 'message_update') {
        updateRenderedMessage(payload);
        return;
      }
      if (payload.event_type === 'message_uploaded') {
        appendMessage(payload);
        return;
      }
      if (confirmOptimisticMessage(payload)) return;
      appendMessage(payload);
    } catch (_) {
      return;
    }
  });

  sendButton.addEventListener('click', sendMessage);
  messagesArea.addEventListener('click', function (event) {
    const regenerateButton = event.target.closest('[data-regenerate-message]');
    if (regenerateButton && messagesArea.contains(regenerateButton)) {
      regenerateMessage(regenerateButton);
      return;
    }

    const copyButton = event.target.closest('[data-copy-message]');
    if (copyButton && messagesArea.contains(copyButton)) {
      copyMessage(copyButton);
      return;
    }

    const editButton = event.target.closest('[data-edit-message]');
    if (editButton && messagesArea.contains(editButton)) {
      editOwnMessage(editButton);
      return;
    }

    const deleteButton = event.target.closest('[data-delete-message]');
    if (deleteButton && messagesArea.contains(deleteButton)) {
      deleteOwnMessage(deleteButton);
      return;
    }

    const button = event.target.closest('[data-feedback-rating]');
    if (!button || !messagesArea.contains(button)) return;
    submitFeedback(button);
  });
  input.addEventListener('keydown', function (event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });

  sendButton.disabled = true;
  initComposerMenus();
  initModelPicker();
  initTonePicker();
  initSkillPicker();
  initUpload();
  scrollToBottom();
})();
