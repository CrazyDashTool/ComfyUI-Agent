# ComfyUI Workflow Master

A standalone AI-agent skill for operating ComfyUI without the ComfyUI-Agent extension.

It contains:

- `SKILL.md` — concise instructions compatible with skill-based coding agents.
- `scripts/comfyui_client.py` — zero-dependency command-line client for ComfyUI's standard HTTP API.

## Install

Copy this directory into your agent's skills directory, keeping `SKILL.md` and `scripts/` together. Common examples:

```bash
# Claude Code
cp -R products/comfyui-workflow-master ~/.claude/skills/

# Project-local installation
mkdir -p .agent/skills
cp -R products/comfyui-workflow-master .agent/skills/
```

Agents that use another skill directory can install the same folder there. The CLI also works by itself.

## Quick start

Start ComfyUI normally, then run:

```bash
cd products/comfyui-workflow-master
python scripts/comfyui_client.py health
python scripts/comfyui_client.py nodes --search sampler
python scripts/comfyui_client.py validate /path/to/workflow-api.json
python scripts/comfyui_client.py queue /path/to/workflow-api.json --wait
```

For a remote server:

```bash
export COMFYUI_URL=http://192.168.1.20:8188
```

Use only a trusted network. Standard ComfyUI installations do not necessarily authenticate API requests.

## Workflow format

The CLI expects ComfyUI's **API format**, available from ComfyUI's developer-mode export. UI workflow JSON (`nodes` and `links` arrays) is a different format and is intentionally not guessed or silently converted.

## Independence

This product does not import this repository's Python package, use its web UI, or call `/crazy_agent/*` routes. It needs only Python 3.9+ and a running ComfyUI server.

## License

Apache-2.0, matching the parent project.
