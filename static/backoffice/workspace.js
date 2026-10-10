(() => {
  "use strict";

  const prefix = "azurelms:workspace:draft:v1:";
  const allowedNames = new Set([
    "title", "description", "instructor", "level", "duration", "price", "cover_mode",
    "gradient_preset", "gradient_cover_title", "gradient_cover_label", "is_active",
    "certificate_requires_all_assignments_approved", "certificate_min_lesson_completion_percent",
    "certificate_min_attendance_percent", "module", "video_url", "content", "order", "xp_reward",
  ]);
  let storageAvailable = true;
  let leavingForSubmit = false;
  let loggingOut = false;
  const controllers = [];

  const storage = {
    read(key) {
      try { return JSON.parse(sessionStorage.getItem(key)); }
      catch { return null; }
    },
    write(key, value) {
      try { sessionStorage.setItem(key, JSON.stringify(value)); storageAvailable = true; return true; }
      catch { storageAvailable = false; return false; }
    },
    remove(key) {
      try { sessionStorage.removeItem(key); }
      catch { storageAvailable = false; }
    },
  };
  const sameValues = (a, b) => {
    if (!a || !b) return false;
    const keys = Object.keys(a).sort();
    return keys.length === Object.keys(b).length && keys.every(key => a[key] === b[key]);
  };
  const validRecord = record => record && record.version === 1 && record.values &&
    typeof record.values === "object" && !Array.isArray(record.values) &&
    Object.entries(record.values).every(([name, value]) => allowedNames.has(name) &&
      (typeof value === "string" || typeof value === "boolean"));

  // A signed-in server session issues this receipt only after a successful write.
  // Do not clear an edit made after submission or a receipt for another request.
  document.querySelectorAll("[data-workspace-saved]").forEach(marker => {
    const scope = marker.dataset.savedScope;
    const nonce = marker.dataset.savedSubmissionId;
    if (!scope || !nonce) return;
    const key = prefix + scope;
    const record = storage.read(key);
    if (validRecord(record) && record.lastSubmission?.id === nonce &&
        sameValues(record.values, record.lastSubmission.values)) storage.remove(key);
  });

  const workbench = document.querySelector("[data-workbench]");
  const switcher = document.querySelector("[data-pane-switch]");
  function showPane(name, focus = false) {
    if (!workbench || !["outline", "editor", "preview"].includes(name)) return;
    workbench.dataset.activePane = name;
    switcher?.querySelectorAll("[data-pane-target]").forEach(button => {
      button.setAttribute("aria-pressed", String(button.dataset.paneTarget === name));
    });
    if (focus) {
      const heading = workbench.querySelector(`[data-pane="${name}"] h2`);
      if (heading) { heading.setAttribute("tabindex", "-1"); heading.focus({preventScroll: true}); }
    }
  }
  if (workbench && switcher) {
    document.documentElement.classList.add("ws-enhanced");
    switcher.hidden = false;
    showPane(workbench.dataset.activePane);
    if (location.hash === "#materials") showPane("editor");
    switcher.addEventListener("click", event => {
      const button = event.target.closest("[data-pane-target]");
      if (button) showPane(button.dataset.paneTarget, true);
    });
    document.querySelectorAll("[data-open-outline]").forEach(button => button.addEventListener("click", () => {
      showPane("outline", true);
      workbench.querySelector(".ws-outline")?.scrollIntoView({block: "nearest"});
    }));
    // Keep field validation visible when a required select lives in a disclosure.
    workbench.addEventListener("invalid", event => {
      let parent = event.target.parentElement;
      while (parent && parent !== workbench) {
        if (parent.tagName === "DETAILS") parent.open = true;
        parent = parent.parentElement;
      }
      showPane("editor");
    }, true);
  }

  document.querySelectorAll("[data-workspace-draft]").forEach(form => {
    if (!form.dataset.draftScope) return;
    const key = prefix + form.dataset.draftScope;
    const fields = [...form.querySelectorAll("input[name], textarea[name], select[name]")]
      .filter(field => allowedNames.has(field.name) && !field.disabled &&
        !["hidden", "file", "password"].includes(field.type));
    const status = form.querySelector("[data-draft-status]");
    const banner = form.querySelector("[data-draft-recovery]");
    const recoveryText = form.querySelector("[data-draft-recovery-text]");
    const editors = new Map();
    const bound = form.dataset.boundForm === "true";
    let restoring = false;
    let touched = false;
    // A preview or rejected POST still contains unsaved text, even before a keystroke.
    let dirty = bound;
    let record = storage.read(key);
    if (!validRecord(record)) record = null;
    let persistedValues = record?.values || null;

    function values() {
      const result = {};
      fields.forEach(field => {
        const editor = editors.get(field.id);
        result[field.name] = field.type === "checkbox" ? field.checked :
          editor ? editor.getData() : field.value;
      });
      return result;
    }
    let initial = values();

    function setStatus(message, isDirty = false) {
      if (!status) return;
      status.textContent = message;
      status.classList.toggle("is-dirty", isDirty);
    }
    function offerRecovery() {
      if (!record || !banner || touched) return;
      if (!sameValues(record.values, values())) {
        banner.hidden = false;
        if (recoveryText) recoveryText.textContent = form.dataset.boundForm === "true" ?
          "Hozir yuborgan matningiz sahifada turibdi. Quyidagi tugma brauzerdagi oldingi qoralamani uning o‘rniga qo‘yadi." :
          "Matn faqat shu brauzer oynasida saqlangan. Tiklagach so‘nggi nusxa bilan solishtiring va Saqlashni bosing.";
      } else {
        banner.hidden = true;
        setStatus("Bu matn brauzer qoralamasida. Platformaga saqlashni tugma bilan tasdiqlang.", true);
      }
    }
    function persist() {
      if (restoring || loggingOut) return;
      const current = values();
      dirty = bound || !sameValues(current, initial);
      record = {version: 1, values: current, lastSubmission: record?.lastSubmission || null};
      const stored = storage.write(key, record);
      if (stored) {
        persistedValues = current;
        setStatus("Matn shu oynada qoralama sifatida saqlanmoqda. Platformaga hali saqlanmagan.", true);
      } else {
        setStatus("Brauzer qoralamani saqlay olmadi. Chiqishdan oldin matnni nusxalang yoki Saqlashni bosing.", true);
      }
      return stored;
    }
    function onEdit() {
      if (restoring) return;
      touched = true;
      if (banner) banner.hidden = true;
      persist();
    }
    form.addEventListener("input", event => {
      if (fields.includes(event.target)) onEdit();
    });
    form.addEventListener("change", event => {
      if (fields.includes(event.target)) onEdit();
    });

    fields.filter(field => field.matches("textarea.django_ckeditor_5")).forEach(field => {
      function attach(editor) {
        if (editors.has(field.id)) return;
        editors.set(field.id, editor);
        // CKEditor normalizes paragraph markup during startup; that is not an edit.
        if (!touched) initial[field.name] = editor.getData();
        editor.model.document.on("change:data", onEdit);
        offerRecovery();
      }
      if (window.editors?.[field.id]) attach(window.editors[field.id]);
      else if (typeof window.ckeditorRegisterCallback === "function") {
        window.ckeditorRegisterCallback(field.id, attach);
      }
    });

    form.querySelector("[data-draft-restore]")?.addEventListener("click", () => {
      if (!record) return;
      restoring = true;
      fields.forEach(field => {
        if (!Object.prototype.hasOwnProperty.call(record.values, field.name)) return;
        const value = record.values[field.name];
        if (field.type === "checkbox") field.checked = value === true;
        else {
          field.value = String(value);
          editors.get(field.id)?.setData(String(value));
        }
      });
      restoring = false;
      touched = true;
      dirty = bound || !sameValues(values(), initial);
      if (banner) banner.hidden = true;
      setStatus("Brauzer qoralamasi tiklandi. Tekshirib, platformaga saqlang.", true);
      showPane("editor");
      fields.find(field => field.type !== "checkbox")?.focus();
    });
    form.querySelector("[data-draft-discard]")?.addEventListener("click", () => {
      storage.remove(key);
      record = null;
      persistedValues = null;
      if (banner) banner.hidden = true;
      setStatus("Brauzer qoralamasi o‘chirildi. Sahifadagi matn o‘zgarmadi.");
    });

    form.addEventListener("submit", event => {
      // CKEditor normally syncs on submit; explicitly sync before taking the snapshot.
      fields.forEach(field => {
        const editor = editors.get(field.id);
        if (editor) field.value = editor.getData();
      });
      persist();
      const action = event.submitter?.value;
      if (action === "lesson_save" || !form.querySelector('[name="lesson_id"]')) {
        const nonce = window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
        let marker = form.querySelector('[name="draft_submission_id"]');
        if (!marker) {
          marker = document.createElement("input");
          marker.type = "hidden";
          marker.name = "draft_submission_id";
          form.append(marker);
        }
        marker.value = nonce;
        record.lastSubmission = {id: nonce, values: values()};
        storage.write(key, record);
      }
      leavingForSubmit = true;
    });
    offerRecovery();
    controllers.push({persist, isDirty: () => dirty, wasEdited: () => touched,
      needsWarning: () => dirty && !sameValues(persistedValues, values())});
  });

  // Other native forms (module order, file upload, library search) also retain text.
  document.addEventListener("submit", event => {
    if (event.target.matches("[data-workspace-logout]")) {
      loggingOut = true;
      leavingForSubmit = true;
      try {
        for (let index = sessionStorage.length - 1; index >= 0; index -= 1) {
          const key = sessionStorage.key(index);
          if (key?.startsWith(prefix)) sessionStorage.removeItem(key);
        }
      } catch { /* The session-scoped key also prevents another login reading it. */ }
      return;
    }
    if (!event.target.matches("[data-workspace-draft]")) {
      controllers.filter(controller => controller.isDirty()).forEach(controller => controller.persist());
      leavingForSubmit = storageAvailable;
    }
  });
  window.addEventListener("beforeunload", event => {
    if (!leavingForSubmit && controllers.some(controller => controller.needsWarning())) {
      event.preventDefault();
      event.returnValue = "";
    }
  });
  window.addEventListener("pagehide", () => {
    // Do not replace an older recoverable draft merely because a bound response opened.
    if (!loggingOut) controllers.filter(controller => controller.wasEdited() && controller.isDirty())
      .forEach(controller => controller.persist());
  });
  window.addEventListener("pageshow", () => { leavingForSubmit = false; });
})();
