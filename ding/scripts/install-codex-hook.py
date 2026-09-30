#!/usr/bin/env python3
"""Install or remove the Ding Codex hook handlers without replacing user hooks."""

from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys


OWNERSHIP_TOKEN = "codex-hook.py"
EVENT_PLANS = {
    "PermissionRequest": {
        "matcher": None,
        "signal": "confirm",
        "timeout": 10,
        "async": False,
    },
    "PreToolUse": {
        "matcher": "^request_user_input$",
        "signal": "confirm",
        "timeout": 10,
        "async": False,
    },
    "Stop": {
        "matcher": None,
        "signal": "done",
        "timeout": 20,
        "async": True,
    },
}


def fail(message: str) -> None:
    print(f"ding-codex-hook: {message}", file=sys.stderr)
    raise SystemExit(2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install or remove the Ding Codex hooks.",
    )
    parser.add_argument(
        "action",
        nargs="?",
        choices=("install", "uninstall", "status"),
        default="install",
    )
    parser.add_argument(
        "--home",
        help="Codex home directory. Defaults to CODEX_HOME or ~/.codex.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resulting hooks.json without writing it.",
    )
    return parser.parse_args()


def codex_home(value: str | None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    configured = os.environ.get("CODEX_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def quoted_posix(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def quoted_windows(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def hook_commands(script: Path) -> tuple[str, str]:
    python = Path(sys.executable).resolve()
    posix = quoted_posix([str(python), str(script)])

    if os.name == "nt":
        windows_command = [str(python), str(script)]
    else:
        windows_command = ["py", "-3", str(script)]
    return posix, quoted_windows(windows_command)


def build_handler(script: Path, plan: dict[str, object]) -> dict[str, object]:
    command, command_windows = hook_commands(script)
    return {
        "type": "command",
        "command": command,
        "commandWindows": command_windows,
        "timeout": plan["timeout"],
        "async": plan["async"],
        "statusMessage": f"ding {plan['signal']}",
    }


def is_owned_handler(handler: object) -> bool:
    if not isinstance(handler, dict) or handler.get("type") != "command":
        return False
    return any(
        isinstance(handler.get(field), str)
        and OWNERSHIP_TOKEN in handler[field]
        for field in ("command", "commandWindows")
    )


def read_document(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"hooks": {}}

    try:
        document = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot read {path}: {error}")

    if not isinstance(document, dict):
        fail(f"{path} must contain a JSON object")
    hooks = document.get("hooks")
    if hooks is None:
        document["hooks"] = {}
    elif not isinstance(hooks, dict):
        fail(f"{path} field 'hooks' must be an object")
    return document


def without_owned_handlers(hooks: dict[str, object]) -> dict[str, object]:
    result = copy.deepcopy(hooks)
    for event in EVENT_PLANS:
        groups = result.get(event)
        if groups is None:
            continue
        if not isinstance(groups, list):
            fail(f"hooks.{event} must be an array")

        kept_groups: list[object] = []
        for group in groups:
            if not isinstance(group, dict):
                fail(f"hooks.{event} entries must be objects")
            handlers = group.get("hooks")
            if handlers is None:
                kept_groups.append(group)
                continue
            if not isinstance(handlers, list):
                fail(f"hooks.{event}[].hooks must be an array")

            kept_handlers = [
                handler for handler in handlers if not is_owned_handler(handler)
            ]
            if kept_handlers:
                updated = copy.deepcopy(group)
                updated["hooks"] = kept_handlers
                kept_groups.append(updated)

        if kept_groups:
            result[event] = kept_groups
        else:
            result.pop(event, None)
    return result


def installed_hooks(
    current: dict[str, object],
    script: Path,
) -> dict[str, object]:
    hooks = without_owned_handlers(current)
    for event, plan in EVENT_PLANS.items():
        groups = hooks.get(event)
        if groups is None:
            groups = []
        if not isinstance(groups, list):
            fail(f"hooks.{event} must be an array")

        group: dict[str, object] = {"hooks": [build_handler(script, plan)]}
        if plan["matcher"] is not None:
            group["matcher"] = plan["matcher"]
        groups.append(group)
        hooks[event] = groups
    return hooks


def matching_paths(handler: object) -> bool:
    return is_owned_handler(handler)


def print_status(hooks: dict[str, object]) -> None:
    for event in EVENT_PLANS:
        groups = hooks.get(event)
        count = 0
        if isinstance(groups, list):
            for group in groups:
                if not isinstance(group, dict):
                    continue
                handlers = group.get("hooks")
                if isinstance(handlers, list):
                    count += sum(matching_paths(handler) for handler in handlers)
        print(f"{event}: {count}")


def write_document(path: Path, document: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_suffix(path.suffix + ".ding.bak")
        shutil.copy2(path, backup)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    home = codex_home(args.home)
    hooks_path = home / "hooks.json"
    script = (Path(__file__).resolve().parent / "codex-hook.py").resolve()
    document = read_document(hooks_path)
    hooks = document["hooks"]
    assert isinstance(hooks, dict)

    if args.action == "status":
        print(f"hooks file: {hooks_path}")
        print_status(hooks)
        return 0

    if args.action == "install":
        updated = installed_hooks(hooks, script)
    else:
        updated = without_owned_handlers(hooks)

    output = copy.deepcopy(document)
    output["hooks"] = updated
    changed = output != document

    if args.dry_run:
        print(
            json.dumps(
                {
                    "changed": changed,
                    "path": str(hooks_path),
                    "hooks": updated,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if changed:
        write_document(hooks_path, output)
        print(f"{args.action}: {hooks_path}")
    else:
        print(f"{args.action}: no changes ({hooks_path})")

    if args.action == "install":
        print("Trust the new/changed hook inside Codex before it can run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
