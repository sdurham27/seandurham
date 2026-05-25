const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const path = require('path');

const CREAM = '#ede8dc';
const DARK  = '#111318';
const OUT   = path.join(__dirname, 'img');

function page(svgOrHtml, w, h, extraCss = '') {
  return `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow+Condensed:wght@200;300&display=swap" rel="stylesheet">
<style>
html, body { margin: 0; padding: 0; background: transparent; width: ${w}px; height: ${h}px; overflow: hidden; }
/* v1 type */
.v1-saint { font-family: 'Barlow Condensed','Arial Narrow',Arial,sans-serif; font-weight: 300; font-size: 27px; letter-spacing: 11px; }
.v1-dizzie { font-family: 'Bebas Neue',Impact,'Arial Black',sans-serif; font-size: 118px; letter-spacing: 2px; }
.v1-mark   { font-family: Georgia,'Times New Roman',serif; font-size: 19px; }
/* bolder type */
.bold-saint  { font-family: 'Barlow Condensed','Arial Narrow',Arial,sans-serif; font-weight: 300; font-size: 32px; letter-spacing: 14px; }
.bold-dizzie { font-family: 'Bebas Neue',Impact,'Arial Black',sans-serif; font-size: 144px; letter-spacing: 1px; }
.bold-mark   { font-family: Georgia,'Times New Roman',serif; font-size: 44px; }
/* wordmark type */
.wm-saint  { display:block; font-family:'Barlow Condensed','Arial Narrow',Arial,sans-serif; font-weight:200; font-size:18px; letter-spacing:22px; text-transform:uppercase; }
.wm-dizzie { display:block; font-family:'Bebas Neue',Impact,sans-serif; font-size:200px; letter-spacing:2px; line-height:0.88; }
.wm-mark   { display:block; font-family:Georgia,serif; font-size:40px; }
${extraCss}
</style>
</head>
<body>${svgOrHtml}</body>
</html>`;
}

