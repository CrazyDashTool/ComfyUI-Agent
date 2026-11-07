<img width="2172" height="724" alt="comfyagentlogo" src="https://github.com/user-attachments/assets/6b4b0ce9-dc37-4bc6-a43d-fc2a255ab26a" />
# ComfyUI-Agent

An in-app AI agent for ComfyUI: a sidebar chat that sees the live canvas, builds and edits workflows, validates and runs them, reads the results, and can research unfamiliar models on Hugging Face. It is a local, bring-your-own-model alternative to the built-in Comfy Agent.

> Beta. The agent is a UI extension (a sidebar panel), not a node on the canvas.

## Features

### Canvas work
- Builds and edits graphs from a text request: searches installed node types, creates nodes and links, changes widget values, mutes or bypasses nodes, and clears or rebuilds the graph.
- Four ready templates: Z-Image Turbo, Qwen-Image, FLUX.1 dev/schnell and SD 1.5/SDXL/single-file checkpoints. Installed model files are picked automatically.
- One-call actions for smaller models: `generate`, `set_prompt`, `set_param`, `create_workflow`.
- `inspect_node` reads a single node deeply: all widget values, combo samples, input and output links with the other node and slot, flags, groups and the installed definition.
- The canvas snapshot includes selected node ids and group titles, and `get_graph` returns them, so "here" and "in this group" are resolved from real context.
- Checks the graph for unknown node types, missing required inputs, unavailable model/combo values and missing output nodes.
- Runs the current canvas, waits for the result, shows the files and sends images back to the model when vision is on.
- Diagnoses failed runs with the failing node, exception and likely fixes, and can read the ComfyUI server log for the real traceback.
- Lists, reads and edits subgraphs, converts selected nodes into a subgraph, and moves the canvas view in and out of one.
- Compares two workflows node by node and applies selected changes as one undoable edit.
- Works with 3D files: recognises GLB, GLTF, OBJ, FBX, STL, splat and related values on the native Load3D nodes, reads their definitions, and has a curated 3D guide for import, turntable and 3D-to-image setups.
- Finds the right node by partial words: `find_nodes` matches class names, display names, categories, search aliases, input names and the file names in the loader lists, so "3d", "glb", "loader" or "checkpoint" work. Native nodes rank first and every hit is marked as a full or partial match.
- Ships a native node reference: the bundled knowledge base maps jobs to the node that does them, including the 3D loader (`Load3D`, shown as **Load 3D & Animation**) and the image loader (`LoadImage`), so the agent stops hunting for a "load glb" node. An empty search tells the model to search again with another word instead of guessing a class name.
- Reads the graph natively: the canvas context lists every node type with all of its input slots and what is plugged into what, so the agent answers "what does this node need" and "what feeds it" from the graph itself instead of opening media files.

### Safety and control
- Every mutating tool runs as a transaction: a failed edit is rolled back automatically, and successful edits get a diff card with **Undo**.
- Undo survives a page reload: the last three canvas snapshots per chat are saved in browser storage and reattached when the chat is opened.
- Unsaved-workflow protection: replacing or clearing a graph with unsaved changes always asks first, even in Auto mode.
- Pinned workflow per chat: the agent works on the workflow it started with. Switching tabs does not silently redirect edits; mutating tools stop with a clear message until you switch back or re-pin from the workflow chip.
- Co-work guard: the agent compares the canvas with its previous step. If you changed a node it is about to edit, it stops, re-reads the graph and retries instead of overwriting your work. Unrelated edits are reported to the model as "keep these".
- Crash recovery: a reply interrupted by a reload is marked in the chat, and a persisted ComfyUI job is verified against the queue on load.
- Execution bar under the composer shows the running prompt, progress and node; cancel stops the current run or removes a pending one. Stopping a reply leaves the ComfyUI job running and monitored.
- `Ask` mode asks before runs and destructive actions; `Auto` mode lets runs through, but destructive actions still ask unless you turn that off.
- Greetings, thanks, capability questions and other small talk are answered in text only: no tool calls, no canvas changes, no roadmap.
- Unknown or unfamiliar models are looked up on the official Hugging Face hub instead of guessed.
- Tool arguments are validated and coerced against JSON schemas; malformed calls are reported back to the model instead of breaking the run.
- Repeated no-progress tool loops, empty replies and step-limit overruns are detected and stopped with a clear message.
- Compatibility check in settings: reports the ComfyUI, frontend and Python versions and verifies the backend modules and frontend APIs the panel depends on, with a pass/warning/failure row for each.

