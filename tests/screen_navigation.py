"""Use the same keyboard-accessible screens and menus as workspace users."""

from playwright.sync_api import expect


def screen(page, name):
    # The account screen can legitimately leave the workspace container empty.
    # Wait for membership initialization, not for its box to have a visible size.
    page.wait_for_function(
        """()=>['staff','portal'].includes(document.body.dataset.access) &&
      !document.querySelector('#workspace').classList.contains('hidden') && !document.querySelector('#workspace').hasAttribute('data-loading')""",
        timeout=20000,
    )
    if page.locator("body").get_attribute("data-screen") == name:
        return
    toggle = page.locator("#menu-toggle")
    if toggle.is_visible() and toggle.get_attribute("aria-expanded") != "true":
        toggle.click()
    link = page.locator(f'[data-route="{name}"]')
    link.click()
    expect(link).to_have_attribute("aria-current", "page")


def menu(page, name):
    panel = page.locator(f"#{name}-menu")
    if not panel.is_visible():
        page.locator(f"#{name}-trigger").click()
    expect(panel).to_be_visible()


def select_workspace(page, tenant):
    menu(page, "scope")
    page.locator("#workspace-select").select_option(tenant)


def switch_account(page):
    menu(page, "account")
    page.locator("#switch-account").click()
