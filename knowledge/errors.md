---
title: Common errors and fixes
tags: errors, oom, missing model, missing media, shape mismatch, import error, validation
---

## "Cannot allocate memory" / CUDA out of memory

Symptoms: `torch.cuda.OutOfMemoryError`, `allocation on device`, the run stops mid-sampling or during VAE decode.

- Lower resolution first; VRAM cost grows roughly with width x height.
- Lower `batch_size` to 1.
- Reduce frame count for video.
- Use an fp8 or GGUF model variant.
- Use tiled VAE decode when only the decode step fails.
- Close other GPU applications, or start ComfyUI with `--lowvram` / `--novram`.
- Check free memory with `system_info` before retrying.

Do not simply retry the same settings; the same allocation will fail again.

## "Value not in list" / invalid combo value

A widget holds a file name or option that is not in the current combo list.

- Run `list_models(folder=...)` or `list_assets(folder=..., kind="model")`.
- Read the exact installed value, including subfolders, and apply it with `set_param` or `update_node`.
- The file may be in the wrong models folder and therefore invisible to that loader.
- After installing a model, the combo list may need a refresh; `validate_graph` forces a fresh `/object_info`.
- Never fix this by inventing a similar file name.

## "Required input is missing" / "no link found"

A required input socket has no link and is not a widget.

- `validate_graph` lists the node and input name.
- Connect the correct source output, or fill the widget if the input is also exposed as a widget.
- A muted or bypassed node can break an expected chain; check node mode with `inspect_node`.

## Shape, tensor or dimension mismatch

Typical messages: `size mismatch`, `expected tensor`, `mat1 and mat2`, latent shape errors.

- Latent width and height must be multiples of 8; SDXL/Flux prefer multiples of 64.
- The VAE must match the model family. A Flux VAE on an SDXL latent produces garbage or shape errors.
- A second sampler must receive the latent from the first stage, not a new empty latent.
- The batch dimensions of conditioning, latent and image must be compatible.
- Wrong text encoder type in `DualCLIPLoader` is a common Flux error.

## "Media input missing" / image does not exist

A Load Image or Load 3D widget points to a file that is not in the ComfyUI input folder.

- Run `list_assets(kind="image")` or `list_assets(kind="3d")` and use an exact returned path.
- Subfolders are part of the value, for example `3d/model.glb` or `shots/frame.png`.
- A file in `output` is not automatically available as an input; copy or upload it.
- The node may show a broken preview and ComfyUI shows a "Media input missing" toast. Treat that as a failed edit and fix the value.

## Missing custom node / import error

- `list_custom_nodes` shows what actually loaded.
- `get_server_logs` with a grep for the pack name shows the traceback.
- `ModuleNotFoundError` means a dependency is missing; install the pack requirements.
- Install the pack, restart ComfyUI, then validate again.
- Red nodes remain red until the class is importable; changing widgets will not help.

## Prompt validation failed before execution

ComfyUI rejects the prompt before running it.

- No active output node: add `SaveImage`, `PreviewImage`, `VHS_VideoCombine`, `SaveGLB` or the model's save node.
- A linked input has the wrong type.
- A required widget is empty or invalid.
- An output node is muted.
- `validate_graph` and `diagnose_error` usually name the node; `get_server_logs` gives the exact validation message.

## Authentication and gated downloads

- A Hugging Face repository can be gated; anonymous downloads return 401/403.
- The user must accept the license on the model page and download it manually, or provide their own token outside this extension.
- `download_model` only supports public Hugging Face files and never sends credentials.
- A failed partial download is removed; retry after checking the exact file path in the repository.

## Server will not start after installing a pack

- Read the console traceback; usually a missing dependency or an incompatible Python version.
- Remove or disable the newly installed pack folder and restart.
- ComfyUI-Manager can disable packs without deleting them.
- Do not delete unrelated packs while debugging; isolate the last change.
