$ErrorActionPreference = "Stop"

function Ensure-ConsoleUtf8 {
    if ($env:LBAI_INSTALL_UTF8 -eq "0") {
        return
    }
    try {
        if ($PSVersionTable.PSVersion.Major -lt 6) {
            chcp 65001 | Out-Null
        }
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        $OutputEncoding = [System.Text.Encoding]::UTF8
    } catch {
        # Some hosts cannot switch code page; continue with best effort.
    }
}

function Get-RemoteUtf8Text([string]$Url, [int]$TimeoutSec = 120) {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec $TimeoutSec
    $stream = $response.RawContentStream
    if (-not $stream) {
        Fail "could not download $Url"
    }
    $ms = New-Object System.IO.MemoryStream
    if ($stream.CanSeek) {
        $stream.Position = 0
    }
    $stream.CopyTo($ms)
    return [System.Text.Encoding]::UTF8.GetString($ms.ToArray())
}

Ensure-ConsoleUtf8

$Repo = "LBAI-Technology-Company/lbai-workspace-kit"
$InstallerVersion = "1.5.4"
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
$InstallStatus = @{}
$InstallStep = 0
$InstallStepsTotal = 14

function Write-Info($Message) {
    Write-Host $Message
}

function Write-Step([string]$Message) {
    $script:InstallStep++
    Write-Info ""
    Write-Info ("[步骤 {0}/{1}] {2}" -f $script:InstallStep, $script:InstallStepsTotal, $Message)
}

function Write-StepDone {
    Write-Info "  -> 完成"
}

function Set-InstallStatus([string]$Name, [string]$State, [string]$Detail = "") {
    $InstallStatus[$Name] = @{ State = $State; Detail = $Detail }
}

function Write-SummaryLine([string]$Label, [string]$Name) {
    $entry = $InstallStatus[$Name]
    if (-not $entry) {
        Write-Info ("{0,-28} [ -- ]" -f $Label)
        return
    }
    $mark = switch ($entry.State) {
        "OK" { "[OK]  " }
        "FAILED" { "[失败]" }
        "SKIPPED" { "[跳过]" }
        "WARN" { "[警告]" }
        default { "[ -- ]" }
    }
    if ($entry.Detail) {
        Write-Info ("{0,-28} {1} {2}" -f $Label, $mark, $entry.Detail)
    } else {
        Write-Info ("{0,-28} {1}" -f $Label, $mark)
    }
}

function Write-InstallSummary {
    Write-Info ""
    Write-Info "========== 安装结果汇总 =========="
    Write-SummaryLine "Git" "Git"
    Write-SummaryLine "Python 3.10+" "Python"
    Write-SummaryLine "LBAI CLI" "Lbai"
    Write-SummaryLine "Python 依赖 (jsonschema)" "PyDeps"
    Write-SummaryLine "用户 PATH (lbai)" "Path"
    Write-SummaryLine "Codex CLI" "CodexCli"
    Write-SummaryLine "Codex marketplace" "CodexMarketplace"
    Write-SummaryLine "Codex 插件 (lbai-workspace)" "CodexPlugin"
    Write-SummaryLine "Cursor MCP server (lbai-workspace)" "CursorMcp"
    Write-SummaryLine "Cursor 全局斜杠命令 (/lbai-*)" "CursorCommands"
    Write-SummaryLine "公用工作区 (active_workspace)" "Workspace"
    Write-SummaryLine "后端登录 (可选)" "Backend"
    Write-Info "=================================="
    Write-Info "已安装：LBAI CLI、Codex CLI、lbai-workspace 插件、Cursor MCP/斜杠命令、~/.lbai/workspace 公用工作区。"
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
    Write-Step "检查运行环境（Git、Python 3.10+）"

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
    $pythonVersion = & $pythonExe @pythonArgs --version
    Write-Info "环境检查通过：$pythonVersion"
    Set-InstallStatus "Git" "OK" (git --version)
    Set-InstallStatus "Python" "OK" $pythonVersion
    Write-StepDone
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
    Write-Info "  [检查] 安装脚本是否需要从 GitHub 更新"
    if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "lbai_core/lbai/cli.py"))) {
        Write-Info "  -> 使用本地 checkout，跳过更新"
        return
    }

    $tag = Get-LatestReleaseTagSoft
    if (-not $tag) {
        Write-Info "  WARNING: 无法解析最新 release，继续使用当前 install.ps1"
        return
    }

    foreach ($url in @(
        "https://github.com/$Repo/releases/latest/download/install.ps1",
        "https://ghproxy.net/https://github.com/$Repo/releases/latest/download/install.ps1",
        "https://ghproxy.net/https://raw.githubusercontent.com/$Repo/$tag/install.ps1",
        "https://raw.githubusercontent.com/$Repo/$tag/install.ps1"
    )) {
        try {
            $script = Get-RemoteUtf8Text -Url $url -TimeoutSec 120
            if ($script -notmatch 'Write-InstallSummary') {
                Write-Info "  尝试下载安装脚本: $url"
                continue
            }
            if ($script -match 'InstallerVersion = "([^"]+)"' -and $Matches[1] -eq $InstallerVersion) {
                Write-Info "  -> 安装脚本已是最新 ($InstallerVersion)"
                return
            }
            Write-Info "  -> 切换到最新安装脚本 ($tag)"
            $env:LBAI_INSTALL_BOOTSTRAP = "1"
            $env:LBAI_VERSION = $tag
            Invoke-Expression $script
            exit $LASTEXITCODE
        } catch {
            Write-Info "  尝试下载安装脚本: $url"
            continue
        }
    }
    Write-Info "  WARNING: 无法拉取最新 install.ps1，继续使用当前脚本"
}

