You are running a focused frontend fix sprint for NEXUS. Work continuously through all items below without stopping for approval between items. Apply governance rules throughout: compact at 50% context, 2-failure retry limit then mark blocked, never call ScheduleWakeup, ask only if genuinely uncertain.

Current baseline: 450 tests passing, 21 browser tests passing.
Every item must leave these baselines intact or higher.
For every UI change: open a headed Playwright browser (headless=False) and take sequential viewport screenshots BEFORE and AFTER to verify the change looks correct. Do not mark any UI item done based on code alone.

---

ITEM B1 — Fix inputs.js navigation timing hack (CRITICAL — do this first)

The form submission in /inputs uses setTimeout(100ms) before navigating to the new incident. This breaks when the server is slow. Fix it properly.

Implementation:
1. Read frontend/static/inputs.js in full
2. Find the form submission handler
3. Remove every setTimeout call from the submission flow
4. Rewrite so navigation happens INSIDE the fetch .then() callback after the response JSON is parsed:
   fetch('/api/v1/incidents/raw-text', {...})
     .then(res => res.json())
     .then(data => {
       const id = data.nexus_incident_id || data.id;
       if (id) {
         window.location.href = `/incident?nexus_incident_id=${id}&return_to=/queue`;
       } else {
         showError('Incident created but could not navigate. Check the queue.');
       }
     })
     .catch(err => {
       showError('Failed to submit incident. Please try again.');
       resetSubmitButton();
     })
5. Add loading state: when submit is clicked, disable the button and change its text to "Submitting..."
6. Add resetSubmitButton() function that re-enables the button and restores original text
7. Add showError(message) function that displays an error inline on the page (not alert())

Verify with headed Playwright:
- Submit a valid incident → verify URL changes to /incident?nexus_incident_id=nxs_...
- Submit an empty form → verify inline error appears, button re-enables
- No setTimeout anywhere in the submission path

Done when: Navigation works 100% of the time regardless of server response time, no setTimeout in submission flow, error states handled gracefully.

---

ITEM B2 — Add in-product onboarding and empty states (CRITICAL — do this second)

A new user landing on the queue page sees 5 incidents with no context. Add onboarding.

Implementation:

Queue page (frontend/queue.html):
1. Add a dismissible banner as the FIRST element inside the main content area, above the incident list:
   <div id="onboarding-banner" class="onboarding-banner" style="display:none;">
     <div class="onboarding-content">
       <strong>Welcome to NEXUS</strong> — These 5 incidents demonstrate the supported outage families.
       Submit your first real incident at <a href="/inputs">the intake page</a>, or click any incident below to explore the investigation workflow.
       <button onclick="dismissOnboarding()" class="onboarding-dismiss">Got it</button>
     </div>
   </div>
2. Add JavaScript:
   function dismissOnboarding() {
     localStorage.setItem('nexus.onboarding.dismissed', '1');
     document.getElementById('onboarding-banner').style.display = 'none';
   }
   // Show banner if not dismissed
   if (!localStorage.getItem('nexus.onboarding.dismissed')) {
     document.getElementById('onboarding-banner').style.display = 'block';
   }
3. Add .onboarding-banner CSS to dashboard.css: subtle background, padding, flex layout with dismiss button on the right

Inputs page (frontend/inputs.html):
4. Add a "Supported incident families" section above the form:
   <div class="supported-families">
     <h3>Supported incident types</h3>
     <ul>
       <li><strong>Checkout timeout</strong> — Retry amplification causing cascading timeouts</li>
       <li><strong>DB pool exhaustion</strong> — Connection pool saturated, new requests blocked</li>
       <li><strong>Deploy regression</strong> — Recent deployment causing 5xx spike</li>
       <li><strong>Queue backlog</strong> — Worker queue backlogged affecting transaction completion</li>
       <li><strong>Auth dependency slowdown</strong> — Token validation failures from slow auth service</li>
     </ul>
     <p class="section-note">Incidents outside these families will receive a structured error with guidance.</p>
   </div>
5. Add placeholder text to the main text area: "Describe the incident symptoms. Example: 'Database connection pool exhausted, all 50 connections in use, new requests timing out after 30 seconds'"

Incident page (frontend/incident.html):
6. Add a one-line caption below the agent progress grid:
   <p class="agent-flow-caption">SENTINEL classifies → PRISM diagnoses → REPLICA reproduces → TRACE debugs → FORGE recommends → GUARDIAN approves</p>
7. For demo/seeded incidents (INC001, INC002, INC003, INC005, INC007), add a "Demo incident" badge near the incident ID. Detect demo incidents by checking if nexus_incident_id starts with "INC" in the JavaScript that renders the page.

