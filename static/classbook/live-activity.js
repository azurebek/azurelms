(() => {
  const root = document.querySelector('[data-live-activity]');
  const payloadNode = document.getElementById('exercisePayload');
  const renderer = root?.querySelector('[data-exercise-renderer]');
  const form = root?.querySelector('[data-answer-form]');
  if (!root || !payloadNode) return;
  const exercise = JSON.parse(payloadNode.textContent);
  let order = [];

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const choice = (item, type) => {
    const label = el('label', 'cb-option');
    const input = document.createElement('input'); input.type = type; input.name = 'answer'; input.value = item.id;
    label.append(input, el('span', '', item.text)); return label;
  };
  const selectFor = (name, options, placeholder) => {
    const select = document.createElement('select'); select.name = name; select.required = true;
    const first = document.createElement('option'); first.value = ''; first.textContent = placeholder; select.append(first);
    options.forEach((item) => { const option = document.createElement('option'); option.value = item.id; option.textContent = item.text; select.append(option); });
    return select;
  };

  if (renderer && form) {
    const kind = exercise.kind, config = exercise.config || {};
    if (['single_choice', 'true_false', 'poll'].includes(kind)) config.options.forEach((item) => renderer.append(choice(item, 'radio')));
    else if (kind === 'multiple_choice') config.options.forEach((item) => renderer.append(choice(item, 'checkbox')));
    else if (['short_answer', 'fill_blank'].includes(kind)) { const input = document.createElement('input'); input.className = 'cb-text-answer'; input.name = 'answer'; input.placeholder = config.placeholder || 'Javobingiz'; input.autocomplete = 'off'; renderer.append(input); }
    else if (kind === 'matching') config.left.forEach((item) => { const row = el('label', 'cb-map-row'); row.append(el('span', '', item.text), selectFor(item.id, config.right, 'Mosini tanlang')); renderer.append(row); });
    else if (['ordering', 'unscramble'].includes(kind)) {
      order = config.items.map((item) => item.id);
      const draw = () => { renderer.replaceChildren(); order.forEach((id, index) => { const item = config.items.find((candidate) => candidate.id === id); const row = el('div', 'cb-order-item'); row.append(el('b', '', String(index + 1)), el('span', '', item.text)); const controls = el('span', 'cb-order-controls'); const up = el('button', '', '↑'); up.type = 'button'; up.disabled = index === 0; up.onclick = () => { [order[index - 1], order[index]] = [order[index], order[index - 1]]; draw(); }; const down = el('button', '', '↓'); down.type = 'button'; down.disabled = index === order.length - 1; down.onclick = () => { [order[index + 1], order[index]] = [order[index], order[index + 1]]; draw(); }; controls.append(up, down); row.append(controls); renderer.append(row); }); };
      draw();
    } else if (kind === 'categorization') config.items.forEach((item) => { const row = el('label', 'cb-map-row'); row.append(el('span', '', item.text), selectFor(item.id, config.categories, 'Kategoriya')); renderer.append(row); });

    const collect = () => {
      if (['single_choice', 'true_false', 'poll'].includes(kind)) return form.querySelector('input[name="answer"]:checked')?.value || null;
      if (kind === 'multiple_choice') return [...form.querySelectorAll('input[name="answer"]:checked')].map((node) => node.value);
      if (['short_answer', 'fill_blank'].includes(kind)) return form.querySelector('[name="answer"]').value;
      if (['ordering', 'unscramble'].includes(kind)) return order;
      if (['matching', 'categorization'].includes(kind)) return Object.fromEntries([...form.querySelectorAll('select')].map((node) => [node.name, node.value]));
      return null;
    };
    const csrf = () => document.cookie.split(';').map((v) => v.trim()).find((v) => v.startsWith('csrftoken='))?.split('=')[1] || '';
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const button = form.querySelector('button[type="submit"]'); const status = form.querySelector('[data-form-status]');
      button.disabled = true; status.textContent = 'Yuborilmoqda…';
      try {
        const response = await fetch(root.dataset.submitUrl, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf()}, body: JSON.stringify({answer: collect()})});
        const data = await response.json();
        status.textContent = data.message;
        if (data.ok) { status.classList.add('is-success'); renderer.querySelectorAll('input,select,button').forEach((node) => node.disabled = true); button.textContent = 'Javob qabul qilindi'; }
        else button.disabled = false;
      } catch (_) { status.textContent = 'Aloqa uzildi. Qayta urinib ko‘ring.'; button.disabled = false; }
    });
  }

  const timer = root.querySelector('[data-timer]');
  const deadline = exercise.closes_at ? new Date(exercise.closes_at).getTime() : null;
  if (timer && deadline) setInterval(() => { const left = Math.max(0, Math.ceil((deadline - Date.now()) / 1000)); timer.textContent = `${String(Math.floor(left / 60)).padStart(2, '0')}:${String(left % 60).padStart(2, '0')}`; if (!left && form) form.querySelector('button[type="submit"]')?.setAttribute('disabled', ''); }, 250);

  const checkState = async () => {
    try { const response = await fetch(root.dataset.stateUrl, {headers: {'X-Requested-With': 'XMLHttpRequest'}}); if (response.ok && (await response.json()).status === 'revealed') location.assign(root.dataset.resultUrl); } catch (_) {}
  };
  if (window.ClassbookSocket) window.ClassbookSocket(root.dataset.sessionId, (data) => {
    if (data.event_type === 'activity_closed' && data.payload.activity_id === exercise.activity_id) checkState();
  });
  setInterval(checkState, 3000);
})();
