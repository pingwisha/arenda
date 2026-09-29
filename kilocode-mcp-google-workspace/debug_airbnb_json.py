import asyncio
from playwright.async_api import async_playwright

url = 'https://ru.airbnb.com/rooms/1705652857435077845'

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800},
            locale='ru-RU',
        )
        page = await context.new_page()
        await page.goto(url, wait_until='domcontentloaded', timeout=45000)
        await page.wait_for_timeout(3000)
        
        json_data = await page.evaluate('''() => {
            const results = [];
            document.querySelectorAll('script').forEach(el => {
                const text = el.textContent || '';
                if (text.includes('price') || text.includes('nightly') || text.includes('total')) {
                    const matches = text.match(/(\"price\"|\"nightly\"|\"total\"|\"amount\")\s*:\s*(\d+\.?\d*)/g);
                    if (matches) {
                        results.push({
                            scriptId: el.id || el.className,
                            matches: matches.slice(0, 10)
                        });
                    }
                }
            });
            return results;
        }''')
        
        print('JSON price data:', json_data)
        await browser.close()

asyncio.run(test())
