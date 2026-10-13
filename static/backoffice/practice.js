(() => {
  "use strict";
  const prefix = "azurelms:practice:draft:v1:";
  // Only authored content and structure. Never persist consent, CSRF or revisions.
  const allowed = name => ["title", "description", "max_xp", "xp_reward", "questions-TOTAL_FORMS"].includes(name) ||
    /^questions-\d{1,3}-(?:id|text|correct|choices-TOTAL_FORMS|choices-\d{1,3}-(?:id|text))$/.test(name);
  const same = (left, right) => left && right && Object.keys(left).length === Object.keys(right).length &&
    Object.keys(left).every(key => left[key] === right[key]);
  const valid = record => record?.version === 1 && record.values && typeof record.values === "object" &&
    !Array.isArray(record.values) && Object.keys(record.values).length <= 1000 &&
    Object.entries(record.values).every(([key, value]) => allowed(key) && typeof value === "string");
  const storage = {
    read(key) { try { const value = JSON.parse(sessionStorage.getItem(key)); return valid(value) ? value : null; } catch { return null; } },
    write(key, value) { try { sessionStorage.setItem(key, JSON.stringify(value)); return true; } catch { return false; } },
    remove(key) { try { sessionStorage.removeItem(key); } catch { /* Scope also changes after logout. */ } },
  };
  const nonce = () => window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  document.querySelectorAll("[data-practice-saved]").forEach(marker => {
    const key = prefix + marker.dataset.savedScope;
    const record = storage.read(key);
    if (record && marker.dataset.savedSubmissionId && record.lastSubmission?.id === marker.dataset.savedSubmissionId &&
        same(record.values, record.lastSubmission.values)) storage.remove(key);
  });

  let leaving = false;
  let loggingOut = false;
  const controllers = [];
  document.querySelectorAll("[data-practice-draft]").forEach(form => {
    if (!form.dataset.draftScope) return;
    const key = prefix + form.dataset.draftScope;
    const fields = [...form.querySelectorAll("input[name],textarea[name],select[name]")]
      .filter(field => allowed(field.name) && !field.disabled && !["file", "password"].includes(field.type));
    const editors = new Map();
    const banner = form.querySelector("[data-draft-recovery]");
    const status = form.querySelector("[data-draft-status]");
    let record = storage.read(key);
    let touched = false;
    let submitting = false;
    const bound = form.dataset.boundForm === "true";
    let persisted = record?.values || null;
    function values() {
      const result = {};
      for (const field of fields) {
        if (field.type === "radio") {
          if (!(field.name in result)) result[field.name] = "";
          if (field.checked) result[field.name] = field.value;
        } else result[field.name] = editors.get(field.id)?.getData() ?? field.value;
      }
      return result;
    }
    let initial = values();
    function setStatus(message) { if (status) status.textContent = message; }
    function persist() {
      const current = values();
      record = {...(record || {}), version: 1, values: current};
      const ok = storage.write(key, record);
      if (ok) persisted = current;
      setStatus(ok ? "Qoralama shu brauzer oynasida saqlanmoqda. Darsga saqlashni alohida tasdiqlang." :
        "Brauzer qoralamani saqlay olmadi. Chiqishdan oldin matnni nusxalang yoki darsga saqlang.");
      return ok;
    }
    function offer() {
      if (banner) banner.hidden = !record || same(record.values, values()) || touched;
    }
    function edit() {
      touched = true;
      if (banner) banner.hidden = true;
      persist();
    }
    // A native POST may add/remove rows. Only its matching response may advance
    // that local draft; opening an unrelated rejected response must not replace it.
    const returnedTransfer = Boolean(bound && record?.lastTransfer?.id &&
      record.lastTransfer.id === form.dataset.draftTransferId && same(record.values, record.lastTransfer.values));
    const ownsBoundDraft = returnedTransfer || (bound && !record);
    if (ownsBoundDraft) persist();
    if (bound && form.dataset.draftGetUrl && window.history?.replaceState) {
      try {
        const target = new URL(form.dataset.draftGetUrl, location.href);
        if (target.origin === location.origin && target.pathname === location.pathname)
          window.history.replaceState(window.history.state, "", target.href);
      } catch { /* POST content remains usable if history is unavailable. */ }
    }
    form.addEventListener("input", event => { if (fields.includes(event.target)) edit(); });
    form.addEventListener("change", event => { if (fields.includes(event.target)) edit(); });
    fields.filter(field => field.matches("textarea.django_ckeditor_5")).forEach(field => {
      function attach(editor) {
        if (editors.has(field.id)) return;
        editors.set(field.id, editor);
        if (!touched) initial[field.name] = editor.getData();
        editor.model.document.on("change:data", edit);
        // CKEditor normalizes empty/rich paragraphs on startup. This is part
        // of our matching response, not a second recoverable draft.
        if (ownsBoundDraft && !touched) persist();
        offer();
      }
      if (window.editors?.[field.id]) attach(window.editors[field.id]);
      else window.ckeditorRegisterCallback?.(field.id, attach);
    });
    function hidden(target, name, value) {
      const input = document.createElement("input");
      input.type = "hidden"; input.name = name; input.value = value;
      target.append(input);
      return input;
    }
    function offline() {
      if (window.navigator?.onLine !== false) return false;
      setStatus("Aloqa yo‘q. Qoralama shu oynada qoladi; aloqa qaytgach amalni qayta bosing.");
      return true;
    }
    form.querySelector("[data-draft-restore]")?.addEventListener("click", () => {
      if (!record || submitting || offline()) return;
      // The server rebuilds the nested forms with the same bounded parser used
      // by ordinary editing. This action cannot save content or create attempts.
      const restored = document.createElement("form");
      // Named action buttons shadow the native form.action property.
      restored.method = "post"; restored.action = form.getAttribute("action") || location.href;
      for (const name of ["csrfmiddlewaretoken", "editor_revision"])
        hidden(restored, name, form.querySelector(`[name="${name}"]`)?.value || "");
      Object.entries(record.values).forEach(([name, value]) => hidden(restored, name, value));
      const transfer = nonce();
      hidden(restored, "action", "restore"); hidden(restored, "draft_transfer_id", transfer);
      record.lastTransfer = {id: transfer, values: {...record.values}};
      storage.write(key, record);
      document.body.append(restored);
      leaving = true; submitting = true;
      restored.submit();
    });
    form.querySelector("[data-draft-discard]")?.addEventListener("click", () => {
      storage.remove(key); record = null; persisted = null;
      if (banner) banner.hidden = true;
      setStatus("Brauzer qoralamasi o‘chirildi. Sahifadagi matn o‘zgarmadi.");
    });
    form.addEventListener("submit", event => {
      if (event.defaultPrevented) return;
      if (submitting || offline()) { event.preventDefault(); return; }
      fields.forEach(field => { if (editors.has(field.id)) field.value = editors.get(field.id).getData(); });
      persist();
      const transfer = nonce();
      let transferField = form.querySelector('[name="draft_transfer_id"]');
      if (!transferField) transferField = hidden(form, "draft_transfer_id", "");
      transferField.value = transfer;
      record.lastTransfer = {id: transfer, values: {...record.values}};
      if (event.submitter?.value === "save") {
        let marker = form.querySelector('[name="draft_submission_id"]');
        if (!marker) marker = hidden(form, "draft_submission_id", "");
        marker.value = transfer;
        record.lastSubmission = {id: transfer, values: {...record.values}};
      }
      storage.write(key, record);
      leaving = true; submitting = true;
    });
    form.addEventListener("invalid", event => {
      let parent = event.target.parentElement;
      while (parent && parent !== form) {
        if (parent.tagName === "DETAILS") parent.open = true;
        parent = parent.parentElement;
      }
    }, true);
    offer();
    controllers.push({persist, edited: () => touched,
      needsWarning: () => (bound || !same(values(), initial)) && !same(values(), persisted),
      reset: () => { submitting = false; }});
  });
  document.addEventListener("submit", event => {
    if (!event.target.matches("[data-workspace-logout]")) return;
    loggingOut = true; leaving = true;
    try {
      for (let index = sessionStorage.length - 1; index >= 0; index--) {
        const key = sessionStorage.key(index);
        if (key?.startsWith(prefix)) storage.remove(key);
      }
    } catch { /* Session-scoped draft keys prevent use after a different login. */ }
  });
  window.addEventListener("beforeunload", event => {
    if (!leaving && controllers.some(controller => controller.needsWarning())) {
      event.preventDefault(); event.returnValue = "";
    }
  });
  window.addEventListener("pagehide", () => {
    if (!loggingOut) controllers.filter(controller => controller.edited()).forEach(controller => controller.persist());
  });
  window.addEventListener("pageshow", () => { leaving = false; controllers.forEach(controller => controller.reset()); });
})();
