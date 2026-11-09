// Loads the viewer against a running test server and checks it renders, with no page errors.
// usage: node tests/viewer_smoke.mjs http://127.0.0.1:8765
import { chromium } from "playwright";
const url = process.argv[2] || "http://127.0.0.1:8765/";
const browser = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
const errors = [];
page.on("pageerror", e => errors.push(e.message));
await page.addInitScript(() => localStorage.setItem("earthlink:skipKeys", "true"));
await page.goto(url, { waitUntil: "load" });
await page.waitForFunction(() => window.EL && Object.keys(window.EL.models).length > 0, null, { timeout: 60000, polling: 500 });
const saved = await page.evaluate(async () => {
  const sink = { n: 0, async save() { this.n++; return "x"; } };
  document.getElementById("pModel").checked = true;
  await EL.capture("smoke", sink); return sink.n;
});
await browser.close();
if (errors.length || saved !== 2) { console.error("FAIL", { errors, saved }); process.exit(1); }
console.log("viewer smoke test passed");
