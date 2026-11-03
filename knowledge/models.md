---
title: Model families and folders
tags: models, checkpoints, diffusion_models, flux, sdxl, qwen, z-image, wan, ltx, vae, text encoders, loras
---

## Where model files belong

Every loader widget is a combo filled from a specific models folder. Put a file in the wrong folder and it will not appear in the widget.

- `checkpoints`: complete Stable Diffusion 1.x, 2.x and SDXL checkpoints (`.safetensors`, `.ckpt`). These contain UNET + CLIP + VAE.
- `diffusion_models` and `unet`: standalone diffusion/UNET weights (Flux, Qwen-Image, Z-Image, Wan, LTX, HunyuanVideo). Use `UNETLoader` / `UnetLoaderGGUF`.
- `text_encoders` and `clip`: CLIP, T5, Qwen and other text encoders. Flux uses `clip_l` + `t5xxl`; Qwen-Image uses a Qwen 2.5 VL encoder; Z-Image uses its own Qwen-based encoder.
- `vae`: VAE files (Flux `ae.safetensors`, SDXL VAE, Qwen-Image VAE, video VAEs). Wrong VAE produces color shifts or shape errors.
- `loras`: LoRA adapters. Load with `LoraLoader` or `LoraLoaderModelOnly`; model and CLIP weights are separate.
- `controlnet`: ControlNet models; pair with the matching preprocessor and base model family.
- `upscale_models`: ESRGAN/RealESRGAN/SwinIR/4x-UltraSharp style upscalers.
- `clip_vision`: CLIP Vision encoders for IP-Adapter, style models and image prompts.
- `embeddings`: textual inversion embeddings, referenced by name in prompts.
- `style_models`, `photomaker`, `instantid`, `ipadapter`: specialized adapters; their loader nodes expect the exact folder.

The fastest way to find real file names is `list_models(folder=...)` or `list_assets(folder=..., kind="model")`. Never guess a file name.

## Stable Diffusion 1.5 and SDXL

- SD 1.5: native 512x512, 20-30 steps, CFG 7-8, `euler_ancestral` or `dpmpp_2m` + `karras`.
- SDXL: native 1024x1024, 20-30 steps, CFG 5-7. Base + refiner is optional; most current SDXL checkpoints work without a refiner.
- SDXL LoRAs usually do not work on SD 1.5 and vice versa. Match the family.
- SDXL VAE is built into most checkpoints; a separate SDXL VAE is only needed when the checkpoint ships without one.

## Flux

Flux uses separate files:

- Diffusion model in `diffusion_models` (`flux1-dev`, `flux1-schnell`, `flux1-dev-fp8`, Kontext/edit variants).
- Text encoders in `text_encoders`: `clip_l.safetensors` and `t5xxl_fp16.safetensors` or `t5xxl_fp8_e4m3fn.safetensors`.
- VAE `ae.safetensors` in `vae`.
- Loader chain: `UNETLoader` + `DualCLIPLoader` (type `flux`) + `VAELoader`, then `CLIPTextEncode`, `EmptySD3LatentImage` or `EmptyLatentImage`, `KSampler`, `VAEDecode`.
- Dev: 20-30 steps, CFG 1.0, guidance 3.0-3.5 when the sampler node exposes it.
- Schnell: 1-4 steps, CFG 1.0. More steps rarely help.
- fp8 and GGUF builds reduce VRAM; GGUF needs the GGUF loader nodes from ComfyUI-GGUF.

## Qwen-Image

- Diffusion model in `diffusion_models`, Qwen 2.5 VL text encoder in `text_encoders`, Qwen-Image VAE in `vae`.
- Typical start: 1024x1024, 20 steps, CFG 2.5-4.0.
- Qwen-Image-Edit variants take a reference image input; follow the official template for the exact wiring.

## Z-Image

- Turbo variant is a few-step distilled model: typically 8 steps, CFG 1.0, 1024x1024.
- It uses its own text encoder and VAE files. Use the official template or `create_workflow(template="z-image")` so the loader types and filenames match.

## Video models

- Wan 2.1/2.2: text-to-video and image-to-video graphs, separate high/low noise models in some variants, CLIP vision for I2V, VAE for video. Frame counts are usually 16-81+ and VRAM use grows with resolution, frames and batch.
- LTX-Video: fast DiT video model, often 121 frames at 24 fps, low step counts. Installed as ComfyUI-LTXVideo; uses LTX conditioning and scheduler nodes.
- HunyuanVideo: heavier model, often used with fp8/GGUF variants and tiled VAE decode.
- Always check the template graph before wiring a video model: node names and expected frame counts differ between versions.

## Quantization and VRAM

- `fp16`/`bf16` is the normal quality target.
- `fp8_e4m3fn` roughly halves weight memory with a small quality cost and is widely supported.
- GGUF Q4/Q5/Q8 builds save more VRAM but need ComfyUI-GGUF and are slower on some GPUs.
- If a model fits but the VAE decode fails with OOM, use tiled VAE decode instead of lowering the model precision.
- Check free VRAM with `system_info` before choosing a model or resolution.

## Rules

- Never invent a model file name. Read it from `list_models`, `list_assets` or the canvas snapshot.
- Combo values must match the installed file exactly, including subfolders such as `flux/model.safetensors`.
- A model in the wrong folder is invisible to its loader even if the path is correct on disk.
- Hugging Face gated repositories cannot be downloaded anonymously; the user must accept the license and download manually.
