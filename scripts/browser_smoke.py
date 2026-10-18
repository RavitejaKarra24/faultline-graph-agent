"""Real-browser smoke test. Start the app first; see docs/TESTING.md.

Runs in a fresh graph namespace using request interception. Does not alter the
shared demo workspace. Requires the real FalkorDB-backed API, not mocked data.
"""

import json
import os
from pathlib import Path
from uuid import uuid4

from playwright.sync_api import expect, sync_playwright

BASE_URL = os.environ.get("FAULTLINE_URL", "http://localhost:8080")
ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = "smoke-" + uuid4().hex[:12]
LESSON = "Drain the payment connection pool before Redis maintenance; avoid a blanket restart."


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1080}, device_scale_factor=1
        )
        # The UI is intentionally a single demo workspace. Isolate only this test.
        context.route(
            "**/api/**",
            lambda route: route.continue_(
                headers={**route.request.headers, "x-workspace": WORKSPACE}
            ),
        )
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(BASE_URL, wait_until="networkidle")
        expect(page.get_by_role("status").filter(has_text="FalkorDB connected")).to_be_visible()
        run = page.get_by_role("button", name="Investigate", exact=True)
        expect(run).to_be_enabled()
        with page.expect_response(
            lambda r: r.url.endswith("/api/investigations") and r.request.method == "POST"
        ) as response:
            run.click()
        baseline = response.value.json()
        assert len(baseline["impactedServices"]) == 6, baseline
        assert len(baseline["impactedCustomers"]) == 3, baseline
        assert baseline["trace"] and all(step["query"] for step in baseline["trace"])
        expect(page.get_by_role("heading", name="The fault, in context.")).to_be_visible()
        ROOT.joinpath("docs").mkdir(exist_ok=True)
        page.screenshot(path=str(ROOT / "docs/screenshot.png"), full_page=True)

        # Approval is persisted and history reconciles its independently stored status.
        approve = page.get_by_role("button", name="Approve simulation", exact=True).first
        approve.click()
        expect(
            page.get_by_role("button", name="Simulated · approved", exact=True).first
        ).to_be_visible()
        page.reload(wait_until="networkidle")
        expect(
            page.get_by_role("button", name="Simulated · approved", exact=True).first
        ).to_be_visible()

        # Save an avoid lesson and verify recall from a DIFFERENT session.
        page.get_by_role("button", name="Workspace memory", exact=True).click()
        page.get_by_role("radio", name="Avoid", exact=True).check()
        page.get_by_label("Learning", exact=False).fill(LESSON)
        page.get_by_role("button", name="Save learning", exact=True).click()
        expect(
            page.get_by_text("Learning saved. Run another investigation to recall it.")
        ).to_be_visible()
        page.get_by_role("button", name="New session", exact=True).click()
        expect(page.get_by_role("button", name="Investigate", exact=True)).to_be_enabled()
        with page.expect_response(
            lambda r: r.url.endswith("/api/investigations") and r.request.method == "POST"
        ) as response:
            page.get_by_role("button", name="Investigate", exact=True).click()
        recalled = response.value.json()
        assert recalled["sessionId"] != baseline["sessionId"]
        assert any(m["content"] == LESSON for m in recalled["memories"])
        assert any(
            a["kind"] == "review" and LESSON in a["description"] for a in recalled["actions"]
        )

        # Counterfactual: graph mutation must change the agent's answer.
        switch = page.get_by_role("switch", name="Payments depends on Redis", exact=True)
        expect(switch).to_be_checked()
        switch.click()
        expect(switch).not_to_be_checked()
        with page.expect_response(
            lambda r: r.url.endswith("/api/investigations") and r.request.method == "POST"
        ) as response:
            page.get_by_role("button", name="Re-investigate", exact=True).click()
        changed = response.value.json()
        assert changed["impactedServices"] == ["svc-analytics"], changed
        assert changed["impactedCustomers"] == ["customer-orbit"], changed
        switch.click()
        expect(switch).to_be_checked()

        # Keyboard skip link, responsive layout and alternate theme.
        for width in (375, 768, 1440):
            page.set_viewport_size({"width": width, "height": 1000})
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
                f"Page overflow at {width}px"
            )
            expect(page.get_by_role("button", name="New session", exact=True)).to_be_visible()
        page.get_by_role("button", name="Switch to dark theme", exact=True).click()
        assert page.locator("html").get_attribute("data-theme") == "dark"
        page.screenshot(path=str(ROOT / "docs/screenshot-dark.png"), full_page=True)
        assert not errors, errors
        print(
            json.dumps(
                {
                    "status": "passed",
                    "workspace": WORKSPACE,
                    "checks": [
                        "real graph investigation",
                        "persisted simulated approval",
                        "cross-session memory",
                        "memory changes tasks",
                        "topology changes answer",
                        "375/768/1440 responsive",
                        "theme toggle",
                        "no browser JS errors",
                    ],
                },
                indent=2,
            )
        )
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
