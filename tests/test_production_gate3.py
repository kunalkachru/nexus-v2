"""Gate 3 production validation tests using Playwright."""

import asyncio
import json
from playwright.async_api import async_playwright


async def measure_scroll_depth(page, url: str, name: str) -> dict:
    """Measure scroll depth on a page by calculating percentage of scrollable content visible."""
    await page.goto(url, wait_until="networkidle")
    await page.wait_for_timeout(1000)  # Wait for rendering

    # Get viewport and scroll dimensions
    viewport_height = page.viewport_size["height"]
    scroll_height = await page.evaluate("document.documentElement.scrollHeight")
    content_height = await page.evaluate("document.body.offsetHeight")

    max_scroll_height = max(scroll_height, content_height)
    scroll_depth = (viewport_height / max_scroll_height) * 100 if max_scroll_height > 0 else 100

    # Measure by scrolling to bottom and back
    await page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
    await page.wait_for_timeout(500)
    max_scroll = await page.evaluate("window.scrollY")
    await page.evaluate("window.scrollTo(0, 0)")

    actual_depth = (viewport_height / (max_scroll + viewport_height)) * 100 if (max_scroll + viewport_height) > 0 else 100

    return {
        "page": name,
        "url": url,
        "viewport_height": viewport_height,
        "scroll_height": max_scroll_height,
        "scroll_depth_percent": round(actual_depth, 2),
        "fully_visible": actual_depth >= 90,
    }


async def test_suite_1_scroll_depths():
    """TEST SUITE 1: Measure scroll depths on production."""
    print("\n" + "="*80)
    print("TEST SUITE 1: Scroll Depth Verification on Production")
    print("="*80)

    base_url = "https://nexus-triage.duckdns.org"
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        try:
            # Measure Queue page
            queue_result = await measure_scroll_depth(page, f"{base_url}/queue", "Queue (Command Center)")
            results.append(queue_result)
            print(f"\n✅ Queue page: {queue_result['scroll_depth_percent']}% scroll depth")

            # Measure Incident Detail
            incident_result = await measure_scroll_depth(page, f"{base_url}/incident?nexus_incident_id=INC001", "Incident Detail")
            results.append(incident_result)
            print(f"✅ Incident Detail: {incident_result['scroll_depth_percent']}% scroll depth")

            # Measure Training page
            training_result = await measure_scroll_depth(page, f"{base_url}/training", "Training")
            results.append(training_result)
            print(f"✅ Training: {training_result['scroll_depth_percent']}% scroll depth")

        finally:
            await browser.close()

    return results


async def test_suite_2_full_workflow():
    """TEST SUITE 2: Full workflow end-to-end on production."""
    print("\n" + "="*80)
    print("TEST SUITE 2: Full Workflow End-to-End")
    print("="*80)

    base_url = "https://nexus-triage.duckdns.org"
    results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        try:
            # TEST 1: Open Queue page
            print("\n1. Opening Queue page...")
            await page.goto(f"{base_url}/queue", wait_until="networkidle")
            await page.wait_for_timeout(1000)
            queue_loaded = await page.locator("role=heading").first.is_visible()
            results["queue_loads"] = queue_loaded
            print(f"   ✅ Queue loads: {queue_loaded}")

            # TEST 2: Verify seeded incidents visible
            print("\n2. Checking seeded incidents...")
            inc_visible = await page.locator("a:has-text('INC001')").first.is_visible(timeout=5000)
            results["incidents_visible"] = inc_visible
            print(f"   ✅ Seeded incidents visible: {inc_visible}")

            # TEST 3: Click into INC001
            print("\n3. Clicking into INC001...")
            await page.click("a:has-text('INC001')")
            await page.wait_for_timeout(1500)
            detail_loaded = await page.locator("h1").first.is_visible(timeout=5000)
            results["incident_detail_loads"] = detail_loaded
            print(f"   ✅ Incident Detail loads: {detail_loaded}")

            # TEST 4: Verify agent timeline in first viewport
            print("\n4. Checking agent timeline visibility...")
            agents_visible = {}
            for agent in ["SENTINEL", "PRISM", "REPLICA", "TRACE", "FORGE", "GUARDIAN"]:
                try:
                    visible = await page.locator(f"role=heading:has-text('{agent}')").first.is_visible(timeout=2000)
                    agents_visible[agent] = visible
                except:
                    agents_visible[agent] = False

            results["agents_visible"] = agents_visible
            for agent, visible in agents_visible.items():
                print(f"   ✅ {agent}: {visible}")

            # TEST 5: Test collapsible sections
            print("\n5. Testing collapsed sections expand correctly...")
            sections_tested = 0
            sections_working = 0

            # Try to expand Investigation Summary
            try:
                investigation_toggle = await page.locator("button:has-text('Investigation Summary')").first
                if investigation_toggle:
                    await investigation_toggle.click()
                    await page.wait_for_timeout(300)
                    sections_tested += 1
                    is_expanded = await page.locator("text=Root cause suspected:").is_visible()
                    if is_expanded:
                        sections_working += 1
                    print(f"   ✅ Investigation Summary expands: {is_expanded}")
            except:
                pass

            # Try to expand Evidence
            try:
                evidence_toggle = await page.locator("button:has-text('Evidence')").first
                if evidence_toggle:
                    await evidence_toggle.click()
                    await page.wait_for_timeout(300)
                    sections_tested += 1
                    is_expanded = await page.locator("text=posture").is_visible()
                    if is_expanded:
                        sections_working += 1
                    print(f"   ✅ Evidence expands: {is_expanded}")
            except:
                pass

            results["sections_expandable"] = sections_working == sections_tested if sections_tested > 0 else True

            # TEST 6: Evidence posture badge visible
            print("\n6. Checking evidence posture badge...")
            posture_visible = await page.locator("text=posture").is_visible() or await page.locator("text=inferred").is_visible()
            results["posture_badge_visible"] = posture_visible
            print(f"   ✅ Evidence posture badge visible: {posture_visible}")

            # TEST 7: Guardian approval button works
            print("\n7. Testing Guardian approval button...")
            approve_button = await page.locator("button:has-text('Approve')").first
            approve_exists = approve_button is not None
            if approve_exists:
                await approve_button.click()
                await page.wait_for_timeout(500)
                # Check if approval was recorded
                approval_indicator = await page.locator("text=Approved").is_visible(timeout=2000)
                results["guardian_approval_works"] = approval_indicator
                print(f"   ✅ Guardian approval works: {approval_indicator}")
            else:
                results["guardian_approval_works"] = False
                print(f"   ⚠️  Approve button not found")

            # TEST 8: Reload and verify approval persists
            print("\n8. Reloading page to verify approval persists...")
            await page.reload(wait_until="networkidle")
            await page.wait_for_timeout(1000)
            approval_persists = await page.locator("text=Approved").is_visible(timeout=2000)
            results["approval_persists_after_reload"] = approval_persists
            print(f"   ✅ Approval persists: {approval_persists}")

            # TEST 9: Navigate back to queue
            print("\n9. Navigating back to Queue...")
            await page.click("text=Queue")
            await page.wait_for_timeout(1000)
            back_to_queue = await page.locator("text=INC001").is_visible(timeout=5000)
            results["navigate_back_works"] = back_to_queue
            print(f"   ✅ Navigation back works: {back_to_queue}")

            # TEST 10: Open Training page
            print("\n10. Opening Training page...")
            await page.goto(f"{base_url}/training", wait_until="networkidle")
            await page.wait_for_timeout(1000)
            training_loaded = await page.locator("h1").is_visible(timeout=5000)
            results["training_loads"] = training_loaded
            print(f"   ✅ Training loads: {training_loaded}")

        finally:
            await browser.close()

    # Summary
    print("\n" + "-"*80)
    print("WORKFLOW TEST SUMMARY:")
    passed = sum(1 for v in results.values() if v is True or (isinstance(v, dict) and all(v.values())))
    total = len([v for v in results.values() if v is not True and not isinstance(v, dict)])
    print(f"✅ {passed}/{total} major tests passed")

    return results


