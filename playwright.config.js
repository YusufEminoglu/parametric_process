module.exports = {
  testDir: './tests',
  testMatch: ['browser_academic.spec.js', 'browser_large_project.spec.js'],
  timeout: 90000,
  use: { headless: true },
};
