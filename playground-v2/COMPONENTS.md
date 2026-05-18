# Komponent Kataloği — playground-v2

> Qayta ishlatiladigan UI pattern'lar. Har bir prototipda shu shablonlardan foydalaning.

---

## 1. Tugmalar (Buttons)

### Asosiy tugma sinflar

```html
<!-- Primary — to'liq ko'k -->
<button class="btn btn--primary">Boshlash</button>

<!-- Ghost — shaffof, border bilan -->
<button class="btn btn--ghost">Ko'proq</button>

<!-- Danger — xavfli amal -->
<button class="btn btn--danger">O'chirish</button>

<!-- Loading holati -->
<button class="btn btn--primary" disabled>
  <span class="btn-spinner"></span> Yuklanmoqda...
</button>
```

### CSS

```css
.btn {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 10px 20px; border-radius: var(--r-pill);
  font-family: inherit; font-size: 0.875rem; font-weight: 600;
  cursor: pointer; border: 1.5px solid transparent;
  transition: background 120ms var(--ease), color 120ms var(--ease),
              box-shadow 120ms var(--ease), transform 120ms var(--ease);
}
.btn:active { transform: scale(0.97); }
.btn--primary { background: var(--blue-mid); color: #fff; }
.btn--primary:hover { background: var(--blue); box-shadow: 0 4px 16px rgba(37,99,235,.3); }
.btn--ghost { background: transparent; border-color: var(--border); color: var(--ink-1); }
.btn--ghost:hover { background: var(--surface); border-color: var(--ink-5); }
.btn--danger { background: var(--red-soft); color: var(--red); border-color: transparent; }
.btn--danger:hover { background: var(--red); color: #fff; }
.btn--sm { padding: 7px 14px; font-size: 0.8rem; }
.btn--lg { padding: 13px 28px; font-size: 1rem; }
```

---

## 2. Karta (Card)

### Asosiy karta

```html
<div class="card">
  <div class="card-header">
    <span class="card-icon">📚</span>
    <div class="card-meta">
      <span class="badge badge--blue">A1</span>
    </div>
  </div>
  <h3 class="card-title">Turk tili — Boshlang'ich</h3>
  <p class="card-desc">A1 dan boshlang'ich daraja kursi</p>
  <div class="card-footer">
    <span class="card-stat">24 dars</span>
    <a href="#" class="btn btn--primary btn--sm">Boshlash</a>
  </div>
</div>
```

### CSS

```css
.card {
  background: var(--white); border: 1px solid var(--border);
  border-radius: var(--r-lg); padding: var(--s-5);
  box-shadow: var(--sh-sm);
  transition: box-shadow 200ms var(--ease), transform 200ms var(--ease),
              background 280ms, border-color 280ms;
}
.card:hover {
  box-shadow: var(--sh-md); transform: translateY(-2px);
}
```

---

## 3. Badge (Nishon)

```html
<span class="badge badge--blue">A1</span>
<span class="badge badge--green">Yangi</span>
<span class="badge badge--amber">Ommabop</span>
<span class="badge badge--purple">Premium</span>
<span class="badge badge--red">Muddati o'tgan</span>
```

### CSS

```css
.badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 9px; border-radius: var(--r-pill);
  font-size: 0.7rem; font-weight: 700; letter-spacing: 0.04em;
}
.badge--blue   { background: var(--blue-soft);   color: var(--blue); }
.badge--green  { background: var(--green-soft);  color: var(--green); }
.badge--amber  { background: var(--amber-soft);  color: var(--amber); }
.badge--purple { background: var(--purple-soft); color: var(--purple); }
.badge--red    { background: var(--red-soft);    color: var(--red); }
```

---

## 4. Forma Elementlari

### Input

```html
<div class="field">
  <label class="field-label" for="email">Email manzil</label>
  <div class="field-wrap">
    <i class="bi bi-envelope field-icon"></i>
    <input class="field-input" type="email" id="email"
           placeholder="email@example.com" autocomplete="email">
  </div>
  <!-- Xato holati -->
  <span class="field-error">Noto'g'ri email format</span>
</div>
```

### CSS

```css
.field { display: grid; gap: 6px; }
.field-label { font-size: 0.8rem; font-weight: 600; color: var(--ink-2); }
.field-wrap { position: relative; }
.field-icon {
  position: absolute; left: 13px; top: 50%; transform: translateY(-50%);
  color: var(--ink-4); font-size: 0.95rem; pointer-events: none;
  transition: color 150ms;
}
.field-input {
  width: 100%; height: 44px; padding: 0 14px 0 38px;
  background: var(--white); border: 1.5px solid var(--border);
  border-radius: var(--r-md); font-family: inherit; font-size: 0.9rem;
  color: var(--ink-0); transition: border-color 150ms, box-shadow 150ms,
  background 280ms, color 280ms;
  outline: none;
}
.field-input::placeholder { color: var(--ink-4); }
.field-input:focus {
  border-color: var(--blue-mid);
  box-shadow: 0 0 0 3px rgba(37,99,235,.12);
}
.field-input:focus + .field-icon,
.field-wrap:focus-within .field-icon { color: var(--blue-mid); }
.field-error { font-size: 0.76rem; color: var(--red); }
/* Xato holati */
.field--error .field-input { border-color: var(--red); }
.field--error .field-input:focus { box-shadow: 0 0 0 3px var(--red-soft); }
```

