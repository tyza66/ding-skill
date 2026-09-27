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

## Run

Resolve `scripts/ding.py` relative to the directory containing this `SKILL.md`, then replace `DING_SKILL_DIR` in the examples with that directory.

```bash
python3 "$DING_SKILL_DIR/scripts/ding.py" confirm
python3 "$DING_SKILL_DIR/scripts/ding.py" done
```

On Windows, use the available Python launcher:

```powershell
py -3 "$env:DING_SKILL_DIR\scripts\ding.py" confirm
py -3 "$env:DING_SKILL_DIR\scripts\ding.py" done
```

The script selects an installed system audio player and falls back to a terminal bell when audio playback is unavailable. A custom audio file can be supplied with `--sound <path>` or `DING_SOUND=<path>`.