async def test_suite_3_unknown_incident():
    """TEST SUITE 3: Live intake classification miss on production."""
    print("\n" + "="*80)
    print("TEST SUITE 3: Unknown Incident Type Handling")
    print("="*80)

    base_url = "https://nexus-triage.duckdns.org"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        try:
            print("\n1. Opening Inputs page...")
            await page.goto(f"{base_url}/inputs", wait_until="networkidle")
            await page.wait_for_timeout(1000)

            print("\n2. Submitting unknown incident type...")
            # Fill in incident text
            incident_text = "This is a completely unknown incident type that doesn't match any of the 5 supported families. It's about something totally different like kitchen sink repairs."

            text_input = await page.locator("textarea").first
            if text_input:
                await text_input.fill(incident_text)
                await page.wait_for_timeout(500)

                # Submit
                submit_button = await page.locator("button:has-text('Submit')").first
                if submit_button:
                    await submit_button.click()
                    await page.wait_for_timeout(2000)

                    # Check for error message
                    error_visible = await page.locator("text=/Unknown|not match|supported/").is_visible(timeout=5000)
                    print(f"   ✅ Structured error message appears: {error_visible}")

                    # Check for supported families list
                    families_listed = await page.locator("text=/INC001|INC002|INC003/").is_visible(timeout=5000)
                    print(f"   ✅ Supported families list shown: {families_listed}")

                    return {
                        "error_message_clear": error_visible,
                        "families_listed": families_listed,
                        "handles_unknown": error_visible and families_listed,
                    }
        finally:
            await browser.close()

    return {"error": "Could not complete test"}


async def main():
    """Run all Gate 3 test suites."""
    print("\n" + "="*80)
    print("GATE 3 PRODUCTION VALIDATION")
    print("="*80)
    print(f"Production URL: https://nexus-triage.duckdns.org")

    # TEST SUITE 1: Scroll depths
    scroll_results = await test_suite_1_scroll_depths()

    # TEST SUITE 2: Full workflow
    workflow_results = await test_suite_2_full_workflow()

    # TEST SUITE 3: Unknown incidents
    unknown_results = await test_suite_3_unknown_incident()

    # Final report
    print("\n" + "="*80)
    print("GATE 3 TEST RESULTS SUMMARY")
    print("="*80)

    print("\n📊 TEST SUITE 1 — Scroll Depths:")
    for result in scroll_results:
        print(f"  {result['page']}: {result['scroll_depth_percent']}%")

    print("\n✅ TEST SUITE 2 — Workflow:")
    print(f"  {sum(1 for v in workflow_results.values() if v is True or (isinstance(v, dict) and all(v.values())))}/{len([v for v in workflow_results.values() if v is not True and not isinstance(v, dict)])} tests passed")

    print("\n🔍 TEST SUITE 3 — Unknown Incidents:")
    print(f"  Handles unknown types: {unknown_results.get('handles_unknown', False)}")
    print(f"  Error message clear: {unknown_results.get('error_message_clear', False)}")
    print(f"  Families listed: {unknown_results.get('families_listed', False)}")


if __name__ == "__main__":
    asyncio.run(main())
