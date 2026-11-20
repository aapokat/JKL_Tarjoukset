# Kertaluonteinen asennus K-keräykselle Windows-koneelle, joka on aina päällä.
# Aja PowerShellissä repon kansiossa:  powershell -ExecutionPolicy Bypass -File tools\windows\asenna.ps1
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo

foreach ($c in @("git", "python")) {
    if (-not (Get-Command $c -ErrorAction SilentlyContinue)) {
        throw "$c puuttuu. Asenna Git (git-scm.com) ja Python (python.org, rasti kohtaan 'Add python.exe to PATH') ja avaa PowerShell uudelleen."
    }
}

Write-Host "Asennetaan Playwright (selaimen ohjaus)"
& python -m pip install --upgrade --quiet playwright
if ($LASTEXITCODE -ne 0) { throw "Playwrightin asennus epäonnistui" }

# Commitit omalla GitHub-nimellä ilman sähköpostiosoitetta.
if (-not (git config user.name)) { git config user.name "aapokat" }
if (-not (git config user.email)) { git config user.email "aapokat@users.noreply.github.com" }

$hour = Read-Host "Mihin aikaan keräys alkaa? (oletus 06:40, valmis noin 25 min myöhemmin)"
if (-not $hour) { $hour = "06:40" }

$script = Join-Path $PSScriptRoot "kerays.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Minimized -File `"$script`"" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Daily -DaysInterval 2 -At $hour
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 1)
# Ajetaan kirjautuneena käyttäjänä, koska keräys avaa selainikkunan. Koneella pitää siis olla käyttäjä kirjautuneena.
Register-ScheduledTask -TaskName "JKL Tarjoukset K-keräys" -Action $action -Trigger $trigger -Settings $settings `
    -Description "Kerää K-kauppojen tarjoukset joka toinen päivä ja vie ne GitHubiin (aapokat/JKL_Tarjoukset)." -Force | Out-Null

Write-Host ""
Write-Host "Valmis. Ajastus: joka toinen päivä klo $hour (Tehtävien ajoitus > JKL Tarjoukset K-keräys)."
Write-Host "Aja seuraavaksi keräys kerran käsin, jotta näet että se toimii ja GitHub-kirjautuminen tallentuu:"
Write-Host "  powershell -ExecutionPolicy Bypass -File tools\windows\kerays.ps1"
