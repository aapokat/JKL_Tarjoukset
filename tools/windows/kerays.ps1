# Kerää K-kauppojen tarjoukset ja vie ne GitHubiin. Tehtävien ajoitus ajaa tämän joka toinen aamu (asenna.ps1).
# Käsin: powershell -ExecutionPolicy Bypass -File tools\windows\kerays.ps1
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
Start-Transcript -Path (Join-Path $PSScriptRoot "kerays.log") -Force | Out-Null

function Run($what) {
    & $what[0] $what[1..($what.Length - 1)]
    if ($LASTEXITCODE -ne 0) { throw "Epäonnistui: $($what -join ' ')" }
}

try {
    Write-Host "$(Get-Date -Format 'dd.MM.yyyy HH:mm') Haetaan repon uusin versio"
    Run @("git", "pull", "--rebase", "--autostash", "origin", "main")

    Write-Host "Kerätään K-kaupat (noin 25 minuuttia, selainikkuna sulkeutuu itse)"
    Run @("python", "site/collect_browser.py", "--show", "--edge")

    Run @("git", "add", "site/data/k-ruoka-snapshot.json")
    & git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Ei muutoksia K-tarjouksiin"
    } else {
        Run @("git", "commit", "-m", "K-kauppojen tarjoukset $(Get-Date -Format 'yyyy-MM-dd')")
        Run @("git", "pull", "--rebase", "origin", "main")
        Run @("git", "push", "origin", "main")
        Write-Host "Valmis: GitHub julkaisee sivun parissa minuutissa"
    }
} catch {
    Write-Host "VIRHE: $_"
    Write-Host "Sivulle jää edellinen K-haku. Katso yllä oleva tuloste."
    Stop-Transcript | Out-Null
    exit 1
}
Stop-Transcript | Out-Null
