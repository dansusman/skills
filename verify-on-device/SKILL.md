---
name: verify-on-device
description: Capture the iPad screen mirrored via WireView to verify a change on real hardware. Use when verifying UI on device (App Store screenshots, support callouts, "what's new" captures, P3 color, ProMotion, Pencil pressure) — not for simulator verification or anything requiring tap/swipe input.
---

# Verify on Device (WireView)

WireView is a closed-source macOS app that mirrors a plugged-in iPad onto the Mac screen. This skill grabs a PNG of that mirror so you can see what's on the device. **The iPad is not directly controllable from this skill — the human drives the iPad; you observe.** Some WireView UI is automatable (see below).

## When to use

- App Store screenshots, "what's new" captures, support article callouts — anything where the *real device* rendering matters (P3 color, ProMotion, real Pencil input, real PDF imports from Files).
- Confirming a visual change looks right on hardware before shipping.
- A user guide or doc where the device screen is the source of truth.

## When NOT to use

- Anything requiring tap/swipe/type **on the iPad** — use the simulator skills (`use-notability-ios`, etc.) instead.
- General iOS verification where a simulator would do — simulators are faster and scriptable.

## Prerequisites

- iPad plugged into the Mac with WireView running and mirroring.
- The process running the helper has both **Accessibility** and **Screen Recording** permission in System Settings → Privacy & Security. First failed run will tell you which is missing.

## How to use

1. Ask the user to position the iPad on the screen/state you want to capture.
2. Run the helper:

   ```bash
   ~/skills/verify-on-device/scripts/wireview-shot.sh /tmp/wireview.png
   ```

   On success it prints the output path. On failure it surfaces a specific stderr line — pass it back to the user verbatim.

3. Read the PNG back with the Read tool — image contents are returned visually.
4. Describe what you see, compare against the expected state, and tell the user what to change on the iPad for the next capture if needed.

### Modes

| Mode | Flag | What you get | How it works |
|---|---|---|---|
| Copy Screen (default) | _(none)_ | Pure iPad screen — no Mac chrome, no WireView sidebar. | Clicks WireView's **Copy Screen** toolbar button via Accessibility, then reads the PNG off the clipboard. **Clobbers the system clipboard** as a side effect. |
| Window capture | `--window` | The full WireView window including sidebar/chrome. | `screencapture -l <windowid>` on the WireView window. No clipboard side effect; useful for documenting WireView itself or when Accessibility is denied. |

## Driving WireView agentically

WireView exposes its toolbar buttons via macOS Accessibility with named descriptions, so a few WireView UI actions are scriptable from this skill:

- `Show Sidebar` — toggle the device-picker sidebar.
- `Open Screen in Preview.app` — open the current screen in Preview.
- `Save Screen` — save to a file via standard save dialog (not used by this skill; the dialog needs a human).
- `Copy Screen` — copy current iPad screen to clipboard. **This skill uses this in default mode.**
- `Record` — start/stop screen recording.

The pattern that works (clicking by description, robust to localization/reorder):

```applescript
tell application "System Events"
    tell process "WireView"
        repeat with b in (buttons of toolbar 1 of window 1)
            if (description of b) contains "<Button Name>" then
                click b
                exit repeat
            end if
        end repeat
    end tell
end tell
```

What this does *not* let you do: tap, swipe, or type on the iPad itself. WireView is a display mirror, not a remote-control bridge.

## Notes

- **Clipboard side effect.** Default mode overwrites the system clipboard. If you're doing this in the middle of a user's workflow, warn them.
- **Permissions.** The first run after install will fail and macOS will prompt for either Accessibility (default mode) or Screen Recording (`--window` mode). Grant and re-run.
- **Resolution.** Default mode captures at whatever resolution WireView's `Copy Screen` produces (full iPad native, in our testing). `--window` mode captures at nominal screen resolution.
