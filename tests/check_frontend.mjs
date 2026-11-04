import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
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
