---
name: ding
description: Play one bundled ding before asking the user to decide, authorize, or clarify, and play three dings when the requested work is fully complete. Use when the user wants audible confirmation and completion signals across an AI session.
---

# Ding

Use the bundled microwave-style sound as a short audible status signal. Do not add spoken narration or explain the sound in the response.

## Signals

- Run `confirm` exactly once immediately before a user-facing message that needs the user to choose, approve, authorize, or provide missing information. If one turn contains several related questions, play one ding before the combined question.
- Run `done` exactly once immediately before the final response for a task that is fully complete. This plays three dings in sequence.
- Do not use `done` for progress updates, partial results, tool-level errors, interruptions, or a task that is blocked while waiting for the user. Use `confirm` for a blocked decision.
- If the user asks to mute notifications or continue in silence, do not play either signal.

## Codex hooks

The optional Codex hook integration maps `PermissionRequest` and the `request_user_input` tool to `confirm`, and a completed `Stop` event to `done`. When that integration is installed, keep using the manual rules above in other AI tools and for user-facing questions that do not use `request_user_input`.

The launchers suppress a duplicate signal when the same event was already played within a few seconds. This lets a manual call and the Codex hook coexist without intentionally playing the same decision or completion cue twice. Hook playback still requires the hook to be trusted in Codex.

## Run

Resolve the `scripts` directory relative to the directory containing this `SKILL.md`, then replace `DING_SKILL_DIR` in the examples with that directory. Use the first launcher that works:

- macOS, Linux, WSL, Git Bash, MSYS2, and Cygwin:

```bash
sh "$DING_SKILL_DIR/scripts/ding" confirm
sh "$DING_SKILL_DIR/scripts/ding" done
```

- Windows Command Prompt:

```bat
"%DING_SKILL_DIR%\scripts\ding.cmd" confirm
"%DING_SKILL_DIR%\scripts\ding.cmd" done
```

- Windows PowerShell:

```powershell
& "$env:DING_SKILL_DIR\scripts\ding.ps1" -Signal confirm
& "$env:DING_SKILL_DIR\scripts\ding.ps1" -Signal done
```

- Python fallback when a native launcher is unavailable:

```bash
python3 "$DING_SKILL_DIR/scripts/ding.py" confirm
python3 "$DING_SKILL_DIR/scripts/ding.py" done
```

All launchers try multiple system audio backends and fall back to the terminal bell when desktop audio is unavailable. A custom audio file can be supplied with `--sound <path>` or `DING_SOUND=<path>`.

For Codex hook installation and trust details, read the repository `README.md`.
