---
title: Model prompting and model selection
tags: prompting, prompt style, model selection, flux, flux.2, qwen, qwen-image, z-image, ideogram, hidream, hunyuan, anima, chroma, negative prompt, template, edit, typography
---

## Universal prompt rules

1. Identify the exact model family and task variant first: base/T2I, Turbo/distilled, edit, inpaint, fill, refiner or reference-conditioned.
2. Do not assume every model wants the same syntax. Use JSON only when the model or workflow expects structured JSON, otherwise natural-language prose.
3. Describe the intended final image, not the steps for drawing it. For an editor, state what must change and what must remain unchanged.
4. Put the most important subject and action first, then composition, environment, lighting, materials, style, color, camera/lens and fine details.
5. Be explicit about text that must appear: quote the exact wording, preserve capitalization and punctuation, specify placement, typography and hierarchy. Do not ask for text unless it is needed.
6. Avoid contradictory attributes ("overhead view" plus "eye-level portrait"), long synonym chains and decorative prompt noise.
7. Use a negative prompt only when the workflow consumes it. At CFG 1 the negative branch is skipped and the negative prompt is inert.
8. For editing, distinguish the source image from reference images, name references explicitly (`<image1>`) and describe their roles.
9. For photorealism specify subject, scene, light source and direction, lens/framing, depth of field, surface detail and realistic color response. Generic quality tags are not a substitute for a concrete description.
10. Keep the official workflow resolution, aspect ratio, sampler, scheduler, CFG and step schedule. A prompt cannot fix an incompatible sampler configuration.
11. If the model has a prompt enhancer, decide whether to enable it. Do not manually over-expand a prompt and then let an enhancer expand it again.
12. If the prompt format is uncertain, write plain language first and check the official model card and workflow before inventing a schema.

## Choosing a model for the task

| Family | Best for | Prompt style | Caution |
|---|---|---|---|
| FLUX.1 Dev | High-quality general images, product and lifestyle photography, detailed illustration | Rich natural-language paragraph | Be concrete, avoid tag soup |
| FLUX.1 Schnell | Fast drafts and iteration | Short to medium natural language | Distilled, weak adherence to dense instructions |
| FLUX.1 Fill | Inpainting, outpainting, object replacement | Local edit instruction plus context | Describe the masked region, preserve the rest |
| FLUX.1 Kontext | Image editing and multi-turn visual changes | Direct imperative edit instructions | Say exactly what changes and what stays |
| FLUX.2 Dev | High-fidelity generation, multi-reference workflows | Detailed natural-language scene | Give each reference a role |
| FLUX.2 Klein 4B/9B | Faster generation and editing, compact variants | Direct, concise natural language | Match the encoder size to the model |
| Z-Image Turbo | Fast photorealistic and general T2I, strong prompt following for its size | Clear natural-language paragraph | Avoid negative-prompt engineering, keep the Turbo schedule |
| Qwen Image 1.x / 2512 | Text rendering, posters, infographics, general images | Detailed prose, quote exact text | Needs its own Qwen encoder and VAE |
| Qwen-Image-2.1 Base | Dense instructions, text, numbers, complex scenes | Detailed prose with explicit spatial relationships | Negative prompt may be inert at CFG 1 |
| Qwen-Image-2.1 Turbo | Fast version of Qwen 2.1 | Concise but specific prose | Keep the fixed 8-step schedule |
| Qwen-Image-2.1 Edit | Instruction editing with multiple references | Explicit edit instruction with `<image1>`, `<image2>` | Assign each image a role |
| Hunyuan Image 2.1 | Detailed images, typography and glyph rendering | Detailed prose, exact text strings | The ByT5 glyph encoder matters for text-heavy tasks |
| HiDream I1 | High-quality general T2I, artistic and photographic work | Rich descriptive prose | Multi-encoder conditioning workflow |
| HiDream E1.1 | Image editing | Explicit natural-language edit instruction | Separate source image from references |
| OmniGen2 | Instruction following, multi-image reasoning | Conversational, task-oriented instructions | Explain the role of every input image |
| Anima Base v1.0 | Anime, manga-inspired and stylized illustration | Character-sheet and art-direction prose | Specify linework, cel shading and palette |
| Chroma | General generation and style exploration | Natural-language description | Verify the Chroma variant, do not assume SDXL syntax |
| Stable Cascade | Legacy staged high-quality generation | Clear descriptive prose | Stage C, Stage B and VAE are separate stages |
| LongCat Image | General generation and instruction-driven visual tasks | Natural language, clear subject and action | Check the exact official task workflow |
| Ideogram 4 | Typography-led design, posters, logos, packaging, layouts | Structured JSON caption with bounding boxes | Plain prose may underperform |
| Krea 2 Turbo | Fast aesthetic and design-oriented generation | Concise art-direction prose | Follow the official Krea workflow, not Ideogram JSON |
| MOSS-Image Base/SFT | General generation and instruction following | Natural language | Base and SFT differ in adherence |
| ERNIE Image | Text-aware generation and designed compositions | Structured explicit prose, exact text in quotes | Needs the matching encoder, VAE and workflow |
| PixelDiT | Pixel-space generation, high-resolution pixel-native workflows | Concrete visual description | No conventional VAE latent decode path |
| Boogu Image Turbo / Edit | Fast generation and editing | Concise natural language, direct edit instruction | Keep the Turbo schedule, state preservation |
| JoyAI Image Edit | Semantic editing and transformations | Natural-language instruction | Preserve identity explicitly |
| Mage-Flow Base/Turbo/Edit | General quality, fast generation, instruction editing | Detailed, concise or direct per variant | Do not transplant settings between flows |

