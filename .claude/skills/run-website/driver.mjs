// Minimal chromium-cli-style REPL driver, built because chromium-cli is not
// installed on this machine. Reads one command per line from stdin, drives a
// single headless Chromium page via Playwright, prints results to stdout.
//
// Commands:
//   nav <path-or-url>         goto BASE_URL + path (or an absolute URL)
//   login <username> <pass>   fills and submits the Django login form
//   wait-for <selector>       waits for a selector (Playwright selector syntax,
//                             e.g. "text=Hoy" works out of the box)
//   click <selector>
//   fill <selector> <value...>
//   select <selector> <value>
//   press <key>
//   text <selector>           prints textContent
//   value <selector>          prints the input/select value
//   eval <js>                 runs JS in the page, prints the JSON result
//   screenshot [name]         saves to ./screenshots/<name-or-counter>.png
//   console                   prints collected console.error/pageerror lines
//   quit | exit
//
// Usage: node driver.mjs   (then pipe commands via a heredoc, see SKILL.md)

import { chromium } from "playwright";
import { createInterface } from "node:readline";
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const SKILL_DIR = dirname(fileURLToPath(import.meta.url));
const SCREENSHOT_DIR = join(SKILL_DIR, "screenshots");
const BASE_URL = process.env.BASE_URL || "http://127.0.0.1:8000";

mkdirSync(SCREENSHOT_DIR, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
const consoleLines = [];
page.on("console", (msg) => {
  if (msg.type() === "error") consoleLines.push(`[console.error] ${msg.text()}`);
});
page.on("pageerror", (err) => consoleLines.push(`[pageerror] ${err}`));

let screenshotCounter = 0;

function splitArgs(rest) {
  return rest.trim().split(/\s+/);
}

async function runCommand(line) {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith("#")) return;

  const spaceIdx = trimmed.indexOf(" ");
  const cmd = spaceIdx === -1 ? trimmed : trimmed.slice(0, spaceIdx);
  const rest = spaceIdx === -1 ? "" : trimmed.slice(spaceIdx + 1);

  switch (cmd) {
    case "nav": {
      const url = /^https?:\/\//.test(rest) ? rest : BASE_URL + rest;
      await page.goto(url);
      console.log(`OK nav ${url}`);
      break;
    }
    case "login": {
      const [username, password] = splitArgs(rest);
      await page.goto(BASE_URL + "/accounts/login/");
      await page.fill('input[name="username"]', username);
      await page.fill('input[name="password"]', password);
      await Promise.all([
        page.waitForLoadState("networkidle"),
        page.click('button[type="submit"], input[type="submit"]'),
      ]);
      console.log(`OK login ${username}`);
      break;
    }
    case "wait-for": {
      await page.waitForSelector(rest, { timeout: 10000 });
      console.log(`OK wait-for ${rest}`);
      break;
    }
    case "click": {
      await page.click(rest);
      console.log(`OK click ${rest}`);
      break;
    }
    case "fill": {
      const [selector, ...valueParts] = splitArgs(rest);
      await page.fill(selector, valueParts.join(" "));
      console.log(`OK fill ${selector}`);
      break;
    }
    case "select": {
      const [selector, value] = splitArgs(rest);
      await page.selectOption(selector, value);
      console.log(`OK select ${selector} ${value}`);
      break;
    }
    case "press": {
      await page.keyboard.press(rest);
      console.log(`OK press ${rest}`);
      break;
    }
    case "text": {
      const value = await page.textContent(rest);
      console.log(`TEXT ${rest} = ${JSON.stringify((value || "").trim())}`);
      break;
    }
    case "value": {
      const value = await page.inputValue(rest);
      console.log(`VALUE ${rest} = ${JSON.stringify(value)}`);
      break;
    }
    case "eval": {
      const result = await page.evaluate(new Function(`return (${rest})`));
      console.log(`EVAL = ${JSON.stringify(result)}`);
      break;
    }
    case "screenshot": {
      const name = rest || String(screenshotCounter++);
      const path = join(SCREENSHOT_DIR, `${name}.png`);
      await page.screenshot({ path, fullPage: true });
      console.log(`OK screenshot ${path}`);
      break;
    }
    case "console": {
      console.log(
        consoleLines.length ? consoleLines.join("\n") : "(no console errors)"
      );
      break;
    }
    case "quit":
    case "exit": {
      await browser.close();
      process.exit(0);
      break;
    }
    default:
      console.log(`ERR unknown command: ${cmd}`);
  }
}

// readline emits "line" for every buffered line almost immediately when
// stdin is a heredoc/pipe, not one at a time as each async handler
// finishes — so commands are chained into one promise and run strictly
// sequentially, or e.g. "quit" can close the browser while earlier
// commands are still in flight.
let chain = Promise.resolve();

const rl = createInterface({ input: process.stdin });
rl.on("line", (line) => {
  chain = chain.then(() => runCommand(line)).catch((err) => {
    console.log(`ERR ${err.message}`);
  });
});
rl.on("close", async () => {
  await chain;
  await browser.close();
  process.exit(0);
});
