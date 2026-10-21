#!/usr/bin/env node
/**
 * Capture the real Parametric Process web interface with Playwright.
 *
 * The cockpit, the visual workflow modeler and the Pareto analytics studio
 * are the plugin's actual UI. They are served by the plugin's own local
 * server (server.py) and driven with the same selectors the repository's
 * browser acceptance tests use — so the screenshots are the real product,
 * not a mock-up.
 *
 * The server is started by serve_real_data.py, which pushes the real Tire
 * cadastral master into it before the browser connects.
 *
 * Usage:
 *   node capture_ui.mjs --url http://127.0.0.1:18111/index.html --out screenshots/ui
 */
import { mkdir } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { execSync } from 'node:child_process';
import path from 'node:path';

// Playwright may live in the project or in the global npm root — resolve
// both so the capture runs on a clean checkout.
const require = createRequire(import.meta.url);
function loadPlaywright() {
  const roots = [];
  try { roots.push(execSync('npm root -g', { encoding: 'utf8' }).trim()); } catch { /* ignore */ }
  for (const root of roots) {
    try { return require(path.join(root, 'playwright')); } catch { /* try next */ }
  }
  return require('playwright');
}
const { chromium } = loadPlaywright();

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, cur, i, arr) => {
    if (cur.startsWith('--')) acc.push([cur.slice(2), arr[i + 1]]);
    return acc;
  }, [])
);

const BASE = (args.url || 'http://127.0.0.1:18111/index.html').replace(/\/index\.html.*$/, '/index.html');
const OUT = args.out || 'screenshots/ui';

await mkdir(OUT, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });

const errors = [];
page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}\n${(e.stack || '').split('\n').slice(0, 6).join('\n')}`));
page.on('console', (m) => { if (m.type() === 'error') errors.push(`console: ${m.text()}`); });

const TITLES = {
  cockpit: '3D cockpit — the real Tire city model',
  parcel_inspector: 'Parcel inspector — design parameters for one block',
  evolutionary_studio: 'Evolutionary Studio — objectives and solver controls',
  wallacei_studio: 'Pareto Analytics Studio',
  pareto_scatter: 'Pareto front scatter',
  pareto_pcp: 'Parallel coordinates plot',
  pareto_fitness: 'Fitness convergence and standard-deviation band',
  pareto_radar: 'Diamond / radar fitness profile',
  pareto_cluster: 'K-Means clustering of the solution set',
  pareto_population: 'Population browser',
  workflow_empty: 'Visual rule workflow modeler — empty',
  workflow_graph: 'Visual rule workflow modeler — a loaded rule chain',
  workflow_result: 'Visual rule workflow modeler — executed result',
  academic_study: 'Academic study workspace',
};

const shot = async (name) => {
  const file = path.join(OUT, `${name}.png`);
  await page.screenshot({ path: file });
  console.log(`  captured ${name}.png`);
};

console.log(`opening ${BASE}`);
await page.goto(BASE, { waitUntil: 'networkidle', timeout: 120000 });

// The cockpit builds the city model progressively — wait for the loading
// overlay to disappear before capturing, otherwise the shot is a splash screen.
try {
  await page.waitForFunction(
    () => {
      const el = document.getElementById('loading');
      return el && el.classList.contains('hidden');
    },
    null,
    { timeout: 300000 }
  );
} catch (err) {
  console.log('  ! loading overlay never hid');
}
await page.waitForTimeout(3000);
const parcelCount = await page.locator('#hud-total-parcels').textContent().catch(() => '?');
console.log(`  parcels rendered: ${parcelCount}`);

// ── 1. the 3D cockpit ──────────────────────────────────────────────────────
await shot('cockpit');

// ── 2. run the solver, then walk the Pareto analytics studio ─────────────
try {
  // Select a parcel in the 3D scene — the design inspector (and its
  // scenario controls) only exists for a selected parcel.
  for (const [x, y] of [[700, 420], [640, 520], [860, 380], [520, 300], [980, 600]]) {
    await page.mouse.click(x, y);
    await page.waitForTimeout(900);
    if (await page.locator('#btn-solve-city').isVisible().catch(() => false)) break;
  }
  await shot('parcel_inspector');

  // The Evolutionary Studio runs the multi-objective solver.
  await page.locator('#tab-btn-wallacei').click({ timeout: 15000, force: true });
  await page.waitForTimeout(1500);
  await shot('evolutionary_studio');

  try {
    await page.locator('#btn-run-wallacei').click({ timeout: 20000, force: true });
  } catch {
    await page.evaluate(() => document.getElementById('btn-run-wallacei').click());
  }
  console.log('  NSGA-II solver started');
  await page.waitForFunction(
    () => {
      const el = document.getElementById('wallacei-analytics-container');
      return el && !el.classList.contains('hidden');
    },
    null,
    { timeout: 420000 }
  );
  await page.waitForTimeout(3000);
  console.log('  solver finished');
  await shot('wallacei_studio');
} catch (err) {
  console.log(`  ! solver: ${String(err).split('\n')[0]}`);
}

const subtabs = [
  ['subtab-scatter', 'pareto_scatter'],
  ['subtab-pcp', 'pareto_pcp'],
  ['subtab-fitness', 'pareto_fitness'],
  ['subtab-radar', 'pareto_radar'],
  ['subtab-cluster', 'pareto_cluster'],
  ['subtab-population', 'pareto_population'],
];
for (const [id, name] of subtabs) {
  try {
    const locator = page.locator(`#${id}`);
    if (await locator.count()) {
      await locator.first().click({ timeout: 8000 });
      await page.waitForTimeout(1200);
      await shot(name);
    }
  } catch (err) {
    console.log(`  ! ${name}: ${String(err).split('\n')[0]}`);
  }
}

