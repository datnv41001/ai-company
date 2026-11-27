"""Exercise the portable artifact itself without a server, inference or database."""
import os
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from scripts.rfq_card import CASES, export


def test_portable_rfq_cards(tmp_path):
    output = Path(os.environ.get("AMC_RFQ_BROWSER_EVIDENCE", tmp_path))
    output.mkdir(parents=True, exist_ok=True)
    export(output / "cards")
    observations = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        for width in (1280, 820, 390):
            for scheme in ("light", "dark"):
                page = browser.new_page(viewport={"width": width, "height": 900}, color_scheme=scheme,
                                        reduced_motion="reduce")
                external, errors = [], []
                page.on("request", lambda req: external.append(req.url) if req.url.startswith(("http:", "https:")) else None)
                page.on("pageerror", lambda error: errors.append(str(error)))
                for key in CASES:
                    page.goto((output / "cards" / f"{key}.html").as_uri())
                    heading = "Đạt mức đặt tối thiểu đã ghi" if key == "after" else "Dưới mức đặt tối thiểu"
                    assert page.get_by_role("heading", name=heading).is_visible()
                    assert page.get_by_text("Chưa có receipt", exact=True).count() == 4
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    assert page.evaluate("getComputedStyle(document.documentElement).colorScheme") == scheme
                    measured = page.evaluate("""() => {
                        const style = getComputedStyle(document.documentElement);
                        const lum = token => {
                            let hex = style.getPropertyValue(token).trim().slice(1);
                            if (hex.length === 3) hex = [...hex].map(c => c+c).join('');
                            const rgb = [0,2,4].map(i => parseInt(hex.slice(i,i+2),16)/255)
                                .map(c => c <= 0.04045 ? c/12.92 : ((c+0.055)/1.055)**2.4);
                            return rgb[0]*0.2126 + rgb[1]*0.7152 + rgb[2]*0.0722;
                        };
                        const ratio = (a,b) => (Math.max(lum(a),lum(b))+.05)/(Math.min(lum(a),lum(b))+.05);
                        return {muted:ratio('--muted','--paper'),normal:ratio('--ink','--paper'),
                                hero:ratio('--hero-ink','--hero'), load_ms:performance.getEntriesByType('navigation')[0].duration};
                    }""")
                    assert min(measured[k] for k in ("muted", "normal", "hero")) >= 4.5
                    observations.append({"width": width, "theme": scheme, "case": key, **measured})
                    page.keyboard.press("Tab")
                    assert page.locator("summary").first.evaluate("el => el === document.activeElement")
                    assert page.locator("summary").first.evaluate("el => getComputedStyle(el).outlineStyle") == "solid"
                    page.keyboard.press("Enter")
                    assert page.locator("details").first.get_attribute("open") is not None
                    assert page.locator("ol li").count() == (2 if key == "after" else 1)
                    assert page.locator("a[download]").get_attribute("href") == key + ".json"
                    page.keyboard.press("Enter")
                    if key == "after":
                        page.screenshot(path=str(output / f"{width}-{scheme}.png"), full_page=True)
                assert external == [] and errors == []
                page.close()
        browser.close()
    (output / "browser-measurements.json").write_text(json.dumps(observations, indent=2), encoding="utf-8")
