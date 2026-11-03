---
title: Workflow patterns and wiring
tags: workflow, graph, txt2img, img2img, inpaint, upscale, controlnet, lora, video, batch
---

## Text-to-image, classic checkpoint

`CheckpointLoaderSimple` -> `CLIPTextEncode` (positive and negative, both fed by the checkpoint CLIP) -> `EmptyLatentImage` -> `KSampler` (model from checkpoint, positive, negative, latent) -> `VAEDecode` -> `SaveImage`.

Widgets that matter: checkpoint name, prompt text, width/height/batch, seed, steps, CFG, sampler, scheduler, denoise (1.0).

## Text-to-image, separate model files

Used by Flux, Qwen-Image, Z-Image and video models:

`UNETLoader` (diffusion model) + `DualCLIPLoader` or model-specific text encoder loader + `VAELoader` -> conditioning node -> latent node -> `KSampler` -> `VAEDecode` -> save node.

Do not insert a standard `CheckpointLoaderSimple` for these models; there is no single checkpoint file to load.

## Image-to-image

`LoadImage` -> `VAEEncode` (same VAE as the sampler) -> `KSampler` with denoise 0.35-0.65 -> `VAEDecode` -> `SaveImage`.

The positive and negative conditioning still come from the text encoder. Keep the same VAE for encode and decode.

## Inpainting

- Load the source image, mask the area in the Mask Editor, and feed the mask into an inpaint graph.
- With a dedicated inpaint model: `VAEEncodeForInpaint` + `KSampler` denoise 1.0, then decode and paste back.
- With a normal model: `VAEEncode` the image, set denoise 0.5-0.8, and composite the result through the mask.
- `SetLatentNoiseMask` is the common core node for latent-space masking.
- Check that the mask is white where the change should happen; an inverted mask produces the opposite result.

## Upscaling

- Model upscale: `UpscaleModelLoader` -> `ImageUpscaleWithModel` -> (optional) `ImageScale` to the target size -> save.
- Latent upscale: `LatentUpscale` or `LatentUpscaleBy` -> second `KSampler` with denoise 0.35-0.6 -> decode.
- Tiled upscale for large images: tiled VAE decode and a tiled upscale node, or an upscale model plus `ImageScale`.
- For a crisp final image, model upscale is usually better than latent upscale alone.

## ControlNet

`LoadImage` -> preprocessor (Canny, Depth, OpenPose, Lineart, etc.) -> `ControlNetLoader` -> `ControlNetApplyAdvanced` (positive, negative, control image, strength, start/end percent) -> `KSampler`.

The ControlNet model must match the base family (SD 1.5 vs SDXL vs Flux). A strength around 0.6-1.0 is typical; 0.0 disables it.

## LoRA

`CheckpointLoaderSimple` -> `LoraLoader` (model + CLIP, strength model, strength CLIP) -> sampler and text encoder. For multiple LoRAs, chain `LoraLoader` nodes.

`LoraLoaderModelOnly` only changes the model; use it when the LoRA has no text-encoder part. Keep total LoRA strength moderate; stacking many strong LoRAs degrades quality.

## Video

- Wan and LTX graphs use dedicated conditioning nodes, frame count, fps and a video combine/save node.
- Typical LTX-Video graph: checkpoint or diffusion loader -> `LTXVConditioning` -> `LTXVScheduler` or `KSampler` -> `VAEDecode` -> `VHS_VideoCombine`.
- Image-to-video adds `LoadImage` and an image conditioning input.
- Video output is usually saved with `VHS_VideoCombine` (VideoHelperSuite) or the model pack's own save node.
- Frames and resolution dominate VRAM. Reduce frames before lowering quality.

## 3D

- Native graph: `Load3D` (widget `model_file`, plus optional viewport image) -> 3D processing nodes -> `Preview3DAdvanced` or `SaveGLB`.
- `Load3D` accepts gltf, glb, obj, fbx, stl and splat formats (spz/splat/ksplat for Gaussian splats) from the ComfyUI input folders.
- `MeshToFile3D`, `RotateMesh`, `MergeMeshes` and `GetMeshInfo` work on mesh data, not on the `Load3D` image outputs.
- Image-to-3D packs add their own loaders and sampler nodes; read the pack docs first.

## Multi-stage and reuse

- Reuse one VAE across encode/decode when possible; mixing VAEs causes color and shape problems.
- A second sampler needs a latent from the first one, not a fresh empty latent.
- `ImageScale` before a second pass controls the working resolution.
- `PreviewImage` is a valid output node for inspection, but `SaveImage` is the normal final output.
- Before running, `validate_graph` checks unknown types, missing links, unavailable combo values, missing media files and missing output nodes.