## Prompting per family

- FLUX.1 Dev: one coherent paragraph. Shot type, subject and action, environment, composition, light direction and quality, materials and surface detail, palette, lens and depth of field. Quote exact text only when required.
- FLUX.1 Schnell: compact version of the Dev prompt. Subject, action, setting, one or two decisive style and lighting details.
- FLUX.1 Fill: what belongs inside the masked area, how it integrates (perspective, lighting, scale, material, contact shadows), and that unmasked areas stay unchanged. For removal ask for a plausible background continuation.
- FLUX.1 Kontext: change target, desired result, preservation constraints. Do not re-describe the whole image.
- FLUX.2 Dev: detailed description plus a role per reference image (identity, product, environment, pose, palette, style).
- FLUX.2 Klein: clear direct prose, core subject first, purposeful modifiers, and for edits the requested change plus what stays.
- Z-Image Turbo: natural-language paragraph with explicit subject, action, environment, framing, lighting and details. Precise spatial language ("left foreground", "centered", "soft background blur"). Distilled: start from the official Turbo sampling settings.
- Qwen Image 1.x: explicit and literal. Exact words in quotation marks, capitalization, line breaks, font character, alignment, placement, layout as regions.
- Qwen-Image-2.1 Base: complete structured description. Object counts, positions, orientation, relative scale, interactions, quoted text, typography. Official base workflow is around 25 steps, CFG 1, Euler, Simple; at CFG 1 the negative prompt has no effect, CFG 2 can help dense prompts and small text but may over-sharpen.
- Qwen-Image-2.1 Turbo: same as Base with fewer clauses. Keep 8 steps, CFG 1, Euler and the fixed ManualSigmas schedule.
- Qwen-Image-2.1 Edit: `Using <image1> as the source image, [edit]. Use <image2> only as a reference for [role]. Preserve [features]. Do not change [constraints].`
- Hunyuan Image 2.1: scene description and composition, then every exact text string with placement and typography. Multilingual or small lettering needs exact characters.
- HiDream I1: rich description of the finished frame, subject hierarchy, precise nouns and verbs, medium and lighting.
- HiDream E1.1: target, object or region, desired change, what must remain untouched, and the role of a second image.
- OmniGen2: write it as a precise instruction to an image editor. Label each input image by role, state the target result and the constraints.
- Anima Base v1.0: character identity and stable traits, pose, expression, clothing, framing, background, line weight, cel shading, highlight style, palette and rendering finish.
- Chroma: descriptive natural language. Test whether the checkpoint uses negative conditioning before relying on it.
- Stable Cascade: clear descriptive prompt; the staged pipeline still has to be wired correctly.
- LongCat Image: direct natural language with subject, action, composition, context, style, plus text if needed and preservation constraints for edits.
- Ideogram 4: structured JSON. `high_level_description`, `style_description` (aesthetics, lighting, medium, art_style, color_palette), `compositional_deconstruction` with `background` and an ordered `elements` list. Each element has `type` ("obj" or "text"), `bbox`, `desc`, `color_palette`, and text elements keep the exact string in `text`. No comments, no trailing commas, validate before sending. The coordinate convention comes from the installed prompt builder.
- Krea 2 Turbo: concise art direction. Subject and concept, medium, composition, palette, lighting, mood. Not Ideogram JSON.
- MOSS-Image: SFT accepts explicit instructions, Base stays on subject, setting, style and composition.
- ERNIE Image: layout and hierarchy explicit, text quoted, location and font character named.
- PixelDiT: describe the final image directly, no VAE decode assumptions.
- Boogu Image: Turbo keeps the prompt short and medium; Edit states the imperative, the target, the result and the preservation constraints.
- JoyAI Image Edit: separate what changes from what remains, preserve identity, hairstyle, pose, clothing and framing.
- Mage-Flow: Base detailed scene description, Turbo concise high-priority description, Edit direct instruction plus preservation constraints.

