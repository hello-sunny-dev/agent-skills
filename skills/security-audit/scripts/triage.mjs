#!/usr/bin/env node
// Triage `npm audit --json`: collapse fan-out to ROOT advisories, flag prod vs dev.
// Usage: npm audit --json | node triage.mjs   (or: node triage.mjs audit.json)
import { readFileSync } from "node:fs";

const raw = process.argv[2]
  ? readFileSync(process.argv[2], "utf8")
  : readFileSync(0, "utf8");
const data = JSON.parse(raw);
const vulns = data.vulnerabilities || {};

// A "root" advisory = a via entry that is an object (has title/url/cwe).
// Everything else is fan-out (via is a string naming another vulnerable pkg).
const roots = new Map(); // url -> {title,severity,url,pkgs:Set,range}
const fanout = [];

for (const [name, v] of Object.entries(vulns)) {
  const objVia = (v.via || []).filter((x) => typeof x === "object");
  if (objVia.length) {
    for (const s of objVia) {
      const key = s.url || s.source || s.title;
      if (!roots.has(key))
        roots.set(key, {
          title: s.title,
          severity: s.severity,
          url: s.url,
          range: s.range,
          pkgs: new Set(),
        });
      roots.get(key).pkgs.add(name);
    }
  } else {
    fanout.push(name);
  }
  // fixAvailable=false + advisory present => needs overrides, not `audit fix`
}

// prod-vs-dev heuristic: a pkg is DEV/BUILD if its whole chain lives under known
// tooling roots. We can't see the full tree here, so flag by name hints + report
// that the human MUST verify with `npm ls <pkg>` + grep for src/ imports.
const DEV_HINTS =
  /eslint|jest|storybook|vite|webpack|babel|svgo|svgr|postcss|tailwind|test|coverage|istanbul|junit|glob|minimatch|brace-expansion|prettier|husky|lint/i;

console.log("=== ROOT ADVISORIES (the real vulns) ===\n");
const SEVERITY = { critical: 0, high: 1, moderate: 2, low: 3, info: 4 };
const rank = (r) => SEVERITY[r.severity] ?? 5;
const rootArr = [...roots.values()].sort((a, b) => rank(a) - rank(b));
for (const r of rootArr) {
  const pkgs = [...r.pkgs];
  const devGuess = pkgs.every((p) => DEV_HINTS.test(p)) ? "DEV/BUILD?" : "VERIFY";
  console.log(`• [${r.severity}] ${r.title}`);
  console.log(`  ${r.url}`);
  console.log(`  vulnerable range: ${r.range}`);
  console.log(`  direct pkg(s): ${pkgs.join(", ")}  → likely ${devGuess}`);
  console.log("");
}

// fixAvailable summary
const noFix = [];
const majorFix = [];
const safeFix = [];
for (const [name, v] of Object.entries(vulns)) {
  const fa = v.fixAvailable;
  if (fa === false) noFix.push(name);
  else if (fa && fa.isSemVerMajor) majorFix.push(`${name}→${fa.name}@${fa.version}`);
  else if (fa === true) safeFix.push(name);
}

console.log("=== FIX AVAILABILITY ===\n");
console.log(`total advisories: ${Object.keys(vulns).length}`);
console.log(`ROOT advisories:  ${roots.size}  (rest is fan-out)`);
console.log("");
console.log(`fixAvailable=false (NEEDS overrides): ${noFix.length}`);
if (noFix.length) console.log("  " + noFix.join(", "));
console.log("");
console.log(`SemVer-MAJOR fix (needs judgment / smoke test): ${majorFix.length}`);
if (majorFix.length) console.log("  " + majorFix.join(", "));
console.log("");
console.log(`safe fix (npm audit fix): ${safeFix.length}`);
if (safeFix.length) console.log("  " + safeFix.join(", "));

console.log("\n=== NEXT STEPS ===");
console.log("1. For each ROOT: `npm ls <pkg>` — confirm it's dev/build tree, not prod.");
console.log("2. `grep -r \"from ['\\\"]<pkg>\" src/` — 0 hits + dev tree = NOT prod-runtime.");
console.log("3. fixAvailable=false → `overrides` floor bump (check `npm view <pkg> version`).");
console.log("4. SemVer-major → flag 'smoke test required' on ticket, assign reviewer.");