Write-Info ""
Write-Info "=========================================="
Write-Info "LBAI Workspace Kit 安装程序 v$InstallerVersion"
Write-Info "开始安装..."
Write-Info "=========================================="

Bootstrap-LatestInstaller

$script:InstallStep = 0

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
    Write-Step "下载并安装 LBAI Workspace Kit"
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("lbai-install-" + [guid]::NewGuid().ToString())
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    $archive = Join-Path $tmp "lbai-workspace-kit.zip"
    $url = "https://github.com/$Repo/archive/refs/tags/$Tag.zip"

    Write-Info "  尝试: $url"
    Write-Info "  正在下载 LBAI Workspace Kit $Tag ..."
    Invoke-WebRequest -Uri $url -OutFile $archive -TimeoutSec 600
    Write-Info "  正在解压并写入 $InstallDir ..."
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
    Write-StepDone
}

function Ensure-UserPath {
    Write-Step "配置用户 PATH（lbai 命令）"
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
        Set-InstallStatus "Path" "OK" "已写入用户 PATH ($BinDir)"
    } else {
        Write-Info "PATH 已包含 lbai。"
        Set-InstallStatus "Path" "OK" "已包含 lbai ($BinDir)"
    }
    Write-StepDone
}

function New-PythonRuntime([string[]]$PythonCommand) {
    Write-Info "  正在创建 Python 虚拟环境: $VenvDir"
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
    Write-Info "  正在安装 Python 依赖 (jsonschema)..."
    & $venvPython -m pip install --disable-pip-version-check -r $requirements | Out-Null
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
    Write-Step "安装或检查 Codex CLI"
    if ($env:LBAI_SKIP_CODEX_CLI -eq "1") {
        Write-Info "跳过 Codex CLI 安装（LBAI_SKIP_CODEX_CLI=1）。"
        Set-InstallStatus "CodexCli" "SKIPPED" "LBAI_SKIP_CODEX_CLI=1"
        return
    }

    $codexBin = Join-Path $env:USERPROFILE ".local\bin\codex.exe"
    if (Test-Command codex) {
        $version = codex --version
        Write-Info "环境检查通过：$version"
        Set-InstallStatus "CodexCli" "OK" $version
        return
    }
    if (Test-Path $codexBin) {
        Write-Info "Codex CLI 已安装到 $codexBin。"
        Write-Info "若当前 PowerShell 仍找不到 codex，请关闭并重新打开终端。"
        Set-InstallStatus "CodexCli" "WARN" "已安装到 $codexBin，需重启 PowerShell"
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
        $version = codex --version
        Write-Info "环境检查通过：$version"
        Set-InstallStatus "CodexCli" "OK" $version
        return
    }
    if (Test-Path $codexBin) {
        Write-Info "Codex CLI 已安装到 $codexBin。"
        Write-Info "请关闭并重新打开 PowerShell 后运行 codex --version。"
        Set-InstallStatus "CodexCli" "WARN" "已安装到 $codexBin，需重启 PowerShell"
        return
    }

    Write-Info "WARNING: Codex CLI 自动安装失败。LBAI CLI 已安装，可稍后手动运行："
    Write-Info "  irm https://chatgpt.com/codex/install.ps1 | iex"
    Write-Info "  npm install -g @openai/codex"
    Set-InstallStatus "CodexCli" "FAILED" "自动安装失败，见上方手动命令"
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

    Write-Step "安装 Codex 插件 (lbai-workspace)"

    if ($env:LBAI_SKIP_CODEX_PLUGIN -eq "1" -or $env:LBAI_SKIP_CODEX_CLI -eq "1") {
        Write-Info "跳过 Codex 插件安装（LBAI_SKIP_CODEX_PLUGIN=1 或 LBAI_SKIP_CODEX_CLI=1）。"
        Set-InstallStatus "CodexMarketplace" "SKIPPED" "LBAI_SKIP_CODEX_PLUGIN=1 或 LBAI_SKIP_CODEX_CLI=1"
        Set-InstallStatus "CodexPlugin" "SKIPPED" "LBAI_SKIP_CODEX_PLUGIN=1 或 LBAI_SKIP_CODEX_CLI=1"
        return
    }

    if (-not (Test-CodexReady)) {
        Write-Info "WARNING: codex 不可用，跳过 lbai-workspace 插件安装。"
        Write-Info "  请关闭并重新打开 PowerShell，然后重新运行 install.ps1。"
        Set-InstallStatus "CodexMarketplace" "FAILED" "codex 不可用"
        Set-InstallStatus "CodexPlugin" "FAILED" "codex 不可用，需先安装/配置 Codex CLI"
        return
    }

    $pluginTag = if ($env:LBAI_PLUGIN_REF) { $env:LBAI_PLUGIN_REF } else { $ReleaseTag }
    if ([string]::IsNullOrWhiteSpace($pluginTag) -or $pluginTag -eq "local") {
        Write-Info "WARNING: 无法确定插件 release tag，跳过 Codex 插件自动安装。"
        Set-InstallStatus "CodexMarketplace" "FAILED" "无法确定 release tag"
        Set-InstallStatus "CodexPlugin" "FAILED" "无法确定 release tag"
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
        Set-InstallStatus "CodexMarketplace" "FAILED" "marketplace 配置失败，见上方手动命令"
        Set-InstallStatus "CodexPlugin" "FAILED" "依赖 marketplace，未安装"
        return
    }

    Set-InstallStatus "CodexMarketplace" "OK" "$CodexPluginMarketplace ($pluginTag)"

    Write-Info "正在安装 lbai-workspace 插件..."
    Invoke-Codex plugin remove lbai-workspace | Out-Null
    if ((Invoke-Codex plugin add "lbai-workspace@$CodexPluginMarketplace") -eq 0) {
        Write-Info "已安装 Codex 插件: lbai-workspace@$CodexPluginMarketplace"
        Write-Info "请在 Codex 桌面 App 中开启新线程，使插件 Skills 生效。"
        Set-InstallStatus "CodexPlugin" "OK" "lbai-workspace@$CodexPluginMarketplace"
        return
    }

    Write-Info "WARNING: Codex 插件安装失败。请手动运行："
    Write-Info "  codex plugin add lbai-workspace@$CodexPluginMarketplace"
    Set-InstallStatus "CodexPlugin" "FAILED" "插件安装失败，见上方手动命令"
}