---

## 5. Progress Bar

```html
<div class="progress">
  <div class="progress-fill" style="width: 68%"></div>
</div>
```

### CSS

```css
.progress {
  height: 6px; background: var(--border);
  border-radius: var(--r-pill); overflow: hidden;
}
.progress-fill {
  height: 100%; border-radius: var(--r-pill);
  background: linear-gradient(90deg, var(--blue-mid), var(--blue));
  transition: width 600ms var(--ease);
}
```

---

## 6. Nav (Navigatsiya)

```html
<nav class="nav">
  <div class="container">
    <a class="nav-logo" href="/">
      <div class="nav-logo-mark">AZ</div>
      <span class="nav-logo-name">AzureLMS</span>
    </a>
    <div class="nav-links">
      <a href="/courses" class="nav-link">Kurslar</a>
      <a href="/pricing" class="nav-link">Narxlar</a>
      <a href="/blog" class="nav-link">Blog</a>
    </div>
    <div class="nav-actions">
      <button class="theme-toggle" id="themeToggle" aria-label="Tema">
        <i class="bi bi-moon" id="themeIcon"></i>
      </button>
      <a href="/auth/login" class="btn btn--ghost btn--sm">Kirish</a>
      <a href="/auth/register" class="btn btn--primary btn--sm">Ro'yxatdan o'tish</a>
    </div>
  </div>
</nav>
```

### CSS

```css
.nav {
  position: sticky; top: 0; z-index: 100;
  background: var(--nav-bg);
  backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--nav-border);
  transition: background 280ms;
}
.nav .container {
  max-width: var(--wrap); margin: 0 auto; padding: 0 24px;
  height: 60px; display: flex; align-items: center; gap: 24px;
}
.nav-logo { display: flex; align-items: center; gap: 8px; margin-right: auto; }
.nav-logo-mark {
  width: 30px; height: 30px; border-radius: 8px;
  background: var(--blue-mid); color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.65rem; font-weight: 800;
}
.nav-logo-name { font-size: 0.9rem; font-weight: 700; color: var(--ink-0); }
.nav-link { font-size: 0.875rem; font-weight: 500; color: var(--ink-2);
  transition: color 120ms; }
.nav-link:hover { color: var(--blue-mid); }
.theme-toggle {
  width: 34px; height: 34px; border-radius: var(--r-md);
  display: flex; align-items: center; justify-content: center;
  color: var(--ink-3); background: transparent;
  border: 1px solid var(--border); transition: all 120ms;
}
.theme-toggle:hover { color: var(--ink-0); background: var(--surface); }
```

---

## 7. Skeleton (Yuklanish holati)

```html
<div class="skeleton" style="height: 20px; width: 60%; border-radius: 6px;"></div>
<div class="skeleton" style="height: 14px; width: 80%; border-radius: 6px; margin-top: 8px;"></div>
```

### CSS

```css
.skeleton {
  background: linear-gradient(90deg,
    var(--border) 25%, var(--border-soft) 50%, var(--border) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s ease-in-out infinite;
}
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

---

## 8. Toast / Bildirishnoma

```html
<div class="toast toast--success">
  <i class="bi bi-check-circle-fill toast-icon"></i>
  <div class="toast-body">
    <strong>Muvaffaqiyatli!</strong>
    <span>Dars tugatildi.</span>
  </div>
</div>
```

### CSS

```css
.toast {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 12px 16px; border-radius: var(--r-lg);
  background: var(--white); border: 1px solid var(--border);
  box-shadow: var(--sh-md); max-width: 280px;
}
.toast-icon { font-size: 1rem; flex-shrink: 0; margin-top: 2px; }
.toast--success .toast-icon { color: var(--green); }
.toast--error   .toast-icon { color: var(--red); }
.toast--warning .toast-icon { color: var(--amber); }
.toast-body { display: flex; flex-direction: column; gap: 2px; font-size: 0.82rem; }
.toast-body strong { font-weight: 700; color: var(--ink-0); }
.toast-body span { color: var(--ink-3); }
```

---

## 9. App Sidebar

```html
<aside class="sidebar">
  <nav class="sidebar-nav">
    <a href="#" class="sidebar-item sidebar-item--active">
      <i class="bi bi-grid sidebar-icon"></i>
      <span>Dashboard</span>
    </a>
    <a href="#" class="sidebar-item">
      <i class="bi bi-book sidebar-icon"></i>
      <span>Kurslarim</span>
    </a>
  </nav>
</aside>
```

### CSS

```css
.sidebar {
  width: 220px; background: var(--white); border-right: 1px solid var(--border);
  height: 100vh; position: sticky; top: 0;
  overflow-y: auto; padding: 16px 12px;
  transition: background 280ms, border-color 280ms;
}
.sidebar-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 12px; border-radius: var(--r-md);
  font-size: 0.85rem; font-weight: 500; color: var(--ink-2);
  transition: background 120ms, color 120ms;
}
.sidebar-item:hover { background: var(--surface); color: var(--ink-0); }
.sidebar-item--active {
  background: var(--blue-soft); color: var(--blue-mid); font-weight: 600;
}
.sidebar-icon { font-size: 1rem; width: 18px; text-align: center; }
```
