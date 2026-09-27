#!/usr/bin/env python3
"""Play the bundled ding once or three times across common desktop platforms."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


COUNT_ALIASES = {
    "confirm": 1,
    "once": 1,
    "1": 1,
    "done": 3,
    "complete": 3,
    "3": 3,
}


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
        help="Print the selected player and sound without playing.",
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
            except ValueError as exc:
                choices = ", ".join(sorted(COUNT_ALIASES))
                raise SystemExit(
                    f"unknown signal {args.signal!r}; choose {choices}, or a positive integer"
                ) from exc

    if count < 1:
        raise SystemExit("count must be at least 1")
    return count


def resolve_sound(value: str | None) -> Path:
    if value:
        sound = Path(value).expanduser().resolve()
    else:
        sound = (Path(__file__).resolve().parent.parent / "assets" / "ding.mp3").resolve()

    if not sound.is_file():
        raise SystemExit(f"sound file not found: {sound}")
    return sound


def powershell_command(sound: Path) -> list[str] | None:
    shell = shutil.which("powershell") or shutil.which("pwsh")
    if not shell:
        return None

    uri = sound.as_uri().replace("'", "''")
    script = (
        "$ErrorActionPreference='Stop';"
        "Add-Type -AssemblyName PresentationCore;"
        "$player=New-Object System.Windows.Media.MediaPlayer;"
        f"$player.Open([Uri]::new('{uri}'));"
        "$player.Play();"
        "Start-Sleep -Milliseconds 1600;"
        "$player.Stop();"
        "$player.Close();"
    )
    return [shell, "-NoProfile", "-NonInteractive", "-Command", script]


def player_commands(sound: Path) -> list[list[str]]:
    path = str(sound)
    commands: list[list[str]] = []

    if sys.platform == "darwin":
        commands.append(["afplay", path])

    if os.name == "nt":
        command = powershell_command(sound)
        if command:
            commands.append(command)

    commands.extend(
        [
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path],
            ["mpg123", "-q", path],
            ["paplay", path],
            ["cvlc", "--play-and-exit", "--intf", "dummy", path],
            ["mpv", "--no-video", "--really-quiet", path],
            ["play", "-q", path],
        ]
    )
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


def main() -> int:
    args = parse_args()
    count = resolve_count(args)
    sound = resolve_sound(args.sound)
    players = available_players(sound)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "count": count,
                    "signal": args.signal,
                    "sound": str(sound),
                    "players": players,
                },
                ensure_ascii=False,
            )
        )
        return 0

    if not players:
        terminal_bell(count)
        return 0

    failed = False
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
        failed = failed or not played

    if failed:
        terminal_bell(count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
