# AzureLMS - Autonomous Shell Architecture

Ushbu hujjat `design-work-playground` loyihasining arxitekturasi va asosiy prinsiplarini belgilaydi. Maqsadimiz: **Vizual jihatdan zamonaviy dizaynni, tizimli va toza arxitektura bilan birlashtirish.**

## 1. Asosiy Prinsiplar

1. **Avtonom Shell (Autonomous Shell):** Har bir mahsulot hududi (Auth, App, Public, Exam) o'zining mustaqil Layout (Shell) iga ega bo'lishi kerak. Bitta Shell ichidagi o'zgarish boshqa Shell'ga ta'sir qilmasligi shart.
2. **Quruq Kod (DRY - Don't Repeat Yourself):** Hech qachon bir xil CSS kodlari (Tokenlar, Reset, Sidebar, Topbar) turli fayllarga ko'chirib yozilmaydi (Copy-Paste qilinmaydi). Ular alohida komponent/css fayl sifatida saqlanib, chaqirib ishlatiladi.
3. **Zanjirli CSS Ulanishi:** HTML sahifalarda `<style>` teglaridan voz kechiladi. Uning o'rniga tashqi CSS fayllar mantiqiy ketma-ketlikda ulanadi.

## 2. CSS Papka Strukturasi (`assets/css/`)

CSS fayllar qat'iy iyerarxiya bo'yicha tashkil qilinadi:

### 2.1. Yadro (Core)
Barcha sahifalarda majburiy bo'lgan fayllar:
* `tokens.css`: Faqat CSS o'zgaruvchilar (Colors, Radius, Shadows, Dark/Light mode).
* `foundation.css`: CSS Reset, asosiy tipografiya (`body`, `a`, `button`), global qoidalar.
* `components.css`: Qayta ishlatiluvchi UI elementlar (Button, Card, Badge, Form Inputs).

### 2.2. Shell (Layout)
Faqat tegishli mahsulot hududiga xos bo'lgan fayllar:
* `auth.css`: Login, Register va Recovery kabi split-screen layout qoidalari.
* `app.css`: Dashboard Sidebar, Topbar va Workspace arxitekturasi.
* `public.css`: Landing pages, Navbar, Footer va ochiq sahifalar layouti.
* `learning.css`: Dars o'tish ekrani (Lesson player).
* `exam.css`: Imtihon topshirish ekrani.

### 2.3. Page-specific (Sahifaga xos) - *Ixtiyoriy*
Juda murakkab va faqat bitta sahifada ishlatiladigan stillar uchun (iloji boricha avoid qilish tavsiya etiladi). Masalan: `app-attendance.css`.

## 3. Zanjirli Ulanish Namunasi

Har bir HTML faylning `<head>` qismida CSS fayllar quyidagi ketma-ketlikda ulanadi:

```html
<!-- 1. External Fonts & Icons -->
<link href="https://fonts.googleapis.com/css..." rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons..." rel="stylesheet">

<!-- 2. Core CSS -->
<link rel="stylesheet" href="../assets/css/tokens.css">
<link rel="stylesheet" href="../assets/css/foundation.css">
<link rel="stylesheet" href="../assets/css/components.css">

<!-- 3. Domain Shell CSS (Masalan, Dashboard sahifasi bo'lsa) -->
<link rel="stylesheet" href="../assets/css/app.css">
```

## 4. Backendga O'tishga Tayyorgarlik
Ushbu arxitektura backend dasturchilar (Django/React) uchun qulaylik yaratishga qaratilgan.
* `app.css` va HTML dagi `.sidebar`, `.topbar` hududlari kelajakda `base_app.html` yoki `<AppLayout>` ga aylanadi.
* Har bir sahifa (masalan, `app-course-list.html`) faqat `<main class="main">` ichidagi o'z kontentini yozadi.
