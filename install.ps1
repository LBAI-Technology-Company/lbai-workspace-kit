$ErrorActionPreference = "Stop"

$Repo = "LBAI-Technology-Company/lbai-workspace-kit"
$InstallerVersion = "1.4.4"
if ($env:LBAI_HOME) {
    $LbaiHome = $env:LBAI_HOME
} else {
    $LbaiHome = Join-Path $env:USERPROFILE ".lbai"
}
$InstallDir = Join-Path $LbaiHome "kit"
$BinDir = Join-Path $LbaiHome "bin"
$VenvDir = Join-Path $LbaiHome "venv"
$PathMarker = "# LBAI Workspace Kit CLI"
$CodexPluginMarketplace = "lbai-internal"

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

function Get-LatestReleaseTagSoft {
    if ($env:LBAI_VERSION) {
        return $env:LBAI_VERSION
    }
    foreach ($apiUrl in @(
        "https://ghproxy.net/https://api.github.com/repos/$Repo/releases/latest",
        "https://api.github.com/repos/$Repo/releases/latest"
    )) {
        try {
            $release = Invoke-RestMethod -Uri $apiUrl -TimeoutSec 30
            if ($release.tag_name) {
                return $release.tag_name
            }
        } catch {
            continue
        }
    }
    return $null
}

function Get-LatestReleaseTag {
    $tag = Get-LatestReleaseTagSoft
    if (-not $tag) {
        Fail "无法获取最新 Release，请检查网络后重试。"
    }
    return $tag
}

function Bootstrap-LatestInstaller {
    if ($env:LBAI_INSTALL_BOOTSTRAP -eq "1") {
        return
    }
    if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "lbai_core/lbai/cli.py"))) {
        return
    }
    if ($MyInvocation.MyCommand.Path -and (Select-String -Path $MyInvocation.MyCommand.Path -Pattern 'Ensure-CodexPlugin' -Quiet)) {
        return
    }

    $tag = Get-LatestReleaseTagSoft
    if (-not $tag) {
        Write-Info "WARNING: 无法解析最新 release tag，跳过 install.ps1 自动升级。"
        return
    }

    Write-Info "检测到旧版或缓存安装脚本，正在从 GitHub 拉取最新 install.ps1 ($tag)..."
    foreach ($url in @(
        "https://ghproxy.net/https://raw.githubusercontent.com/$Repo/$tag/install.ps1",
        "https://raw.githubusercontent.com/$Repo/$tag/install.ps1"
    )) {
        try {
            $script = (Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 120).Content
            if ($script -match 'Ensure-CodexPlugin') {
                $env:LBAI_INSTALL_BOOTSTRAP = "1"
                $env:LBAI_VERSION = $tag
                Invoke-Expression $script
                exit $LASTEXITCODE
            }
        } catch {
            continue
        }
    }
    Write-Info "WARNING: 无法从 GitHub 拉取最新 install.ps1，继续使用当前安装脚本。"
}

Bootstrap-LatestInstaller

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

function Install-CodexViaOfficialScript {
    $env:CODEX_NON_INTERACTIVE = "1"
    if (Test-Command curl) {
        curl.exe -fsSL --connect-timeout 20 --max-time 300 https://chatgpt.com/codex/install.ps1 | powershell -NoProfile -Command -
        return ($LASTEXITCODE -eq 0)
    }
    $script = (Invoke-WebRequest -UseBasicParsing -Uri "https://chatgpt.com/codex/install.ps1" -TimeoutSec 300).Content
    Invoke-Expression $script
    return ($LASTEXITCODE -eq 0)
}

function Install-CodexViaNpm {
    if (-not (Test-Command npm)) {
        return $false
    }
    Write-Info "  尝试 npm 全局安装 @openai/codex ..."
    npm install -g @openai/codex | Out-Null
    return ($LASTEXITCODE -eq 0)
}

function Install-CodexViaGithubBinary {
    $asset = if ([Environment]::Is64BitOperatingSystem) { "codex-x86_64-pc-windows-msvc.zip" } else { $null }
    if (-not $asset) {
        return $false
    }
    Write-Info "  尝试 GitHub release 二进制 ($asset) ..."
    $localBin = Join-Path $env:USERPROFILE ".local\bin"
    New-Item -ItemType Directory -Path $localBin -Force | Out-Null
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("codex-install-" + [guid]::NewGuid().ToString())
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    foreach ($url in @(
        "https://ghproxy.net/https://github.com/openai/codex/releases/latest/download/$asset",
        "https://github.com/openai/codex/releases/latest/download/$asset"
    )) {
        try {
            $archive = Join-Path $tmp $asset
            Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $archive -TimeoutSec 300
            Expand-Archive -Path $archive -DestinationPath $tmp -Force
            $candidate = Get-ChildItem -Path $tmp -Recurse -Filter "codex.exe" | Select-Object -First 1
            if ($candidate) {
                Copy-Item -Path $candidate.FullName -Destination (Join-Path $localBin "codex.exe") -Force
                return $true
            }
        } catch {
            continue
        }
    }
    return $false
}