Training page (frontend/training.html):
8. After the scorecard loads, check if incidents_handled is 0 or equals exactly 5 (the hardcoded demo value). If so, show a callout:
   <div class="empty-state-callout">Submit real incidents via <a href="/inputs">the intake page</a> to see your actual metrics here.</div>

Verify with headed Playwright:
- First visit to queue shows banner
- Dismiss banner
- Revisit queue — banner gone
- Inputs page shows 5 family descriptions
- Incident page shows agent flow caption

Done when: All 4 pages have onboarding/guidance content, dismissal persists in localStorage, no existing tests broken.

---

ITEM B3 — Replace inline CSS with design system classes (CODE QUALITY)

incident.html has hundreds of style="" attributes. Extract to dashboard.css.

Implementation:
1. Read frontend/incident.html in full and identify all repeated inline style patterns
2. Take a Playwright screenshot BEFORE making any changes (this is your baseline)
3. Add these utility classes to frontend/static/dashboard.css:
   .font-xs { font-size: 0.75rem; }
   .font-sm { font-size: 0.85rem; }
   .font-md { font-size: 0.9rem; }
   .font-lg { font-size: 1.5rem; }
   .mb-4 { margin-bottom: 4px; }
   .mb-8 { margin-bottom: 8px; }
   .mb-12 { margin-bottom: 12px; }
   .mb-16 { margin-bottom: 16px; }
   .mt-8 { margin-top: 8px; }
   .mt-12 { margin-top: 12px; }
   .p-0 { padding: 0; }
   .p-6 { padding: 6px; }
   .p-12 { padding: 12px; }
   .agent-grid-3col { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
   .agent-grid-cell { padding: 6px; background-color: rgba(255,255,255,0.05); border-radius: 4px; }
   .hero-tight { padding: 12px 0; }
   .hero-panel-flush { padding: 0; }
   .stat-tight { flex: 1; }
   .stat-label-xs { font-size: 0.7rem; }
   .stat-value-sm { font-size: 0.9rem; }
4. Replace inline styles in incident.html with these classes where applicable
5. Take a Playwright screenshot AFTER — must be pixel-identical to the before screenshot
6. IMPORTANT: Only replace static styles. Leave any style="" attributes that are set dynamically by JavaScript.
7. Apply the same process to queue.html, training.html, inputs.html

Done when: grep -c 'style="' frontend/incident.html returns ≤ 20 (only JS-dynamic styles remain), before/after screenshots are visually identical, all tests pass.

---

ITEM B4 — Fix Guardian button structural viewport position (UX CRITICAL)

Guardian approval buttons must be visible in the initial viewport without scrolling. The current sticky CSS approach is unreliable. Fix structurally.

Implementation:
1. Read frontend/incident.html and find the Guardian Gate card / approval buttons section
2. Move the entire Guardian Gate card to be the FIRST section after the hero stats block, before any <details> collapsed sections
3. Remove position: sticky and top: 120px CSS from the Guardian card — structural position is more reliable
4. Add data-testid="guardian-approve-btn" to the Approve button
5. Add data-testid="guardian-reject-btn" to the Reject button
6. Add data-testid="guardian-escalate-btn" to the Escalate button if it exists
7. Verify the card renders at the top of the content area, below the hero stats
8. Test at three viewport sizes using Playwright:
   - 1280x720 (desktop): Guardian buttons must have visible bounding box without scrolling
   - 768x1024 (tablet): same
   - 390x844 (mobile): acceptable if scroll needed, but must be within first 2 scrolls

Take sequential viewport screenshots at 1280x720 showing what is visible before any scrolling — Guardian buttons must appear in these screenshots.

Done when:
- Playwright waitForSelector('[data-testid="guardian-approve-btn"]', {state: 'visible'}) succeeds within 3 seconds at 1280x720
- Guardian buttons visible in first viewport screenshot without scrolling
- Click approve → reload → approved state still shown (persistence still working)
- All 450 existing tests pass

---

AFTER ALL ITEMS:

1. Run full browser test suite:
   npm run browser:verify
   Report exact count — must be 21+ passing

2. Run unit tests:
   pytest tests/ --ignore=tests/test_production_gate3.py -q
   Report exact count — must be 450+ passing

3. Run smoke tests against production:
   bash scripts/test-live.sh https://nexus-triage.duckdns.org
   Report all 5 results

4. Commit and push:
   git add -A && git commit -m "fix(frontend): navigation timing, onboarding, inline CSS cleanup, Guardian viewport fix" && git push origin master

5. Report final status table:
   | Item | Status | Notes |
   |------|--------|-------|
   | B1: Navigation fix | PASS/FAIL | |
   | B2: Onboarding | PASS/FAIL | |
   | B3: Inline CSS | PASS/FAIL | |
   | B4: Guardian viewport | PASS/FAIL | |
