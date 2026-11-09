import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const file = join(here, "..", "web", "agent.js");
const src = readFileSync(file, "utf8");
const lines = src.split(/\r?\n/);
const failures = [];

const tmp = mkdtempSync(join(tmpdir(), "ca-check-"));
try {
  const copy = join(tmp, "agent.mjs");
  writeFileSync(copy, src);
  execFileSync(process.execPath, ["--check", copy], { stdio: "pipe" });
} catch (e) {
  failures.push("web/agent.js does not parse as an ES module:\n" + (e.stderr?.toString() || e.message));
} finally {
  rmSync(tmp, { recursive: true, force: true });
}

function block(startLine, endLine) {
  const from = lines.findIndex((l) => l.startsWith(startLine));
  if (from < 0) throw new Error(`marker not found: ${startLine}`);
  if (lines[from].includes(endLine)) return lines[from];
  const to = lines.findIndex((l, i) => i > from && l.startsWith(endLine));
  if (to < 0) throw new Error(`end marker not found after ${startLine}: ${endLine}`);
  return lines.slice(from, to + 1).join("\n");
}

function literal(text) {
  return new Function(`return (${text});`)();
}

function fnSource(name) {
  const at = src.indexOf(`function ${name}(`);
  if (at < 0) throw new Error(`function not found: ${name}`);
  let depth = 0, p = src.indexOf("(", at);
  for (let k = p; k < src.length; k++) {
    if (src[k] === "(") depth++;
    else if (src[k] === ")") {
      depth--;
      if (depth === 0) { p = k; break; }
    }
  }
  let i = src.indexOf("{", p);
  for (let k = i; k < src.length; k++) {
    if (src[k] === "{") depth++;
    else if (src[k] === "}") {
      depth--;
      if (depth === 0) return src.slice(at, k + 1);
    }
  }
  throw new Error(`unbalanced function: ${name}`);
}

const localeBlocks = {
  en: "const EN = {",
  ru: "const RU_STR = {",
  de: "const DE_STR = {",
  pl: "const PL_STR = {",
  fr: "const FR_STR = {",
};
const locales = {};
for (const [lang, marker] of Object.entries(localeBlocks)) {
  try {
    locales[lang] = literal(block(marker, "};").replace(/^const \w+ = /, "").replace(/;$/, ""));
  } catch (e) {
    failures.push(`cannot read ${lang} locale: ${e.message}`);
  }
}

