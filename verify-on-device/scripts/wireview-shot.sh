#!/usr/bin/env bash
# Capture the iPad screen via WireView.
#
# Default mode uses WireView's own "Copy Screen" toolbar button (clicked
# via Accessibility) and reads the resulting PNG off the clipboard. This
# yields the pure iPad screen — no Mac window chrome, no WireView sidebar.
#
# `--window` mode falls back to `screencapture -l <windowid>` on the
# WireView window itself; use when WireView Accessibility is unavailable
# or you actually want to see the WireView UI.
#
# Usage: wireview-shot.sh [--window] [output.png]
# Default output: /tmp/wireview.png
# Exit codes: 0 ok; 1 WireView not running / window not found; 2 capture failed.
#
# Side effect: default mode overwrites the system clipboard with the PNG.
set -euo pipefail

mode="copy"
out="/tmp/wireview.png"
for arg in "$@"; do
    case "$arg" in
        --window) mode="window" ;;
        -h|--help)
            grep '^# ' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *) out="$arg" ;;
    esac
done

if ! pgrep -x WireView >/dev/null; then
    echo "WireView not running" >&2
    exit 1
fi

if [[ "$mode" == "copy" ]]; then
    # Click "Copy Screen" via Accessibility. Match by description to survive
    # toolbar reordering or localization of menu labels.
    clicked=$(osascript <<'AS' 2>&1 || true
tell application "System Events"
    tell process "WireView"
        try
            set tb to toolbar 1 of window 1
        on error
            return "ERR no toolbar"
        end try
        repeat with b in (buttons of tb)
            if (description of b) contains "Copy Screen" then
                click b
                return "OK"
            end if
        end repeat
        return "ERR no Copy Screen button"
    end tell
end tell
AS
)
    if [[ "$clicked" != "OK" ]]; then
        echo "could not click Copy Screen: $clicked" >&2
        echo "hint: grant Accessibility permission to the process running this script (System Settings → Privacy & Security → Accessibility)" >&2
        exit 2
    fi

    # WireView writes the PNG to the clipboard synchronously, but give it a
    # beat to settle in case the toolbar action is async on slower machines.
    sleep 0.2

    saved=$(osascript <<AS 2>&1 || true
try
    set png to (the clipboard as «class PNGf»)
    set f to open for access POSIX file "$out" with write permission
    set eof of f to 0
    write png to f
    close access f
    return "OK"
on error e
    return "ERR " & e
end try
AS
)
    if [[ "$saved" != "OK" ]]; then
        echo "could not read PNG from clipboard: $saved" >&2
        exit 2
    fi

    echo "$out"
    exit 0
fi

# --window mode: capture the WireView window itself by id.
# Resolve the CGWindowID via a tiny Swift one-liner (AppleScript doesn't expose it).
window_id=$(/usr/bin/swift - <<'SWIFT'
import CoreGraphics
import Foundation
let info = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
let mine = info.filter { ($0[kCGWindowOwnerName as String] as? String) == "WireView" }
func area(_ w: [String: Any]) -> CGFloat {
    guard let b = w[kCGWindowBounds as String] as? [String: CGFloat] else { return 0 }
    return (b["Width"] ?? 0) * (b["Height"] ?? 0)
}
if let best = mine.max(by: { area($0) < area($1) }),
   let id = best[kCGWindowNumber as String] as? Int {
    print(id)
}
SWIFT
)
if [[ -z "$window_id" ]]; then
    echo "WireView window not found" >&2
    exit 1
fi

if ! /usr/sbin/screencapture -l "$window_id" -o -x "$out"; then
    echo "screencapture failed — grant Screen Recording permission to the process running this script" >&2
    exit 2
fi
if [[ ! -f "$out" ]]; then
    echo "screencapture wrote no file (Screen Recording permission likely denied)" >&2
    exit 2
fi
echo "$out"
