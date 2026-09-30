#!/usr/bin/env python3
"""Map Codex hook events to the bundled Ding signals."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def hook_decision(payload: object) -> tuple[str | None, str]:
    if not isinstance(payload, dict):
        return None, "invalid-payload"

    event = payload.get("hook_event_name")
    if event == "PermissionRequest":
        return "confirm", "permission-request"

    if event == "PreToolUse":
        if payload.get("tool_name") == "request_user_input":
            return "confirm", "request-user-input"
        return None, "unmatched-tool"

    if event == "Stop":
        if payload.get("stop_hook_active") is True:
            return None, "stop-hook-continuation"
        return "done", "turn-stop"

    return None, "unsupported-event"


def dry_run_result(payload: object, signal: str | None, reason: str) -> None:
    event = payload.get("hook_event_name") if isinstance(payload, dict) else None
    tool_name = payload.get("tool_name") if isinstance(payload, dict) else None
    print(
        json.dumps(
            {
                "event": event,
                "reason": reason,
                "signal": signal,
                "tool_name": tool_name,
            },
            ensure_ascii=False,
        )
    )


def play(signal: str) -> None:
    command = [
        sys.executable,
        str(skill_root() / "scripts" / "ding.py"),
        signal,
        "--dedupe-window",
        "6" if signal == "done" else "4",
        "--dedupe-against",
        "confirm" if signal == "done" else "done",
    ]
    try:
        subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def main() -> int:
    if os.environ.get("DING_HOOK_DISABLE") == "1":
        return 0

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError, UnicodeError):
        return 0

    signal, reason = hook_decision(payload)
    if os.environ.get("DING_HOOK_DRY_RUN") == "1":
        dry_run_result(payload, signal, reason)
        return 0

    if signal:
        play(signal)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
