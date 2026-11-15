# Changelog

All notable changes to **Kisukisu (கிசுகிசு)** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-11-15 — Initial Release

### Features & Highlights
- **Obsidian Presenter HUD & Reader**: Floating teleprompter interface featuring glass-like aesthetics, rounded pill geometry, customizable opacity, and smooth continuous scrolling.
- **Windows Stealth Screen-Sharing Shield**: Integrated native `WDA_EXCLUDEFROMCAPTURE` to keep private speaker notes invisible during Google Meet, Zoom, and Teams screen sharing.
- **Cross-Platform Compatibility**: Fully functional across Windows, macOS, and Linux with native font fallbacks and platform-appropriate windowing behaviors.
- **Apple Dynamic Island Mini-Pill & Compact Mode**: Ultra-compact minimized capsule mode displaying current slide, time, and active cue.
- **Script Library Hub**: Central management window with instant search, creation, editing, outline navigation, and file import (`.md`, `.txt`, `.docx`, `.pdf`).
- **Universal Document Parser**: Automatically extracts headers, presenter cues (`[CUE: ...]`), live prompts, and spoken text (`SAY:`).
- **Multilingual & Tamil Unicode Support**: Native rendering of Tamil (`கிசுகிசு`), Hindi, Telugu, and international UTF-8 scripts.
- **Appearance Studio**: Real-time theme customization (Midnight Obsidian, OLED Black, Paper White, Warm Cream, Cyber Terminal), custom font families, font sizes, line spacing, and color palette import/export.
- **Local-First & Zero-Trust Privacy**: Zero network calls, zero telemetry, zero cloud tracking. All scripts and settings stay 100% on your local machine.
- **Automated Test Suite**: Comprehensive headless unit test coverage for config hardening, geometry validation, document parsing, shortcuts, and script management.
