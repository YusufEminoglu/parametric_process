const { test, expect } = require('playwright/test');

test('400-parcel model remains responsive during a sustained 30-second session', async ({ page }) => {
  test.setTimeout(90000);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  await page.goto('http://127.0.0.1:18101/index.html', { waitUntil: 'networkidle', timeout: 30000 });
  await expect.poll(() => page.evaluate(() => window.planxDebug?.performance?.featureCount), { timeout: 30000 }).toBe(400);
  const baseline = await page.evaluate(() => ({
    performance: window.planxDebug.performance,
    motion: window.__parametricProcessViewport.getMotionCounts(),
    memory: window.__parametricProcessViewport.getMemoryInfo(),
  }));
  expect(baseline.performance.totalMs).toBeLessThan(20000);
  expect(baseline.motion).toEqual({ traffic: 0, pedestrians: 0 });
  await page.locator('#toggle-landscape').check();
  await page.locator('#toggle-architectural-detail').check();
  await page.locator('#toggle-landscape').uncheck();
  await page.locator('#toggle-architectural-detail').uncheck();
  const responsiveness = await page.evaluate(async () => {
    const samples = [];
    let previous = performance.now();
    const deadline = previous + 30000;
    while (performance.now() < deadline) {
      await new Promise(resolve => requestAnimationFrame(resolve));
      const now = performance.now();
      samples.push(now - previous);
      previous = now;
    }
    samples.sort((a, b) => a - b);
    return { frames: samples.length, p95GapMs: samples[Math.floor(samples.length * 0.95)], maxGapMs: samples.at(-1) };
  });
  console.log('LARGE_PROJECT_METRICS', JSON.stringify({ baseline, responsiveness }));
  expect(responsiveness.frames).toBeGreaterThan(180);
  expect(responsiveness.p95GapMs).toBeLessThan(150);
  expect(responsiveness.maxGapMs).toBeLessThan(1500);
  expect(errors).toEqual([]);
});
