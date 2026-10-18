"""Record the real local app with locally generated narration (macOS).

Requires: Playwright Chromium, macOS `say`, and ffmpeg/ffprobe.
Run: uv run --python 3.12 --with playwright python scripts/record_demo.py
The narration is synthetic speech; the browser interactions and API are real.
"""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from uuid import uuid4

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get("FAULTLINE_URL", "http://localhost:8080")
WORKSPACE = "video-" + uuid4().hex[:12]
LESSON = "Avoid blanket Redis restarts. Drain payment pools before maintenance."
NARRATION = [
    "Meet Faultline, an incident command desk built for Graph Hacks. All demo data is fictional, but the database and queries are real. Falkor D B is the primary context layer. No A I key is required.",
    "Redis is timing out. The agent follows enabled dependency paths and finds six downstream services and three potentially affected customers. It also resolves the owning teams, previous incidents, and runbooks. These are graph facts, not keyword matches.",
    "Follow the arrows. Northstar Commerce depends on Storefront, then Checkout, then Payments, then Redis. Blast radius reasoning traverses that chain in reverse. This view and the response read the same graph.",
    "The query trace shows seven actual graph tool calls, with Cypher, bound parameters, result counts, and timings. This is an audit trail, not hidden model reasoning. The default planner is a deterministic sequence of specialist stages.",
    "Now save a lesson: avoid blanket Redis restarts, and drain payment pools first. This is persistent operator memory in Falkor D B, not browser storage. Helpful lessons can also be saved.",
    "Start a new session and investigate again. The earlier lesson is recalled. Avoid feedback changes applicable runbook recommendations into human review tasks, so the next response does not silently repeat a rejected approach.",
    "Here is the falsifiable test. Disable the Payments to Redis dependency and investigate again. The answer now has one downstream service, Analytics, and one customer, Orbit Labs. Changing a relationship changes the answer. The graph is not decoration.",
    "Response tasks cite their evidence. Approving a task persists a simulated approval only. No page is sent, no runbook is executed, and no infrastructure is changed. Human review stays in control.",
    "Faultline connects company context, multi hop reasoning, and durable incident memory. The repository includes source, real database tests, Docker setup, and a full README. This recording uses synthetic narration over the real running application.",
]


def command(args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def main():
    output = ROOT / "artifacts/faultline-demo.mp4"
    output.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="faultline-video-") as directory:
        temp = Path(directory)
        clips = []
        for index, text in enumerate(NARRATION):
            clip = temp / f"voice-{index}.aiff"
            command(["say", "-v", "Samantha", "-r", "165", "-o", str(clip), text])
            duration = float(
                command(
                    [
                        "ffprobe",
                        "-v",
                        "error",
                        "-show_entries",
                        "format=duration",
                        "-of",
                        "default=noprint_wrappers=1:nokey=1",
                        str(clip),
                    ]
                )
            )
            clips.append((clip, duration))
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1440, "height": 1000},
                record_video_dir=str(temp),
                record_video_size={"width": 1440, "height": 1000},
            )
            context.route(
                "**/api/**",
                lambda route: route.continue_(
                    headers={**route.request.headers, "x-workspace": WORKSPACE}
                ),
            )
            page = context.new_page()
            started = time.monotonic()
            video = page.video
            offsets = []

            def narrate(index):
                offsets.append(round((time.monotonic() - started) * 1000))
                page.wait_for_timeout(int((clips[index][1] + 0.6) * 1000))

            def investigate():
                button = page.get_by_role("button", name="Investigate", exact=True)
                if button.count() == 0:
                    button = page.get_by_role("button", name="Re-investigate", exact=True)
                with page.expect_response(
                    lambda r: r.url.endswith("/api/investigations") and r.request.method == "POST"
                ) as response:
                    button.click()
                assert response.value.status == 200
                expect(page.get_by_role("heading", name="The fault, in context.")).to_be_visible()
                page.evaluate("window.scrollTo(0, 0)")

            page.goto(BASE_URL, wait_until="networkidle")
            expect(page.get_by_role("button", name="Investigate", exact=True)).to_be_enabled()
            narrate(0)
            investigate()
            narrate(1)
            page.get_by_role(
                "heading", name="Dependency topology", exact=True
            ).scroll_into_view_if_needed()
            page.evaluate("window.scrollBy(0, -100)")
            narrate(2)
            page.get_by_role("button", name="Show query trace", exact=True).click()
            page.locator(".trace-trigger").nth(1).click()
            page.locator(".query-detail").scroll_into_view_if_needed()
            narrate(3)
            page.get_by_role("button", name="Workspace memory", exact=True).click()
            page.get_by_role("radio", name="Avoid", exact=True).check()
            page.get_by_label("Learning", exact=False).fill(LESSON)
            page.get_by_role("button", name="Save learning", exact=True).click()
            expect(
                page.get_by_text("Learning saved. Run another investigation to recall it.")
            ).to_be_visible()
            page.evaluate("window.scrollTo(0, 0)")
            narrate(4)
            page.get_by_role("button", name="New session", exact=True).click()
            expect(page.get_by_role("button", name="Investigate", exact=True)).to_be_enabled()
            investigate()
            narrate(5)
            switch = page.get_by_role("switch", name="Payments depends on Redis", exact=True)
            switch.scroll_into_view_if_needed()
            switch.click()
            expect(switch).not_to_be_checked()
            investigate()
            narrate(6)
            page.get_by_role(
                "heading", name="A considered next move.", exact=True
            ).scroll_into_view_if_needed()
            page.get_by_role("button", name="Approve simulation", exact=True).first.click()
            expect(
                page.get_by_role("button", name="Simulated · approved", exact=True).first
            ).to_be_visible()
            narrate(7)
            page.evaluate("window.scrollTo(0, 0)")
            narrate(8)
            context.close()
            video_path = video.path()
            browser.close()
        args = ["ffmpeg", "-y", "-i", video_path]
        for clip, _ in clips:
            args += ["-i", str(clip)]
        filters = [f"[{i + 1}:a]adelay={offset}|{offset}[a{i}]" for i, offset in enumerate(offsets)]
        filters.append(
            "".join(f"[a{i}]" for i in range(len(clips)))
            + f"amix=inputs={len(clips)}:duration=longest:normalize=0[audio]"
        )
        args += [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "0:v",
            "-map",
            "[audio]",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "25",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            "-movflags",
            "+faststart",
            "-shortest",
            str(output),
        ]
        command(args)
        print(
            json.dumps(
                {
                    "video": str(output),
                    "workspace": WORKSPACE,
                    "narration": "macOS Samantha synthetic speech",
                    "bytes": output.stat().st_size,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