## Task prompt patterns

- Photorealistic portrait: editorial portrait of the subject, age range and expression, looking direction, framing and camera angle, environment, key light direction with fill or rim light, skin texture, hair, hands, filmic grading, lens and depth of field.
- Product photography: commercial product photograph, orientation and placement, surface and background, softbox key light direction with fill and rim, material reflections, crisp edges, contact shadow, camera angle and lens, no extra labels beyond the quoted text.
- Poster and typography: Ideogram 4 JSON. For other text-capable models describe each text block separately and quote exact strings, with reading order, alignment, hierarchy and negative space.
- Image editing: in the source image change only the target, preserve identity, pose, composition, perspective, background and lighting, match color temperature, shadows, texture, grain and depth of field, add nothing else.
- Character design: identity and stable traits, pose and action, expression, clothing, shot type and angle, background, art style with linework, shading, palette and lighting, and the distinctive features to keep.

## Negative prompt policy

- Do not add a negative prompt by default for every model.
- When the workflow runs CFG 1 and skips the unconditional branch, the negative prompt is inert. Do not spend prompt budget on it.
- When negative conditioning is active, use a short list of concrete failure modes for the task (extra fingers, duplicated objects, unreadable text, watermark).
- Avoid generic mega-negative prompts. They suppress wanted details and rarely map onto instruction-following models.
- For editing models, preservation instructions in the positive prompt matter more than a long negative prompt.

## How to write the prompt for a model

1. Classify the task: T2I, I2I, inpainting, outpainting, text-heavy design, multi-reference composition or edit.
2. Choose the model whose strengths match the task. Ideogram 4 for precise typography, Qwen Image or Hunyuan Image for text, FLUX.1/2 Dev for general fidelity, a Turbo variant for speed, Anima for anime, PixelDiT for pixel-space, an editing model for edits.
3. Check the exact workflow and see whether it expects plain text, JSON, image markers or a prompt-enhancer input.
4. Build the prompt from the matching family section above.
5. Include exact text only when requested. Never invent brand names, logos or copy.
6. Label the role of every reference image and use the exact markers the workflow requires.
7. Check for contradictions, missing spatial relationships and unnecessary verbosity.
8. Check whether negative conditioning is active at the chosen CFG and workflow settings.
9. Return the prompt in the format the node expects. JSON only when the node expects JSON, and validate it.
10. Never claim a model is best at everything. Explain the trade-off: quality, speed, text rendering, editing, style or VRAM.

## Confidence and sources

The model card, the official ComfyUI workflow JSON and the current node implementation win over any prompting advice here. Verify sampler settings, negative-prompt behaviour, JSON key names, image marker syntax and bounding-box conventions against the workflow in use.

- The workflow the user already has is the authority: read it with get_graph or list_workflows.
- Official templates: list_templates and read_template.
- Unknown model: model_lookup returns the official repository data.