const variants = [

  // ── V1 concept: cream (use on dark backgrounds) ──────────────────────────
  { name: 'logo-v1-cream', w: 1000, h: 1000, markup: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" width="1000" height="1000">
      <!-- no fill on outer circle — transparent background -->
      <circle cx="250" cy="250" r="213" fill="none" stroke="${CREAM}" stroke-width="0.9"/>
      <line x1="86"  y1="155" x2="158" y2="155" stroke="${CREAM}" stroke-width="0.7" opacity="0.65"/>
      <line x1="342" y1="155" x2="414" y2="155" stroke="${CREAM}" stroke-width="0.7" opacity="0.65"/>
      <text x="250" y="163" class="v1-saint"  text-anchor="middle" fill="${CREAM}">SAINT</text>
      <line x1="86"  y1="178" x2="414" y2="178" stroke="${CREAM}" stroke-width="0.45" opacity="0.35"/>
      <text x="250" y="295" class="v1-dizzie" text-anchor="middle" fill="${CREAM}">DIZZIE</text>
      <line x1="86"  y1="315" x2="414" y2="315" stroke="${CREAM}" stroke-width="0.45" opacity="0.35"/>
      <text x="250" y="350" class="v1-mark"   text-anchor="middle" fill="${CREAM}" opacity="0.7">†</text>
    </svg>` },

  // ── V1 concept: dark (use on light backgrounds) ───────────────────────────
  { name: 'logo-v1-dark', w: 1000, h: 1000, markup: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" width="1000" height="1000">
      <circle cx="250" cy="250" r="213" fill="none" stroke="${DARK}" stroke-width="0.9"/>
      <line x1="86"  y1="155" x2="158" y2="155" stroke="${DARK}" stroke-width="0.7" opacity="0.65"/>
      <line x1="342" y1="155" x2="414" y2="155" stroke="${DARK}" stroke-width="0.7" opacity="0.65"/>
      <text x="250" y="163" class="v1-saint"  text-anchor="middle" fill="${DARK}">SAINT</text>
      <line x1="86"  y1="178" x2="414" y2="178" stroke="${DARK}" stroke-width="0.45" opacity="0.35"/>
      <text x="250" y="295" class="v1-dizzie" text-anchor="middle" fill="${DARK}">DIZZIE</text>
      <line x1="86"  y1="315" x2="414" y2="315" stroke="${DARK}" stroke-width="0.45" opacity="0.35"/>
      <text x="250" y="350" class="v1-mark"   text-anchor="middle" fill="${DARK}" opacity="0.7">†</text>
    </svg>` },

  // ── Bolder/Delight: cream (use on dark backgrounds) ──────────────────────
  { name: 'logo-bolder-cream', w: 1000, h: 1000, markup: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" width="1000" height="1000">
      <circle cx="250" cy="250" r="222" fill="none" stroke="${CREAM}" stroke-width="8"/>
      <text x="250" y="155" class="bold-saint"  text-anchor="middle" fill="${CREAM}">SAINT</text>
      <text x="250" y="304" class="bold-dizzie" text-anchor="middle" fill="${CREAM}">DIZZIE</text>
      <text x="250" y="380" class="bold-mark"   text-anchor="middle" fill="${CREAM}" opacity="0.58">†</text>
    </svg>` },

  // ── Bolder/Delight: dark (use on light backgrounds) ──────────────────────
  { name: 'logo-bolder-dark', w: 1000, h: 1000, markup: `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" width="1000" height="1000">
      <circle cx="250" cy="250" r="222" fill="none" stroke="${DARK}" stroke-width="8"/>
      <text x="250" y="155" class="bold-saint"  text-anchor="middle" fill="${DARK}">SAINT</text>
      <text x="250" y="304" class="bold-dizzie" text-anchor="middle" fill="${DARK}">DIZZIE</text>
      <text x="250" y="380" class="bold-mark"   text-anchor="middle" fill="${DARK}" opacity="0.58">†</text>
    </svg>` },

  // ── Wordmark: cream (use on dark backgrounds) ────────────────────────────
  { name: 'logo-wordmark-cream', w: 1200, h: 420,
    css: 'body { display:flex; align-items:center; justify-content:center; }',
    markup: `
    <div style="text-align:center;">
      <span class="wm-saint" style="color:${CREAM}; opacity:0.65; margin-bottom:4px;">Saint</span>
      <span class="wm-dizzie" style="color:${CREAM};">DIZZIE</span>
      <span class="wm-mark"   style="color:${CREAM}; opacity:0.35; margin-top:10px;">†</span>
    </div>` },

  // ── Wordmark: dark (use on light backgrounds) ────────────────────────────
  { name: 'logo-wordmark-dark', w: 1200, h: 420,
    css: 'body { display:flex; align-items:center; justify-content:center; }',
    markup: `
    <div style="text-align:center;">
      <span class="wm-saint" style="color:${DARK}; opacity:0.65; margin-bottom:4px;">Saint</span>
      <span class="wm-dizzie" style="color:${DARK};">DIZZIE</span>
      <span class="wm-mark"   style="color:${DARK}; opacity:0.35; margin-top:10px;">†</span>
    </div>` },

];

(async () => {
  const browser = await chromium.launch();

  for (const v of variants) {
    const pg = await browser.newPage();
    await pg.setViewportSize({ width: v.w, height: v.h });
    await pg.setContent(page(v.markup, v.w, v.h, v.css || ''));
    // Wait for Google Fonts
    await pg.evaluate(() => document.fonts.ready);
    await pg.waitForTimeout(400);

    const out = `${OUT}/${v.name}.png`;
    await pg.screenshot({ path: out, omitBackground: true,
      clip: { x: 0, y: 0, width: v.w, height: v.h } });
    console.log('✓', v.name + '.png');
    await pg.close();
  }

  await browser.close();
  console.log('\nDone — 6 PNGs in img/');
})().catch(e => { console.error(e); process.exit(1); });
