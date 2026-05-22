# Kod Yozish Qoidalari va Standartlar

Ushbu hujjat `design-work-playground` da ishlash uchun majburiy qoidalarni belgilaydi.

## 1. Fayl Nomlash Konvensiyasi

Fayllar BEM-ga o'xshash mantiq asosida bo'lim nomini prefix sifatida ishlatib nomlanadi:

| Format | Noto'g'ri (❌) | To'g'ri (✅) |
|---|---|---|
| `{section}-{page}.html` | `login.html`, `AuthLogin.html` | `auth-login.html` |
| `{section}-{page}.html` | `courses.html`, `app_courses.html`| `app-course-list.html` |
| `{section}-shell.html` | `index.html` (app ichida bo'lsa) | `app-shell.html` |

**Papka iyerarxiyasi:**
Har bir hudud o'z papkasida bo'ladi (`auth/`, `app/`, `public/`, `exam/`, `blog/`).

## 2. CSS Yozish Qoidalari (BEM Metodologiyasi)

Klasslar qisqartirilgan BEM (Block Element Modifier) uslubida nomlanadi.

```css
.blok               /* Asosiy konteyner */
.blok-element       /* Blokning ichki qismi */
.blok--modifier     /* Blok yoki elementning holati/turi */
```

**Misol (Button):**
```html
<button class="btn btn--primary btn--sm">Bosish</button>
```

**Misol (Card):**
```html
<div class="card card--featured">
  <div class="card-header">...</div>
  <div class="card-body">...</div>
</div>
```

## 3. Dark Mode va Tokenlar

* **Hech qachon HTML/CSS ichida to'g'ridan-to'g'ri hex kod (masalan `#ff0000`) ishlatmang!**
* Barcha ranglar, soyalar, qalinliklar va radiuslar `var(--token-nomi)` orqali ulanishi shart.
* Bu Dark Mode qanday ishlashini ta'minlaydi. Token o'zgarishi bilan sahifa avtomat dark/light rejimga o'tadi.

✅ **To'g'ri:** `color: var(--ink-0); background: var(--surface);`
❌ **Noto'g'ri:** `color: #0d1b2a; background: #f7f9fb;`

### FOUC (Flash of Unstyled Content) ning oldini olish
Barcha HTML fayllarning `<body>` tegidan oldin quyidagi skript bo'lishi shart:

```html
<script>
  // Sahifa yuklanishidan oldin temani aniqlash
  (function() {
    const html = document.documentElement;
    let saved; try { saved = localStorage.getItem('az-theme'); } catch(_) {}
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    html.setAttribute('data-theme', saved ? saved : (prefersDark ? 'dark' : 'light'));
  })();
</script>
```

## 4. Accessibility (A11y) va Foydalanish Qulayligi

* Interaktiv elementlarda (`a`, `button`, `input`) majburiy hover va focus holatlari bo'lishi kerak.
* Focus state: Klaviatura orqali harakatlanganda qaysi elementda ekanligini bildirish uchun aniq border yoki outline ko'rsatilishi kerak (odatda `box-shadow` orqali hal qilinadi).
* Rasm (`img`) larda doim `alt=""` atributi bo'lishi shart.
* Forma elementlarida label majburiy.

## 5. Responsive Dizayn (Mobile-First)

Media query'lar asosan `min-width` orqali yoziladi.
```css
/* Mobil uchun default stillar */
.grid { grid-template-columns: 1fr; }

/* Planshet va undan kattalar uchun */
@media (min-width: 768px) {
  .grid { grid-template-columns: 1fr 1fr; }
}
```
Standart Breakpointlar:
* Mobile: Default (max-width kerak emas)
* Tablet: `768px`
* Desktop: `1024px`
* Large Desktop: `1280px`
