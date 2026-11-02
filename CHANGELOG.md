# Changelog

## 0.4.5 — 2026-11-02

### Added

- Plan and Fast modes in the composer, with the run permission (Ask / Auto) moved to a compact switch below.
- Plan mode: plan proposals, a live roadmap, path re-checking after results and errors, more frequent questions for important choices, and goal-preserving context compression for long tasks.
- Update checking on page load with a notification sound and banner. "Check GitHub on start" is on by default; "Update automatically" is off by default.
- Manual "Check now" and "Update manually" buttons in settings.
- Automatic canvas check after every edit: unavailable combo values and missing media files are reported to the model immediately, and tools return the widget values actually applied.
- Canvas validation now detects media files that do not exist in the input folder instead of only checking the declared options.

### Changed

- The model is instructed to fix reported canvas problems before running or claiming success.
- README updated for the new modes, update settings and canvas checks.

### Fixed

- The model could report a successful Load Image update when the file was not actually available; the edit is now verified and the failure is surfaced in the tool result.
