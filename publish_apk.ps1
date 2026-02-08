# Build and Push APK
Write-Host "--- BUILD START ---"

$rootDir = "c:\Users\Admin\DEV\AIRBNB_LEAD_GENERATOR"
$appDir = "$rootDir\luxo_rj_scraper\app"

Set-Location $appDir
flutter build apk --release --no-tree-shake-icons

if ($LASTEXITCODE -eq 0) {
    Copy-Item "build\app\outputs\flutter-apk\app-release.apk" "$rootDir\Airbnb-lead-gen.apk" -Force
    Set-Location $rootDir
    git add Airbnb-lead-gen.apk
    git commit -m "Update APK"
    git push
    Write-Host "--- SUCCESS ---"
    Write-Host "Link: https://github.com/caiofrk/AIRBNB_LEAD_GENERATOR/raw/main/Airbnb-lead-gen.apk"
}
else {
    Write-Host "--- FAILED ---"
    exit 1
}