const keysUsed = new Set([...src.matchAll(/\bt\("([^"\\]+)"/g)].map((m) => m[1]));
if (locales.en) {
  for (const key of keysUsed) {
    if (!(key in locales.en)) failures.push(`missing English i18n key: ${key}`);
  }
  for (const [lang, dict] of Object.entries(locales)) {
    for (const key of Object.keys(locales.en)) {
      if (!(key in dict)) failures.push(`${lang} i18n misses key: ${key}`);
    }
  }
}

const tools = {};
try {
  const body = block("const TOOLS = {", "};").split("\n");
  const starts = [];
  body.forEach((line, i) => {
    const m = /^  ([a-z][a-z0-9_]*): \{$/.exec(line);
    if (m) starts.push({ name: m[1], line: i });
  });
  starts.forEach((tool, i) => {
    const end = i + 1 < starts.length ? starts[i + 1].line : body.length - 1;
    tools[tool.name] = body.slice(tool.line, end).join("\n");
  });
} catch (e) {
  failures.push("cannot read TOOLS: " + e.message);
}

for (const [name, body] of Object.entries(tools)) {
  if (!/\bdesc:/.test(body)) failures.push(`tool ${name} has no desc`);
  if (!/\bparams:/.test(body)) failures.push(`tool ${name} has no params`);
  if (!/\brun:/.test(body)) failures.push(`tool ${name} has no run`);
}

for (const marker of ["SEARCH_TOOLS", "SMALLTALK_TOOLS", "RETRY_SAFE_TOOLS", "REPLACE_TOOLS", "QUIET_TOOLS", "AUTO_CHECK_SKIP"]) {
  try {
    const text = block(`const ${marker} = new Set([`, "]);");
    const names = [...text.matchAll(/"([a-z][a-z0-9_]*)"/g)].map((m) => m[1]);
    for (const name of names) {
      if (!(name in tools)) failures.push(`${marker} references unknown tool: ${name}`);
    }
  } catch (e) {
    failures.push(`cannot read ${marker}: ${e.message}`);
  }
}

if (!Object.keys(tools).length) failures.push("no tools found");

if (tools.find_nodes) {
  if (!/Partial words/i.test(tools.find_nodes)) failures.push("find_nodes does not tell the model that partial words work");
  if (!/again/i.test(tools.find_nodes)) failures.push("find_nodes does not tell the model to search again with another word");
  if (!/search_aliases|aliases/i.test(tools.find_nodes)) failures.push("find_nodes does not expose the search aliases");
} else {
  failures.push("tool find_nodes is missing");
}

const css = readFileSync(join(here, "..", "web", "agent.css"), "utf8");
const backend = readFileSync(join(here, "..", "agent_server.py"), "utf8");

if (!/never invent a class name/i.test(backend)) failures.push("the system prompt does not forbid guessing class names");
if (!/there is no "load glb" node/i.test(backend)) failures.push("the system prompt does not name the 3D loader");

const themeMatch = /const THEMES = \[([^\]]*)\];/.exec(src);
if (!themeMatch) {
  failures.push("THEMES list is missing");
} else {
  const ids = [...themeMatch[1].matchAll(/"([^"]+)"/g)].map((m) => m[1]);
  if (ids.join(",") !== "comfy,claude,lux,colors") failures.push(`unexpected themes: ${ids.join(", ")}`);
  for (const id of ids) {
    if (id !== "comfy" && !css.includes(`.ca-theme-${id}`)) failures.push(`theme ${id} has no .ca-theme-${id} styles`);
    if (!css.includes(`.ca-pv.p-${id}`)) failures.push(`theme ${id} has no preview thumbnail styles`);
    const key = "theme" + id[0].toUpperCase() + id.slice(1);
    for (const [lang, dict] of Object.entries(locales)) {
      if (!(key in dict)) failures.push(`${lang} i18n misses theme key: ${key}`);
    }
  }
}

for (const symbol of ["LS_DARK", "function setDark(", "ca-dark", "ca-theme-grid", "ca-theme-card", "ca-lever", "ca-gold-flow", "ca-settings-tab-ind", "ca-panel-in", "ca-tab-next"]) {
  const hay = symbol.startsWith("ca-") || symbol === "LS_DARK" ? css + src : src;
  if (!hay.includes(symbol)) failures.push(`missing theme control: ${symbol}`);
}
if (!/\.ca-theme-grid\s*\{/.test(css)) failures.push("theme preview grid styles are missing");
if (!/\.ca-lever\.on\b/.test(css)) failures.push("theme light/dark lever styles are missing");


for (const symbol of ["function loadTheme(", "function applyTheme(", "function setTheme(", "function openImageEditor(", "function edApplyCrop(", "function edUndo(", "function edRedo(", "async function runCompatCheck(", "SETTINGS_TAB", "function selectSettingsTab(", "function syncSettingsTabs(", "async function planPreflight(", "function planNodeCandidates(", "function renderPreflight(", "function nodeAlternatives(", "function slotSummary(", "function groupSlotNames(", "function nodeTypeSummary(", "function findAtt(", "function attNames(", "function chatAtts(", "function pickFileWidget(", "function attChip(", "function attSizeLabel(", "function setFileWidget(", "function setWidgetSafe(", "function setWidgetsSafe(", "function uploadAttachment(", "function shrinkChatContext(", "function createLoaderNode(", "function loaderFileWidget(", "function insertAttachmentNode(", "function nodeIndex(", "function queryTokens(", "function scoreNodes(", "function searchNodes(", "function suggestNodes(", "async function compactChat(", "function ctxBudgetChars(", "function isCtxOverflow("]) {
  if (!src.includes(symbol)) failures.push(`missing frontend function: ${symbol}`);
}
for (const selector of [".ca-editor-overlay", ".ca-editor-canvas", ".ca-editor-tool", ".ca-compat-row", ".ca-settings-tabs", ".ca-settings-tab", ".ca-settings-section", ".ca-settings-tab-ind", ".ca-preflight", ".ca-pf-item", ".ca-pf-phase", ".ca-chip.att .ca-att-name", ".ca-chip.att .ca-att-size", ".ca-chip.att .ca-att-path"]) {
  if (!css.includes(selector)) failures.push(`missing CSS selector: ${selector}`);
}
for (const key of ["tabAI", "tabCustom", "tabLogs", "planPreflight", "planPhaseSetup", "planPhaseBuild", "attInInput", "attUploadFailed", "ctxRescued", "attToCanvas", "attAdded"]) {
  if (!(key in (locales.en || {}))) failures.push(`missing English settings tab key: ${key}`);
}
if (!tools.apply_attachment) failures.push("tool apply_attachment is missing");
if (!/\bapply_attachment\b/.test(src)) failures.push("apply_attachment is not referenced in the frontend");
if (!tools.check_model_setup) {
  failures.push("tool check_model_setup is missing");
} else {
  const cm = tools.check_model_setup;
  if (!/missing/i.test(cm)) failures.push("check_model_setup does not report the missing files");
  if (!/folder/i.test(cm)) failures.push("check_model_setup does not report the models folder");
  if (!/loader/i.test(cm)) failures.push("check_model_setup does not report the loader node");
  if (!/prompt/i.test(cm)) failures.push("check_model_setup does not report the prompt style");
}
if (tools.generate && !/batch/.test(tools.generate)) failures.push("tool generate has no batch parameter");
if (tools.run_workflow && !/batch/.test(tools.run_workflow)) failures.push("tool run_workflow has no batch parameter");
for (const symbol of ["const MODEL_FAMILIES = [", "function modelFamily(", "function comboFiles(", "function matchFiles(", "const BATCH_MAX = 8", "function planBatch(", "function waitForPrompts("]) {
  if (!src.includes(symbol)) failures.push(`missing model readiness helper: ${symbol}`);
}
if (!/check_model_setup/.test(src)) failures.push("check_model_setup is not referenced in the frontend");
if (!/check_model_setup/.test(backend)) failures.push("the backend system prompt does not use check_model_setup");
if (!/\bbatch\b/.test(backend)) failures.push("the backend system prompt does not mention the batch parameter");
if (!/no negative prompt field/i.test(backend)) failures.push("the system prompt does not explain what to do when there is no negative prompt field");
const knowledge = join(here, "..", "knowledge", "model-prompting.md");
if (!existsSync(knowledge)) {
  failures.push("knowledge/model-prompting.md is missing");
} else {
  const kb = readFileSync(knowledge, "utf8");
  for (const token of ["FLUX.1", "Z-Image", "Qwen-Image", "negative prompt"]) {
    if (!kb.includes(token)) failures.push(`knowledge/model-prompting.md does not mention: ${token}`);
  }
}

try {
  const plan = new Function(
    "randSeed",
    ["cloneJson", "batchLatentId", "seedInputIds", "planBatch"].map(fnSource).join("\n") + "\nreturn planBatch;",
  )(() => 777);
  const withLatent = {
    "1": { class_type: "EmptyLatentImage", inputs: { width: 1024, height: 1024, batch_size: 1 } },
    "2": { class_type: "KSampler", inputs: { seed: 5, steps: 20 } },
  };
  const native = plan(withLatent, 4);
  if (native.mode !== "native") failures.push(`batch plan did not use the native batch: ${native.mode}`);
  if (native.runs.length !== 1) failures.push("the native batch must stay one run");
  if (native.runs[0].output["1"].inputs.batch_size !== 4) failures.push("the native batch does not set batch_size");
  if (withLatent["1"].inputs.batch_size !== 1) failures.push("the native batch must not change the canvas payload");

  const withoutLatent = {
    "1": { class_type: "VAEEncode", inputs: { pixels: ["2", 0] } },
    "3": { class_type: "KSampler", inputs: { seed: 5, steps: 20 } },
  };
  const queued = plan(withoutLatent, 3);
  if (queued.mode !== "queued") failures.push(`batch plan did not queue the runs: ${queued.mode}`);
  if (queued.runs.length !== 3) failures.push("the queued batch must have one run per shot");
  const seeds = queued.runs.map((r) => r.output["3"].inputs.seed);
  if (seeds.join(",") !== "5,6,7") failures.push(`the queued batch seeds are wrong: ${seeds.join(",")}`);
  if (withoutLatent["3"].inputs.seed !== 5) failures.push("the queued batch must not change the canvas payload");

  const linked = { "1": { class_type: "EmptyLatentImage", inputs: { batch_size: ["9", 0] } } };
  if (plan(linked, 2).mode !== "queued") failures.push("a linked batch_size must not be treated as a widget");

  const linkedSeed = { "3": { class_type: "KSampler", inputs: { seed: ["7", 0] } } };
  const linkedPlan = plan(linkedSeed, 2);
  if (linkedPlan.runs[0].output["3"].inputs.seed === linkedPlan.runs[1].output["3"].inputs.seed) failures.push("a linked seed must still give different shots");
  if (!linkedPlan.runs.every((r) => typeof r.output["3"].inputs.seed === "number")) failures.push("a linked seed must become a number in the queued run");

  const single = plan(withLatent, 1);
  if (single.mode !== "single" || single.runs.length !== 1) failures.push("a single shot must stay a single run");
  if (single.runs[0].output !== withLatent) failures.push("a single shot must use the payload as it is");
} catch (e) {
  failures.push("cannot test the batch plan: " + e.message);
}
try {
  const runAt = src.indexOf("\n  set_prompt: {");
  const bodyAt = src.indexOf("\n    run: async", runAt);
  const braceAt = src.indexOf("{", src.indexOf("=>", bodyAt));
  let depth = 0;
  let end = -1;
  for (let k = braceAt; k < src.length; k++) {
    if (src[k] === "{") depth++;
    else if (src[k] === "}") { depth--; if (depth === 0) { end = k; break; } }
  }
  if (runAt < 0 || bodyAt < 0 || end < 0) throw new Error("the set_prompt tool is missing");
  const runSrc = src.slice(src.indexOf("async", bodyAt), end + 1);
  const applied = [];
  const setPrompt = new Function("findPromptTargets", "setWidget", "commit", "return " + runSrc)(
    () => targets,
    (node, name, value) => applied.push(`${node.id}.${name}=${value}`),
    () => {},
  );
  const pos = { node: { id: 4, type: "CLIPTextEncode" }, widget: { name: "text" } };
  const neg = { node: { id: 5, type: "CLIPTextEncode" }, widget: { name: "text" } };

  let targets = { positive: pos, negative: null, all: [pos] };
  let res = JSON.parse(await setPrompt({ positive: "a cat", negative: "blurry" }));
  if (res.skipped.length !== 1) failures.push("a missing negative prompt field must be skipped, not rejected");
  if (!/do not call this tool again/i.test(res.skipped[0] || "")) failures.push("the skipped negative prompt does not tell the model to stop retrying");
  if (res.updated.length !== 1 || !/positive/.test(res.updated[0])) failures.push("the positive prompt must still be applied when the negative one is skipped");

  targets = { positive: pos, negative: neg, all: [pos, neg] };
  res = JSON.parse(await setPrompt({ positive: "a cat", negative: "blurry" }));
  if (res.skipped.length) failures.push("an existing negative prompt field must be used");
  if (res.updated.length !== 2) failures.push("the negative prompt was not applied");

  targets = { positive: null, negative: null, all: [] };
  let failed = false;
  try { await setPrompt({ positive: "a cat" }); } catch { failed = true; }
  if (!failed) failures.push("a missing positive prompt field must still be rejected");
} catch (e) {
  failures.push("cannot test the prompt tool: " + e.message);
}
for (const symbol of [
  "const fxNodes = new Map()",
  "function fxAppear(",
  "function fxHighlight(",
  "function fxDraw(",
  "function fxPatchCanvas(",
  "function fxNodePath(",
  "function fxApplyDom(",
  "function fxOverlay(",
  "function fxTick(",
]) {
  if (!src.includes(symbol)) failures.push(`missing canvas animation helper: ${symbol}`);
}
const hlSource = fnSource("highlightChanges");
if (/bgcolor|boxcolor/.test(hlSource)) failures.push("the node highlight still changes the node colors");
if (!/fxHighlight\(/.test(hlSource)) failures.push("the node highlight does not use the animated outline");
if (!/fxAppear\(/.test(src)) failures.push("the appearance animation is not called");
if (!/\.ca-fx-node/.test(css)) failures.push("the canvas animation styles are missing");
try {
  const fxSource = [
    "const FX_APPEAR_MS = 420;",
    "const FX_HIGHLIGHT_MS = 4200;",
    "const FX_STAGGER_MS = 55;",
    "const FX_RADIUS = 8;",
    "const fxNodes = new Map();",
    "let fxFrame = null;",
    "let fxColors = { at: -1e9, ok: '#4cc38a', warn: '#e8b04a', accent: '#6d9cff' };",
    ["fxThemeColors", "fxReducedMotion", "fxColorRgba", "fxNodeEl", "fxLayerScale", "fxTranslate", "fxAppearProgress", "fxPatchCanvas", "fxAttach", "fxTitleHeight", "fxNodePath", "fxDraw", "fxOverlay", "fxApplyDom", "fxCleanup", "fxLoop", "fxTick", "fxAppear", "fxHighlight", "clearHighlight"].map(fnSource).join("\n"),
  ].join("\n");
  const fx = new Function(
    "app",
    "ui",
    "LG",
    "performance",
    "requestAnimationFrame",
    "getComputedStyle",
    "window",
    "document",
    fxSource + "\nreturn { fxAppear, fxHighlight, fxNodes, clearHighlight, fxTick };",
  );
  const node = { id: 7, renderingSize: [220, 90], renderingShape: 2, title_mode: 0, onDrawForeground: null };
  const strokes = [];
  const scales = [];
  const ctx = {
    globalAlpha: 1,
    strokeStyle: "",
    lineWidth: 0,
    shadowColor: "",
    shadowBlur: 0,
    save() {},
    restore() {},
    beginPath() {},
    roundRect() {},
    rect() {},
    arc() {},
    scale(x, y) { scales.push([x, y]); },
    translate() {},
    stroke() { strokes.push({ style: this.strokeStyle, width: this.lineWidth, alpha: this.globalAlpha }); },
  };
  const canvas = {
    getNodeModeAlpha: () => 1,
    drawNode: () => {},
    setDirtyCanvas: () => {},
  };
  const app = { canvas, graph: { setDirtyCanvas: () => {}, getNodeById: () => node } };
  const ui = { root: {} };
  const getComputedStyle = () => ({
    getPropertyValue: (name) => ({ "--ca-ok": "#2f8f5b", "--ca-warn": "#b7791f", "--ca-accent": "#c96442" })[name] || "",
  });
  const fakeWindow = { matchMedia: () => ({ matches: false }) };
  const clock = { now: () => 1000 };
  const layer = { children: [], appendChild(el) { this.children.push(el); el.parentElement = this; el.isConnected = true; } };
  const fades = [];
  const nodeEl = {
    style: { transform: "translate(1280px, 290px)", setProperty(k, v) { this[k] = v; } },
    offsetWidth: 270,
    offsetHeight: 405,
    parentElement: layer,
    animate: (frames, opts) => { fades.push({ frames, opts }); return { cancel() {} }; },
  };
  const fakeDocument = {
    querySelector: (sel) => (sel.includes('"7"') ? nodeEl : null),
    createElement: () => ({ style: { setProperty(k, v) { this[k] = v; } }, className: "", parentElement: null, isConnected: false, remove() { this.isConnected = false; } }),
  };
  const api = fx(app, ui, () => ({ NODE_TITLE_HEIGHT: 30 }), clock, () => 1, getComputedStyle, fakeWindow, fakeDocument);

  api.fxHighlight(node, "added");
  if (node.bgcolor !== undefined || node.boxcolor !== undefined) failures.push("the highlight changed the node colors");
  if (typeof node.onDrawForeground !== "function") failures.push("the highlight did not install a draw hook");
  if (canvas.getNodeModeAlpha(node) !== 1) failures.push("the patched alpha changed a node without an animation");
  node.onDrawForeground(ctx, canvas, null);
  if (!strokes.length) failures.push("the highlight did not draw an outline");
  else {
    const last = strokes[strokes.length - 1];
    if (last.style !== "#2f8f5b") failures.push(`the highlight outline does not use the theme color: ${last.style}`);
    if (!(last.alpha > 0)) failures.push("the highlight outline is not visible");
  }
  api.fxTick(1000);
  if (!layer.children.length) failures.push("the highlight did not add an overlay to the node");
  else {
    const overlay = layer.children[0];
    if (!/ca-fx-pulse/.test(overlay.className)) failures.push(`the overlay is not pulsing: ${overlay.className}`);
    if (overlay.style["--ca-fx-color"] !== "#2f8f5b") failures.push(`the overlay does not use the theme color: ${overlay.style["--ca-fx-color"]}`);
  }
  api.fxAppear(node);
  if (!(canvas.getNodeModeAlpha(node) < 1)) failures.push("the appearance animation does not fade the node in");
  canvas.drawNode(node, ctx);
  if (!scales.length) failures.push("the appearance animation does not scale the node");
  api.fxTick(1000);
  if (!fades.length) failures.push("the appearance animation does not fade the node element");
  else {
    const fade = fades[fades.length - 1];
    if (fade.frames[0].opacity !== 0 || fade.frames[fade.frames.length - 1].opacity !== 1) failures.push("the node fade does not go from hidden to visible");
    if (!(fade.opts.duration > 0)) failures.push("the node fade has no duration");
    if (fade.opts.delay === undefined || fade.opts.fill !== "backwards") failures.push("the node fade does not wait for its stagger delay");
  }
  api.clearHighlight();
} catch (e) {
  failures.push("cannot test the canvas animations: " + e.message);
}
for (const marker of [
  '@routes.get("/crazy_agent/compatibility")',
  "def compatibility_report()",
  "def public_download_redirect(",
  "def persona_name(",
  "persona_name(cfg.get(\"agent_name\")",
  '"agent_name": ""',
  '"user_name": ""',
  "allow_redirects=False",
  '"--no-recurse-submodules"',
  ".installing",
  '@routes.get("/crazy_agent/preflight")',
  "def preflight_nodes(",
  "def pack_declared_classes(",
  '@routes.get("/crazy_agent/model_context")',
  "def estimate_prompt_tokens(",
  "def fit_context(",
  "def strip_images(",
  "def trim_history(",
  "def clean_orphans(",
  "def thought_signature(",
  "def openai_calls(",
  "extra_content",
  "CONTEXT_RESERVE",
]) {
  if (!backend.includes(marker)) failures.push(`backend is missing: ${marker}`);
}
for (const marker of ["agent_name", "user_name", "ca-name-field"]) {
  if (!src.includes(marker) && !css.includes(marker)) failures.push(`frontend is missing: ${marker}`);
}
if (!/\.ca-name-field \.ca-sub\s*\{/.test(css)) failures.push("persona name field styles are missing");

if (failures.length) {
  console.error(failures.join("\n"));
  console.error(`\n${failures.length} frontend check(s) failed`);
  process.exit(1);
}
console.log(`Frontend checks passed: ${Object.keys(tools).length} tools, ${keysUsed.size} i18n keys, ${Object.keys(locales).length} locales.`);