### Models and research
- Sees the exact open workflow name, purpose, main model files with their roles, sampler, latent size, prompts, open tabs, node count and links.
- Lists model files on disk and system/GPU information.
- `list_assets` indexes images, video, audio, 3D models and model files across the ComfyUI input, output, temp and model folders, so file names come from disk instead of guesses. The **@** menu has an **Assets** tab with thumbnails; a referenced asset passes its exact path and metadata to the model.
- `inspect_media` reads an image, video, audio or 3D file: dimensions, duration, frame rate, average color, GLB/GLTF/OBJ/STL/PLY structure, plus a preview frame when vision is on.
- `analyze_workflow` explains the graph and reports unused nodes, validation problems, potential bottlenecks and a qualitative speed/VRAM note.
- Workflow versions: named snapshots with `save_workflow_version`, `list_workflow_versions` and `restore_workflow_version`; a restore saves a safety version first.
- `get_environment` reports Python, PyTorch, CUDA/cuDNN, GPUs with VRAM, disk space, ComfyUI version and key packages. `inspect_model` reads a model's safetensors header (tensors, parameters, dtypes, metadata). `list_node_packs` and `set_custom_node_enabled` manage installed packs.
- Project memory: `remember` stores a short preference or convention; saved entries are injected into every turn and can be inspected or removed with `list_memory` / `forget_memory`.
- `search_knowledge` queries a bundled reference about model families, samplers, workflow patterns, custom node packs, common errors and 3D pipelines.
- `download_model` downloads a public Hugging Face file into the right models folder, shows it as a gated action first, and never overwrites an existing file unless asked.
- `install_custom_node` clones a public GitHub node pack into `custom_nodes`, validates the repository and branch, and reports whether a restart and requirements install are needed.
- `model_lookup` searches Hugging Face, fetches the official repository card and README, and returns the repo URL, pipeline, tags, files, download counts and README excerpt. It works even when web search is off and needs no API key.
- Optional web search for current docs, model pages and release notes.

### Chat and workflow UX
- Streams answers token by token over SSE, with retries, a configurable step limit, stop, and fallback to a normal request if streaming is unavailable.
- Markdown rendering: headings, lists, quotes, links, tables with horizontal scrolling, task checkboxes, underlined text and highlighted code blocks with copy and wrap.
- Expandable model thoughts and per-step timing, input and result.
- Generated images in chat with copy and `@` reference buttons, plus inline video and audio playback; the agent can show earlier images and embed files by name.
- Interactive answer buttons that apply parameter values, open a node on the canvas or jump to the last error.
- `@` references to nodes, saved/open workflows, past generations (including the graph that produced them) and indexed assets.
- Attachments by button, paste or drag and drop: images, audio, video (Gemini-compatible endpoints), 3D files and text/JSON files.
- Attached files are uploaded into the ComfyUI input folder right away (3D files into `input/3d`), and the chat shows the exact path. The agent uses that path as it is in a loader widget or calls `apply_attachment` to drop the file into a node, so an attached photo can be loaded into the workflow without asking the user to upload it again. A **+** button on the file in the chat adds it to the canvas: an image into a Load Image node, a 3D model into a Load 3D node where ComfyUI renders it.
- Built-in image editor before sending: brush, crop, text with color and size, rotate left/right, undo, redo and reset. Click the thumbnail or the pencil on an image chip; the edited image replaces the attachment.
- Four panel themes picked from preview cards in settings: **ComfyUI** (follows the ComfyUI colors), **Claude** (warm cream and orange, or the dark clay-grey version), **Luxurious** (gold on ivory or black, with a diamond send button and gold shine) and **Colors** (frosted translucent panels over a soft orange and sage ambient glow). A switch turns the light or dark version of the selected theme on. Both choices are saved in the browser.
- Agent and user names: choose what the assistant calls itself (shown in the panel title and used in its replies) and how it should address you.
- Edit any of your messages and resend; the chat context and canvas return to the state before it.
- Live roadmap card for multi-step tasks with a progress bar and start/done/failed/skipped states.
- Plan mode: the agent proposes a numbered plan first, then waits for approval, changes or cancellation before editing. It re-checks the plan after important results, asks more often when a choice matters, and compresses long histories while keeping the goal. An approved plan becomes the roadmap automatically.
- Plan pre-flight: before the plan is shown, every node type the plan needs is checked. The card tells you which nodes are ready, which pack is installed but did not load, which pack still has to be installed and which node name does not exist at all, with installed alternatives for the last case. A plan that needs a new pack is split into "install and restart" and "build the graph".
- Fast mode is the classic behavior: plan the work internally and act right away.
- Self-update: on page load the panel checks GitHub, plays a short notification sound and shows a banner when a newer version exists. Automatic fast-forward is optional; ComfyUI is never restarted automatically.
- Automatic canvas check after every edit: unavailable combo values and missing media files are reported back to the model immediately, so it fixes a broken Load Image instead of claiming success.
- Performance tracking per run (steps, tool calls, tokens, estimated cost, time, errors) and session totals in settings.
- Chat export as Markdown or full JSON, including errors, rollbacks, plans, roadmaps and approvals.
- Automatic chat titles, start ideas and follow-up suggestions generated by the model (can be turned off).
- Skills: saved instruction packs the agent can read, create and delete.
- **Standalone product:** [`ComfyUI Workflow Master`](products/comfyui-workflow-master/) packages the core workflow-operating guidance with a zero-dependency CLI. It works with standard ComfyUI APIs and does not require this extension.
- Up to 5 chats can run at the same time; history keeps up to 40 chats and the last 80 messages of each.
- Expandable panel and five UI languages: English, Русский, Deutsch, Polski, Français.

