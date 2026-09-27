#!/usr/bin/env python3
"""Play the bundled ding once or three times across common desktop platforms."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
from urllib.parse import quote


COUNT_ALIASES = {
    "confirm": 1,
    "once": 1,
    "1": 1,
    "done": 3,
    "complete": 3,
    "3": 3,
}


def fail(message: str) -> None:
    print(f"ding: {message}", file=sys.stderr)
    raise SystemExit(2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Play the bundled ding once or three times.",
    )
    parser.add_argument(
        "signal",
        nargs="?",
        default="confirm",
        help="confirm/once (1 ding), done/complete (3 dings), or a positive count",
    )
    parser.add_argument(
        "--count",
        type=int,
        help="Override the number of dings.",
    )
    parser.add_argument(
        "--sound",
        default=os.environ.get("DING_SOUND"),
        help="Audio file to play. Defaults to assets/ding.mp3.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the selected players and sound without playing.",
    )
    return parser.parse_args()


def resolve_count(args: argparse.Namespace) -> int:
    if args.count is not None:
        count = args.count
    else:
        count = COUNT_ALIASES.get(args.signal.lower())
        if count is None:
            try:
                count = int(args.signal)
            except ValueError:
                choices = ", ".join(sorted(COUNT_ALIASES))
                fail(
                    f"unknown signal {args.signal!r}; choose {choices}, or a positive integer"
                )

    if count < 1:
        fail("count must be at least 1")
    return count


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve_sound(value: str | None) -> Path:
    if value:
        sound = Path(value).expanduser().resolve()
    else:
        sound = (skill_root() / "assets" / "ding.mp3").resolve()

    if not sound.is_file():
        fail(f"sound file not found: {sound}")
    return sound


def resolved_wav(sound: Path) -> Path | None:
    default_mp3 = (skill_root() / "assets" / "ding.mp3").resolve()
    wav = (skill_root() / "assets" / "ding.wav").resolve()
    if sound == default_mp3 and wav.is_file():
        return wav
    if sound.suffix.lower() == ".wav" and sound.is_file():
        return sound
    return None


def is_windows_host_bridge() -> bool:
    system = platform.system().lower()
    release = platform.release().lower()
    return (
        "microsoft" in release
        or "microsoft" in system
        or "wsl" in system
        or "msys" in system
        or "cygwin" in system
        or "MINGW" in os.environ.get("MSYSTEM", "")
    )


def to_windows_path(path: Path) -> str | None:
    converter = shutil.which("wslpath") or shutil.which("cygpath")
    if not converter:
        return None

    result = subprocess.run(
        [converter, "-w", str(path)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    converted = result.stdout.strip()
    return converted or None


def powershell_uri(path: str) -> str:
    normalized = path.replace("\\", "/")
    return "file:///" + quote(normalized.lstrip("/"), safe="/:")


def powershell_command(
    sound: Path,
    wav: Path | None,
    shell: str | None = None,
) -> list[str] | None:
    shell = shell or shutil.which("powershell") or shutil.which("pwsh")
    if not shell:
        return None

    if is_windows_host_bridge() and os.name != "nt":
        sound_path = to_windows_path(sound)
        wav_path = to_windows_path(wav) if wav else None
        if not sound_path:
            return None
    else:
        sound_path = str(sound)
        wav_path = str(wav) if wav else None

    uri = powershell_uri(sound_path).replace("'", "''")
    wav_literal = (wav_path or "").replace("'", "''")
    script = (
        "$ErrorActionPreference='Stop';"
        "try {"
        "Add-Type -AssemblyName PresentationCore;"
        "$player=New-Object System.Windows.Media.MediaPlayer;"
        f"$player.Open([Uri]::new('{uri}'));"
        "$player.Play();"
        "Start-Sleep -Milliseconds 1600;"
        "$player.Stop();$player.Close();"
        "exit 0"
        "} catch {};"
    )
    if wav_path:
        script += (
            "try {"
            "$player=New-Object System.Media.SoundPlayer;"
            f"$player.SoundLocation='{wav_literal}';"
            "$player.PlaySync();"
            "exit 0"
            "} catch {};"
        )
    script += "exit 1"

    return [
        shell,
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        script,
    ]


def player_commands(sound: Path) -> list[list[str]]:
    path = str(sound)
    wav = resolved_wav(sound)
    commands: list[list[str]] = []

    if sys.platform == "darwin":
        commands.append(["afplay", path])

    if os.name == "nt":
        command = powershell_command(sound, wav)
        if command:
            commands.append(command)

    commands.extend(
        [
            ["pw-play", path],
            ["paplay", path],
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path],
            ["mpg123", "-q", path],
            ["mpg321", "-q", path],
            ["mpv", "--no-video", "--really-quiet", path],
            ["mplayer", "-really-quiet", "-nolirc", "-vo", "null", path],
            ["cvlc", "--play-and-exit", "--intf", "dummy", path],
            ["vlc", "--play-and-exit", "--intf", "dummy", path],
            ["gst-play-1.0", "--quiet", path],
            ["play", "-q", path],
        ]
    )

    if wav:
        commands.append(["aplay", "-q", str(wav)])

    if is_windows_host_bridge() and os.name != "nt":
        command = powershell_command(
            sound,
            wav,
            shell=shutil.which("powershell.exe") or shutil.which("pwsh.exe"),
        )
        if command:
            commands.append(command)

    return commands


def available_players(sound: Path) -> list[list[str]]:
    return [
        command
        for command in player_commands(sound)
        if shutil.which(command[0])
    ]


def terminal_bell(count: int) -> None:
    bell = "\a" * count
    try:
        with open("/dev/tty", "w", encoding="utf-8") as tty:
            tty.write(bell)
            tty.flush()
    except OSError:
        sys.stdout.write(bell)
        sys.stdout.flush()


def play_wav_with_winsound(wav: Path, count: int) -> bool:
    if os.name != "nt":
        return False

    try:
        import winsound

        for index in range(count):
            if index:
                time.sleep(0.12)
            winsound.PlaySound(str(wav), winsound.SND_FILENAME)
        return True
    except (ImportError, RuntimeError, OSError):
        return False


def main() -> int:
    args = parse_args()
    count = resolve_count(args)
    sound = resolve_sound(args.sound)
    players = available_players(sound)
    wav = resolved_wav(sound)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "count": count,
                    "host_bridge": is_windows_host_bridge(),
                    "platform": platform.platform(),
                    "players": players,
                    "signal": args.signal,
                    "sound": str(sound),
                },
                ensure_ascii=False,
            )
        )
        return 0

    for index in range(count):
        if index:
            time.sleep(0.12)
        played = False
        for command in players:
            result = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if result.returncode == 0:
                played = True
                break
        if not played and wav:
            played = play_wav_with_winsound(wav, 1)
        if not played:
            terminal_bell(1)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
