$ErrorActionPreference = "Stop"

$Repo = "LBAI-Technology-Company/lbai-workspace-kit"
if ($env:LBAI_HOME) {
    $LbaiHome = $env:LBAI_HOME
} else {
    $LbaiHome = Join-Path $env:USERPROFILE ".lbai"
}
$InstallDir = Join-Path $LbaiHome "kit"
$BinDir = Join-Path $LbaiHome "bin"
$VenvDir = Join-Path $LbaiHome "venv"
$PathMarker = "# LBAI Workspace Kit CLI"

function Write-Info($Message) {
    Write-Host $Message
}

function Fail($Message) {
    Write-Error $Message
    exit 1
}

function Test-Command($Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Ensure-WingetPackage([string]$Id) {
    if (-not (Test-Command winget)) {
        return $false
    }
    winget list --id $Id -e --accept-source-agreements | Out-Null
    if ($LASTEXITCODE -eq 0) {
        return $true
    }
    Write-Info "正在安装 $Id ..."
    winget install --id $Id -e --accept-package-agreements --accept-source-agreements --disable-interactivity
    return ($LASTEXITCODE -eq 0)
}

function Ensure-Prerequisites {
    Write-Info "正在检查运行环境（Git、Python 3.10+）..."

    if (-not (Test-Command git)) {
        if (-not (Ensure-WingetPackage "Git.Git")) {
            Fail "未检测到 Git。请打开 https://git-scm.com/download/win 安装后重试，或确认 winget 可用。"
        }
    }

    if (-not (Test-Command py) -and -not (Test-Command python)) {
        if (-not (Ensure-WingetPackage "Python.Python.3.12")) {
            Fail "未检测到 Python 3.10+。请打开 https://www.python.org/downloads/ 安装后重试，或确认 winget 可用。"
        }
    }

    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"

    if (-not (Test-Command git)) {
        Fail "Git 仍未可用，请关闭并重新打开 PowerShell 后重试。"
    }
    if (-not (Resolve-PythonCommand -Quiet)) {
        Fail "Python 3.10+ 仍未可用，请关闭并重新打开 PowerShell 后重试。"
    }

    Write-Info "环境检查通过：$(git --version)"
    $pythonCommand = Resolve-PythonCommand
    $pythonArgs = @()
    if ($pythonCommand.Count -gt 1) {
        $pythonArgs = $pythonCommand[1..($pythonCommand.Count - 1)]
    }
    $pythonExe = $pythonCommand[0]
    Write-Info "环境检查通过：$(& $pythonExe @pythonArgs --version)"
}

function Get-LatestReleaseTag {
    if ($env:LBAI_VERSION) {
        return $env:LBAI_VERSION
    }
    try {
        $release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest" -TimeoutSec 30
        return $release.tag_name
    } catch {
        Fail "无法获取最新 Release，请检查网络后重试。"
    }
}

function Test-PythonVersion([string[]]$Command) {
    try {
        $pythonArgs = @()
        if ($Command.Count -gt 1) {
            $pythonArgs = $Command[1..($Command.Count - 1)]
        }
        $pythonExe = $Command[0]
        & $pythonExe @pythonArgs -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Resolve-PythonCommand {
    param([switch]$Quiet)
    if (Test-Command py) {
        $cmd = @("py", "-3")
        if (Test-PythonVersion $cmd) {
            return $cmd
        }
    }
    if (Test-Command python) {
        $cmd = @("python")
        if (Test-PythonVersion $cmd) {
            return $cmd
        }
    }
    if ($Quiet) {
        return $null
    }
    Fail "Python 3.10+ is required"
}

function Install-KitFromRelease([string]$Tag) {
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("lbai-install-" + [guid]::NewGuid().ToString())
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    $archive = Join-Path $tmp "lbai-workspace-kit.zip"
    $url = "https://github.com/$Repo/archive/refs/tags/$Tag.zip"

    Write-Info "Downloading LBAI Workspace Kit $Tag ..."
    Invoke-WebRequest -Uri $url -OutFile $archive -TimeoutSec 600
    Expand-Archive -Path $archive -DestinationPath $tmp -Force
    $src = Get-ChildItem -Path $tmp -Directory | Where-Object { $_.Name -like "lbai-workspace-kit-*" } | Select-Object -First 1
    if (-not $src) {
        Fail "下载包内容无效。"
    }

    if (Test-Path $InstallDir) {
        Remove-Item -Recurse -Force $InstallDir
    }
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
    Copy-Item -Path (Join-Path $src.FullName "*") -Destination $InstallDir -Recurse -Force
}

function Ensure-UserPath {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath -notlike "*$BinDir*") {
        if ([string]::IsNullOrWhiteSpace($userPath)) {
            $newPath = $BinDir
        } else {
            $newPath = "$userPath;$BinDir"
        }
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        $env:Path = "$env:Path;$BinDir"
        Write-Info "已将 lbai 加入用户 PATH。"
    } else {
        Write-Info "PATH 已包含 lbai。"
    }
}

function New-PythonRuntime([string[]]$PythonCommand) {
    if (Test-Path $VenvDir) {
        Remove-Item -Recurse -Force $VenvDir
    }

    $pythonArgs = @()
    if ($PythonCommand.Count -gt 1) {
        $pythonArgs = $PythonCommand[1..($PythonCommand.Count - 1)]
    }
    $pythonExe = $PythonCommand[0]
    & $pythonExe @pythonArgs -m venv $VenvDir | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Fail "could not create Python runtime at $VenvDir. Install Python venv support and rerun install.ps1."
    }

    $venvPython = Join-Path $VenvDir "Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        Fail "Python runtime was created but $venvPython was not found."
    }

    $requirements = Join-Path $InstallDir "lbai_core\requirements.txt"
    & $venvPython -m pip install --quiet --disable-pip-version-check -r $requirements | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Fail "could not install Python dependencies into $VenvDir. Check network or pip configuration, then rerun install.ps1."
    }

    return $venvPython
}

