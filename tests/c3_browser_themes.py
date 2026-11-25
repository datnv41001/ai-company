"""Capture the same live task/evidence state under both supported color schemes."""
from playwright.sync_api import expect


def capture_themes(page, filename):
    for mode in ("light", "dark"):
        page.emulate_media(color_scheme=mode)
        expect(page.locator("html")).to_have_attribute("data-theme", mode)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        path = filename if mode == "light" else filename.with_stem(filename.stem + "-dark")
        page.screenshot(path=path, animations="disabled")
    page.emulate_media(color_scheme="light")
