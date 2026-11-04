# Changelog

## 0.4.8 — 2026-11-04

### Added

- Themes in settings as preview cards: **ComfyUI** (the existing look), **Claude** (warm cream with an orange accent, or the dark clay-grey version from the reference), **Luxurious** (gold on ivory or black, with a diamond-shaped send button, gold shine on primary buttons and a gem on user messages) and **Colors** (frosted transparent panels with pill-shaped controls over a drifting orange and sage glow). A switch below the cards sets the light or dark version of the selected theme; the ComfyUI theme keeps ComfyUI's own colors. Both choices are saved in the browser.
- Agent and user names in settings: the assistant's name replaces the header title and is used in its replies, and the user name tells the assistant how to address you. Both names are stored in the local config.
- Settings are split into three tabs: **AI** (provider, model, limits, permissions, search), **Customization** (language, themes, names, skills) and **Logs** (chat export, server log, performance, extension updates and compatibility). The active tab is marked by a pill that slides to the new position, and the panel content slides in from the direction of the switch.
- The panel opens with a smooth fade, slide and scale, and the chat and settings views rise into place instead of snapping.
- Image editor before sending: click the pencil on an image attachment to draw, crop, add text, rotate left/right, undo/redo and reset, then apply the result back to the attachment. Works with mouse, touch and pen; Escape and Ctrl+Z / Ctrl+Shift+Z are supported.
- Compatibility report: a new **Compatibility** block in settings plus the `GET /crazy_agent/compatibility` route check Python, aiohttp, PyTorch, the ComfyUI version, the frontend build, extension files, model folders and the browser-side APIs (`app.graph`, `graphToPrompt`, `queuePrompt`, sidebar, workflow manager, LiteGraph, viewport), and flag every item as ok, warning or failure.
- Plan pre-flight: in Plan mode every node type the plan needs is checked before the plan is shown. The plan card marks each one as ready, pack installed but not registered, pack missing or node name unknown, and offers installed alternatives for the unknown ones. A plan that needs a new pack is split into a setup phase (install or enable the pack, restart ComfyUI) and a build phase, and the roadmap starts with the setup steps.
- Attached files become real files: an image or 3D file added in the chat is uploaded into the ComfyUI input folder (3D files into `input/3d`) right away, and the chat shows the exact path under the file.
- New `apply_attachment` tool puts an attached file into a loader widget by node id, so an attached photo can be loaded into the workflow without a manual upload. Called without a node id it creates the matching loader node (Load Image for an image, Load 3D for a 3D file), and it reuses a loader that already holds the file instead of adding a second one.
- A "+" button on an attached file in the chat adds the file to the canvas with one click: an image goes into a Load Image node and a 3D model into a Load 3D node, where ComfyUI renders it.
- The canvas context now lists every node type with all of its input slots, connected or not, plus what is plugged into which slot. The agent reads the graph from those blocks instead of opening media files.
- Context window handling: the panel keeps the last two images and counts images in the context budget, the backend measures the prompt against the model's loaded context window, and a new `GET /crazy_agent/model_context` route reports that window.
- Node search by partial words: `find_nodes` matches class names, display names, categories, the search aliases ComfyUI ships, input names and the file names in the loader lists, so "3d", "glb", "loader" or "checkpoint" find something. Native nodes rank first, every hit says whether it is a full or a partial match, and a query with no hit returns the closest node names instead of a dead end.
- A native node reference in the bundled knowledge base (`knowledge/nodes.md`): it maps jobs to the node that does them, including the 3D loader (`Load3D`, shown as **Load 3D & Animation**), the image loader (`LoadImage`), checkpoint, sampler, latent, conditioning, image editing and output nodes.
- Context overflow recovery: when a request does not fit the loaded context window, the backend trims the oldest turns instead of only dropping images, and the panel summarizes the conversation and retries.

### Changed

- The frosted theme is called **Colors** now; a browser that still had the old name stored keeps the same look, the saved value is migrated automatically.
- Model downloads follow Hugging Face redirects manually and validate every hop: only HTTPS, no embedded credentials and only the `huggingface.co` / `hf.co` hosts plus their known CDN hosts. Checksum, resume, disk-space and no-overwrite behaviour is unchanged.
- Node installation is stricter: repository names cannot start with `.` or `-`, the branch is validated, clones run with `--depth 1 --single-branch --no-tags --no-recurse-submodules` and without prompts, and the checkout is staged in a hidden folder and moved into place only after it succeeds.
- The frontend contract check now also verifies the theme cards, preview thumbnails and light/dark lever against the stylesheet and i18n, the image editor functions and styles, the compatibility functions and route, the download redirect allowlist and the hardened clone flags.
- The backend tests cover the context budget: the prompt estimate, the image trimming and the fit against the loaded context window.
- `propose_plan` takes an optional list of node types, so the pre-flight knows which nodes the plan needs. The plan-mode prompt asks for it.
- The pre-flight route reads the installed packs on disk, compares them with the registered nodes and answers with the state of every requested node type. Pack sources are scanned once in the background at startup and cached per pack.
- Conversation compaction is available in every mode, not only in Plan, and triggers on the context budget instead of a message count.
- When the model answers with an empty reply, the agent drops the older images, says so in the chat and retries once instead of reporting "empty reply after several attempts".
- A request that does not fit the loaded context window is trimmed first: the oldest turns are dropped, the goal and the recent work stay. Only when that is still not enough the request is refused with the required and available token counts instead of being sent and failing silently.
- The system prompt tells the model that an attached file is already uploaded, that its exact path goes into the loader widget, that an image belongs in a Load Image node and a 3D model in a Load 3D node, and that the graph structure comes from the canvas node blocks.
- The system prompt names the node for each job and forbids guessing class names: there is no "load glb" node, the 3D loader is `Load3D` ("Load 3D & Animation"), and an empty search means searching again with another word.
- After a node search that found nothing, the agent is asked to search again with a shorter word instead of answering with a made-up class name.
- The panel reads the real loaded context window from the backend and compacts the conversation earlier, instead of relying on a fixed character budget.

### Notes

- The compatibility route is active after a ComfyUI restart; before that the panel still runs the browser-side checks and reports the missing backend.
- The pre-flight route needs a ComfyUI restart as well. Until then the plan card is shown without the availability check.
- The context window check, the `model_context` route and the token-aware trimming need a ComfyUI restart. The partial node search, the retry after an empty search, the image drop and the empty-reply rescue work in the browser without it.
- Undo history in the image editor is kept in memory for the open editor only.

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