function Ensure-CursorMcp {
    Write-Step "配置 Cursor MCP server (lbai-workspace)"

    if ($env:LBAI_SKIP_CURSOR_MCP -eq "1") {
        Write-Info "跳过 Cursor MCP 配置（LBAI_SKIP_CURSOR_MCP=1）。"
        Set-InstallStatus "CursorMcp" "SKIPPED" "LBAI_SKIP_CURSOR_MCP=1"
        return
    }

    $kitRoot = if ($env:LBAI_KIT_ROOT) { $env:LBAI_KIT_ROOT } else { $InstallDir }
    $mcpScript = Join-Path $kitRoot "cursor_plugin\mcp_server.py"
    $venvPython = Join-Path $VenvDir "Scripts\python.exe"
    if (-not (Test-Path $mcpScript) -or -not (Test-Path $venvPython)) {
        Write-Info "WARNING: 缺少 cursor_plugin\mcp_server.py 或 venv python，跳过 Cursor MCP 配置。"
        Set-InstallStatus "CursorMcp" "FAILED" "缺少 mcp_server.py 或 venv python"
        return
    }

    $cursorDir = Join-Path $HOME ".cursor"
    $mcpJson = Join-Path $cursorDir "mcp.json"
    if (-not (Test-Path $cursorDir)) {
        Write-Info "WARNING: 未检测到 ~\.cursor 目录，跳过 Cursor MCP 配置。"
        Write-Info "  请先安装 Cursor 桌面 App，然后重新运行 install.ps1。"
        Set-InstallStatus "CursorMcp" "SKIPPED" "Cursor 未安装（~\.cursor 不存在）"
        return
    }

    # Idempotent upsert: preserve any other mcpServers entries.
    try {
        $data = @{}
        if (Test-Path $mcpJson) {
            $data = Get-Content -Raw $mcpJson | ConvertFrom-Json -AsHashtable -ErrorAction Stop
            if (-not $data) { $data = @{} }
        }
        if (-not $data.ContainsKey('mcpServers') -or $data['mcpServers'] -isnot [hashtable]) {
            $data['mcpServers'] = @{}
        }
        $data['mcpServers']['lbai-workspace'] = @{
            command = $venvPython
            args    = @($mcpScript)
            env     = @{ PYTHONPATH = (Join-Path $kitRoot 'lbai_core') }
        }
        $json = $data | ConvertTo-Json -Depth 3 -Compress:$false
        # Ensure trailing newline (PowerShell 5 fallback: expand-compress cycle).
        Set-Content -Path $mcpJson -Value $(if (-not $json.EndsWith("`n")) { $json + "`n" } else { $json }) -Encoding UTF8 -NoNewline
        Write-Info "已写入 Cursor MCP 配置: $mcpJson"
        Write-Info "  lbai-workspace -> $venvPython $mcpScript"
        Write-Info "  请重启 Cursor，使 MCP server 在任意项目生效。"
        Set-InstallStatus "CursorMcp" "OK" "lbai-workspace @ ~\.cursor\mcp.json"
    } catch {
        Write-Info "WARNING: Cursor MCP 配置写入失败。请手动合并 ~\.cursor\mcp.json。"
        Write-Info "  错误: $($_.Exception.Message)"
        Set-InstallStatus "CursorMcp" "FAILED" "mcp.json 写入失败"
    }
}

