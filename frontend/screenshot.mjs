import { chromium } from 'playwright';

const SCRATCHPAD = 'C:/Users/Eren/AppData/Local/Temp/claude/c--Users-Eren-Desktop-vs-code-review-radar/7e9e30ca-0821-44f7-b2dd-f1eae4f6cd4d/scratchpad';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
await page.setViewportSize({ width: 1440, height: 900 });
page.on('pageerror', err => console.log('PAGE ERROR:', err.message));

await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 15000 });
await page.waitForTimeout(4000);

// Screenshot the top first
await page.screenshot({ path: `${SCRATCHPAD}/sections-top.png` });

// Scroll to Metrikler section (where trend chart should appear)
const reportDiv = await page.$('div.overflow-y-auto');
if (reportDiv) {
  await page.evaluate(el => el.scrollTop = 600, reportDiv);
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${SCRATCHPAD}/sections-metrik.png` });

  await page.evaluate(el => el.scrollTop = 1800, reportDiv);
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${SCRATCHPAD}/sections-konu.png` });

  await page.evaluate(el => el.scrollTop = 4000, reportDiv);
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${SCRATCHPAD}/sections-segment.png` });
}

console.log('Done');
await browser.close();
