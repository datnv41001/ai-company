"""Inspect the archived HTML bytes and their appointment controls without a server."""

from hashlib import sha256
import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from app.knowledge_store import canonical, digest


def test_service_landing_files():
    folder = Path(__file__).resolve().parents[1] / "docs/evaluation/service-landing-edit"
    records = json.loads((folder / "receipts.json").read_text(encoding="utf8"))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        for width in (390, 820, 1280):
            page = browser.new_page(viewport={"width": width, "height": 880}, offline=True, color_scheme="light")
            for version in ("before", "after"):
                path = folder / f"{version}.html"
                receipt = records[version]
                package = receipt["package"]
                issued = {k: v for k, v in package.items() if k not in ("id", "created_by", "digest", "measurement")}
                assert digest(canonical(issued)) == package["digest"] == receipt["file_qa"]["digest"]
                assert sha256(path.read_bytes()).hexdigest() == package["files"]["landing.html"]["sha256"]
                page.goto(path.as_uri())
                sections = package["master"]["sections"]
                expect(page.locator("section p").nth(0)).to_have_text(sections["benefit"])
                expect(page.locator("section p").nth(1)).to_have_text(sections["commercial_terms"])
                expect(page.get_by_role("link", name="Đặt lịch")).to_have_attribute("href", "#request")
                form = page.locator("#request")
                quantity = form.get_by_label("Số lượng (machine)")
                quantity.fill("0")
                assert not form.evaluate("(form) => form.checkValidity()")
                quantity.fill(str(receipt["form"]["quantity"]))
                form.get_by_label("Địa điểm thử").select_option(receipt["form"]["place"])
                form.get_by_label("Lịch dịch vụ dự kiến").select_option(str(receipt["form"]["days"]))
                assert form.evaluate("(form) => form.checkValidity()")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                if out := os.getenv("AMC_SERVICE_EDIT_SCREENS"):
                    Path(out).mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=Path(out) / f"{version}-{width}.png", full_page=True)
                form.get_by_role("button").click()
                expect(form.get_by_role("status")).to_have_text("Mở bản này trong Studio để gửi dữ liệu thử.")
            page.close()
        browser.close()
