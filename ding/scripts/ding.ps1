[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Signal = "confirm",

    [int]$Count = 0,

    [string]$Sound = "",

    [Nullable[double]]$DedupeWindow = $null,

    [string[]]$DedupeAgainst = @(),

    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$SkillRoot = Split-Path -Parent $PSScriptRoot
$DefaultMp3 = Join-Path $SkillRoot "assets\ding.mp3"
$DefaultWav = Join-Path $SkillRoot "assets\ding.wav"

if ([string]::IsNullOrWhiteSpace($Sound)) {
    if (-not [string]::IsNullOrWhiteSpace($env:DING_SOUND)) {
        $Sound = $env:DING_SOUND
    }
    else {
        $Sound = $DefaultMp3
    }
}

$SoundPath = [System.IO.Path]::GetFullPath($Sound)
if (-not (Test-Path -LiteralPath $SoundPath -PathType Leaf)) {
    Write-Error "sound file not found: $SoundPath"
    exit 2
}

$Aliases = @{
    "confirm" = 1
    "once" = 1
    "1" = 1
    "done" = 3
    "complete" = 3
    "3" = 3
}

if ($Count -lt 1) {
    $Key = $Signal.ToLowerInvariant()
    if ($Aliases.ContainsKey($Key)) {
        $Count = $Aliases[$Key]
    }
    else {
        $Parsed = 0
        if (-not [int]::TryParse($Signal, [ref]$Parsed) -or $Parsed -lt 1) {
            Write-Error "unknown signal: $Signal"
            exit 2
        }
        $Count = $Parsed
    }
}

$StateKey = if ($Count -eq 1) {
    "confirm"
}
elseif ($Count -eq 3) {
    "done"
}
else {
    "count-$Count"
}

if ($null -eq $DedupeWindow) {
    $ConfiguredWindow = $env:DING_DEDUPE_WINDOW
    if (-not [string]::IsNullOrWhiteSpace($ConfiguredWindow)) {
        $ParsedWindow = 0.0
        if ([double]::TryParse($ConfiguredWindow, [ref]$ParsedWindow)) {
            $DedupeWindow = $ParsedWindow
        }
        else {
            Write-Error "invalid DING_DEDUPE_WINDOW: $ConfiguredWindow"
            exit 2
        }
    }
    else {
        $DedupeWindow = if ($StateKey -eq "done") { 6.0 } else { 4.0 }
    }
}

$DedupeWindowSeconds = [double]$DedupeWindow
if (
    $DedupeWindowSeconds -lt 0 -or
    [double]::IsNaN($DedupeWindowSeconds) -or
    [double]::IsInfinity($DedupeWindowSeconds)
) {
    Write-Error "dedupe window must be a finite non-negative number"
    exit 2
}

$StateDir = if (-not [string]::IsNullOrWhiteSpace($env:DING_STATE_DIR)) {
    $env:DING_STATE_DIR
}
else {
    Join-Path ([System.IO.Path]::GetTempPath()) "ding-skill-$($env:USERNAME)"
}

function Get-StatePath {
    param([string]$Key)
    return Join-Path $StateDir "$Key.stamp"
}

function Test-RecentState {
    param(
        [string]$Key,
        [double]$Window
    )

    if ($Window -le 0) {
        return $false
    }

    try {
        $Marker = Get-Item -LiteralPath (Get-StatePath $Key) -ErrorAction Stop
        return ([DateTime]::UtcNow - $Marker.LastWriteTimeUtc).TotalSeconds -lt $Window
    }
    catch {
        return $false
    }
}

function Set-StateMarker {
    param([string]$Key)

    try {
        New-Item -ItemType Directory -Force $StateDir | Out-Null
        [System.IO.File]::WriteAllText((Get-StatePath $Key), [DateTime]::UtcNow.Ticks.ToString())
    }
    catch {
    }
}

function Test-Command {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Invoke-MediaPlayer {
    param([string]$Path)

    try {
        Add-Type -AssemblyName PresentationCore
        $Player = New-Object System.Windows.Media.MediaPlayer
        $Player.Open([Uri]::new($Path))
        $Player.Play()
        Start-Sleep -Milliseconds 1600
        $Player.Stop()
        $Player.Close()
        return $true
    }
    catch {
        return $false
    }
}

function Invoke-SoundPlayer {
    param([string]$Path)

    try {
        $Player = New-Object System.Media.SoundPlayer
        $Player.SoundLocation = $Path
        $Player.PlaySync()
        return $true
    }
    catch {
        return $false
    }
}

function Invoke-ExternalPlayer {
    param(
        [string]$Command,
        [string[]]$Arguments
    )

    try {
        & $Command @Arguments *> $null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Invoke-PlayOnce {
    if (Invoke-MediaPlayer $SoundPath) {
        return $true
    }

    if ((Test-Path -LiteralPath $DefaultWav -PathType Leaf) -and (Test-Path -LiteralPath $SoundPath)) {
        $WavPath = if ($SoundPath -eq $DefaultMp3) { $DefaultWav } else { $SoundPath }
        if ($WavPath.ToLowerInvariant().EndsWith(".wav") -and (Invoke-SoundPlayer $WavPath)) {
            return $true
        }
    }

    if ((Test-Command "ffplay") -and (Invoke-ExternalPlayer "ffplay" @("-nodisp", "-autoexit", "-loglevel", "quiet", $SoundPath))) {
        return $true
    }
    if ((Test-Command "mpg123") -and (Invoke-ExternalPlayer "mpg123" @("-q", $SoundPath))) {
        return $true
    }
    if ((Test-Command "mpg321") -and (Invoke-ExternalPlayer "mpg321" @("-q", $SoundPath))) {
        return $true
    }
    if ((Test-Command "mpv") -and (Invoke-ExternalPlayer "mpv" @("--no-video", "--really-quiet", $SoundPath))) {
        return $true
    }
    if ((Test-Command "mplayer") -and (Invoke-ExternalPlayer "mplayer" @("-really-quiet", "-nolirc", "-vo", "null", $SoundPath))) {
        return $true
    }
    if ((Test-Command "vlc") -and (Invoke-ExternalPlayer "vlc" @("--play-and-exit", "--intf", "dummy", $SoundPath))) {
        return $true
    }

    return $false
}

if ($DryRun) {
    $Players = New-Object System.Collections.Generic.List[string]
    $Players.Add("windows-media-player")
    if (Test-Path -LiteralPath $DefaultWav -PathType Leaf) {
        $Players.Add("sound-player")
    }
    foreach ($Name in @("ffplay", "mpg123", "mpg321", "mpv", "mplayer", "vlc")) {
        if (Test-Command $Name) {
            $Players.Add($Name)
        }
    }
    $Players.Add("console-beep")

    [pscustomobject]@{
        count = $Count
        platform = "windows"
        players = $Players
        signal = $Signal
        sound = $SoundPath
    } | ConvertTo-Json -Compress

    exit 0
}

if (Test-RecentState $StateKey $DedupeWindowSeconds) {
    exit 0
}
foreach ($Other in $DedupeAgainst) {
    if (Test-RecentState $Other $DedupeWindowSeconds) {
        exit 0
    }
}
Set-StateMarker $StateKey

for ($Index = 0; $Index -lt $Count; $Index++) {
    if (-not (Invoke-PlayOnce)) {
        try {
            [console]::Beep(880, 150)
        }
        catch {
        }
    }

    if ($Index + 1 -lt $Count) {
        Start-Sleep -Milliseconds 120
    }
}

exit 0
