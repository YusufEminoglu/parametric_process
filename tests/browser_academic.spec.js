const { test, expect } = require('playwright/test');

test('academic study user journey works in a real browser', async ({ page }) => {
  const pageErrors = [];
  const consoleErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('console', message => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  await page.goto('http://127.0.0.1:18100/index.html', { waitUntil: 'networkidle' });
  await expect(page.locator('#tab-btn-academic')).toBeVisible();
  await page.locator('#tab-btn-academic').click();
  await expect(page.locator('#academic-study-view')).toBeVisible();
  await expect(page.locator('#academic-schema-badge')).toHaveText('parametric-process-study/3.0');
  await page.locator('#academic-name').fill('Browser acceptance study');
  await page.locator('#academic-crs').fill('EPSG:32635');
  await page.locator('#academic-seeds').fill('101,202,303');
  await page.locator('#academic-bcr').fill('0.42');
  await page.locator('#academic-far').fill('2.4');
  await page.locator('#academic-height').fill('21');
  await page.locator('#academic-rainfall').fill('60');
  await page.locator('#academic-create').click();
  await expect(page.locator('#academic-result')).toContainText('Browser acceptance study');
  await expect(page.locator('#academic-result')).toContainText('"study_id"');
  await expect(page.locator('#academic-export')).toBeEnabled();
  const downloadPromise = page.waitForEvent('download');
  await page.locator('#academic-export').click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^parametric-process-study-[a-f0-9]{16}\.json$/);
  expect(pageErrors).toEqual([]);
  expect(consoleErrors).toEqual([]);
});

test('every example workflow template loads and executes', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  await page.goto('http://127.0.0.1:18100/index.html#workflow', { waitUntil: 'networkidle' });
  await page.locator('#tab-btn-workflow').click();
  const templates = {
    balanced: 6,
    feasibility: 5,
    low_carbon: 6,
    climate: 7,
    ppud: 4,
    district: 4,
  };
  for (const [template, nodeCount] of Object.entries(templates)) {
    await page.locator('#workflow-template').selectOption(template);
    await page.locator('#workflow-new').click();
    await expect(page.locator('#workflow-node-layer .workflow-node')).toHaveCount(nodeCount);
    await expect(page.locator('#workflow-edge-layer .workflow-edge')).toHaveCount(nodeCount - 1);
    await page.locator('#workflow-run').click();
    await page.locator('#workflow-run-status.success').waitFor({ state: 'visible', timeout: 120000 });
    await expect(page.locator('#workflow-run-status')).toContainText(`Completed ${nodeCount} components`);
  }
  expect(errors).toEqual([]);
});

test('Three.js viewport exposes measurable render budgets', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('http://127.0.0.1:18100/index.html', { waitUntil: 'networkidle' });
  await expect(page.locator('#hud-render-fps')).not.toHaveText('-- FPS', { timeout: 10000 });
  for (const quality of ['low', 'balanced', 'high']) {
    await page.locator('#viewport-quality').selectOption(quality);
    await expect.poll(() => page.evaluate(() => window.__parametricProcessViewport.getQuality())).toBe(quality);
  }
  await page.locator('#toggle-landscape').check();
  await page.locator('#toggle-architectural-detail').check();
  await page.waitForTimeout(100);
  const info = await page.evaluate(() => window.__parametricProcessViewport.getRenderInfo());
  expect(info).toEqual(expect.objectContaining({ calls: expect.any(Number), triangles: expect.any(Number) }));
  const instancing = await page.evaluate(() => {
    let lods = 0;
    let balconyLods = 0;
    let instances = 0;
    window.__parametricProcessViewport.visitScene(object => {
      if (object.isLOD && object.userData.urbanAsset === 'instanced-trees') lods += 1;
      if (object.isLOD && object.userData.urbanAsset === 'instanced-balconies') balconyLods += 1;
      if (object.isInstancedMesh) instances += object.count;
    });
    return { lods, balconyLods, instances };
  });
  expect(instancing.lods).toBeGreaterThan(0);
  expect(instancing.balconyLods).toBeGreaterThan(0);
  expect(instancing.instances).toBeGreaterThan(0);
  expect(errors).toEqual([]);
});

test('performance-first panels remain usable in a QGIS-sized viewport', async ({ page }) => {
  await page.setViewportSize({ width: 960, height: 700 });
  await page.goto('http://127.0.0.1:18100/index.html', { waitUntil: 'networkidle' });
  await expect(page.locator('#toggle-motion')).not.toBeChecked();
  await expect(page.locator('#toggle-traffic')).not.toBeChecked();
  await expect(page.locator('#toggle-pedestrians')).not.toBeChecked();
  await expect(page.locator('#toggle-landscape')).not.toBeChecked();
  await expect(page.locator('#toggle-architectural-detail')).not.toBeChecked();
  await page.locator('#btn-toggle-palette').click();
  await expect(page.locator('body')).toHaveClass(/palette-collapsed/);
  await expect(page.locator('#btn-toggle-palette')).toHaveAttribute('aria-expanded', 'false');
  await page.locator('#btn-toggle-dock').click();
  await expect(page.locator('body')).toHaveClass(/dock-collapsed/);
  const scorecard = await page.locator('#city-scorecard').boundingBox();
  expect(scorecard.x).toBeGreaterThanOrEqual(0);
  expect(scorecard.x + scorecard.width).toBeLessThanOrEqual(960);
});

test('guided onboarding advances and heavy motion layers load on demand', async ({ page }) => {
  await page.goto('http://127.0.0.1:18100/index.html', { waitUntil: 'networkidle' });
  expect(await page.evaluate(() => window.__parametricProcessViewport.getMotionCounts())).toEqual({ traffic: 0, pedestrians: 0 });
  await page.locator('#btn-onboarding').click();
  await expect(page.locator('#onboarding-step-label')).toHaveText('Step 1 of 6');
  for (let step = 2; step <= 6; step++) {
    await page.locator('#onboarding-next').click();
    await expect(page.locator('#onboarding-step-label')).toHaveText(`Step ${step} of 6`);
  }
  await page.locator('#onboarding-next').click();
  await expect(page.locator('#onboarding-card')).toBeHidden();
  await page.locator('#toggle-traffic').check();
  await expect.poll(() => page.evaluate(() => window.__parametricProcessViewport.getMotionCounts().traffic)).toBeGreaterThan(0);
  await page.locator('#toggle-pedestrians').check();
  await expect.poll(() => page.evaluate(() => window.__parametricProcessViewport.getMotionCounts().pedestrians)).toBeGreaterThan(0);
});
