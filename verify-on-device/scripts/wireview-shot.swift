#!/usr/bin/env swift
import AppKit
import CoreGraphics

// Capture the WireView mirror window (iPad mirrored to Mac) to a PNG by
// finding its window id via CGWindowListCopyWindowInfo and shelling out to
// `screencapture -l <id>`. We use the system tool rather than ScreenCaptureKit
// because it's synchronous, has no entitlement requirements beyond Screen
// Recording (which the user has already granted for WireView itself), and
// `CGWindowListCreateImage` is obsoleted in macOS 15+.
//
// Usage: wireview-shot.swift [output.png]
//   Default output: /tmp/wireview.png
// Exit codes:
//   0 success
//   1 WireView not running / window not found
//   2 capture failed (likely missing Screen Recording permission)

let outputPath = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "/tmp/wireview.png"
let targetApp = "WireView"

func die(_ code: Int32, _ msg: String) -> Never {
    FileHandle.standardError.write((msg + "\n").data(using: .utf8)!)
    exit(code)
}

guard let infoList = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] else {
    die(2, "could not enumerate windows")
}

let candidates = infoList.filter { ($0[kCGWindowOwnerName as String] as? String) == targetApp }
if candidates.isEmpty {
    die(1, "\(targetApp) window not found (is the app running and mirroring?)")
}

func area(_ w: [String: Any]) -> CGFloat {
    guard let b = w[kCGWindowBounds as String] as? [String: CGFloat] else { return 0 }
    return (b["Width"] ?? 0) * (b["Height"] ?? 0)
}

let best = candidates.max(by: { area($0) < area($1) })!
guard let windowID = best[kCGWindowNumber as String] as? CGWindowID else {
    die(2, "window has no id")
}

let proc = Process()
proc.launchPath = "/usr/sbin/screencapture"
// -l: capture window by id; -o: omit window shadow; -x: silent (no sound).
proc.arguments = ["-l", String(windowID), "-o", "-x", outputPath]
let errPipe = Pipe()
proc.standardError = errPipe
do {
    try proc.run()
} catch {
    die(2, "could not launch screencapture: \(error)")
}
proc.waitUntilExit()

if proc.terminationStatus != 0 {
    let errData = errPipe.fileHandleForReading.readDataToEndOfFile()
    let errStr = String(data: errData, encoding: .utf8) ?? ""
    die(2, "screencapture failed (exit \(proc.terminationStatus)): \(errStr) — grant Screen Recording permission to the process running this script")
}

if !FileManager.default.fileExists(atPath: outputPath) {
    die(2, "screencapture reported success but wrote no file (Screen Recording permission likely denied)")
}

print(outputPath)
