# Changelog

## 0.4.9 — 2026-11-09

### Added

- **ComfyUI MCP Bridge**: Official ComfyUI MCP (`comfy.org/mcp`, package `comfy-mcp`) integrated directly as the agent bridge to ComfyUI canvas and execution. Added `/crazy_agent/mcp/status`, `/crazy_agent/mcp/tools`, `/crazy_agent/mcp/call`, and `/crazy_agent/mcp/install` routes.
- **First Startup Wizard**: Interactive 4-step modal onboarding on first launch:
  1. Theme selection (themes grid, dark/light mode toggle, and interface language).
  2. Provider & Model setup (preset picker, base URL, API key, model loader, vision toggle).
  3. Personas setup (Agent name and User address name).
  4. ComfyUI MCP verification and one-click installer (mandatory step ensuring `comfy-mcp` bridge is ready).
- **llama.cpp Provider**: Added dedicated `llamacpp` provider and local preset (`http://127.0.0.1:8080/v1`). Queries `n_ctx` from llama.cpp server `/props` automatically for context budgeting.
- **Multimodal Audio and Video for llama.cpp**:
  - Full support for video input (`video_url`) and audio input (`input_audio`) when provider is `llamacpp` and the model supports multimodal capabilities.
  - Automatic modality detection from model architecture/name (e.g., Qwen2-VL, Qwen2.5-VL, MiniCPM-V, Gemma-3, Qwen2-Audio, Whisper, Omni) and `/props` modalities.
  - Informative notifications when a text-only model is used with video/audio attachments.
  - Video thumbnail generation and automatic file uploads to the ComfyUI input directory.
- Model readiness check: the new `check_model_setup` tool looks at a model before it is used. It reports the parts of the family (diffusion model, text encoders, VAE), which of them are installed in the ComfyUI model folders, which are missing, the loader node and the models folder for each part, and the prompt style of the family. The agent calls it before it builds or runs a workflow, so a missing text encoder or VAE is reported instead of a workflow that cannot run.
- A prompting guide in the bundled knowledge base (`knowledge/model-prompting.md`): how to write a prompt for each family (one coherent paragraph for FLUX and Z-Image, quoted text and layout for Qwen-Image, a direct instruction for the editors, no negative prompt where the sampler ignores it) and which family fits which task.
- Batch generation: `generate` and `run_workflow` take a `batch` of 1-8 shots, and `create_workflow` sets the `batch_size` of the latent node. When the workflow has a latent node the shots run as one batch, otherwise several prompts are queued with consecutive seeds. The job bar shows how many shots are done, and the result lists every file.
- Smooth node appearance: nodes the agent creates now fade and scale in on the canvas instead of popping up, with a short stagger so a batch of new nodes arrives one after another.

### Changed

- The change highlight no longer repaints the node. Created and changed nodes get a pulsing outline instead, and the color of that outline comes from the active panel theme: green for a new node, amber for a changed one and the theme accent for the rest. The node keeps its own title and body colors, so the graph stays readable and a saved workflow is not affected.
- Negative prompts that have no field on canvas are safely skipped without failing generation runs.
- Thought signature persistence and reply support for Gemini 3 / Google AI Studio models.

## 0.4.8 — 2026-11-04
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
- The system prompt now asks the model to check the model first (parts, missing files, loader nodes, prompt style) and to use the batch parameter instead of queueing several runs by hand.

### Notes

- The compatibility route is active after a ComfyUI restart; before that the panel still runs the browser-side checks and reports the missing backend.
- The pre-flight route needs a ComfyUI restart as well. Until then the plan card is shown without the availability check.
- The context window check, the `model_context` route and the token-aware trimming need a ComfyUI restart. The partial node search, the retry after an empty search, the image drop and the empty-reply rescue work in the browser without it.
- Undo history in the image editor is kept in memory for the open editor only.
- The node appearance animation and the themed outline are frontend changes and work after a page reload; no ComfyUI restart is needed.

### Fixed

- A negative prompt with no place on the canvas no longer breaks the run. `set_prompt` used to fail when the workflow had no negative prompt field, so `generate` never produced an image and the agent called it again and again with the same negative prompt. The negative prompt is now skipped with a note that tells the agent to leave it out or to add a text node for it, the positive prompt is still applied and the generation goes through.
- The system prompt now says what to do when there is no negative prompt field: do not call the tool again with the same negative prompt, either drop it (many models ignore it, especially at CFG 1) or add a text node and link it to the sampler's negative input.
- Google AI Studio no longer rejects a tool call with "Function call is missing a thought_signature in functionCall parts". The Gemini thought signature is read from the response and sent back with the function call, in the same `extra_content.google.thought_signature` shape the API expects.
- Tool calls that arrive without an `index` (the Gemini compatibility layer often omits it) no longer merge into a single call, so parallel tool calls stay separate.

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
