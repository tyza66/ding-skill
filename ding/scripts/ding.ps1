[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Signal = "confirm",

    [int]$Count = 0,

    [string]$Sound = "",

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