function Ensure-CodexCli {
    if ($env:LBAI_SKIP_CODEX_CLI -eq "1") {
        Write-Info "跳过 Codex CLI 安装（LBAI_SKIP_CODEX_CLI=1）。"
        return
    }

    $codexBin = Join-Path $env:USERPROFILE ".local\bin\codex.exe"
    if (Test-Command codex) {
        Write-Info "环境检查通过：$(codex --version)"
        return
    }
    if (Test-Path $codexBin) {
        Write-Info "Codex CLI 已安装到 $codexBin。"
        Write-Info "若当前 PowerShell 仍找不到 codex，请关闭并重新打开终端。"
        return
    }

    Write-Info "未检测到 Codex CLI，正在尝试多种安装方式..."
    $installed = $false
    try {
        Write-Info "  尝试 OpenAI 官方安装脚本..."
        if (Install-CodexViaOfficialScript) { $installed = $true }
    } catch {
        $installed = $false
    }
    if (-not $installed -and (Install-CodexViaNpm)) { $installed = $true }
    if (-not $installed -and (Install-CodexViaGithubBinary)) { $installed = $true }

    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"

    if (Test-Command codex) {
        Write-Info "环境检查通过：$(codex --version)"
        return
    }
    if (Test-Path $codexBin) {
        Write-Info "Codex CLI 已安装到 $codexBin。"
        Write-Info "请关闭并重新打开 PowerShell 后运行 codex --version。"
        return
    }

    Write-Info "WARNING: Codex CLI 自动安装失败。LBAI CLI 已安装，可稍后手动运行："
    Write-Info "  irm https://chatgpt.com/codex/install.ps1 | iex"
    Write-Info "  npm install -g @openai/codex"
}

function Invoke-Codex {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    $codexBin = Join-Path $env:USERPROFILE ".local\bin\codex.exe"
    if (Test-Command codex) {
        & codex @Args
        return $LASTEXITCODE
    }
    if (Test-Path $codexBin) {
        & $codexBin @Args
        return $LASTEXITCODE
    }
    return 127
}

function Test-CodexReady {
    return ((Invoke-Codex --version) -eq 0)
}

function Ensure-CodexPlugin {
    param([string]$ReleaseTag)

    if ($env:LBAI_SKIP_CODEX_PLUGIN -eq "1" -or $env:LBAI_SKIP_CODEX_CLI -eq "1") {
        Write-Info "跳过 Codex 插件安装（LBAI_SKIP_CODEX_PLUGIN=1 或 LBAI_SKIP_CODEX_CLI=1）。"
        return
    }

    if (-not (Test-CodexReady)) {
        Write-Info "WARNING: codex 不可用，跳过 lbai-workspace 插件安装。"
        Write-Info "  请关闭并重新打开 PowerShell，然后重新运行 install.ps1。"
        return
    }

    $pluginTag = if ($env:LBAI_PLUGIN_REF) { $env:LBAI_PLUGIN_REF } else { $ReleaseTag }
    if ([string]::IsNullOrWhiteSpace($pluginTag) -or $pluginTag -eq "local") {
        Write-Info "WARNING: 无法确定插件 release tag，跳过 Codex 插件自动安装。"
        return
    }

    Write-Info "正在配置 LBAI Codex 插件 marketplace ($pluginTag)..."
    $marketplaceOk = $false
    if ((Invoke-Codex plugin marketplace upgrade $CodexPluginMarketplace) -eq 0) {
        $marketplaceOk = $true
        Write-Info "已升级 Codex marketplace: $CodexPluginMarketplace"
    } else {
        Invoke-Codex plugin marketplace remove $CodexPluginMarketplace | Out-Null
        if ((Invoke-Codex plugin marketplace add $Repo --ref $pluginTag) -eq 0) {
            $marketplaceOk = $true
            Write-Info "已添加 Codex marketplace: $CodexPluginMarketplace"
        }
    }

    if (-not $marketplaceOk) {
        Write-Info "WARNING: Codex marketplace 配置失败。请确认已登录 Codex 后手动运行："
        Write-Info "  codex plugin marketplace add $Repo --ref $pluginTag"
        Write-Info "  codex plugin add lbai-workspace@$CodexPluginMarketplace"
        return
    }

    Write-Info "正在安装 lbai-workspace 插件..."
    Invoke-Codex plugin remove lbai-workspace | Out-Null
    if ((Invoke-Codex plugin add "lbai-workspace@$CodexPluginMarketplace") -eq 0) {
        Write-Info "已安装 Codex 插件: lbai-workspace@$CodexPluginMarketplace"
        Write-Info "请在 Codex 桌面 App 中开启新线程，使插件 Skills 生效。"
        return
    }

    Write-Info "WARNING: Codex 插件安装失败。请手动运行："
    Write-Info "  codex plugin add lbai-workspace@$CodexPluginMarketplace"
}

Ensure-Prerequisites
$pythonCommand = Resolve-PythonCommand
$releaseTag = Get-LatestReleaseTag
Write-Info "Latest release: $releaseTag"
Install-KitFromRelease -Tag $releaseTag
$runtimePython = New-PythonRuntime -PythonCommand $pythonCommand
Write-LbaiLauncher -RuntimePython $runtimePython
Ensure-UserPath
Ensure-CodexCli
Ensure-CodexPlugin -ReleaseTag $releaseTag
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
if (-not (Test-CodexReady) -and ((Test-Command codex) -or (Test-Path (Join-Path $env:USERPROFILE ".local\bin\codex.exe")))) {
    Write-Info "  关闭并重新打开 PowerShell，然后重新运行 install.ps1 以自动安装 lbai-workspace 插件"
}
