---
title: Samplers, schedulers and step settings
tags: sampler, scheduler, steps, cfg, denoise, seed, ksampler, lcm, turbo
---

## Sampler choices

- `euler`: fast, predictable, good default for distilled models.
- `euler_ancestral`: adds noise each step; more variation and texture, slightly less stable.
- `dpmpp_2m`: strong general-purpose sampler; pairs well with `karras`.
- `dpmpp_2m_sde` and `dpmpp_3m_sde`: detailed, good for SDXL and photographic work; `3m` is slower.
- `dpmpp_3m_sde_gpu`: GPU variant of the same family.
- `ddim`: older, simple, useful for compatibility.
- `uni_pc`: high quality at low step counts; sometimes softer.
- `lcm`: for LCM/LCM-LoRA models, 4-8 steps, CFG 1-2.
- `res_multistep` / RES4LYF samplers: experimental, installed with RES4LYF.

## Scheduler choices

- `normal`: baseline schedule.
- `karras`: usually the best default; emphasizes low-noise detail.
- `exponential`: smooth, good for photographic models.
- `sgm_uniform`: common for SDXL and Flux-family graphs.
- `simple`: few-step distilled models.
- `beta`: stable, sometimes better at high step counts.
- `ddim_uniform`: matches DDIM sampling.

## Practical defaults

- SD 1.5: 20-30 steps, CFG 7-8, `dpmpp_2m` + `karras` or `euler_ancestral` + `normal`, 512x512.
- SDXL: 20-30 steps, CFG 5-7, `dpmpp_2m` + `karras`, 1024x1024.
- Flux dev: 20-30 steps, CFG 1.0, guidance 3.0-3.5, `euler` + `simple` or `dpmpp_2m`.
- Flux schnell: 1-4 steps, CFG 1.0.
- Qwen-Image: about 20 steps, CFG 2.5-4.0.
- Z-Image Turbo: about 8 steps, CFG 1.0.
- LCM or Lightning/Turbo LoRA: 4-8 steps, CFG 1-2, scheduler `simple` or `sgm_uniform`.

## Denoise

- Text-to-image: denoise 1.0.
- Image-to-image: 0.35-0.65 is the useful range. Low values keep composition; high values repaint more.
- Upscale pass or hires fix: 0.35-0.55. Above 0.7 the second pass often changes the image too much.
- Inpainting: 1.0 inside the mask with a dedicated inpaint model, or 0.5-0.8 with a normal model.
- A denoise of 0 with an img2img graph returns the input almost unchanged; that is expected, not a bug.

## Seed and batches

- A fixed seed plus unchanged settings reproduces an image; the seed widget may auto-increment after a queued run depending on ComfyUI settings.
- `batch_size` in the latent/image node creates several images in one run; it multiplies VRAM use.
- Changing width, height or batch size invalidates cached latents and often changes composition.
- Width and height should be multiples of 8; SDXL and Flux are usually trained around multiples of 64. Prefer 1024x1024, 832x1216, 1216x832.
- Video models care about frame count: use the value the template expects, not an arbitrary number.

## Common mistakes

- CFG 7 on a distilled model (Flux, turbo, LCM) burns the image.
- 4 steps on a normal SDXL checkpoint gives noise or mush.
- `ddim` with `karras` is legal but rarely optimal.
- A second KSampler without `VAEEncode` of the first result is not an img2img pass.
- The scheduler is a widget on `KSampler`; setting a nonexistent widget name does nothing. Confirm with `get_node_info` or `inspect_node`.
