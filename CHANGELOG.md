# Changelog

## 0.4.7 — 2026-11-03

### Added

- Persistent undo: the last three canvas snapshots per chat survive a page reload, so **Undo** works after reopening ComfyUI.
- Workflow protection: replacing or clearing a graph with unsaved changes always asks, even in Auto mode.
- Pinned workflow per chat: the agent adopts the workflow it starts on. If you switch tabs, mutating tools stop with a clear message instead of editing the wrong graph; the workflow chip in the composer shows the pin and allows re-pinning.
- Workflow versions: named snapshots in browser storage plus `save_workflow_version`, `list_workflow_versions` and `restore_workflow_version` (a safety version is saved before a restore).
- Crash recovery: a reply interrupted by a page reload is marked in the chat, and a persisted ComfyUI job is re-checked against the queue on load.
- Execution bar: the composer shows the running prompt, progress and a cancel button. `get_queue` reads running/pending prompts and `cancel_execution` stops the current run or removes a pending one.
- 3D support: 3D files are recognised in canvas values and attachments, a new `knowledge/3d.md` covers GLB/GLTF/OBJ/FBX/STL import, the native Load3D family and image-to-3D / 3D-to-image workflows, and 3D attachments are uploaded to the `input/3d` folder with an exact `Load3D.model_file` hint.
- Asset index and references: `list_assets` searches images, video, audio, 3D models and model files across the ComfyUI input, output, temp and model folders; the **@** menu lists them with thumbnails, and a referenced asset passes its exact path and metadata to the model.
- `inspect_media` reads images, video, audio and 3D files (dimensions, duration, frame rate, average color, GLB/GLTF/OBJ/STL/PLY structure) and attaches a preview frame when vision is on.
- Curated knowledge base: bundled docs about model families, samplers, workflow patterns, custom node packs, common errors and 3D pipelines, a `search_knowledge` tool and a short title index in the system prompt.
- Model downloads: `download_model` fetches public Hugging Face `resolve` files into a chosen models folder, resumes from a `.part` file with an HTTP Range request, verifies an optional SHA-256 checksum, checks disk space and never overwrites unless requested.
- Custom node installation: `install_custom_node` clones a public GitHub repository into `custom_nodes`, validates owner/name and branch, and reports when a restart and requirements install are needed.
- Diagnostics tools: `get_environment` (Python, PyTorch, CUDA, GPU/VRAM, disk, ComfyUI version, packages), `inspect_model` (safetensors header, tensor count, parameters, dtypes, metadata), `list_node_packs` and `set_custom_node_enabled`.
- Project memory: `remember`, `list_memory` and `forget_memory`, with saved facts injected into every turn.
- `analyze_workflow` returns purpose, models, data flow, key parameters, subgraphs, validation problems and qualitative performance notes.
- Co-work protection: the agent remembers the canvas from its previous step, detects nodes the user changed in parallel and refuses to overwrite them, then re-reads the graph and retries. Unrelated user edits are noted in the tool result instead of being reverted.
- `inspect_node` reads one node in full: every widget value, combo sample, links with the other node and slot, flags, groups and the installed definition.
- Canvas context now includes selected node ids, group titles, subgraph summaries and the viewport; `get_graph` returns them too, and numeric validation checks INT/FLOAT min/max ranges.
- Automated checks: `tests/test_helpers.py` covers provider conversion, path/URL validation, knowledge search, asset indexing, model header parsing, custom-node toggling and resumable/checksummed downloads; `tests/check_frontend.mjs` validates the module syntax, i18n key parity and tool schemas.

### Changed

- Stopping a reply no longer interrupts a ComfyUI run: the job keeps going and stays visible in the execution bar until it finishes or is cancelled explicitly.
- The system prompt documents the new reliability, version, queue, memory, environment and inspection tools, the pinned workflow, and tells the agent to preserve parallel user edits.
- Custom-node enable/disable now renames in the correct direction (the previous implementation returned "already in the requested state").
- README updated with the new tools, backend routes, 3D and co-work behavior, and restart notes.

### Notes

- Workflow versions and memory live in browser `localStorage` and are capped (20 versions, 20 memory entries).
- The new backend routes are active after a ComfyUI restart; frontend tools show a restart hint if they answer 404 before that.
- Downloads are limited to `huggingface.co` / `hf.co` public resolve URLs. Gated repositories need their token configured outside the agent.
- Installed packs are cloned only; Python requirements are reported but not installed automatically.

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
