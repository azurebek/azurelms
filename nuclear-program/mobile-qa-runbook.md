# Mobil QA runbook — loyihani telefonda ochish

*A5 "Mobil oltin oqim quality gate" uchun. Loyiha lokal ishlaydi; bu hujjat uni telefonda qanday ochishni va nimani qaysi yo'l bilan sinash mumkinligini yozadi.*

Ikkita yo'l bor va **ikkalasi ham kerak bo'ladi**: birinchisi tez va bepul, ammo mikrofonni bermaydi.

---

## 1-yo'l — bir xil Wi-Fi (LAN)

Layout, klaviatura, navigatsiya, checkout, davomat va fayl yuklash uchun yetarli.

### Kompyuterda

```powershell
cd C:\Users\AZUREBEK\Desktop\azurelms
.\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

PowerShell uslubi (`.\`, teskari slash). `./venv/...` bash uslubi va PowerShell uni topa olmaydi; loyiha papkasida turish ham shart.

`0.0.0.0` muhim: default `runserver` faqat `127.0.0.1` da tinglaydi va telefon uni ko'rmaydi.

### Telefonda

Telefon **bir xil Wi-Fi**ga ulangan bo'lsin, so'ng:

```
http://<KOMPYUTER-IP>:8000
```

IP ni topish:

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' }
```

**Wi-Fi yoki hotspot almashsa IP ham o'zgaradi.** Bir marta shu tuzoqqa tushilgan: kompyuter uy Wi-Fi'sidan (`192.168.1.x`) telefon hotspot'iga (`172.20.10.x`) o'tgan va "server ishlamayapti" deb o'ylangan. Ochilmasa — birinchi navbatda IP ni qayta tekshiring. Telefon hotspot'i aslida qulay: telefon router bo'ladi.

`ALLOWED_HOSTS` lokal rejimda `*` — hech narsa sozlash shart emas. CSRF ham ishlaydi, chunki so'rov same-origin.

### Agar ochilmasa — Windows Firewall

Bu eng ko'p uchraydigan to'siq. Tarmoq profili `Public` bo'lsa Windows kiruvchi ulanishlarni bloklaydi.

Profilni tekshirish:

```powershell
Get-NetConnectionProfile | Select-Object Name, NetworkCategory
```

**Owner o'zi bajaradi** (administrator PowerShell). Butun profilni `Private` qilishdan ko'ra faqat shu portni ochish xavfsizroq:

```powershell
New-NetFirewallRule -DisplayName "AzureLMS dev 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -Profile Private,Public
```

QA tugagach o'chirib qo'yish:

```powershell
Remove-NetFirewallRule -DisplayName "AzureLMS dev 8000"
```

Kafega yoki ochiq Wi-Fi'ga ulanganda bu qoidani yoqib qoldirmang — server o'sha tarmoqdagi hammaga ochiq bo'ladi.

---

## 2-yo'l — HTTPS tunnel

**Mikrofon va Telegram Mini App uchun majburiy.**

Sabab texnik va chetlab o'tib bo'lmaydi: `static/js/exam-shell.js` speaking javobini `getUserMedia` bilan yozadi, brauzerlar esa mikrofonni faqat **secure context**da (HTTPS yoki `localhost`) beradi. Telefonda `http://192.168.x.x:8000` secure context emas — mikrofon ishlamaydi. Bu kod xatosi emas.

```powershell
ngrok http 8000
```

ngrok bergan `https://...` manzilini oling va serverni **shu manzilni bilgan holda** yurgizing:

```powershell
$env:CSRF_TRUSTED_ORIGINS="https://SIZNING-MANZIL.ngrok-free.app"
.\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

`CSRF_TRUSTED_ORIGINS` nima uchun kerak: ngrok brauzerga HTTPS beradi, Django esa lokal profilda so'rovni HTTP deb biladi. CSRF Origin tekshiruvi `https://...` va `http://...` ni taqqoslab rad etadi, ya'ni **har qanday forma yuborish yiqiladi**. Bu sozlama o'sha nomuvofiqlikni yopadi.

ngrok bepul hisobda har ishga tushirishda yangi manzil beradi — buyruqni har safar yangilash kerak.

---

## Avval kontent — busiz QA ma'nosiz

Bo'sh bazada faqat landing, narxlar va bo'sh ekranlar ko'rinadi; dars, imtihon, checkout va davomat sahifalari sinalmay qoladi.

```powershell
.\venv\Scripts\python.exe manage.py seed_demo
```

Ikki modulli kurs, beshta dars, vazifa, guruh va faol o'quvchi yaratiladi (`demo-student` / `demo12345`). Faqat lokal muhitda ishlaydi, `--wipe` bilan izsiz olinadi.

## Nimani qaysi yo'l bilan sinash mumkin

| A5 bandi | LAN | Tunnel |
|---|:--:|:--:|
| Messenger 320–414px | ✅ | ✅ |
| Dars sarlavhasi 360px | ✅ | ✅ |
| Imtihon landscape 568×320 / 640×360 | ✅ | ✅ |
| Klaviatura xulqi, accessibility | ✅ | ✅ |
| Checkout oqimi | ✅ | ✅ |
| O'qituvchi davomati | ✅ | ✅ |
| Fayl yuklash (chek, vazifa) | ✅ | ✅ |
| WebSocket reconnect | ✅ | ✅ |
| **Speaking mikrofoni** | ❌ | ✅ |
| **Telegram Mini App** | ❌ | ✅ |

Tartib: avval LAN bilan layout va klaviatura muammolarini yig'ing — ular ko'proq va tezroq topiladi. Mikrofon va Mini App uchun keyin bitta tunnel sessiyasi yeting.

---

## Qanday dalil yig'iladi

A5 acceptance uchta qurilma klassini talab qiladi: **Android Chrome, iOS Safari, desktop Chrome**. Har topilma uchun:

- qurilma va brauzer nomi;
- ekran o'lchami (portrait/landscape);
- muammo turi: overflow · overlap · console xato · klaviatura sahifani bloklashi · bo'sh/xato holat · dark/light;
- skrinshot yoki qisqa video.

`0` bo'lishi kerak bo'lganlar: overflow, overlap, console xato, klaviatura bloklashi.

**Nimani agent qila oladi va qila olmaydi.** Agent brauzerni istalgan o'lchamda ochib, overflow, console xato va hisoblangan CSS ni tekshira oladi — bu real qurilma sinovining o'rnini bosmaydi. Haqiqiy klaviatura, haqiqiy mikrofon, iOS Safari ning o'ziga xosliklari va sensorli aniqlik faqat qurilmada ko'rinadi. Shuning uchun A5 chiqish sharti owner qo'lida.

---

## Tez eslatma

```powershell
# 0. QA uchun kontent
.\venv\Scripts\python.exe manage.py seed_demo

# 1. LAN (layout, klaviatura, checkout)
.\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000

# 2. Tunnel (mikrofon, Mini App) — ikkita terminal
ngrok http 8000
$env:CSRF_TRUSTED_ORIGINS="https://<manzil>.ngrok-free.app"; .\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000

# QA tugagach
.\venv\Scripts\python.exe manage.py seed_demo --wipe
```
