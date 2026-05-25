const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
  });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 520, height: 520 });

  const htmlPath = path.resolve(__dirname, 'saintdizzie.html');
  await page.goto(`file://${htmlPath}`);

  // Wait for fonts to load
  await page.waitForTimeout(2000);

  // Pause all animations so we can control them manually via currentTime
  // We'll capture frames by setting animation-play-state and using JS to advance time
  // Use a total duration of 6s (covers ring spin partial, pulse, glitch cycle)
  // 60 frames at ~100ms each = 6 seconds total
  const framesDir = path.resolve(__dirname, 'frames');
  if (!fs.existsSync(framesDir)) fs.mkdirSync(framesDir);

  const totalFrames = 72;  // 72 frames
  const frameDurationMs = 83; // ~12fps, 6s total

  // Inject helper to freeze and manually set animation time
  await page.evaluate(() => {
    // Pause all animations
    document.getAnimations().forEach(a => { a.pause(); });
  });

  for (let i = 0; i < totalFrames; i++) {
    const timeMs = i * frameDurationMs;
    await page.evaluate((t) => {
      document.getAnimations().forEach(a => {
        try { a.currentTime = t; } catch(e) {}
      });
    }, timeMs);

    await page.screenshot({
      path: path.join(framesDir, `frame_${String(i).padStart(4,'0')}.png`),
      clip: { x: 0, y: 0, width: 520, height: 520 }
    });
  }

  await browser.close();
  console.log(`Captured ${totalFrames} frames to ${framesDir}`);
})();
