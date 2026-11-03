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
if (failures.length) {
  console.error(failures.join("\n"));
  console.error(`\n${failures.length} frontend check(s) failed`);
  process.exit(1);
}
console.log(`Frontend checks passed: ${Object.keys(tools).length} tools, ${keysUsed.size} i18n keys, ${Object.keys(locales).length} locales.`);
