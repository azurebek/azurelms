/* ============================================================
   AzureLMS — ExamShell runtime
   Backend kontrakti: build_section_payload dispatcheri —
   payload'da 'tasks' bo'lsa boy reading-task engine (reading_item_id),
   'questions' bo'lsa oddiy Question engine (question_id).
   Oqim: start → section state → render → autosave → submit → result.
   ============================================================ */
(() => {
  'use strict';

  const cfgEl = document.getElementById('exam-config');
  if (!cfgEl) return;
  const CFG = JSON.parse(cfgEl.textContent);

  const bodyEl = document.querySelector('[data-exam-body]');
  const navEl = document.querySelector('[data-exam-nav]');
  const footEl = document.querySelector('[data-exam-foot]');
  const subEl = document.querySelector('[data-exam-sub]');
  const timerEl = document.querySelector('[data-exam-timer]');
  const timerLabelEl = document.querySelector('[data-exam-time]');
  const overlayEl = document.querySelector('[data-exam-overlay]');

  const state = {
    started: false,
    submitting: false,
    finished: false,
    deadline: null,
    timerId: null,
    sectionIndex: 0,
    payload: null,          // joriy section payload
    sectionDone: {},        // sectionId -> counts {answered,total}
    pendingSaves: new Map(),// key -> {timer, run}
    lastBlurAt: 0,
    audio: null,
    audioSession: false,
    rec: null,              // MediaRecorder holati
  };

  /* ---------- utils ---------- */
  const esc = (value) => String(value == null ? '' : value)
    .replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const fmtClock = (totalSecs) => {
    const s = Math.max(0, Math.floor(totalSecs));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    const mm = String(m).padStart(2, '0');
    const ss = String(sec).padStart(2, '0');
    return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
  };

  const wordCount = (text) => {
    const trimmed = (text || '').trim();
    return trimmed ? trimmed.split(/\s+/).length : 0;
  };

  async function api(url, { method = 'POST', json = null, form = null } = {}) {
    const opts = { method, headers: { 'X-CSRFToken': CFG.csrf } };
    if (json) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(json); }
    if (form) { opts.body = form; }
    const res = await fetch(url, opts);
    let data = {};
    try { data = await res.json(); } catch (e) { /* bo'sh javob */ }
    if (!res.ok) {
      const err = new Error(data.error || 'Xatolik yuz berdi.');
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  const sectionStateUrl = (sectionId) => CFG.urls.sectionState.replace('/0/', `/${sectionId}/`);

  /* ---------- toasts ---------- */
  let toastsBox = null;
  function toast(message, kind = 'info', ms = 4200) {
    if (!toastsBox) {
      toastsBox = document.createElement('div');
      toastsBox.className = 'x-toasts';
      document.body.appendChild(toastsBox);
    }
    const el = document.createElement('div');
    el.className = `x-toast${kind === 'error' ? ' is-error' : kind === 'warn' ? ' is-warn' : ''}`;
    const icon = kind === 'error' ? 'bi-x-circle' : kind === 'warn' ? 'bi-exclamation-triangle' : 'bi-info-circle';
    el.innerHTML = `<i class="bi ${icon}"></i><span>${esc(message)}</span>`;
    toastsBox.appendChild(el);
    setTimeout(() => el.remove(), ms);
  }

  /* ---------- vaqt tugashi / fatal ---------- */
  function goResult() {
    state.finished = true;
    window.location.href = CFG.urls.result;
  }
  function handleApiError(err, { silent = false } = {}) {
    const msg = String(err.message || '');
    if (err.status === 400 && msg.includes('vaqti tugadi')) {
      toast('Imtihon vaqti tugadi — javoblaringiz tekshiruvga yuborildi.', 'warn');
      setTimeout(goResult, 900);
      return true;
    }
    if (err.status === 404 && msg.includes('Faol imtihon')) {
      if (state.finished || state.submitting) return true;
      toast('Faol urinish topilmadi. Sahifa yangilanadi.', 'error');
      setTimeout(() => window.location.reload(), 1200);
      return true;
    }
    if (!silent) toast(msg || 'Xatolik yuz berdi.', 'error');
    return false;
  }

  /* ---------- taymer ---------- */
  function startTimer() {
    if (!state.deadline || !timerEl) return;
    timerEl.hidden = false;
    const tick = () => {
      const left = (state.deadline.getTime() - Date.now()) / 1000;
      if (timerLabelEl) timerLabelEl.textContent = fmtClock(left);
      if (left <= 60) timerEl.classList.add('is-low');
      if (left <= 0) {
        clearInterval(state.timerId);
        autoSubmit();
      }
    };
    tick();
    state.timerId = setInterval(tick, 500);
  }

  async function autoSubmit() {
    if (state.submitting || state.finished) return;
    state.submitting = true;
    toast("Vaqt tugadi — imtihon avtomatik yakunlanmoqda…", 'warn');
    try { await flushSaves(); } catch (e) { /* saqlash xatosi yakunlashni to'xtatmasin */ }
    try { await api(CFG.urls.submit); } catch (err) { /* allaqachon expire bo'lgan bo'lishi mumkin */ }
    goResult();
  }

  /* ---------- autosave navbati ---------- */
  function queueSave(key, run, delay = 1200) {
    const existing = state.pendingSaves.get(key);
    if (existing) clearTimeout(existing.timer);
    const timer = setTimeout(async () => {
      state.pendingSaves.delete(key);
      try { await run(); } catch (err) { handleApiError(err); }
    }, delay);
    state.pendingSaves.set(key, { timer, run });
  }

  async function flushSaves() {
    const jobs = [];
    state.pendingSaves.forEach(({ timer, run }) => {
      clearTimeout(timer);
      jobs.push(run().catch((err) => handleApiError(err, { silent: true })));
    });
    state.pendingSaves.clear();
    if (jobs.length) await Promise.all(jobs);
  }

  window.addEventListener('beforeunload', (e) => {
    if (state.pendingSaves.size && !state.finished) {
      e.preventDefault();
      e.returnValue = '';
    }
  });

  /* ---------- blur proctoring ---------- */
  function onBlurLike() {
    if (!state.started || state.finished || state.submitting) return;
    const now = Date.now();
    if (now - state.lastBlurAt < 3000) return;
    state.lastBlurAt = now;
    api(CFG.urls.blur)
      .then((data) => toast(`Diqqat! Sahifadan chiqish qayd etildi (${data.warnings}-marta).`, 'warn'))
      .catch(() => { /* jim */ });
  }
  window.addEventListener('blur', onBlurLike);
  document.addEventListener('visibilitychange', () => { if (document.hidden) onBlurLike(); });

  /* ---------- mavzu (theme) ---------- */
  document.querySelectorAll('[data-exam-theme]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const root = document.documentElement;
      const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('az-v2-theme', next); } catch (e) { /* private mode */ }
      const icon = btn.querySelector('i');
      if (icon) icon.className = next === 'dark' ? 'bi bi-sun' : 'bi bi-moon';
    });
  });

  /* ---------- section nav ---------- */
  function typeIcon(type) {
    return { listening: 'bi-headphones', reading: 'bi-book', writing: 'bi-pencil', speaking: 'bi-mic', grammar_quiz: 'bi-ui-checks' }[type] || 'bi-card-checklist';
  }

  function isSectionDone(sectionId) {
    const info = state.sectionDone[sectionId];
    return Boolean(info && info.total > 0 && info.answered >= info.total);
  }

  function renderNav() {
    if (!navEl) return;
    navEl.innerHTML = CFG.sections.map((sec, i) => {
      const done = isSectionDone(sec.id);
      const current = i === state.sectionIndex;
      const cls = current ? 'is-current' : done ? 'is-done' : '';
      const dot = done ? '<i class="bi bi-check-lg"></i>' : '<i class="bi bi-dot"></i>';
      const sep = i < CFG.sections.length - 1 ? '<i class="bi bi-chevron-right exam-sep"></i>' : '';
      return `<button type="button" class="exam-step ${cls}" data-x-nav="${i}"><span class="exam-step-dot">${dot}</span> ${esc(sec.title)}</button>${sep}`;
    }).join('');
    navEl.querySelectorAll('[data-x-nav]').forEach((btn) => {
      btn.addEventListener('click', () => switchSection(Number(btn.getAttribute('data-x-nav'))));
    });
  }

  async function switchSection(index) {
    if (!state.started || index === state.sectionIndex || index < 0 || index >= CFG.sections.length) return;
    stopAudio();
    stopRecorderHard();
    await flushSaves();
    loadSection(index);
  }

  function renderFoot(countsText) {
    if (!footEl) return;
    const i = state.sectionIndex;
    const prev = CFG.sections[i - 1];
    const next = CFG.sections[i + 1];
    footEl.innerHTML = `
      ${prev ? `<button type="button" class="exam-foot-btn" data-x-prev><i class="bi bi-arrow-left"></i> ${esc(prev.title)}</button>` : '<span></span>'}
      <span class="exam-foot-note" data-x-counts>${esc(countsText || '')}</span>
      ${next
        ? `<button type="button" class="exam-foot-btn exam-foot-next" data-x-next>${esc(next.title)} <i class="bi bi-arrow-right"></i></button>`
        : `<button type="button" class="exam-foot-btn exam-foot-next" data-x-finish style="background:var(--green);">Imtihonni yakunlash <i class="bi bi-check2-circle"></i></button>`}
    `;
    const prevBtn = footEl.querySelector('[data-x-prev]');
    const nextBtn = footEl.querySelector('[data-x-next]');
    const finBtn = footEl.querySelector('[data-x-finish]');
    if (prevBtn) prevBtn.addEventListener('click', () => switchSection(i - 1));
    if (nextBtn) nextBtn.addEventListener('click', () => switchSection(i + 1));
    if (finBtn) finBtn.addEventListener('click', confirmFinish);
  }

  function countsText(counts, total) {
    if (!total) return '';
    return `${counts.answered || 0} / ${total} javob berildi`;
  }

  /* ---------- section yuklash ---------- */
  async function loadSection(index) {
    state.sectionIndex = index;
    const sec = CFG.sections[index];
    if (subEl) subEl.textContent = `${sec.title} · ${sec.typeLabel}`;
    renderNav();
    renderFoot('');
    bodyEl.innerHTML = '<div class="x-loading"><span><i class="bi bi-arrow-repeat"></i> Yuklanmoqda…</span></div>';
    try {
      const payload = await api(sectionStateUrl(sec.id), { method: 'GET' });
      state.payload = payload;
      rememberCounts(payload.state);
      renderSection(payload);
    } catch (err) {
      if (!handleApiError(err)) {
        bodyEl.innerHTML = `<div class="x-loading"><span>${esc(err.message)}</span></div>`;
      }
    }
  }

  function rememberCounts(sectionState) {
    if (!sectionState) return;
    const total = (sectionState.question_map || []).length;
    const counts = sectionState.counts || {};
    const sec = CFG.sections[state.sectionIndex];
    state.sectionDone[sec.id] = { answered: counts.answered || 0, total };
  }

  function applySectionState(sectionState) {
    if (!sectionState) return;
    rememberCounts(sectionState);
    renderNav();
    const countsEl = footEl && footEl.querySelector('[data-x-counts]');
    if (countsEl) countsEl.textContent = countsText(sectionState.counts || {}, (sectionState.question_map || []).length);
    // reyl statuslarini yangilash
    (sectionState.question_map || []).forEach((entry) => {
      const key = entry.item_id != null ? `i${entry.item_id}` : `q${entry.question_id}`;
      const btn = bodyEl.querySelector(`[data-x-rail="${key}"]`);
      if (btn) {
        btn.classList.toggle('is-done', entry.status === 'done');
        btn.classList.toggle('is-review', entry.status === 'review');
      }
      const tab = bodyEl.querySelector(`[data-x-tabdot="${key}"]`);
      if (tab) tab.closest('.x-wtab, .x-sp-part') && tab.closest('.x-wtab, .x-sp-part').classList.toggle('is-done', entry.status === 'done' || entry.status === 'review');
    });
  }

  function renderSection(payload) {
    stopAudio();
    stopRecorderHard();
    const type = payload.section.section_type;
    if (payload.tasks) {
      renderRich(payload);
    } else if (type === 'writing') {
      renderWriting(payload);
    } else if (type === 'speaking') {
      renderSpeaking(payload);
    } else {
      renderQuestionList(payload);
    }
    renderFoot(countsText(payload.state.counts || {}, (payload.state.question_map || []).length));
  }

  /* ---------- umumiy bo'laklar ---------- */
  function railHTML(questionMap) {
    if (!questionMap.length) return '';
    const btns = questionMap.map((entry) => {
      const key = entry.item_id != null ? `i${entry.item_id}` : `q${entry.question_id}`;
      const cls = entry.status === 'done' ? ' is-done' : entry.status === 'review' ? ' is-review' : '';
      return `<button type="button" class="x-rail-btn${cls}" data-x-rail="${key}">${esc(entry.label)}</button>`;
    }).join('');
    return `
      <aside class="x-rail" data-appscroll>
        <div class="x-rail-title">Savollar</div>
        <div class="x-rail-grid">${btns}</div>
        <div class="x-rail-legend">
          <span><span class="x-rail-dot" style="background:var(--azure);"></span> Javob berildi</span>
          <span><span class="x-rail-dot" style="background:var(--amber-soft);border:1px solid var(--amber);"></span> Belgilangan</span>
          <span><span class="x-rail-dot" style="background:var(--paper-2);border:1px solid var(--line);"></span> Bo'sh</span>
        </div>
      </aside>`;
  }

  function bindRail(root) {
    root.querySelectorAll('[data-x-rail]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const target = root.querySelector(`[data-x-anchor="${btn.getAttribute('data-x-rail')}"]`);
        if (target) {
          target.scrollIntoView({ behavior: 'smooth', block: 'center' });
          root.querySelectorAll('.is-current[data-x-anchor]').forEach((el) => el.classList.remove('is-current'));
          target.classList.add('is-current');
        }
      });
    });
  }

  function flagButtonHTML(key, flagged) {
    return `<button type="button" class="x-flag${flagged ? ' is-on' : ''}" data-x-flag="${key}" aria-label="Belgilash"><i class="bi ${flagged ? 'bi-flag-fill' : 'bi-flag'}"></i></button>`;
  }

  function bindFlags(root) {
    root.querySelectorAll('[data-x-flag]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const key = btn.getAttribute('data-x-flag');
        const body = key.startsWith('i') ? { reading_item_id: Number(key.slice(1)) } : { question_id: Number(key.slice(1)) };
        try {
          const data = await api(CFG.urls.reviewFlag, { json: body });
          btn.classList.toggle('is-on', data.is_flagged_for_review);
          btn.innerHTML = `<i class="bi ${data.is_flagged_for_review ? 'bi-flag-fill' : 'bi-flag'}"></i>`;
          applySectionState(data.section_state);
        } catch (err) { handleApiError(err); }
      });
    });
  }

  function instructionsHTML(payload) {
    const html = payload.section.instructions || '';
    return html ? `<div class="x-instructions">${html}</div>` : '';
  }

  /* ---------- audio pleer (listening) ---------- */
  function stopAudio() {
    if (state.audio) {
      try { state.audio.pause(); } catch (e) { /* noop */ }
      state.audio = null;
    }
    state.audioSession = false;
  }

  function audioPlayerHTML(section) {
    const limit = section.audio_play_limit || 0;
    const limitChip = limit
      ? `<div class="x-audio-limit"><i class="bi bi-info-circle"></i> Audio faqat ${limit} marta tinglanadi</div>`
      : '';
    const playsLeft = limit
      ? `<span class="x-plays-left" data-x-playsleft><i class="bi bi-arrow-repeat" style="color:var(--azure);"></i> ${Math.max(section.plays_left ?? limit, 0)} tinglash qoldi</span>`
      : '';
    return `
      <section class="x-audio" data-x-audio>
        <div class="x-audio-head">
          <div class="x-audio-ico">🎧</div>
          <div style="flex:1;min-width:0;">
            <div class="x-audio-name">${esc(section.title)} — audio</div>
            <div class="x-audio-desc">Diqqat bilan tinglang va savollarga javob bering.</div>
            ${limitChip}
          </div>
        </div>
        <div class="x-audio-controls">
          <button type="button" class="x-audio-play" data-x-play aria-label="Play"><i class="bi bi-play-fill"></i></button>
          <span class="x-audio-time" data-x-cur>0:00</span>
          <div class="x-audio-track"><div class="x-audio-fill" data-x-fill></div></div>
          <span class="x-audio-time" data-x-dur>–:–</span>
        </div>
        <div class="x-audio-foot">
          <button type="button" class="x-rate is-on" data-x-rate="1">1×</button>
          <button type="button" class="x-rate" data-x-rate="1.25">1.25×</button>
          <button type="button" class="x-rate" data-x-rate="1.5">1.5×</button>
          <button type="button" class="x-rec-act" data-x-back10 style="height:30px;"><i class="bi bi-arrow-counterclockwise"></i> 10s</button>
          ${playsLeft}
        </div>
      </section>`;
  }

  function bindAudioPlayer(root, payload) {
    const box = root.querySelector('[data-x-audio]');
    if (!box) return;
    const section = payload.section;
    const audio = new Audio(section.media_url);
    audio.preload = 'metadata';
    state.audio = audio;
    let playsLeft = section.audio_play_limit ? Math.max(section.plays_left ?? section.audio_play_limit, 0) : null;

    const playBtn = box.querySelector('[data-x-play]');
    const curEl = box.querySelector('[data-x-cur]');
    const durEl = box.querySelector('[data-x-dur]');
    const fillEl = box.querySelector('[data-x-fill]');
    const leftEl = box.querySelector('[data-x-playsleft]');

    const fmtA = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
    const syncLeft = () => {
      if (leftEl && playsLeft != null) leftEl.innerHTML = `<i class="bi bi-arrow-repeat" style="color:var(--azure);"></i> ${playsLeft} tinglash qoldi`;
      if (playsLeft === 0 && !state.audioSession) playBtn.disabled = true;
    };
    syncLeft();

    audio.addEventListener('loadedmetadata', () => { if (isFinite(audio.duration)) durEl.textContent = fmtA(audio.duration); });
    audio.addEventListener('timeupdate', () => {
      curEl.textContent = fmtA(audio.currentTime);
      if (isFinite(audio.duration) && audio.duration > 0) fillEl.style.width = `${(audio.currentTime / audio.duration) * 100}%`;
    });
    audio.addEventListener('ended', () => {
      state.audioSession = false;
      playBtn.innerHTML = '<i class="bi bi-play-fill"></i>';
      syncLeft();
    });

    playBtn.addEventListener('click', async () => {
      if (!audio.paused) {
        audio.pause();
        playBtn.innerHTML = '<i class="bi bi-play-fill"></i>';
        return;
      }
      if (!state.audioSession) {
        // yangi tinglash sessiyasi — serverda ro'yxatdan o'tkazamiz (limit himoyasi)
        try {
          const data = await api(CFG.urls.audioPlay, { json: { section_id: section.id } });
          if (data.plays_left != null) playsLeft = data.plays_left;
          state.audioSession = true;
          audio.currentTime = 0;
        } catch (err) {
          if (err.status === 403) {
            playsLeft = 0;
            syncLeft();
            toast('Tinglash limiti tugadi.', 'warn');
            return;
          }
          handleApiError(err);
          return;
        }
      }
      syncLeft();
      audio.play().catch(() => toast('Audio ijro etilmadi. Havolani tekshiring.', 'error'));
      playBtn.innerHTML = '<i class="bi bi-pause-fill"></i>';
    });

    box.querySelectorAll('[data-x-rate]').forEach((btn) => {
      btn.addEventListener('click', () => {
        audio.playbackRate = Number(btn.getAttribute('data-x-rate'));
        box.querySelectorAll('[data-x-rate]').forEach((b) => b.classList.toggle('is-on', b === btn));
      });
    });
    const back10 = box.querySelector('[data-x-back10]');
    if (back10) back10.addEventListener('click', () => { if (state.audioSession) audio.currentTime = Math.max(0, audio.currentTime - 10); });
  }

  /* ---------- ODDIY savollar ro'yxati (grammar / simple listening) ---------- */
  function questionCardHTML(question, index) {
    const resp = question.response || {};
    const key = `q${question.id}`;
    let control = '';
    if (question.choices && question.choices.length) {
      control = `<div class="x-opts">${question.choices.map((choice, ci) => `
        <button type="button" class="x-opt${resp.selected_choice_id === choice.id ? ' is-picked' : ''}" data-x-choice="${choice.id}" data-x-q="${question.id}">
          <span class="x-opt-key">${String.fromCharCode(65 + ci)}</span>
          <span class="x-opt-text">${esc(choice.text)}</span>
        </button>`).join('')}</div>`;
    } else {
      control = `<textarea class="x-essay" data-x-text="${question.id}" rows="4" style="height:auto;min-height:110px;" placeholder="Javobingizni yozing…">${esc(resp.answer_text || '')}</textarea>`;
    }
    return `
      <article class="x-card" data-x-anchor="${key}">
        <div class="x-card-head">
          <div class="x-card-q">
            <span class="x-card-tag">Savol ${index + 1}</span>
            <div style="min-width:0;"><div class="x-card-text">${question.text || ''}</div></div>
          </div>
          ${flagButtonHTML(key, resp.is_flagged_for_review)}
        </div>
        ${control}
      </article>`;
  }

  function renderQuestionList(payload) {
    const hasAudio = Boolean(payload.section.media_url);
    bodyEl.innerHTML = `
      <div class="x-withrail">
        <main class="x-maincol" data-appscroll>
          <div class="x-maincol-inner">
            ${instructionsHTML(payload)}
            ${hasAudio ? audioPlayerHTML(payload.section) : ''}
            ${payload.questions.length
              ? payload.questions.map((q, i) => questionCardHTML(q, i)).join('')
              : '<div class="x-empty"><i class="bi bi-inbox"></i> Bu bo\'limda hali savollar yo\'q.</div>'}
          </div>
        </main>
        ${railHTML(payload.state.question_map || [])}
      </div>`;
    if (hasAudio) bindAudioPlayer(bodyEl, payload);
    bindRail(bodyEl);
    bindFlags(bodyEl);

    bodyEl.querySelectorAll('[data-x-choice]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const qid = Number(btn.getAttribute('data-x-q'));
        const card = btn.closest('.x-card');
        card.querySelectorAll('[data-x-choice]').forEach((b) => b.classList.remove('is-picked'));
        btn.classList.add('is-picked');
        try {
          const data = await api(CFG.urls.save, { json: { question_id: qid, choice_id: Number(btn.getAttribute('data-x-choice')), current_question_id: qid } });
          applySectionState(data.section_state);
        } catch (err) { handleApiError(err); }
      });
    });

    bodyEl.querySelectorAll('[data-x-text]').forEach((area) => {
      area.addEventListener('input', () => {
        const qid = Number(area.getAttribute('data-x-text'));
        queueSave(`q${qid}`, async () => {
          const data = await api(CFG.urls.save, { json: { question_id: qid, answer_text: area.value, current_question_id: qid } });
          applySectionState(data.section_state);
        });
      });
    });
  }

  /* ---------- BOY task engine (reading / rich listening) ---------- */
  const TF_LABELS = { true_false_not_given: 1, yes_no_not_given: 1 };

  function optionLabel(option, index) {
    return option.label || option.key || String.fromCharCode(65 + index);
  }

  function richItemHTML(task, item) {
    const key = `i${item.id}`;
    const resp = item.response || {};
    const flag = task.allow_review_flag ? flagButtonHTML(key, resp.is_flagged_for_review) : '';
    const helper = item.helper_text ? `<div class="x-helper">${esc(item.helper_text)}</div>` : '';

    // 1) per-item variantlar (single/multiple choice)
    if (task.task_type === 'single_choice' || task.task_type === 'multiple_choice') {
      const picked = new Set(task.task_type === 'multiple_choice' ? (resp.selected_option_ids || []) : (resp.selected_option_id != null ? [resp.selected_option_id] : []));
      const multi = task.task_type === 'multiple_choice';
      const hint = multi && task.max_selections_per_item > 1 ? `<div class="x-helper"><i class="bi bi-check2-square"></i> ${task.max_selections_per_item} ta javob tanlang</div>` : '';
      return `
        <article class="x-card" data-x-anchor="${key}">
          <div class="x-card-head">
            <div class="x-card-q">
              <span class="x-card-tag">${esc(item.short_label || item.id)}</span>
              <div style="min-width:0;"><div class="x-card-text">${esc(item.prompt)}</div>${helper}${hint}</div>
            </div>
            ${flag}
          </div>
          <div class="x-opts">${item.options.map((option, oi) => `
            <button type="button" class="x-opt${picked.has(option.id) ? ' is-picked' : ''}" data-x-ritem="${item.id}" data-x-ropt="${option.id}" data-x-multi="${multi ? 1 : 0}" data-x-max="${task.max_selections_per_item || 1}">
              <span class="x-opt-key">${esc(optionLabel(option, oi))}</span>
              <span class="x-opt-text">${esc(option.text)}</span>
            </button>`).join('')}</div>
        </article>`;
    }

    // 2) shared-option turlari (TF/NG, YN/NG, matching)
    if (task.shared_options && task.shared_options.length && (TF_LABELS[task.task_type] || task.task_type === 'matching')) {
      if (task.task_type !== 'matching' && task.shared_options.length <= 4) {
        // TF/NG — tugmalar qatori
        return `
          <article class="x-card" data-x-anchor="${key}">
            <div class="x-card-head">
              <div class="x-card-q">
                <span class="x-card-tag">${esc(item.short_label || item.id)}</span>
                <div style="min-width:0;"><div class="x-card-text">${esc(item.prompt)}</div>${helper}</div>
              </div>
              ${flag}
            </div>
            <div class="x-tfrow">${task.shared_options.map((option) => `
              <button type="button" class="x-tfbtn${resp.selected_option_id === option.id ? ' is-picked' : ''}" data-x-ritem="${item.id}" data-x-ropt="${option.id}" data-x-shared="1">${esc(option.text || option.label)}</button>`).join('')}</div>
          </article>`;
      }
      // matching — dropdown
      const options = task.shared_options.map((option, oi) => {
        const lab = optionLabel(option, oi);
        const text = option.text ? `${lab}. ${option.text}` : lab;
        return `<option value="${option.id}"${resp.selected_option_id === option.id ? ' selected' : ''}>${esc(text.length > 46 ? text.slice(0, 44) + '…' : text)}</option>`;
      }).join('');
      return `
        <div class="x-matchrow" data-x-anchor="${key}">
          <span class="x-mlabel">${esc(item.short_label || item.id)}</span>
          <span class="x-mprompt">${esc(item.prompt)}${helper}</span>
          <select class="x-select${resp.selected_option_id ? ' is-picked' : ''}" data-x-rselect="${item.id}">
            <option value="">Tanlang…</option>${options}
          </select>
          ${flag}
        </div>`;
    }

    // 3) matn turlari (text_input / structured_gap_fill / diagram_label)
    const words = task.max_words_per_answer ? `<span class="x-wordhint">≤ ${task.max_words_per_answer} so'z</span>` : '';
    return `
      <div class="x-inputrow" data-x-anchor="${key}">
        <span class="x-mlabel">${esc(item.short_label || item.id)}</span>
        <span class="x-mprompt">${esc(item.prompt)}${helper}</span>
        <input class="x-input" type="text" value="${esc(resp.text_answer || '')}" data-x-rtext="${item.id}" placeholder="Javob…">
        ${words}
        ${flag}
      </div>`;
  }

  function richTaskHTML(task) {
    const range = task.question_from && task.question_to ? `Savol ${task.question_from}–${task.question_to}` : '';
    const shared = task.task_type === 'matching' && task.shared_options.length ? `
      <div class="x-shared">
        <div class="x-shared-title">Variantlar ro'yxati</div>
        ${task.shared_options.map((option, oi) => `<div class="x-shared-item"><b>${esc(optionLabel(option, oi))}.</b><span>${esc(option.text)}</span></div>`).join('')}
      </div>` : '';
    return `
      <div class="x-taskhead">
        ${range ? `<div class="x-range">${esc(range)}</div>` : ''}
        <h2>${esc(task.title || '')}</h2>
        ${task.instructions ? `<div class="x-taskinstr">${task.instructions}</div>` : ''}
      </div>
      ${task.body ? `<div class="x-taskbody">${task.body}</div>` : ''}
      ${shared}
      ${task.items.map((item) => richItemHTML(task, item)).join('')}`;
  }

  function passageHTML(passage, index) {
    const labels = (passage.paragraph_labels || '').trim();
    let body;
    if (labels) {
      const parts = passage.body.split(/\n\s*\n/);
      const letters = labels.split(/[,\s]+/).filter(Boolean);
      body = parts.map((part, pi) => `
        <div class="x-para">
          <span class="x-para-label">${esc(letters[pi] || String.fromCharCode(65 + pi))}</span>
          <p class="x-para-text">${part}</p>
        </div>`).join('');
    } else {
      body = `<div class="x-passage-body">${passage.body || ''}</div>`;
    }
    return `
      <div class="x-passage" style="margin-bottom:30px;">
        <span class="x-passage-tag">PASSAGE ${index + 1}</span>
        <h1>${esc(passage.title || '')}</h1>
        ${body}
      </div>`;
  }

  function renderRich(payload) {
    const hasPassages = payload.passages && payload.passages.length;
    const hasAudio = Boolean(payload.section.media_url);
    const tasksHTML = `
      ${instructionsHTML(payload)}
      ${hasAudio ? audioPlayerHTML(payload.section) : ''}
      ${payload.tasks.length
        ? payload.tasks.map((task) => richTaskHTML(task)).join('')
        : '<div class="x-empty"><i class="bi bi-inbox"></i> Task topilmadi.</div>'}`;

    if (hasPassages) {
      bodyEl.innerHTML = `
        <div class="x-split">
          <div class="x-pane" data-appscroll><div class="x-pane-inner">${payload.passages.map((p, i) => passageHTML(p, i)).join('')}</div></div>
          <div class="x-pane" data-appscroll><div class="x-pane-inner">${tasksHTML}</div></div>
        </div>`;
    } else {
      bodyEl.innerHTML = `
        <div class="x-withrail">
          <main class="x-maincol" data-appscroll><div class="x-maincol-inner">${tasksHTML}</div></main>
          ${railHTML(payload.state.question_map || [])}
        </div>`;
      bindRail(bodyEl);
    }
    if (hasAudio) bindAudioPlayer(bodyEl, payload);
    bindFlags(bodyEl);
    bindRichControls();
  }

  async function saveReadingItem(itemId, body) {
    body.reading_item_id = itemId;
    body.current_item_id = itemId;
    const data = await api(CFG.urls.save, { json: body });
    applySectionState(data.section_state);
    return data;
  }

  function bindRichControls() {
    // single / multiple choice
    bodyEl.querySelectorAll('[data-x-ropt][data-x-multi]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const itemId = Number(btn.getAttribute('data-x-ritem'));
        const card = btn.closest('.x-card');
        const multi = btn.getAttribute('data-x-multi') === '1';
        try {
          if (multi) {
            const max = Number(btn.getAttribute('data-x-max')) || 99;
            const willPick = !btn.classList.contains('is-picked');
            const pickedNow = card.querySelectorAll('.x-opt.is-picked').length;
            if (willPick && pickedNow >= max) { toast(`Ko'pi bilan ${max} ta javob tanlash mumkin.`, 'warn'); return; }
            btn.classList.toggle('is-picked');
            const ids = Array.from(card.querySelectorAll('.x-opt.is-picked')).map((b) => Number(b.getAttribute('data-x-ropt')));
            await saveReadingItem(itemId, { option_ids: ids });
          } else {
            card.querySelectorAll('.x-opt').forEach((b) => b.classList.remove('is-picked'));
            btn.classList.add('is-picked');
            await saveReadingItem(itemId, { option_id: Number(btn.getAttribute('data-x-ropt')) });
          }
        } catch (err) { handleApiError(err); }
      });
    });

    // TF/NG shared tugmalar
    bodyEl.querySelectorAll('[data-x-shared]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const itemId = Number(btn.getAttribute('data-x-ritem'));
        const row = btn.closest('.x-card');
        row.querySelectorAll('[data-x-shared]').forEach((b) => b.classList.remove('is-picked'));
        btn.classList.add('is-picked');
        try { await saveReadingItem(itemId, { option_id: Number(btn.getAttribute('data-x-ropt')) }); }
        catch (err) { handleApiError(err); }
      });
    });

    // matching select
    bodyEl.querySelectorAll('[data-x-rselect]').forEach((sel) => {
      sel.addEventListener('change', async () => {
        const itemId = Number(sel.getAttribute('data-x-rselect'));
        sel.classList.toggle('is-picked', Boolean(sel.value));
        try { await saveReadingItem(itemId, { option_id: sel.value ? Number(sel.value) : '' }); }
        catch (err) { handleApiError(err); }
      });
    });

    // text input
    bodyEl.querySelectorAll('[data-x-rtext]').forEach((input) => {
      input.addEventListener('input', () => {
        const itemId = Number(input.getAttribute('data-x-rtext'));
        queueSave(`i${itemId}`, async () => {
          await saveReadingItem(itemId, { text_answer: input.value });
          input.classList.add('is-saved');
          setTimeout(() => input.classList.remove('is-saved'), 1600);
        });
      });
    });
  }

  /* ---------- WRITING ---------- */
  function renderWriting(payload) {
    const questions = payload.questions;
    if (!questions.length) {
      bodyEl.innerHTML = '<div class="x-loading"><div class="x-empty"><i class="bi bi-inbox"></i> Writing topshirig\'i hali qo\'shilmagan.</div></div>';
      return;
    }
    let active = 0;
    const current = payload.state.current_question_id;
    const idx = questions.findIndex((q) => q.id === current);
    if (idx >= 0) active = idx;

    const draw = () => {
      const q = questions[active];
      const resp = q.response || {};
      const tabs = questions.length > 1 ? `
        <div class="x-wtabs">${questions.map((question, i) => {
          const done = (question.response && (question.response.answer_text || '').trim()) ? ' is-done' : '';
          return `<button type="button" class="x-wtab${i === active ? ' is-active' : ''}${done}" data-x-wtab="${i}"><span class="x-wtab-dot" data-x-tabdot="q${question.id}"></span> Task ${i + 1}</button>`;
        }).join('')}</div>` : '';
      const min = q.min_word_count || 0;
      const max = q.max_word_count || 0;
      const req = min && max ? `min ${min} · max ${max}` : min ? `min: ${min}` : max ? `max: ${max}` : '';
      const meta = `
        <div class="x-wmeta">
          ${min ? `<span><i class="bi bi-hash"></i> Minimum ${min} so'z</span>` : ''}
          ${max ? `<span><i class="bi bi-slash-circle"></i> Maksimum ${max} so'z</span>` : ''}
          <span><i class="bi bi-award"></i> ${q.points} ball</span>
        </div>`;

      bodyEl.innerHTML = `
        <div class="x-writing">
          <div class="x-wtask" data-appscroll>
            <div class="x-wtask-inner">
              <div class="x-kicker"><i class="bi bi-${active + 1}-circle"></i> WRITING TASK ${active + 1}</div>
              ${meta}
              <div class="x-wprompt">${q.text || ''}</div>
              ${instructionsHTML(payload)}
            </div>
          </div>
          <div class="x-weditor">
            <div class="x-weditor-top">
              ${tabs}
              <span class="x-savestate" data-x-savestate><i class="bi bi-cloud"></i> <span>—</span></span>
              ${flagButtonHTML(`q${q.id}`, resp.is_flagged_for_review)}
            </div>
            <div class="x-wbody">
              <textarea class="x-essay" data-x-essay placeholder="Yozishni boshlang…">${esc(resp.answer_text || '')}</textarea>
            </div>
            <div class="x-wfoot">
              <div class="x-wprogress"><div class="x-wprogress-fill" data-x-wfill></div></div>
              <span class="x-wcount" data-x-wcount>0 so'z</span>
              ${req ? `<span class="x-wreq">${esc(req)}</span>` : ''}
              <span class="x-wreq" data-x-wchars>0 belgi</span>
            </div>
          </div>
        </div>`;

      const area = bodyEl.querySelector('[data-x-essay]');
      const fill = bodyEl.querySelector('[data-x-wfill]');
      const countEl = bodyEl.querySelector('[data-x-wcount]');
      const charsEl = bodyEl.querySelector('[data-x-wchars]');
      const saveEl = bodyEl.querySelector('[data-x-savestate]');

      const paint = (words) => {
        countEl.textContent = `${words} so'z`;
        charsEl.textContent = `${area.value.length} belgi`;
        countEl.className = 'x-wcount';
        fill.className = 'x-wprogress-fill';
        let pct = min ? Math.min(100, (words / min) * 100) : (words ? 100 : 0);
        if (min && words < min) countEl.classList.add('is-short');
        else if (max && words > max) { countEl.classList.add('is-over'); fill.classList.add('is-over'); pct = 100; }
        else if (words) { countEl.classList.add('is-ok'); fill.classList.add('is-ok'); }
        fill.style.width = `${pct}%`;
      };
      paint(wordCount(area.value));

      const setSave = (mode, label) => {
        saveEl.className = `x-savestate is-${mode}`;
        saveEl.innerHTML = `<i class="bi ${mode === 'saved' ? 'bi-cloud-check' : mode === 'saving' ? 'bi-cloud-arrow-up' : 'bi-cloud-slash'}"></i> <span>${esc(label)}</span>`;
      };

      area.addEventListener('input', () => {
        paint(wordCount(area.value));
        setSave('saving', 'Yozilmoqda…');
        queueSave(`q${q.id}`, async () => {
          try {
            const data = await api(CFG.urls.save, { json: { question_id: q.id, answer_text: area.value, current_question_id: q.id } });
            q.response = q.response || {};
            q.response.answer_text = area.value;
            applySectionState(data.section_state);
            setSave('saved', 'Saqlandi');
          } catch (err) {
            setSave('error', 'Saqlanmadi');
            throw err;
          }
        }, 1400);
      });

      bodyEl.querySelectorAll('[data-x-wtab]').forEach((btn) => {
        btn.addEventListener('click', async () => {
          await flushSaves();
          active = Number(btn.getAttribute('data-x-wtab'));
          draw();
        });
      });
      bindFlags(bodyEl);
    };
    draw();
  }

  /* ---------- SPEAKING ---------- */
  function stopRecorderHard() {
    const rec = state.rec;
    if (!rec) return;
    try { if (rec.recorder && rec.recorder.state !== 'inactive') rec.recorder.stop(); } catch (e) { /* noop */ }
    if (rec.stream) rec.stream.getTracks().forEach((t) => t.stop());
    if (rec.timerId) clearInterval(rec.timerId);
    state.rec = null;
  }

  function renderSpeaking(payload) {
    const questions = payload.questions;
    if (!questions.length) {
      bodyEl.innerHTML = '<div class="x-loading"><div class="x-empty"><i class="bi bi-inbox"></i> Speaking topshirig\'i hali qo\'shilmagan.</div></div>';
      return;
    }
    let active = 0;
    const current = payload.state.current_question_id;
    const idx = questions.findIndex((q) => q.id === current);
    if (idx >= 0) active = idx;

    const draw = () => {
      stopRecorderHard();
      const q = questions[active];
      const resp = q.response || {};
      const parts = questions.map((question, i) => {
        const saved = Boolean(question.response && question.response.audio_url);
        const cls = i === active ? ' is-active' : saved ? ' is-done' : '';
        const icon = saved ? 'bi-check-circle-fill' : i === active ? 'bi-mic-fill' : 'bi-circle';
        return `<button type="button" class="x-sp-part${cls}" data-x-part="${i}"><i class="bi ${icon}"></i> Part ${i + 1}</button>`;
      }).join('<i class="bi bi-chevron-right" style="color:var(--ink-4);font-size:11px;flex:0 0 auto;"></i>');

      bodyEl.innerHTML = `
        <div class="x-speaking">
          <div class="x-sp-parts">${parts}</div>
          <div class="x-sp-body" data-appscroll>
            <div class="x-sp-inner">
              <section class="x-prompt-card">
                <div class="x-kicker"><i class="bi bi-${active + 1}-circle"></i> PART ${active + 1}</div>
                <h1 style="font-size:15px;">Topshiriq:</h1>
                <div class="x-wprompt">${q.text || ''}</div>
                ${instructionsHTML(payload)}
              </section>
              <section class="x-rec" data-x-rec>
                <div class="x-rec-hint" data-x-rechint>${resp.audio_url ? 'Javobingiz yuklangan. Qayta yozishingiz mumkin.' : 'Mikrofon tugmasini bosib yozishni boshlang'}</div>
                <div class="x-rec-wrap">
                  <span class="x-rec-ring"></span>
                  <button type="button" class="x-rec-btn" data-x-recbtn aria-label="Yozish"><i class="bi bi-mic-fill"></i></button>
                </div>
                <div class="x-rec-time" data-x-rectime>00:00</div>
                <div class="x-rec-max">Maksimal: 5:00</div>
                <div class="x-rec-preview" data-x-preview hidden></div>
                <div class="x-rec-actions" data-x-recacts></div>
                <div data-x-savedchip>${resp.audio_url ? `<span class="x-rec-saved"><i class="bi bi-cloud-check"></i> Javob saqlangan</span><div class="x-rec-preview"><audio controls src="${esc(resp.audio_url)}"></audio></div>` : ''}</div>
              </section>
            </div>
          </div>
        </div>`;

      bodyEl.querySelectorAll('[data-x-part]').forEach((btn) => {
        btn.addEventListener('click', () => { active = Number(btn.getAttribute('data-x-part')); draw(); });
      });
      bindSpeakingRecorder(q, draw);
    };
    draw();
  }

  function bindSpeakingRecorder(question, redraw) {
    const box = bodyEl.querySelector('[data-x-rec]');
    const btn = box.querySelector('[data-x-recbtn]');
    const timeEl = box.querySelector('[data-x-rectime]');
    const hintEl = box.querySelector('[data-x-rechint]');
    const previewEl = box.querySelector('[data-x-preview]');
    const actsEl = box.querySelector('[data-x-recacts]');
    const MAX_SECS = 300;

    let blob = null;

    const startRec = async () => {
      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch (e) {
        toast("Mikrofonga ruxsat berilmadi. Brauzer sozlamalarini tekshiring.", 'error');
        return;
      }
      const mime = window.MediaRecorder && MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '';
      const recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      const chunks = [];
      recorder.addEventListener('dataavailable', (e) => { if (e.data && e.data.size) chunks.push(e.data); });
      recorder.addEventListener('stop', () => {
        stream.getTracks().forEach((t) => t.stop());
        if (state.rec && state.rec.timerId) clearInterval(state.rec.timerId);
        blob = new Blob(chunks, { type: mime || 'audio/webm' });
        state.rec = null;
        box.classList.remove('is-recording');
        btn.innerHTML = '<i class="bi bi-mic-fill"></i>';
        hintEl.textContent = "Yozuv tayyor — eshitib ko'ring va yuklang";
        previewEl.hidden = false;
        previewEl.innerHTML = `<audio controls src="${URL.createObjectURL(blob)}"></audio>`;
        actsEl.innerHTML = `
          <button type="button" class="x-rec-act is-primary" data-x-upload><i class="bi bi-cloud-arrow-up"></i> Javobni yuklash</button>
          <button type="button" class="x-rec-act" data-x-retry><i class="bi bi-arrow-counterclockwise"></i> Qayta yozish</button>`;
        actsEl.querySelector('[data-x-upload]').addEventListener('click', upload);
        actsEl.querySelector('[data-x-retry]').addEventListener('click', reset);
      });

      let secs = 0;
      const timerId = setInterval(() => {
        secs += 1;
        timeEl.textContent = `${String(Math.floor(secs / 60)).padStart(2, '0')}:${String(secs % 60).padStart(2, '0')}`;
        if (secs >= MAX_SECS) stopRec();
      }, 1000);

      state.rec = { recorder, stream, timerId };
      recorder.start();
      box.classList.add('is-recording');
      btn.innerHTML = '<i class="bi bi-stop-fill"></i>';
      hintEl.textContent = "Yozilmoqda… To'xtatish uchun tugmani qayta bosing";
      previewEl.hidden = true;
      previewEl.innerHTML = '';
      actsEl.innerHTML = '';
    };

    const stopRec = () => {
      if (state.rec && state.rec.recorder && state.rec.recorder.state !== 'inactive') state.rec.recorder.stop();
    };

    const reset = () => {
      blob = null;
      previewEl.hidden = true;
      previewEl.innerHTML = '';
      actsEl.innerHTML = '';
      timeEl.textContent = '00:00';
      hintEl.textContent = 'Mikrofon tugmasini bosib yozishni boshlang';
    };

    const upload = async () => {
      if (!blob) return;
      const uploadBtn = actsEl.querySelector('[data-x-upload]');
      uploadBtn.disabled = true;
      uploadBtn.innerHTML = '<i class="bi bi-arrow-repeat"></i> Yuklanmoqda…';
      const form = new FormData();
      form.append('question_id', String(question.id));
      form.append('current_question_id', String(question.id));
      form.append('audio', blob, 'javob.webm');
      try {
        const data = await api(CFG.urls.audioUpload, { form });
        question.response = question.response || {};
        question.response.audio_url = data.audio_url;
        applySectionState(data.section_state);
        toast('Speaking javobi saqlandi.', 'info');
        redraw(); // saqlangan holat + part chipi yangilanadi
      } catch (err) {
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = '<i class="bi bi-cloud-arrow-up"></i> Javobni yuklash';
        handleApiError(err);
      }
    };

    btn.addEventListener('click', () => {
      if (state.rec) stopRec();
      else startRec();
    });
  }

  /* ---------- yakunlash ---------- */
  function confirmFinish() {
    if (!state.started || state.submitting || state.finished) return;
    const doneInfo = CFG.sections.map((sec) => {
      const info = state.sectionDone[sec.id];
      return info ? `${sec.title}: ${info.answered}/${info.total}` : `${sec.title}: —`;
    }).join(' · ');
    const back = document.createElement('div');
    back.className = 'x-modal-back';
    back.innerHTML = `
      <div class="x-modal">
        <h3>Imtihonni yakunlaysizmi?</h3>
        <p>Javoblaringiz o'qituvchi tekshiruviga yuboriladi va qayta o'zgartirib bo'lmaydi.</p>
        <p class="x-modal-warn"><i class="bi bi-info-circle"></i> ${esc(doneInfo)}</p>
        <div class="x-modal-actions">
          <button type="button" class="x-modal-btn" data-x-cancel>Bekor qilish</button>
          <button type="button" class="x-modal-btn is-primary" data-x-confirm>Ha, yakunlash</button>
        </div>
      </div>`;
    document.body.appendChild(back);
    back.querySelector('[data-x-cancel]').addEventListener('click', () => back.remove());
    back.addEventListener('click', (e) => { if (e.target === back) back.remove(); });
    back.querySelector('[data-x-confirm]').addEventListener('click', async () => {
      const confirmBtn = back.querySelector('[data-x-confirm]');
      confirmBtn.disabled = true;
      confirmBtn.textContent = 'Yuborilmoqda…';
      state.submitting = true;
      try {
        await flushSaves();
        await api(CFG.urls.submit);
        goResult();
      } catch (err) {
        state.submitting = false;
        confirmBtn.disabled = false;
        confirmBtn.textContent = 'Ha, yakunlash';
        if (handleApiError(err)) return;
      }
    });
  }

  document.querySelectorAll('[data-exam-finish]').forEach((btn) => btn.addEventListener('click', confirmFinish));

  /* ---------- start oqimi ---------- */
  async function startExam(startBtn) {
    if (startBtn) { startBtn.disabled = true; startBtn.innerHTML = '<i class="bi bi-arrow-repeat"></i> Boshlanmoqda…'; }
    try {
      const data = await api(CFG.urls.start);
      state.started = true;
      if (data.deadline) {
        state.deadline = new Date(data.deadline);
        startTimer();
      }
      if (overlayEl) overlayEl.remove();
      loadSection(0);
    } catch (err) {
      if (startBtn) { startBtn.disabled = false; startBtn.innerHTML = '<i class="bi bi-play-fill"></i> Imtihonni boshlash'; }
      if (err.data && err.data.code === 'pending_review') {
        toast('Oldingi urinish hali tekshirilmoqda.', 'warn');
        setTimeout(goResult, 900);
        return;
      }
      handleApiError(err);
    }
  }

  const startBtn = document.querySelector('[data-exam-start]');
  if (startBtn) startBtn.addEventListener('click', () => startExam(startBtn));
})();
