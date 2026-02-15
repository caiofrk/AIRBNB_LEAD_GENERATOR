# Build and Push APK
Write-Host "--- BUILD START ---"

$rootDir = "c:\Users\Admin\DEV\AIRBNB_LEAD_GENERATOR"
$appDir = "$rootDir\luxo_rj_scraper\app"

Set-Location $appDir
flutter build apk --release --no-tree-shake-icons

if ($LASTEXITCODE -eq 0) {
    # Extract version from pubspec.yaml
    $pubspec = Get-Content "$appDir\pubspec.yaml" | Out-String
    $version = ([regex]"version:\s*([0-9\.]+)").Match($pubspec).Groups[1].Value
    
    $destFile = "$rootDir\Airbnb-lead-gen-v$version.apk"
    Copy-Item "build\app\outputs\flutter-apk\app-release.apk" $destFile -Force
    
    Set-Location $rootDir
    git add $destFile
    git commit -m "Update APK to v$version"
    git push
    Write-Host "--- SUCCESS ---"
    Write-Host "File: Airbnb-lead-gen-v$version.apk"
    Write-Host "Link: https://github.com/caiofrk/AIRBNB_LEAD_GENERATOR/raw/main/Airbnb-lead-gen-v$version.apk"
}
else {
    Write-Host "--- FAILED ---"
    exit 1
}