// ── 3. the visual rule workflow modeler ────────────────────────────────────
try {
  await page.locator('#tab-btn-workflow').click({ timeout: 10000 });
  await page.waitForTimeout(1500);
  await shot('workflow_empty');
  // load the balanced example workflow and run it for real
  await page.locator('#workflow-template').selectOption('balanced');
  await page.locator('#workflow-new').click();
  await page.waitForTimeout(1500);
  await shot('workflow_graph');
  await page.locator('#workflow-run').click();
  await page.locator('#workflow-run-status.success').waitFor({ state: 'visible', timeout: 180000 });
  await page.waitForTimeout(2500);
  await shot('workflow_result');
} catch (err) {
  console.log(`  ! workflow: ${String(err).split('\n')[0]}`);
}

// ── 4. the academic study view ────────────────────────────────────────────
try {
  await page.locator('#tab-btn-academic').click({ timeout: 10000 });
  await page.waitForTimeout(1500);
  await shot('academic_study');
} catch (err) {
  console.log(`  ! academic: ${String(err).split('\n')[0]}`);
}

await browser.close();

// Record what was captured so the guide builder can embed the real files.
const captured = [];
for (const file of await (await import('node:fs/promises')).readdir(OUT)) {
  if (!file.endsWith('.png')) continue;
  const id = file.replace(/\.png$/, '');
  captured.push({
    id,
    title: TITLES[id] || id.replace(/_/g, ' '),
    path: `screenshots/ui/${file}`,
  });
}
await (await import('node:fs/promises')).writeFile(
  path.join(OUT, 'ui_captures.json'),
  JSON.stringify({ captured }, null, 2),
  'utf8'
);
console.log(`  manifest: ${captured.length} captures`);

if (errors.length) {
  console.log(`\npage errors (${errors.length}):`);
  for (const e of errors.slice(0, 12)) console.log(`   ${e}`);
} else {
  console.log('\nno page errors');
}
console.log('UI capture complete');
