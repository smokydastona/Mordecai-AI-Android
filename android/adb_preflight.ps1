$ErrorActionPreference = 'Stop'

if (-not (Get-Command adb -ErrorAction SilentlyContinue)) {
    throw 'adb is not available on PATH'
}

$devices = & adb devices | Select-Object -Skip 1 | Where-Object { $_ -match '\S' -and $_ -notmatch 'offline' }
if (-not $devices) {
    throw 'No ready Android device detected over adb'
}

$model = (& adb shell getprop ro.product.model).Trim()
$androidVersion = (& adb shell getprop ro.build.version.release).Trim()
$buildFingerprint = (& adb shell getprop ro.build.fingerprint).Trim()
$battery = (& adb shell dumpsys battery | Select-String 'level').ToString().Split(':')[-1].Trim()

[pscustomobject]@{
    Model = $model
    AndroidVersion = $androidVersion
    BatteryLevel = $battery
    BuildFingerprint = $buildFingerprint
} | Format-List