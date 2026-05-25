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

  // Wait for fonts and initial render
  await page.waitForTimeout(2500);

  const framesDir = path.resolve(__dirname, 'frames');
  if (!fs.existsSync(framesDir)) {
    fs.mkdirSync(framesDir);
  } else {
    // Clean old frames
    fs.readdirSync(framesDir).forEach(f => fs.unlinkSync(path.join(framesDir, f)));
  }

  // Capture 90 frames over 6 seconds = 15fps real-time
  const totalFrames = 90;
  const intervalMs = 67; // ~15fps

  for (let i = 0; i < totalFrames; i++) {
    await page.screenshot({
      path: path.join(framesDir, `frame_${String(i).padStart(4,'0')}.png`),
      clip: { x: 0, y: 0, width: 520, height: 520 }
    });
    if (i < totalFrames - 1) {
      await page.waitForTimeout(intervalMs);
    }
  }

  await browser.close();
  console.log(`Captured ${totalFrames} frames to ${framesDir}`);
})();
