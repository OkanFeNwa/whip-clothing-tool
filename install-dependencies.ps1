<#
.SYNOPSIS
Installs the dependencies needed by Whip Clothing Tool.

.DESCRIPTION
By default this installs the RUNTIME dependencies:
  - Blender (via winget, if not already present)
  - Sollumz add-on/extension, downloaded from its official GitHub release
    and installed into the current Blender user profile

Use -Dev to also install the BUILD toolchain:
  - Node.js LTS, Rust (rustup), Visual Studio 2022 Build Tools with the
    Native Desktop workload

The script is safe to run more than once: existing installations are detected
and Sollumz is replaced only with the same version from the official release.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File .\install-dependencies.ps1

.EXAMPLE
powershell -ExecutionPolicy Bypass -File .\install-dependencies.ps1 -Dev
#>

[CmdletBinding()]
param(
    [switch]$Dev,
    [string]$BlenderPath
)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Write-Step([string]$Message) { Write-Host "`n==> $Message" -ForegroundColor Cyan }
function Write-Ok([string]$Message)   { Write-Host "OK: $Message" -ForegroundColor Green }
function Write-Note([string]$Message) { Write-Host "NOTE: $Message" -ForegroundColor Yellow }

function Test-Winget {
    $cmd = Get-Command winget -ErrorAction SilentlyContinue
    return $null -ne $cmd
}

function Install-WingetPackage {
    param(
        [Parameter(Mandatory)][string]$Id,
        [string]$Override
    )
    if (-not (Test-Winget)) {
        Write-Note "winget is not available. Install manually: https://learn.microsoft.com/windows/package-manager/winget/"
        return $false
    }
    Write-Step "Installing $Id with winget..."
    $wingetArgs = @(
        'install', '--exact', '--id', $Id, '--source', 'winget',
        '--accept-package-agreements', '--accept-source-agreements', '--silent'
    )
    if ($Override) { $wingetArgs += @('--override', $Override) }
    & winget @wingetArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Note "winget returned exit code $LASTEXITCODE for $Id. Check the output above."
        return $false
    }
    return $true
}

function Find-Blender {
    param([string]$Explicit)

    if ($Explicit -and (Test-Path -LiteralPath $Explicit -PathType Leaf)) {
        return (Resolve-Path -LiteralPath $Explicit).Path
    }
    if ($env:WCT_BLENDER -and (Test-Path -LiteralPath $env:WCT_BLENDER -PathType Leaf)) {
        return (Resolve-Path -LiteralPath $env:WCT_BLENDER).Path
    }

    $command = Get-Command blender.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    $roots = @($env:ProgramFiles, ${env:ProgramFiles(x86)}, $env:LOCALAPPDATA) | Where-Object { $_ }
    foreach ($root in $roots) {
        $base = Join-Path $root 'Blender Foundation'
        if (Test-Path -LiteralPath $base) {
            $found = Get-ChildItem -LiteralPath $base -Filter blender.exe -File -Recurse -ErrorAction SilentlyContinue |
                     Select-Object -First 1
            if ($found) { return $found.FullName }
        }
    }
    return $null
}

function Get-BlenderUserPath {
    param([Parameter(Mandatory)][string]$BlenderExe)
    $expression = "import bpy; print('WCT_USER_PATH=' + bpy.utils.resource_path('USER'))"
    $output = & $BlenderExe --background --factory-startup --python-expr $expression 2>&1
    $line = $output | Where-Object { "$_" -like 'WCT_USER_PATH=*' } | Select-Object -First 1
    if (-not $line) {
        throw "Could not determine the Blender user resources path. Blender output:`n$output"
    }
    return ("$line" -replace '^WCT_USER_PATH=', '')
}