function Ensure-CursorCommands {
    Write-Step "安装 Cursor 全局斜杠命令 (~/.cursor/commands/)"

    if ($env:LBAI_SKIP_CURSOR_COMMANDS -eq "1") {
        Write-Info "跳过 Cursor 全局斜杠命令（LBAI_SKIP_CURSOR_COMMANDS=1）。"
        Set-InstallStatus "CursorCommands" "SKIPPED" "LBAI_SKIP_CURSOR_COMMANDS=1"
        return
    }

    $kitRoot = if ($env:LBAI_KIT_ROOT) { $env:LBAI_KIT_ROOT } else { $InstallDir }
    $srcDir = Join-Path $kitRoot ".cursor\commands"
    $dstDir = Join-Path $HOME ".cursor\commands"

    if (-not (Test-Path $srcDir)) {
        Write-Info "WARNING: 缺少 $srcDir，跳过 Cursor 全局斜杠命令。"
        Set-InstallStatus "CursorCommands" "FAILED" "缺少 .cursor\commands 源目录"
        return
    }

    $sources = @(Get-ChildItem -Path $srcDir -Filter 'lbai-*.md' -File -ErrorAction SilentlyContinue)
    if ($sources.Count -eq 0) {
        Write-Info "WARNING: 未找到 lbai-*.md 命令文件，跳过 Cursor 全局斜杠命令。"
        Set-InstallStatus "CursorCommands" "FAILED" "缺少 lbai-*.md 命令文件"
        return
    }

    New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
    foreach ($src in $sources) {
        Copy-Item -Path $src.FullName -Destination (Join-Path $dstDir $src.Name) -Force
    }

    $count = $sources.Count
    Write-Info "已安装 Cursor 全局斜杠命令: $dstDir ($count 个 lbai-*.md)"
    Write-Info "  请重启 Cursor，在 Agent 中输入 /lbai 即可使用。"
    Set-InstallStatus "CursorCommands" "OK" "$count 个命令 @ ~\.cursor\commands\"
}

