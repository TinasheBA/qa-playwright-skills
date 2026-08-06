---
name: qa-test-reviewer
description: >-
  Adversarially review a QA test plan or a set of automated tests for coverage
  gaps, weak assertions, and flakiness before they're trusted. Use this skill
  whenever the user asks to review, critique, sanity-check, or "find the holes
  in" a test plan, test cases, acceptance-criteria coverage, or Playwright/other
  test code — and especially as a separate second pass over tests just written
  (including tests an AI wrote), since authors reliably miss their own gaps. Also
  use it when the user has requirements/acceptance criteria and wants to know
  what still isn't tested. This is a critic, not an author: it hunts for what's
  missing and what will break, and reports specific, located findings rather
  than a vague "looks good".
---

# QA Test Reviewer

This skill exists to do one thing well: find what a test plan or test suite is
missing or getting wrong, *before* anyone relies on it. Its value is not
intelligence — it's refusing to be lazy. Asked "does this look good?", a
reviewer drifts toward "looks good". So this skill never asks that question. It
runs fixed passes that force specific, located findings.

Two hard rules make the difference between real review and rubber-stamping:

1. **You are trying to break it, not bless it.** Approach every plan and test as
   if a bug is hiding in it and your job is to find it. Default to suspicion. If
   you're unsure whether something is covered, treat it as *not* covered until
   proven otherwise.
2. **Every finding must be specific and located.** Never "consider adding more
   tests" or "coverage could be improved". Say *which* acceptance criterion has
   no test, *which* scenario is missing, *which* line asserts nothing. A finding
   the author can't act on in under a minute isn't a finding.

This matters most when reviewing tests that were just written — including your
own or another AI's. The assumptions that produced a gap also hide it from the
author, so a fresh adversarial pass with a checklist catches what self-review
rationalises away. Run this as a genuinely separate step, not a glance back at
work you just did.

## First, identify what you're reviewing

Pick the pass that fits the input; do both if both are present:

- **A test plan / test cases / acceptance criteria** (prose, a table, a
  spreadsheet, tickets) → run **Pass A: Coverage & test design** below.
- **Test code** (Playwright or otherwise) → run **Pass B: Code-level review**
  below, using `references/playwright-code-smells.md` for Playwright specifics.

If you were given requirements *and* tests, do both and, most importantly, check
them against each other — the plan may promise coverage the code doesn't
deliver.

## Pass A: Coverage & test design

Full checklist in `references/test-plan-rubric.md`. The backbone:

**1. Map every requirement to a test — out loud.** Build an explicit list: each
acceptance criterion (or user story, or documented behaviour) on one side, the
test(s) that cover it on the other. Any criterion with nothing next to it is a
finding, stated by name. This single step catches the majority of real gaps, and
it's the step reviewers most often skip.

**2. Run the gap checklist against each feature.** For every behaviour, the happy
path is the easy half. Deliberately probe the rest — these are the buckets where
defects actually live:

- Boundary values (0, 1, max, max+1, empty, very long, negative).
- Negative / error paths (invalid input, wrong type, missing fields, rejected).
- Empty and "first run" states (no data yet, no results, new account).
- Permissions and roles (logged out, wrong role, expired session, another
  user's resource).
- Concurrency and duplication (double submit, two users, stale data).
- Data lifecycle (creation, update, delete, and cleanup between runs).
- Cross-cutting: what happens on a slow network, an error response, a refresh
  mid-flow.

Name the specific missing case, not the bucket: "no test for submitting the form
twice quickly (duplicate order risk)", not "consider concurrency".

**3. Judge the quality of the tests that *do* exist.** Coverage on paper can
still be hollow:

- Does each test assert an *observable outcome*, or does it just execute steps
  and never really check anything? A test with no meaningful assertion is a
  false sense of security.
- Is the test title honest about what it verifies?
- Are steps concrete and reproducible, or vague ("verify it works")?
- Is the test at the right layer — a slow UI test for something an API test
  would cover more reliably?

**4. Weigh what's *over*-tested too.** Ten near-identical happy-path variations
while the error paths go untested is a misallocation. Say so — good review
redirects effort, it doesn't only add to the pile.

## Pass B: Code-level review

For test *code*, run Pass A's coverage thinking plus a code-quality pass. For
Playwright/TypeScript the high-value smells are in
`references/playwright-code-smells.md`; the essentials:

- **Flakiness smells** — hard sleeps (`waitForTimeout`), `networkidle` used as a
  wait, one-shot assertions (`expect(await ...isVisible())`) instead of
  auto-retrying `expect(locator)`, structural CSS/XPath selectors, race
  conditions around navigation and responses.
- **Isolation smells** — shared mutable state between tests, order dependence,
  fixed data that collides under parallel workers, missing cleanup.
- **Assertion smells** — tests that act but never assert, assertions on
  implementation details rather than user-visible outcomes, swallowed errors.
- **Maintainability smells** — copy-pasted selectors that should be a page
  object, secrets hard-coded in the test, magic values with no meaning.

For each, point at the location and give the fix, briefly.

## How to report findings

Report so the author can act immediately. Order by severity — a missing
critical-path test or a guaranteed flake first, style nits last. Use this shape:

```
## Summary
<2–3 sentences: overall coverage state and the most important gap.>

## Coverage map
<Each requirement/criterion → covered / partially covered / NOT covered,
 with the test name or "none".>

## Findings
### 🔴 High — <short title>
- Where: <criterion name / file:line / test title>
- Problem: <what's missing or wrong>
- Why it matters: <the bug or false-confidence it allows>
- Fix: <the specific test to add or change>

### 🟡 Medium — ...
### 🟢 Low — ...

## What's done well
<Briefly — honest reviewers acknowledge solid coverage so the signal on the
 problems stays credible.>
```

Severity guide: **High** = a real user-facing path or contract with no coverage,
or a test that will flake/fail spuriously in CI. **Medium** = a meaningful edge
case missing, or a weak/hollow assertion. **Low** = naming, structure, minor
duplication.

## The two failure modes to avoid

- **Rubber-stamping** — "looks comprehensive, nice work." If you produced no
  located findings on a non-trivial suite, you didn't review it; you skimmed it.
  Go back to the coverage map and the gap checklist.
- **Noise** — twenty style nitpicks that bury the one missing auth test.
  Severity-order exists so the important finding is read first. Prune the trivia
  or clearly mark it Low.

## Reference files

- `references/test-plan-rubric.md` — the full coverage and test-design checklist,
  with prompts for teasing out missing cases.
- `references/playwright-code-smells.md` — Playwright/TypeScript-specific smells
  with before/after examples, mirroring the `playwright-test-author` skill so the
  two agree on what "good" looks like.
