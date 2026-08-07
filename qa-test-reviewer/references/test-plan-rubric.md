# Test Plan & Coverage Rubric

Work through these in order. The point of a written rubric is to stop review from collapsing into a vibe check. Each item forces a concrete question with a concrete answer.

## 1. Build the coverage map first

Before judging anything, list every testable claim and what covers it:

| Requirement / acceptance criterion | Covered by | Status |
|---|---|---|
| e.g. "Valid login → dashboard" | `login.spec: valid login` | ✅ |
| e.g. "Locked account shows a message" | none | ❌ NOT COVERED |

Sources for "requirements" if none are labelled: acceptance criteria on the ticket, the user stories, the API contract, the UI states in the design, and the plain description of what the feature does. Anything the product promises is fair game to test.

The uncovered rows are your first and most important findings. State each by name.

## 2. Gap checklist, applied to every feature

The happy path is rarely where bugs live. For each behaviour, ask each question and record any "no test for that" as a located finding.

**Inputs and boundaries**

- Minimum, maximum, and just past the maximum (max+1, max-length+1).
- Zero, one, and many. Empty string, empty list, empty file.
- Negative numbers, very large numbers, decimals where integers are expected.
- Wrong type, wrong format, unexpected characters, unicode or emoji, whitespace.

**Error and negative paths**

- Every validation rule rejected as well as accepted.
- Server errors (500), timeouts, and slow responses handled gracefully.
- Duplicate or conflicting submissions (409-type cases).

**State and lifecycle**

- Empty or first-run state (no data, new account, no results found).
- Create, read, update, delete, and that delete actually removes.
- Data cleanup between runs so tests stay repeatable.
- Stale data (record changed by someone else since it loaded).

**Identity and permissions**

- Logged out, logged in, wrong role, expired or invalid session.
- Accessing another user's resource (horizontal privilege).
- Elevated actions blocked for normal users (vertical privilege).

**Concurrency and timing**

- Double-click or double-submit.
- Two users acting on the same resource.
- Actions fired before the page or data is ready.

**Cross-cutting**

- Slow or flaky network, offline.
- Refresh or back-button mid-flow.
- Accessibility of the path being tested (reachable by keyboard, labelled).

You don't need a test for every cell for every feature. Judgement applies. But each *missing* one should be a conscious decision, not an oversight. Surface the ones that carry real risk.

## 3. Quality of existing tests

A test can exist and still be worthless. Check:

- **Does it actually assert?** Steps that navigate and click but never `expect(...)` anything prove nothing. Flag any test whose only "assertion" is that it didn't throw.
- **Does it assert the right thing?** Observable outcome (what a user or API consumer sees) rather than an internal detail (a CSS class, a private field, a DOM path).
- **Is it at the right layer?** A slow, fragile UI test for logic an API test would nail more cheaply is a design smell.
- **Is it independent?** Could it run alone, in any order, in parallel? Note any ordering or shared-state assumptions.
- **Is the title truthful?** `test('user can log in')` that only checks the button is enabled is lying.

## 4. Balance and prioritisation

Are there many near-duplicate happy-path tests while error paths go untested? Recommend reallocating rather than piling on. Is the critical user flow (the thing that loses money if it breaks) covered first and well? Is anything being tested that doesn't matter, like brittle checks on cosmetic details that will generate false failures?

## 5. Questions that tease out hidden gaps

When a plan looks complete, these prompts often reveal the missing 20%:

- "What's the worst input a hostile or careless user could send here?"
- "What happens if this step half-succeeds: request sent, response lost?"
- "Which of these tests would still pass if the feature were quietly broken?"
- "If I shipped exactly what's tested and nothing more, what breaks in production?"
- "What does the ticket's acceptance criteria say, word for word, that no test mentions?"