## Requirements

- ComfyUI with a recent frontend that provides the sidebar tab API. Creating subgraphs also relies on that frontend API.
- An LLM with **tool calling**. Vision-capable models are recommended so the agent can see images.
- Network access to your LLM endpoint. Model lookup uses `huggingface.co`; web search is optional.

## Installation

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/CrazyDashTool/ComfyUI-Agent
```

Restart ComfyUI and open the **Agent** tab in the left sidebar (chat icon). No extra dependencies are needed: the backend uses `aiohttp`, which ships with ComfyUI.

To update:

```bash
cd ComfyUI/custom_nodes/ComfyUI-Agent
git pull
```

The extension also checks for updates itself when the page loads, notifies with a sound and a banner, and can fast-forward a clean checkout if automatic updates are enabled. Manual `git pull` always works. Restart ComfyUI after updating the backend and reload the page after frontend changes.

## Setup

1. Open the Agent panel and click the gear icon.
2. Pick a preset, or choose **Custom** and enter a base URL.
3. Enter the API key (not needed for local servers), then click **Load list** to fetch models or type a model name.
4. Adjust the options you need and click **Save**.

Any OpenAI-compatible endpoint works. Anthropic is supported through its native API.

| Preset | Provider type | Default base URL |
|---|---|---|
| OpenAI | OpenAI-compatible | `https://api.openai.com/v1` |
| Google AI Studio | OpenAI-compatible | `https://generativelanguage.googleapis.com/v1beta/openai` |
| Anthropic | Anthropic | `https://api.anthropic.com` |
| OpenRouter | OpenAI-compatible | `https://openrouter.ai/api/v1` |
| DeepSeek | OpenAI-compatible | `https://api.deepseek.com/v1` |
| Groq | OpenAI-compatible | `https://api.groq.com/openai/v1` |
| Ollama (local) | OpenAI-compatible | `http://localhost:11434/v1` |
| LM Studio (local) | OpenAI-compatible | `http://localhost:1234/v1` |
| Custom | OpenAI-compatible | your URL |

### Settings reference

The settings panel has three tabs: **AI** (provider, model, limits, permissions and search), **Customization** (language, theme, names and skills) and **Logs** (chat export, server log, performance, extension updates and the compatibility report). Language, theme, names and AI fields are saved with the **Save** button on their tab. The selected tab is marked by a pill that slides over, and the panel content moves in from the side you came from.