function Install-Sollumz {
    param(
        [Parameter(Mandatory)][string]$BlenderExe,
        [Parameter(Mandatory)][string]$UserPath
    )

    Write-Step 'Downloading the latest Sollumz release...'
    $headers = @{ 'User-Agent' = 'whip-clothing-tool-installer' }
    $release = Invoke-RestMethod -Uri 'https://api.github.com/repos/Sollumz/Sollumz/releases/latest' -Headers $headers
    $asset = $release.assets | Where-Object { $_.name -eq 'Sollumz.zip' } | Select-Object -First 1
    if (-not $asset) {
        throw 'The latest Sollumz release does not contain Sollumz.zip'
    }

    $temp = Join-Path $env:TEMP 'wct-sollumz-install'
    $zip = Join-Path $temp 'Sollumz.zip'
    $extract = Join-Path $temp 'extracted'
    Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path $extract -Force | Out-Null

    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zip -Headers $headers
    Expand-Archive -LiteralPath $zip -DestinationPath $extract -Force

    $manifest = Get-ChildItem -LiteralPath $extract -Filter 'blender_manifest.toml' -File -Recurse |
                Select-Object -First 1
    if (-not $manifest) {
        throw 'Sollumz.zip did not contain blender_manifest.toml'
    }

    $destination = Join-Path $UserPath 'extensions\user_default\sollumz'
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    if (Test-Path -LiteralPath $destination) {
        Remove-Item -LiteralPath $destination -Recurse -Force
    }
    Copy-Item -LiteralPath $manifest.Directory.FullName -Destination $destination -Recurse -Force
    Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue

    Write-Ok "Sollumz $($release.tag_name) copied to $destination"

    # Copying the files is not enough in Blender 4.2+: the extension must also
    # be enabled and the preference saved, otherwise the Python modules are not
    # importable by the export worker.
    Write-Step 'Enabling Sollumz in Blender preferences...'
    $enable = "import bpy; bpy.ops.preferences.addon_enable(module='bl_ext.user_default.sollumz'); bpy.ops.wm.save_userpref(); print('WCT_SOLLUMZ_ENABLED')"
    $enableOutput = & $BlenderExe --background --python-expr $enable 2>&1
    if (-not (("$enableOutput" -join "`n") -match 'WCT_SOLLUMZ_ENABLED')) {
        throw "Sollumz was copied but could not be enabled. Blender output:`n$enableOutput"
    }
    Write-Ok 'Sollumz enabled and saved in the Blender profile'
}

# ---------------------------------------------------------------------------
# Runtime dependencies
# ---------------------------------------------------------------------------

Write-Host 'Whip Clothing Tool - dependency installer' -ForegroundColor White

$blender = Find-Blender -Explicit $BlenderPath
if (-not $blender) {
    Write-Step 'Blender was not found. Installing it...'
    if (Install-WingetPackage -Id 'BlenderFoundation.Blender') {
        $blender = Find-Blender
    }
}
if (-not $blender) {
    throw 'Blender is required but could not be installed automatically. Install it from https://www.blender.org/download/ and re-run this script.'
}
Write-Ok "Blender found: $blender"

$userPath = Get-BlenderUserPath -BlenderExe $blender
Write-Ok "Blender user resources: $userPath"

Install-Sollumz -BlenderExe $blender -UserPath $userPath

Write-Step 'Verifying Sollumz and its Python dependencies inside Blender...'
$verify = "import szio, pymateria; print('WCT_DEPS_OK')"
$output = & $blender --background --python-expr $verify 2>&1
if (-not (("$output" -join "`n") -match 'WCT_DEPS_OK')) {
    Write-Note "The verification did not report success. Blender output:"
    Write-Host $output
} else {
    Write-Ok 'szio and pymateria load correctly inside Blender'
}

# ---------------------------------------------------------------------------
# Optional build toolchain
# ---------------------------------------------------------------------------

if ($Dev) {
    Write-Step 'Installing build tools (Node.js, Rust, Visual Studio Build Tools)...'
    $null = Install-WingetPackage -Id 'OpenJS.NodeJS.LTS'
    $null = Install-WingetPackage -Id 'Rustlang.Rustup'
    $vsOverride = '--quiet --wait --norestart --add Microsoft.VisualStudio.Workload.NativeDesktop'
    $null = Install-WingetPackage -Id 'Microsoft.VisualStudio.2022.BuildTools' -Override $vsOverride
    Write-Note 'Open a NEW terminal so PATH picks up node/npm/cargo, then run: npm install'
}

Write-Host "`nDone. You can now run whip_clothing_tool.exe." -ForegroundColor Green
if (-not (Get-Command blender.exe -ErrorAction SilentlyContinue) -and -not $env:WCT_BLENDER) {
    Write-Note "Blender is not on PATH, but the app also scans the standard Blender Foundation folders and should find it automatically.`nIf your installation is in a custom location, set WCT_BLENDER to:`n  $blender"
}
