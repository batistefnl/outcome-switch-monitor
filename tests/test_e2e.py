import pytest
from playwright.sync_api import expect, sync_playwright

pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def page(browser):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    errors = []
    pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.errors = errors
    yield pg
    ctx.close()
    assert not errors, f"erreurs JavaScript : {errors}"


def test_home_and_showcase(page, offline_server, stats):
    page.goto(offline_server)
    expect(page.locator("h1")).to_have_text("Outcome Switch Monitor")
    chips = page.locator("#showcase button")
    expect(chips).to_have_count(len(stats["showcase"]))
    chips.first.click()
    expect(page.locator(".trial-head h2")).to_contain_text(stats["showcase"][0]["nct"])
    expect(page.locator(".verdict.human")).to_be_visible()
    expect(page.locator(".oc.reg").first).to_be_visible()
    expect(page.locator(".oc.dep").first).to_be_visible()


def test_search_and_open(page, offline_server):
    page.goto(offline_server)
    page.fill("#q", "pancreas CPI-613")
    expect(page.locator("#results li button").first).to_contain_text("NCT03504423")
    page.locator("#results li button").first.click()
    expect(page.locator(".verdict.human .v")).to_have_text("Major change")
    expect(page.locator(".verdict.human")).to_contain_text("Demoted to secondary")


def test_search_by_id_enter(page, offline_server):
    page.goto(offline_server)
    page.fill("#q", "nct03504423")
    page.press("#q", "Enter")
    expect(page.locator(".trial-head h2")).to_contain_text("NCT03504423")


def test_history_loads(page, offline_server, stats):
    nct = stats["showcase"][0]["nct"]
    page.goto(f"{offline_server}/#{nct}")
    page.click("text=Load version history")
    expect(page.locator(".hist .ver").first).to_be_visible(timeout=60000)
    expect(page.locator(".hist .ver.ref")).to_have_count(1)


def test_dashboard(page, offline_server, stats):
    page.goto(offline_server)
    page.click("nav >> text=Dashboard")
    expect(page.locator("#dash svg")).to_have_count(5)
    expect(page.locator(".tile.hero .value")).to_have_text(f"{round(100 * stats['human']['changement']['non_identical'][0])} %")
    page.locator("#dash g.bar").first.hover()
    expect(page.locator("#tip")).to_be_visible()
    expect(page.locator("#tip")).to_contain_text("substantive change")
    expect(page.locator("#dash table").last.locator("tbody tr")).to_have_count(len(stats["agreement"]))


def test_live_off_without_key(page, offline_server):
    page.goto(offline_server)
    page.click("nav >> text=Check a new trial")
    expect(page.locator("#live-status")).to_contain_text("Live classification is off")
    expect(page.locator("#live-go")).to_be_disabled()


@pytest.mark.network
def test_live_check_with_stub_model(page, live_server):
    page.goto(live_server)
    page.click("nav >> text=Check a new trial")
    expect(page.locator("#live-go")).to_be_enabled()
    page.fill("#live-id", "NCT01070316")
    page.click("#live-go")
    expect(page.locator("#live-view .trial-head")).to_contain_text("Checked live", timeout=120000)
    expect(page.locator("#live-view .verdict .who")).to_contain_text("stub/model")


def test_live_rejects_bad_id(page, live_server):
    page.goto(live_server)
    page.click("nav >> text=Check a new trial")
    page.fill("#live-id", "12345")
    page.click("#live-go")
    expect(page.locator("#live-status")).to_contain_text("NCT01234567")


def test_unknown_trial_message(page, offline_server):
    page.goto(f"{offline_server}/#NCT00000000")
    expect(page.locator("#explore-view .error")).to_contain_text("not in the corpus")
    page.errors.clear()  # le 404 attendu est journalisé par le navigateur


@pytest.mark.parametrize("width", [375, 768])
def test_no_horizontal_scroll_on_small_screens(browser, offline_server, stats, width):
    ctx = browser.new_context(viewport={"width": width, "height": 800})
    page = ctx.new_page()
    for target in (f"{offline_server}/#{stats['showcase'][1]['nct']}", None):
        if target:
            page.goto(target)
            expect(page.locator(".trial-head")).to_be_visible()
        else:
            page.click("nav >> text=Dashboard")
            expect(page.locator("#dash svg").first).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth") <= width
    ctx.close()


def test_theme_toggle(page, offline_server):
    page.goto(offline_server)
    page.click("#theme")
    expect(page.locator("html")).to_have_attribute("data-theme", "light")
    page.click("#theme")
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
    assert bg == "rgb(18, 18, 17)"