| Setting | Default | What it does |
|---|---|---|
| Language | English | UI language and the language the agent replies in. |
| Theme | ComfyUI | Panel appearance: **ComfyUI**, **Claude**, **Luxurious** or **Colors**, picked from preview cards. The switch below sets the light or dark version (the ComfyUI theme keeps ComfyUI's own colors). |
| Agent name | Comfy Agent | What the assistant calls itself; shown in the header and used in replies. |
| Your name | — | How the assistant should address you. |
| Preset | — | Fills the provider and base URL for a known service. |
| Provider | OpenAI-compatible | OpenAI-compatible API or Anthropic's native API. |
| Base URL | `https://api.openai.com/v1` | Endpoint of the LLM server. |
| API key | empty | Stored only in `config.json` on the server; never sent to the browser. |
| Model | empty | Model name, or pick one with **Load list**. |
| Max tokens | 0 | 0 leaves the provider default in place; Anthropic uses 8192 when unset. |
| Temperature | empty | Empty leaves the provider default in place. |
| Max steps per reply | 30 | 1–200 tool/model steps before the agent stops. |
| Stream the answer | on | SSE token streaming with automatic fallback. |
| Confirm destructive actions | on | Asks even in `Auto` mode before deleting nodes, clearing the canvas or replacing it. |
| Highlight changes | on | Outlines created, removed and changed nodes on the canvas. |
| Check GitHub on start | on | Compares the folder with GitHub when the page loads; a newer version triggers a banner and a notification sound. |
| Update automatically | off | Fast-forwards a clean `main` checkout without asking. Off keeps the update waiting behind the banner and the **Update** button. |
| Check now / Update manually | buttons | Run a forced check or apply the update immediately. |
| Vision | on | Sends images (canvas results and attachments) to the model. |
| Suggestions | on | Generates start ideas, follow-up replies and automatic chat titles. |
| Web search | off | Off, Ollama, Tavily, Brave, Serper or SearXNG. |
| Search API key | empty | Required for Ollama, Tavily, Brave and Serper. |
| SearXNG URL | empty | Base URL of a self-hosted SearXNG instance. |
| Extra instructions | empty | Appended to the system prompt for every request. |

Settings are saved to `config.json` next to the extension. On POSIX systems the file is written with `0600` permissions.

## Web access

### Hugging Face model lookup

`model_lookup` works without any web-search setting. When the agent meets an unfamiliar or new model, or you ask what a model is, it:

1. searches the official Hugging Face model hub,
2. fetches the repository card and README,
3. answers with the repo id, official URL, pipeline, tags, files, download counts and a README excerpt.

It contacts only `huggingface.co`, needs no API key, and treats README text as reference data rather than instructions. Private or gated repositories may not expose their README without authentication; public repos work normally.

### Optional web search

Enabling a provider adds the `web_search` and `read_url` tools. `read_url` allows only public `http(s)` addresses and blocks private, loopback, link-local and reserved hosts. Search and page text are treated as untrusted data. Supported providers:

| Provider | What it needs |
|---|---|
| Ollama web search | API key |
| Tavily | API key |
| Brave Search | Subscription token |
| Serper | API key |
| SearXNG | URL of your instance (JSON output enabled) |

## How the agent works

- The live canvas snapshot is refreshed on every step: workflow name and unsaved state, purpose, output nodes, model files and roles, sampler, latent size, prompts, open tabs, nodes, widgets and links.
- The agent changes the canvas only through tools. Tools run in the browser, where the graph lives; LLM calls, log reads and optional web search go through the backend, so provider keys stay on the server.
- Model lookup runs directly in the browser against `huggingface.co`, which allows cross-origin requests.
- A mutating tool snapshots the graph first. If it fails, the graph is restored and the chat shows a rollback note; if it succeeds, the change card offers **Undo**.
- Before each edit the agent compares the canvas with the state after its previous step. Nodes you changed yourself are protected: the tool refuses to overwrite them, and the model is told to re-read the graph and retry. Other user changes are reported back so the agent keeps them.
- Asset search reads the input, output, temp and model folders in the background and caches the index; model downloads and node installs are loopback-only endpoints with their own validation.
- `search_knowledge` reads bundled Markdown reference files and returns matching sections. The content is treated as reference, not as instructions.
- When the model only announces an action without calling a tool, the agent nudges it to act (up to twice). Repeated identical calls with identical results are stopped by a loop guard, and the step limit ends long runs cleanly.
- Plain questions and small talk stay read-only, even when they include `@` references or attachments.
- Workflow questions are answered from the deterministic canvas summary with the exact workflow name, purpose and model files; a tab name alone is not treated as an answer.
- In Plan mode the path is re-checked after validation, a run or an error, and `ask_user` is used more often for choices that really matter. An approved plan becomes the roadmap and is updated step by step.
- In Plan mode the plan card shows a pre-flight for the node types the plan needs: ready, pack installed but not registered, pack missing or node name unknown. Missing packs are installed first and the graph is built after the restart, so a missing custom node no longer breaks the run halfway.
- In Plan mode a long conversation is compressed before the model call: older messages are summarized into a goal-preserving note while the recent messages stay intact. The chat shows a short note when this happens.
- Updates are checked with `git fetch` and applied with `git merge --ff-only` on `main` only. The update endpoint accepts requests only from the same machine and requires a custom header; a dirty checkout is never touched.

## Usage

- `Build a Z-Image Turbo workflow`
- `Change the prompt to a cat in a spacesuit and generate`
- `What is z_image_turbo_bf16.safetensors?`
- `What workflow is open and which models does it use?`
- `Compare the canvas with my saved "portrait" workflow`
- `Add a Load3D node with a turntable and use my hand.glb`
- `Download flux1-dev.safetensors into diffusion_models`
- `Install ComfyUI-Manager from GitHub`

Tips:

- Type `@` to reference nodes, saved/open workflows or past generations.
- `Enter` sends; `Shift+Enter` inserts a newline.
- Paste or drag files onto the composer to attach them. Limits: 6 attachments, images up to 8 MB, video/audio up to 16 MB, 3D files up to 64 MB, text/JSON up to 1 MB, and up to 8 references. An attached file is uploaded into the ComfyUI input folder at once, and the chip under the message shows its path, so you can ask for it to be loaded into a node.
- Switch **Plan / Fast** above the send button to choose the agent mode; the **Ask / Auto** switch below it controls run approvals.
- When the agent asks a question, choose one of the options or type your own answer.
- Use **Undo** on a canvas change card to return to the graph from before that edit.
- In a diff card, tick the changes you want and apply them as one undoable edit.
- Hover over one of your messages to edit and resend it or roll the chat and canvas back to that point.
- Expand a run card to inspect tokens, estimated cost and time; settings keeps session totals.
- Use the header buttons to start a new chat, switch between running chats, expand the panel or export the current chat.

## Tools

The agent chooses tools through the model's tool-calling interface. Availability depends on settings.

### Canvas

| Tool | Purpose |
|---|---|
| `get_graph` | Read every node, widget value, link and output name. |
| `find_nodes` | Search installed node types by partial keywords: class name, display name, category, search aliases, input names or file names. Returns class names with inputs and outputs, marked as a full or partial match. |
| `get_node_info` | Full node definition: inputs, combo options, defaults, ranges and outputs. |
| `inspect_node` | Deep-read one node: all widget values, combo samples, every link, flags, groups and definition. |
| `build_graph` | Create nodes and links in one call. |
| `update_node` | Change widget values, title, position or mode. |
| `disconnect_input` | Remove a link from a node input. |
| `remove_nodes` | Delete nodes by id. |
| `clear_graph` | Remove everything from the canvas. |
| `validate_graph` | Check node types, required inputs, model values and output nodes. |
| `apply_attachment` | Put a file from the chat into a loader widget (`LoadImage.image`, `Load3D.model_file`, …) by node id, or create the matching loader node when no node id is given. |

### Fast actions

| Tool | Purpose |
|---|---|
| `generate` | Set the prompt and optional parameters, run the canvas and return the result. |
| `set_prompt` | Change positive/negative prompt text without node ids. |
| `set_param` | Change a widget value by name on one or all nodes. |
| `create_workflow` | Build a ready workflow from one of the four templates. |

### Generation

| Tool | Purpose |
|---|---|
| `run_workflow` | Queue the current canvas and wait for the result or execution error. |
| `get_queue` | Read running and pending prompts from the ComfyUI queue. |
| `cancel_execution` | Stop the current run or remove a pending prompt (asks first). |
| `list_generations` | List recent generations with files and prompt text. |
| `show_images` | Show earlier generated files in the chat. |
| `inspect_generation` | Read the graph behind a generation and attach its images. |
| `load_generation_workflow` | Restore a past generation's workflow on the canvas. |

### Workflows and templates

| Tool | Purpose |
|---|---|
| `list_workflows` | List the user's saved workflows. |
| `read_workflow` | Read a saved or open workflow without switching to it. |
| `load_workflow` | Open a saved workflow, replacing the current graph. |
| `list_open_workflows` | List workflows currently open in tabs. |
| `list_templates` | Search official ComfyUI and custom-pack example workflows. |
| `read_template` | Read a template's nodes, settings and links. |
| `load_template` | Open a template on the canvas. |
| `diff_workflows` | Compare the canvas with another workflow and apply selected changes. |
| `save_workflow_version` | Save a named snapshot of the current workflow. |
| `list_workflow_versions` | List saved versions with size, node count and time. |
| `restore_workflow_version` | Restore a version (asks first and saves a safety version). |

### Subgraphs

| Tool | Purpose |
|---|---|
| `list_subgraphs` | List nested graphs with inputs, outputs and size. |
| `read_subgraph` | Read one subgraph in full. |
| `edit_subgraph` | Edit inner widgets, titles, modes or delete inner nodes. |
| `create_subgraph` | Convert canvas nodes into a subgraph. |
| `enter_subgraph` / `exit_subgraph` | Move the canvas view in or out; navigation only. |

### Models, packs and system

| Tool | Purpose |
|---|---|
| `list_models` | List model folders and files on disk. |
| `model_lookup` | Search Hugging Face and read the official repository card and README. |
| `system_info` | GPU, VRAM and ComfyUI/PyTorch versions. |
| `get_environment` | Python, PyTorch, CUDA/cuDNN, GPUs, disk, ComfyUI version and package versions. |
| `inspect_model` | Model file details, including safetensors tensors, parameters, dtypes and metadata. |
| `list_custom_nodes` | List installed custom-node packs with categories and examples. |
| `get_custom_node_docs` | Read a pack's README, files and nodes. |
| `list_node_packs` | List installed and disabled packs with file counts and requirements. |
| `set_custom_node_enabled` | Enable or disable a pack by renaming its folder (asks first; restart to load). |

### Assets, knowledge and installs

| Tool | Purpose |
|---|---|
| `list_assets` | Search images, video, audio, 3D models and model files across ComfyUI folders. |
| `inspect_media` | Read image/video/audio/3D metadata and attach a preview frame. |
| `search_knowledge` | Search the bundled reference on models, samplers, workflows, native nodes, node packs, errors and 3D. |
| `download_model` | Download a public Hugging Face file into a models folder (asks first; resumes and verifies SHA-256). |
| `install_custom_node` | Clone a public GitHub node pack into `custom_nodes` (asks first; restart to load). |
| `remember` / `list_memory` / `forget_memory` | Manage short project preferences and conventions. |

### Diagnostics

| Tool | Purpose |
|---|---|
| `diagnose_error` | Explain the last failed run with the failing node, exception and likely fixes. |
| `get_server_logs` | Read the ComfyUI console log tail, optionally filtered. |
| `analyze_workflow` | Explain the graph, report validation problems, bottlenecks and a speed/VRAM note. |

### Planning and interaction

| Tool | Purpose |
|---|---|
| `ask_user` | Ask a question with 2–5 ready-made options and wait. |
| `propose_plan` | Plan mode only: show a numbered plan and wait for approval. |
| `create_roadmap` | Create the live checklist for a multi-step task. |
| `update_roadmap` | Mark a step start/done/failed/skipped and update progress. |
| `offer_actions` | Add clickable parameter, node or error actions under an answer. |

### Web and skills

| Tool | Purpose |
|---|---|
| `web_search` | Search the web when a provider is enabled. |
| `read_url` | Read a public page when web search is enabled. |
| `read_skill` | Read a saved instruction pack. |
| `save_skill` | Create or overwrite a skill (only when asked). |
| `delete_skill` | Delete a skill (only when asked). |

## Where data is stored

- `config.json` next to the extension: provider settings and API keys in plain text on disk. It is gitignored, written with restricted permissions where supported, and secrets are stripped before the config is sent to the browser.
- Browser `localStorage`: up to 40 chats, the last 80 messages of each, UI language and the permission mode. Image, audio and video parts are replaced with placeholders in saved messages; text/JSON attachments and small attachment thumbnails may remain. Tool output is clipped for storage. The last three canvas snapshots per chat are kept for persistent undo (size-capped per chat), plus up to 20 named workflow versions (`crazy_agent.versions.v1`) and 20 project-memory entries (`crazy_agent.memory.v1`).
- `skills/*.md`: saved skills. The folder is gitignored.
- `knowledge/*.md`: bundled reference documents shipped with the extension. They are read-only at runtime and not modified by the agent.
- Downloads go directly to the chosen ComfyUI models folder; installed node packs go to `custom_nodes` as a normal git clone.
- Session performance totals live in memory and reset when the page is reloaded or **Reset stats** is pressed.

Network calls go to your configured LLM endpoint, to the optional search provider, to `huggingface.co` when `model_lookup` runs, and to your git remote when the update check runs. There is no telemetry.

## Project structure

| File | Purpose |
|---|---|
| `__init__.py` | Registers the backend routes and the `web/` directory. |
| `agent_server.py` | LLM proxy (OpenAI-compatible and Anthropic), SSE streaming, retries, config, skills, web search and page reading. |
| `web/agent.js` | Panel UI, agent loop, canvas tools, references, permissions and model lookup. |
| `web/agent.css` | Styles and animations built on ComfyUI theme variables. |
| `config.json` | Local provider settings (created after saving). |
| `knowledge/` | Bundled curated reference documents used by `search_knowledge`. |
| `skills/` | Saved skill files. |
| `tests/` | Backend unit tests and a frontend contract check (module syntax, i18n parity, tool schemas). |

### Tests

```bash
python -m unittest discover -s tests -p "test_*.py"
node tests/check_frontend.mjs
```

The backend tests stub ComfyUI's `server` and `folder_paths` modules, so they run without a ComfyUI process. The frontend check also verifies the theme cards, previews and light/dark lever against the stylesheet and i18n, the image editor entry points, the attachment and loader functions and the security markers in the backend (download redirect allowlist, atomic node clone).

### Backend API

| Route | Purpose |
|---|---|
| `GET /crazy_agent/config` | Public config (secrets removed). |
| `POST /crazy_agent/config` | Save settings. |
| `GET /crazy_agent/models` | Load the provider's model list. |
| `POST /crazy_agent/chat` | One-shot LLM request with tools. |
| `POST /crazy_agent/chat_stream` | SSE streaming LLM request with tools. |
| `POST /crazy_agent/suggest` | Start ideas, follow-ups and chat titles. |
| `POST /crazy_agent/compact` | Summarize older messages for plan-mode context compression. |
| `GET /crazy_agent/update` | Compare the extension folder with GitHub (5-minute cache). |
| `POST /crazy_agent/update` | Fast-forward a clean `main` checkout (loopback and custom header only). |
| `GET /crazy_agent/logs` | Tail the ComfyUI server log. |
| `GET /crazy_agent/pack_docs` | Read an installed custom-node pack's docs. |
| `GET /crazy_agent/assets` | Search the local asset index by kind, folder and keywords. |
| `GET /crazy_agent/knowledge` | List or search the bundled knowledge base. |
| `GET /crazy_agent/environment` | Python, PyTorch, CUDA, GPU, disk and package diagnostics. |
| `GET /crazy_agent/compatibility` | ComfyUI, frontend and Python versions plus backend dependency checks. |
| `GET /crazy_agent/model_context` | The provider's loaded and maximum context window for the current model. |
| `GET /crazy_agent/model_info` | Model file size, metadata and safetensors header summary. |
| `GET /crazy_agent/custom_nodes` | List installed and disabled custom-node packs. |
| `POST /crazy_agent/custom_node_toggle` | Enable or disable a pack by renaming its folder (loopback and custom header only). |
| `POST /crazy_agent/download_model` | Download a public Hugging Face file into a models folder (loopback and custom header only). |
| `POST /crazy_agent/install_node` | Clone a public GitHub node pack into `custom_nodes` (loopback and custom header only). |
| `POST /crazy_agent/web_search` | Run a configured web search. |
| `POST /crazy_agent/read_url` | Fetch a public page (private hosts blocked). |
| `GET /crazy_agent/skills` | List skills. |
| `GET /crazy_agent/skills/{name}` | Read a skill. |
| `POST /crazy_agent/skills` | Create or overwrite a skill. |
| `POST /crazy_agent/skills/delete` | Delete a skill. |

## Limitations

- Beta software: expect rough edges, especially with small local models.
- Answer quality depends heavily on the model. A model with reliable tool calling is required; vision is needed for the agent to actually see images.
- The context window is the limit for everything: tool schemas, the system prompt, the conversation and the images. The panel reads the model's loaded context window, keeps the last two images, counts images in the context budget, and drops older images when the model answers with an empty reply instead of failing. When a request does not fit, the backend trims the oldest turns, and the panel compacts the conversation and retries; only if that is still not enough it answers with the required and available token counts instead of a silent error.
- The canvas snapshot shows the top level of a workflow; nested subgraphs are available through the subgraph tools.
- Undo of the last three canvas edits survives a reload; older diff cards and message rollback rely on in-memory snapshots and stop working after a reload. Very large graphs skip persistent snapshots when they exceed the storage cap.
- Workflow versions and project memory are stored in the browser, not on disk, so they do not sync between browsers or machines.
- Video attachments are forwarded only to Gemini-compatible endpoints. Audio support depends on the provider.
- Streaming needs server-sent events. If the browser or a proxy blocks them, the agent falls back to a plain request.
- Private or gated Hugging Face repositories may not return a README without authentication.
- Web search is off by default; model lookup still works without it.
- Self-update works only for a git checkout of `main`, only from the panel on the machine that runs ComfyUI, and only while the folder has no tracked local changes. Restart ComfyUI afterwards to load backend changes.
- Asset search, knowledge search, model downloads, node installs and the compatibility check are backend routes: after updating the extension, restart ComfyUI once to activate them.
- Downloads are limited to public `huggingface.co` / `hf.co` resolve URLs. Redirects are checked hop by hop against the Hugging Face CDN hosts, and redirects to any other host are refused. Gated repositories need their token configured outside the agent.
- Node installs clone into a temporary folder and move it into `custom_nodes` only after a successful clone. Submodules and tags are not fetched, branch names are validated, and Python requirements are reported but not installed automatically.

## Troubleshooting

- **"The model returned an empty reply"**: the endpoint answered with no text after retries. Try again or choose a model with reliable tool calling.
- **The agent answers but does not act**: use a stronger tool-calling model, or ask for one of the one-call actions (`generate`, `set_prompt`, `set_param`, `create_workflow`).
- **Model lookup returns no repository**: pass the exact repo id (`owner/name`) or another spelling; not every local filename exists on Hugging Face.
- **Run is blocked**: switch from `Ask` to `Auto`, or approve the pending action in the chat.
- **`list_assets` or `search_knowledge` fails with 404**: restart ComfyUI so the new backend routes load, then reload the page.
- **The compatibility check reports a missing backend route**: restart ComfyUI once and run the check again; the panel itself keeps working.
- **The agent stopped instead of editing a node you changed**: this is the co-work guard. Send "continue" after your change; the agent re-reads the canvas and applies its edit only where it does not conflict.
- **Update is skipped**: the checkout has tracked local changes, the branch is not `main`, or the panel is not opened on the machine running ComfyUI. Commit or discard the changes and check again from settings.
- **An edit was rolled back**: read the error note in the chat, then ask the agent to fix the cause and retry.
- **Streaming stops working**: the agent retries with a normal request automatically; check the browser console and any proxy in front of ComfyUI.

## License

Apache-2.0, see [LICENSE](LICENSE).

## Created by CrazyDashTool

[GitHub](https://github.com/CrazyDashTool) · [YouTube](https://www.youtube.com/@CrazyDashToolOficial)