function Write-LbaiLauncher([string]$RuntimePython) {
    $launcher = Join-Path $BinDir "lbai.cmd"
    @"
@echo off
setlocal
set "LBAI_HOME=$LbaiHome"
set "LBAI_KIT_ROOT=$InstallDir"
set "PYTHONPATH=$InstallDir\lbai_core;%PYTHONPATH%"
"$RuntimePython" -m lbai.cli %*
"@ | Set-Content -Path $launcher -Encoding ASCII
}

Ensure-Prerequisites
$pythonCommand = Resolve-PythonCommand
$releaseTag = Get-LatestReleaseTag
Write-Info "Latest release: $releaseTag"
Install-KitFromRelease -Tag $releaseTag
$runtimePython = New-PythonRuntime -PythonCommand $pythonCommand
Write-LbaiLauncher -RuntimePython $runtimePython
Ensure-UserPath
Write-Info "Installed Python runtime and dependencies (jsonschema)."

if (-not $env:LBAI_SKIP_BACKEND_AUTH -and -not [Console]::IsInputRedirected) {
    Write-Info "Optional backend knowledge service setup."
    & (Join-Path $BinDir "lbai.cmd") auth backend-login --optional
}

$kitVersion = "unknown"
$versionFile = Join-Path $InstallDir "VERSION"
if (Test-Path $versionFile) {
    $kitVersion = (Get-Content $versionFile -Raw).Trim()
}

Write-Info "LBAI Workspace Kit installed."
Write-Info "已安装版本: $kitVersion"
Write-Info "Release: $releaseTag"
Write-Info "lbai path: $(Join-Path $BinDir 'lbai.cmd')"
Write-Info ""
Write-Info "Next steps:"
Write-Info "  关闭并重新打开 PowerShell"
Write-Info "  lbai auth login"
Write-Info "  lbai auth doctor"
Write-Info "  lbai auth backend-login"
Write-Info "  lbai init-workspace"
