$ErrorActionPreference = "Stop"

function Get-RemoteUtf8Text([string]$Url, [int]$TimeoutSec = 120) {
    $client = New-Object System.Net.WebClient
    $client.Headers.Add("User-Agent", "lbai-workspace-kit-installer")
    try {
        $bytes = $client.DownloadData($Url)
    } finally {
        $client.Dispose()
    }
    return [System.Text.Encoding]::UTF8.GetString($bytes)
}

# ASCII-only bootstrap for Windows PowerShell. GitHub release assets are UTF-8;
# piping install.ps1 through "irm | iex" can decode Chinese text with the wrong
# code page on Chinese Windows. This script downloads raw bytes and runs install.ps1
# as UTF-8, and switches the console to UTF-8 before any localized output.

try {
    if ($PSVersionTable.PSVersion.Major -lt 6) {
        chcp 65001 | Out-Null
    }
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
}

$Repo = "LBAI-Technology-Company/lbai-workspace-kit"
$Url = "https://github.com/$Repo/releases/latest/download/install.ps1"
$script = Get-RemoteUtf8Text -Url $Url -TimeoutSec 120
Invoke-Expression $script
exit $LASTEXITCODE
