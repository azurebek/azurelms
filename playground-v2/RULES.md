# Kod Yozish Qoidalari — playground-v2

> Har bir kontributorga majburiy. Yangi sahifa yaratishdan oldin o'qing.

---

## 1. Fayl Konvensiyasi

| Qoida | To'g'ri | Noto'g'ri |
|---|---|---|
| Nom formati | `kebab-case.html` | `AuthLogin.html`, `auth_login.html` |
| Bo'lim prefiksi | `auth-login.html` | `login.html` |
| Shell fayli | `auth-shell.html` yoki asosiy fayl | `index.html` (faqat papka ildizida) |
| Ko'chirma | `auth-login-v2.html` emas — yangi bo'limda | — |

### Standart fayl nomi sxemasi
```
{section}-{page}.html
```
Masalan: `app-course-detail.html`, `exam-listening.html`, `blog-article.html`

---

## 2. HTML Tuzilmasi

### Har bir sahifa uchun majburiy bosh qism

```html
<!DOCTYPE html>
<html lang="uz" data-theme="light">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>[Sahifa nomi] — AzureLMS</title>
  <meta name="description" content="[Qisqa tavsif]">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400&display=swap" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
  <style>
    /* 1. Reset */
    /* 2. Tokens (`:root` va `[data-theme="dark"]`) */
    /* 3. Base styles */
    /* 4. Komponentlar */
    /* 5. Layout */
    /* 6. Animatsiyalar */
    /* 7. Responsive */
  </style>
</head>
<body>
  <!-- Kontent -->
  <script>
    /* 1. Theme init (BIRINCHI — FOUC oldini olish uchun) */
    /* 2. Interaktivlik */
  </script>
</body>
</html>
```

### Majburiy `<script>` bloki boshi

```javascript
// Theme — sahifaning birinchi skripti bo'lishi shart (FOUC yo'q)
(function() {
  const html = document.documentElement;
  let saved; try { saved = localStorage.getItem('az-theme'); } catch(_) {}
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  html.setAttribute('data-theme', saved ? saved : (prefersDark ? 'dark' : 'light'));
})();
```

---

## 3. CSS Qoidalari

### 3.1 Majburiy

```css
/* ✅ To'g'ri */
color: var(--ink-0);
background: var(--white);
border: 1px solid var(--border);

/* ❌ Noto'g'ri — hardcoded rang */
color: #0d1b2a;
background: white;
border: 1px solid #dde4ee;
```

### 3.2 CTA / Footer sirtlar

```css
/* ✅ Har doim qorong'u — dark mode ham to'g'ri */
background: var(--deep);
color: var(--on-deep);

/* ❌ Noto'g'ri — dark modeda rang o'zgaradi */
background: var(--ink-0);
color: var(--bg);
```

### 3.3 CSS tartibi (har bir blok)

```css
/* Avval layout xususiyatlari */
display: flex;
align-items: center;
gap: 12px;

/* Keyin vizual */
background: var(--white);
border: 1px solid var(--border);
border-radius: var(--r-lg);

/* Oxirida effektlar */
box-shadow: var(--sh-sm);
transition: box-shadow 120ms var(--ease);
```

### 3.4 Media query formati

```css
/* Mobile-first — min-width */
.grid { grid-template-columns: 1fr; }
@media (min-width: 768px) { .grid { grid-template-columns: 1fr 1fr; } }
@media (min-width: 1024px) { .grid { grid-template-columns: repeat(3, 1fr); } }
```

### 3.5 Animatsiya — reduced-motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 4. Komponent Nomi Qoidalari

BEM-ga yaqin, lekin soddalashtirilgan:

```
.{blok}               — asosiy komponent
.{blok}-{element}     — ichki qism
.{blok}--{modifier}   — variatsiya
```

Misollar:
```css
.card              /* blok */
.card-title        /* element */
.card-body         /* element */
.card--featured    /* modifier */

.btn               /* blok */
.btn--primary      /* modifier */
.btn--ghost        /* modifier */
.btn--sm           /* o'lcham modifier */
```

---

## 5. Accessibility (A11y)

### Majburiy

- [ ] Barcha `<img>` larda `alt` atribut
- [ ] `<button>` larda matn yoki `aria-label`
- [ ] Form `<input>` larida `<label>` yoki `aria-label`
- [ ] Interaktiv elementlar klaviatura bilan ishlaydimi? (`:focus-visible`)
- [ ] Renk kontrasti: kamida **4.5:1** (matn), **3:1** (katta matn/UI)

### Focus ring standarti

```css
:focus-visible {
  outline: 2px solid var(--blue-mid);
  outline-offset: 2px;
  border-radius: 4px;
}
```

---

## 6. Performance Qoidalari

| Qoida | Izoh |
|---|---|
| External font — `display=swap` | FOUT o'rniga FOUT (kamroq CLS) |
| `<link rel="preconnect">` | Fonts uchun birinchi |
| `loading="lazy"` | Ekran pastidagi rasmlar uchun |
| Inline SVG | Kichik ikonlar uchun (CDN o'rniga) |
| `will-change: transform` | Faqat aktiv animatsiya davomida |

---

## 7. Sahifa Yaratish Tekshiruvi

Har yangi sahifa commit qilishdan oldin:

- [ ] Light modeda to'g'ri ko'rinadimi?
- [ ] Dark modeda to'g'ri ko'rinadimi?
- [ ] 375px (mobil) da to'g'ri ko'rinadimi?
- [ ] 1280px (desktop) da to'g'ri ko'rinadimi?
- [ ] Klaviatura (Tab) bilan navigatsiya ishlayaptimi?
- [ ] Barcha tokenlar `TOKENS.md` dan olinganmi?
- [ ] Hardcoded rang qoldiqmi yo'qmi?
- [ ] `--deep` / `--on-deep` CTA/footer da ishlatilganmi?
- [ ] JavaScript xatolar konsollarda yo'qmi?
