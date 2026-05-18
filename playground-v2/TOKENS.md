# CSS Tokenlar — playground-v2

> Har bir prototipda `:root {}` va `[data-theme="dark"] {}` blokiga
> aynan shu tokenlarni nusxalang. O'zgartirish kerak bo'lsa avval shu faylni yangilang.

---

## Tayyor nusxa — `<style>` ichiga joylashtiring

```css
/* ══════════════════ TOKENS — LIGHT ══════════════════ */
:root {
  /* Sirtlar */
  --bg:          #eff2f6;
  --surface:     #f7f9fb;
  --white:       #ffffff;
  --border:      #dde4ee;
  --border-soft: #e8eef6;

  /* Matn */
  --ink-0: #0d1b2a;
  --ink-1: #1e3248;
  --ink-2: #2f4a66;
  --ink-3: #4d6680;
  --ink-4: #7a90a8;
  --ink-5: #a8bcce;
  --ink-6: #d1dce8;

  /* Har doim qorong'u sirt */
  --deep:    #0d1b2a;
  --on-deep: #eff2f6;

  /* Aksent — Ko'k */
  --blue:      #1d57d8;
  --blue-mid:  #2563eb;
  --blue-soft: rgba(29, 87, 216, 0.09);

  /* Aksent — Yashil */
  --green:      #15803d;
  --green-mid:  #16a34a;
  --green-soft: rgba(21, 128, 61, 0.10);

  /* Aksent — Sariq */
  --amber:      #b45309;
  --amber-mid:  #d97706;
  --amber-soft: rgba(180, 83, 9, 0.10);

  /* Aksent — Binafsha */
  --purple:      #6d28d9;
  --purple-soft: rgba(109, 40, 217, 0.09);

  /* Aksent — Qizil */
  --red:      #dc2626;
  --red-mid:  #ef4444;
  --red-soft: rgba(220, 38, 38, 0.09);

  /* Nav */
  --nav-bg:     rgba(239, 242, 246, 0.88);
  --nav-border: rgba(180, 200, 220, 0.5);

  /* Shadow */
  --sh-xs: 0 1px 2px rgba(13,27,42,.04);
  --sh-sm: 0 1px 3px rgba(13,27,42,.05), 0 4px 12px rgba(13,27,42,.07);
  --sh-md: 0 4px 12px rgba(13,27,42,.08), 0 16px 48px rgba(13,27,42,.10);
  --sh-lg: 0 8px 24px rgba(13,27,42,.10), 0 32px 64px rgba(13,27,42,.12);

  /* Border radius */
  --r-sm:   6px;
  --r-md:   10px;
  --r-lg:   14px;
  --r-xl:   20px;
  --r-pill: 999px;

  /* Spacing */
  --s-1:  4px;
  --s-2:  8px;
  --s-3:  12px;
  --s-4:  16px;
  --s-5:  20px;
  --s-6:  24px;
  --s-8:  32px;
  --s-10: 40px;
  --s-12: 48px;
  --s-16: 64px;
  --s-24: 96px;

  /* Layout */
  --wrap: min(100%, 1160px);
  --gap:  clamp(48px, 7vw, 96px);

  /* Animatsiya */
  --ease:     cubic-bezier(0.16, 1, 0.3, 1);
  --ease-in:  cubic-bezier(0.4, 0, 1, 1);
  --ease-out: cubic-bezier(0, 0, 0.2, 1);
}

/* ══════════════════ TOKENS — DARK ══════════════════ */
[data-theme="dark"] {
  /* Sirtlar */
  --bg:          #0c1520;
  --surface:     #111d2b;
  --white:       #152233;
  --border:      #1e3450;
  --border-soft: #172a40;

  /* Matn */
  --ink-0: #dce9f5;
  --ink-1: #b8d0e6;
  --ink-2: #8aadc8;
  --ink-3: #6288a4;
  --ink-4: #3f607e;
  --ink-5: #284259;
  --ink-6: #1a2f44;

  /* Har doim qorong'u sirt */
  --deep:    #070e18;
  --on-deep: #dce9f5;

  /* Aksent — Ko'k */
  --blue:      #60a5fa;
  --blue-mid:  #3b82f6;
  --blue-soft: rgba(96, 165, 250, 0.12);

  /* Aksent — Yashil */
  --green:      #4ade80;
  --green-mid:  #22c55e;
  --green-soft: rgba(74, 222, 128, 0.12);

  /* Aksent — Sariq */
  --amber:      #fbbf24;
  --amber-mid:  #f59e0b;
  --amber-soft: rgba(251, 191, 36, 0.12);

  /* Aksent — Binafsha */
  --purple:      #a78bfa;
  --purple-soft: rgba(167, 139, 250, 0.12);

  /* Aksent — Qizil */
  --red:      #f87171;
  --red-mid:  #ef4444;
  --red-soft: rgba(248, 113, 113, 0.12);

  /* Nav */
  --nav-bg:     rgba(12, 21, 32, 0.88);
  --nav-border: rgba(30, 52, 80, 0.8);

  /* Shadow (dark modeda quyuqroq) */
  --sh-xs: 0 1px 2px rgba(0,0,0,.16);
  --sh-sm: 0 1px 3px rgba(0,0,0,.20), 0 4px 12px rgba(0,0,0,.24);
  --sh-md: 0 4px 12px rgba(0,0,0,.28), 0 16px 48px rgba(0,0,0,.30);
  --sh-lg: 0 8px 24px rgba(0,0,0,.32), 0 32px 64px rgba(0,0,0,.36);
}
```

---

## Auth sahifalari uchun aksent tokenlar

Har bir auth sahifasida `--accent` o'zgaruvchisi alohida belgilanadi:

```css
/* auth-login.html */
:root { --accent: #f26a3d; --accent-soft: rgba(242,106,61,.10); }

/* auth-register.html */
:root { --accent: #22c472; --accent-soft: rgba(34,196,114,.10); }

/* auth-recovery.html */
:root { --accent: #6b7df0; --accent-soft: rgba(107,125,240,.10); }

/* checkout.html */
:root { --accent: #1d57d8; --accent-soft: rgba(29,87,216,.10); }
```

---

## Tokenlarni tekshirish — checklisti

- [ ] Barcha ranglar `var(--...)` orqali ishlatilganmi?
- [ ] Hardcoded rang yo'qmi? (`#fff`, `#000`, `black` kabi)
- [ ] `--deep` / `--on-deep` CTA va footer uchun ishlatilganmi?
- [ ] Dark mode tekshirilganmi? (toggle qilib ko'ring)
- [ ] `transition: background 280ms, color 280ms` barcha rangli elementlardami?
