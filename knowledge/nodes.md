---
title: Native nodes and what they are for
tags: nodes, native, loader, class name, display name, core, 3d, image, video, audio, sampler, checkpoint
---

## How to name a node

- The class name is what tools need: `Load3D`, `LoadImage`, `KSampler`.
- The display name is what the user sees in the canvas: `Load 3D & Animation`, `Load Image`, `KSampler`.
- Never invent a class name and never search for a file format instead of the node. There is no "load glb" node: the 3D loader is `Load3D` ("Load 3D & Animation"), it loads glb, gltf, obj, fbx, stl, ply and splat files.
- Confirm the exact class name with `find_nodes` using a SHORT partial word ("3d", "checkpoint", "upscale"). `get_node_info` shows the real inputs of a class name.
- Installed packs add their own nodes. `list_custom_nodes` shows which packs exist and what they are for.

## Loading files

- Images: `LoadImage` ("Load Image"). Widget `image`, value is a file name from the input folder.
- 3D models and splats: `Load3D` ("Load 3D & Animation"). Widget `model_file`, value is the exact path such as `3d/car.glb`. It also renders the model, so its image output can feed image nodes. `Load3DAdvanced` adds viewport and camera inputs.
- Video: `VHS_VideoCombine` in the Video Helper Suite pack, or `SaveAnimatedWEBP` in core. Video loaders live in packs.
- Audio: `LoadAudio` in core, `SaveAudio` in core.
- Checkpoints: `CheckpointLoaderSimple` ("Load Checkpoint") gives MODEL, CLIP and VAE. `UNETLoader`, `VAELoader`, `CLIPLoader` and `LoraLoader` load the parts separately.
- ControlNet: `ControlNetLoader` plus `ControlNetApply` or `ControlNetApplyAdvanced`.
- Upscalers: `ImageUpscaleWithModel` (model file) and `ImageScale` (plain resize).

## Generating

- `KSampler` ("KSampler") is the standard sampler: model, positive, negative, latent, denoise, seed, steps, cfg, sampler_name, scheduler.
- `KSamplerAdvanced` adds start/end step, so it is the one for samplers that need a custom step range.
- `SamplerCustom` with `BasicGuider` and `BasicScheduler` for full manual control, `CFGGuider` when the CFG scale is fixed.
- `EmptyLatentImage` for the starting latent, `VAEDecode` to turn a latent into an image, `VAEEncode` for the opposite direction.
- `CLIPTextEncode` ("CLIP Text Encode (Prompt)") for positive and negative conditioning. `ConditioningCombine` merges two conditionings, `ConditioningControlNet` applies ControlNet.

## Editing images

- `ImageScale`, `ImageScaleBy`, `ImageUpscaleWithModel` for size.
- `ImageComposite` and `ImageCompositeMasked` for pasting, `ImageBlend` for mixing with a mask, `ImageBatch` for stacking.
- `ImageCrop` and `ImagePadForOutpaint` for framing, `ImageFlip`, `ImageRotate`.
- `ImageQuantize` for palette work, `ImageRemoveBackground` for cutouts.
- `SaveImage` ("Save Image") writes the result to the output folder, `PreviewImage` shows it in the canvas only.

## 3D and splats

- `Load3D` ("Load 3D & Animation") loads the model and renders it.
- `Preview3DAdvanced` shows a mesh in the viewer, `SaveGLB` writes the mesh to a `.glb` file.
- `Save3DAdvanced` writes meshes, `SaveGaussianSplat` and `SavePointCloud` write splats and point clouds.
- `PreviewGaussianSplat` and `PreviewPointCloud` show them.
- `MeshToFile3D` turns a mesh into a file path, `RotateMesh` fixes the orientation, `MergeMeshes` combines meshes, `GetMeshInfo` reports vertices and faces.
- Image-to-3D and 3D-to-image live in packs such as Hunyuan3D or Stable3D. Read the pack docs and its templates first.

## Utility nodes

- `Reroute` for tidy links, `Note` for comments, `PrimitiveNode` for a value, `Group` for a visual group.
- `PreviewAny` shows any output type, `Anything Everywhere` (pack) copies a value to many nodes.

## Checklist before building

1. Did the user ask for a 3D file? Then the loader is `Load3D`, not `LoadImage`, and not a "load glb" node.
2. Does the class name exist? `find_nodes` with a partial word, then `get_node_info` for the inputs.
3. Are the file values real names from the input folder? `list_assets` lists them.
4. Does the graph end in an output node? `SaveImage`, `SaveGLB`, `Save3DAdvanced`, `SaveGaussianSplat` or a preview node.
