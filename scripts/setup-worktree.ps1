# Worktree sozlash skripti — A varianti (har worktree to'liq izolyatsiyada)
#
# Foydalanish:
#   cd C:\Projects\azurelms-claude    # yoki -codex, -antigravity
#   powershell -ExecutionPolicy Bypass -File ..\azurelms\scripts\setup-worktree.ps1
#
# Skript bajaradi:
#   1. Yangi `venv\` yaratadi (Python venv)
#   2. requirements.txt'dan paketlarni o'rnatadi (~5-10 daqiqa)
#   3. Asosiy worktree'dan `.env` va `.env.local` ni nusxa oladi (mavjud bo'lsa)
#   4. Bo'sh `db.sqlite3` yaratish uchun `migrate` yugurtadi
#
# Asosiy worktree'ning `db.sqlite3` ni ko'chirish kerak bo'lsa qo'lda:
#   Copy-Item ..\azurelms\db.sqlite3 .

$ErrorActionPreference = "Stop"

Write-Host "▶ Worktree sozlanmoqda: $(Get-Location)" -ForegroundColor Cyan

# 1. Venv
if (Test-Path "venv") {
    Write-Host "✓ venv allaqachon mavjud, o'tkazib yuborildi"
} else {
    Write-Host "→ venv yaratilmoqda..."
    python -m venv venv
}

# 2. Bog'liqliklar
Write-Host "→ pip install -r requirements.txt (5-10 daqiqa)"
& .\venv\Scripts\python.exe -m pip install --upgrade pip --quiet
& .\venv\Scripts\pip.exe install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ pip install muvaffaqiyatsiz tugadi" -ForegroundColor Red
    exit 1
}

# 3. .env nusxa olish
$mainWorktree = "..\azurelms"
foreach ($envFile in ".env", ".env.local") {
    $src = Join-Path $mainWorktree $envFile
    if (Test-Path $src) {
        Copy-Item $src -Destination $envFile -Force
        Write-Host "✓ $envFile nusxa olindi"
    }
}

# 4. Migrate (bo'sh db.sqlite3 yaratadi)
Write-Host "→ python manage.py migrate"
& .\venv\Scripts\python.exe manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ migrate muvaffaqiyatsiz tugadi" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Worktree tayyor: $(Get-Location)" -ForegroundColor Green
Write-Host ""
Write-Host "Keyingi qadamlar:"
Write-Host "  - IDE'ni shu papkadan oching"
Write-Host "  - Superuser yaratish: .\venv\Scripts\python.exe manage.py createsuperuser"
Write-Host "  - Yoki asosiy bazadan nusxa: Copy-Item $mainWorktree\db.sqlite3 . -Force"
