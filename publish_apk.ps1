# Automation Script to Build and Push the APK to GitHub
Write-Host "🚀 Iniciando processo de atualização do APK..." -ForegroundColor Cyan

# 1. Navigate to flutter app directory
$appDir = "luxo_rj_scraper/app"
if (Test-Path $appDir) {
    Push-Location $appDir
} else {
    Write-Error "Pasta do app não encontrada!"
    exit
}

# 2. Build the APK
Write-Host "📦 Compilando APK em modo Release... (Isso pode levar um minuto)" -ForegroundColor Yellow
flutter build apk --release --no-tree-shake-icons --android-skip-build-dependency-validation

if ($LASTEXITCODE -ne 0) {
    Write-Error "Falha na compilação do Flutter!"
    Pop-Location
    exit
}

# 3. Move and Rename APK
Write-Host "🚚 Movendo APK para a raiz do projeto..." -ForegroundColor Yellow
$destination = "../../Airbnb-lead-gen.apk"
Copy-Item "build/app/outputs/flutter-apk/app-release.apk" $destination -Force

Pop-Location

# 4. Git Push
Write-Host "📤 Enviando para o GitHub..." -ForegroundColor Yellow
git add Airbnb-lead-gen.apk
git commit -m "dist: update APK with latest features and fixes"
git push

Write-Host "✅ Sucesso! O novo APK já está disponível no GitHub." -ForegroundColor Green
Write-Host "🔗 Baixe agora em: https://github.com/caiofrk/AIRBNB_LEAD_GENERATOR/raw/main/Airbnb-lead-gen.apk" -ForegroundColor Blue