function Ensure-SharedWorkspace {
    Write-Step "创建/更新公用工作区 (~/.lbai/workspace)"
    if ($env:LBAI_SKIP_WORKSPACE_INIT -eq "1") {
        Write-Info "跳过公用工作区初始化（LBAI_SKIP_WORKSPACE_INIT=1）。"
        Set-InstallStatus "Workspace" "SKIPPED" "LBAI_SKIP_WORKSPACE_INIT=1"
        return
    }

    $output = & (Join-Path $BinDir "lbai.cmd") workspace ensure --quiet 2>&1 | Out-String
    if ($output -match 'workspace_ensure_status: (READY|PENDING_BIND)') {
        if ($output -match 'workspace_ensure_status: PENDING_BIND') {
            if ($output -match '(?m)^workspace_path: (.+)$') {
                $wsPath = $Matches[1].Trim()
                Write-Info "  -> 工作区目录已创建: $wsPath"
            } else {
                Write-Info "  -> 工作区目录已创建: ~/.lbai/workspace"
            }
            Write-Info "  -> 下一步: lbai bind-github"
            Set-InstallStatus "Workspace" "OK" "待绑定"
            return
        }
        if ($output -match '(?m)^active_workspace: (.+)$') {
            $wsPath = $Matches[1].Trim()
            Write-Info "  -> 工作区就绪: $wsPath"
            Set-InstallStatus "Workspace" "OK" $wsPath
        } else {
            Write-Info "  -> 工作区就绪: ~/.lbai/workspace"
            Set-InstallStatus "Workspace" "OK" "~/.lbai/workspace"
        }
        return
    }
    Write-Info $output.TrimEnd()
    Set-InstallStatus "Workspace" "FAILED" "公用工作区初始化失败"
}

Ensure-Prerequisites
$pythonCommand = Resolve-PythonCommand
Write-Step "解析 GitHub 最新 release 版本"
$releaseTag = Get-LatestReleaseTag
Write-Info "  -> 最新 release: $releaseTag"
Write-StepDone
Install-KitFromRelease -Tag $releaseTag
Write-Step "创建 Python 运行环境与 lbai 命令"
$runtimePython = New-PythonRuntime -PythonCommand $pythonCommand
Write-Info "  正在写入 $(Join-Path $BinDir 'lbai.cmd') ..."
Write-LbaiLauncher -RuntimePython $runtimePython
Write-StepDone
Ensure-UserPath
Ensure-CodexCli
Ensure-CodexPlugin -ReleaseTag $releaseTag
Ensure-CursorMcp
Ensure-CursorCommands
Ensure-SharedWorkspace
Set-InstallStatus "PyDeps" "OK" "jsonschema 等 ($VenvDir)"

if (-not $env:LBAI_SKIP_BACKEND_AUTH -and -not [Console]::IsInputRedirected) {
    Write-Step "可选：后端知识服务登录"
    $backendExit = & (Join-Path $BinDir "lbai.cmd") auth backend-login --optional
    if ($backendExit -eq 0) {
        Set-InstallStatus "Backend" "OK" "已完成或已跳过"
    } else {
        Set-InstallStatus "Backend" "WARN" "未完成，可稍后运行 lbai auth backend-login"
    }
} else {
    Set-InstallStatus "Backend" "SKIPPED" "非交互环境或 LBAI_SKIP_BACKEND_AUTH=1"
}

$kitVersion = "unknown"
$versionFile = Join-Path $InstallDir "VERSION"
if (Test-Path $versionFile) {
    $kitVersion = (Get-Content $versionFile -Raw).Trim()
}

Set-InstallStatus "Lbai" "OK" "v$kitVersion ($(Join-Path $BinDir 'lbai.cmd'))"
Write-Step "输出安装结果汇总"
Write-InstallSummary

Write-Info "Release: $releaseTag"
Write-Info ""
& (Join-Path $BinDir "lbai.cmd") setup-guide
if (-not (Test-CodexReady) -and ((Test-Command codex) -or (Test-Path (Join-Path $env:USERPROFILE ".local\bin\codex.exe")))) {
    Write-Info ""
    Write-Info "提示：Codex CLI 已安装但插件未就绪，重新打开 PowerShell 后重新运行 install.ps1"
}
Write-Info ""
Write-Info "升级：重新运行 install.ps1    卸载：lbai uninstall"
