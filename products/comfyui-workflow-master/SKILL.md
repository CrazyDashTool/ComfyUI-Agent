---
name: comfyui-workflow-master
description: Build, inspect, validate, run, and troubleshoot ComfyUI API workflows through a standalone zero-dependency CLI. Use when a user asks to create or execute a ComfyUI workflow, inspect installed nodes or models, or diagnose a failed ComfyUI prompt.
license: Apache-2.0
compatibility: Python 3.9+ and a reachable ComfyUI server; no ComfyUI-Agent installation required.
metadata:
  author: CrazyDashTool
  version: 1.0.0
---

# ComfyUI Workflow Master

Operate ComfyUI through its standard HTTP API with `scripts/comfyui_client.py`.

## Rules

1. Run `health`, then `nodes` before creating or changing a workflow. Never invent node class names, input names, or enum values.
2. Work with **API-format** workflow JSON: an object keyed by node id, where each node has `class_type` and `inputs`.
3. Preserve an existing workflow unless the user asks for a rebuild. Save generated JSON before queueing it.
4. Run `validate` before `queue`. Fix every reported error rather than claiming success.
5. Use sensible defaults when details do not matter. Ask only when the choice changes the intended result.
6. Never install nodes, download models, overwrite files, or cancel jobs without the user's approval.
7. After queueing, use `wait` and report the prompt id, output files, or exact error briefly.

## Commands

Set the server once if it is not the default:

```bash
export COMFYUI_URL=http://127.0.0.1:8188
```

```bash
python scripts/comfyui_client.py health
python scripts/comfyui_client.py nodes --search checkpoint
python scripts/comfyui_client.py nodes --type KSampler
python scripts/comfyui_client.py validate workflow.json
python scripts/comfyui_client.py queue workflow.json
python scripts/comfyui_client.py wait PROMPT_ID --timeout 600
python scripts/comfyui_client.py cancel PROMPT_ID
```

Add `--json` for machine-readable output. `queue --wait` validates, submits, and waits in one command.

## Workflow procedure

1. Discover node definitions with `nodes --search TERM` and `nodes --type EXACT_CLASS`.
2. Read the returned `input.required` and `input.optional` schemas. Loader enum values are the files actually installed on the server.
3. Create API workflow JSON. Links use `["source_node_id", output_index]`; literals use ordinary JSON values.
4. Call `validate`. Validation checks local structure and asks ComfyUI to validate when supported.
5. Call `queue --wait`. Return output filenames from the history response.
6. If execution fails, quote the failing node id/type and server message, inspect that node definition, change only what is necessary, then retry once.

## Minimal API workflow shape

```json
{
  "1": {
    "class_type": "ExampleNode",
    "inputs": {
      "value": 1,
      "input": ["2", 0]
    }
  }
}
```

This skill deliberately does not contain fixed model-specific workflows: installed node and model names differ between ComfyUI systems. Discover the real schema first.
