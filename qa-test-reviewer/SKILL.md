---
name: qa-test-reviewer
description: >-
  Adversarially review a QA test plan or a set of automated tests for coverage
  gaps, weak assertions, and flakiness before they're trusted. Use this skill
  whenever the user asks to review, critique, sanity-check, or "find the holes
  in" a test plan, test cases, acceptance-criteria coverage, or Playwright or
  other test code. Especially useful as a separate second pass over tests just
  written (including tests an AI wrote), since authors reliably miss their own
  gaps. Also use it when the user has requirements/acceptance criteria and wants
  to know what still isn't tested. This is a critic, not an author: it hunts for
  what's missing and what will break, and reports specific, located findings
  rather than a vague "looks good".
---

# QA Test Reviewer

This skill exists to do one thing well: find what a test plan or test suite is missing or getting wrong, *before* anyone relies on it. Its value isn't intelligence. It's refusing to be lazy. Asked "does this look good?", a reviewer drifts toward "looks good". So this skill never asks that question. It runs fixed passes that force specific, located findings.

Two hard rules make the difference between real review and rubber-stamping.

**One: you are trying to break it, not bless it.** Approach every plan and test as if a bug is hiding in it and your job is to find it. Default to suspicion. If you're unsure whether something is covered, treat it as *not* covered until proven otherwise.

**Two: every finding must be specific and located.** Never "consider adding more tests" or "coverage could be improved". Say *which* acceptance criterion has no test, *which* scenario is missing, *which* line asserts nothing. A finding the author can't act on in under a minute isn't a finding.

This matters most when reviewing tests that were just written, including your own or another AI's. The assumptions that produced a gap also hide it from the author, so a fresh adversarial pass with a checklist catches what self-review talks itself out of. Run this as a genuinely separate step, not a glance back at work you just did.

A note on what this skill can and cannot do. Passes A and B share their definition of "good" with the `playwright-test-author` skill on purpose. They catch *drift* from that standard (a leftover sleep, an unmapped acceptance criterion, a hollow assertion), but they can't catch a defect the standard itself doesn't forbid. That's what **Pass C: Beyond the rules** is for: a mandatory rules-agnostic step that asks what could still be broken in production even if everything else here is green. Run all three passes that apply. Skipping Pass C means the reviewer shares whatever blind spots the author skill has, which is exactly the failure mode two separate skills are supposed to prevent.

## First, identify what you're reviewing

Pick the passes that fit the input. Always run every pass that applies. Pass C in particular is mandatory whenever a plan or code is present, since it's the only pass that steps outside the shared standard.

- A test plan, test cases, or acceptance criteria (prose, table, spreadsheet, tickets). Run **Pass A: Coverage & test design**.
- Test code (Playwright or otherwise). Run **Pass B: Code-level review**, using `references/playwright-code-smells.md` for Playwright specifics.
- Anything at all. Run **Pass C: Beyond the rules** last, on whatever is in front of you.

If you were given requirements *and* tests, do A, B, and C, and most importantly check the plan and the code against each other. The plan may promise coverage the code doesn't deliver.

## Pass A: Coverage & test design

Full checklist in `references/test-plan-rubric.md`. The backbone:

**1. Map every requirement to a test, out loud.** Build an explicit list: each acceptance criterion (or user story, or documented behaviour) on one side, the test(s) that cover it on the other. Any criterion with nothing next to it is a finding, stated by name. This single step catches the majority of real gaps, and it's the step reviewers most often skip.

**2. Run the gap checklist against each feature.** For every behaviour, the happy path is the easy half. Deliberately probe the rest. These are the buckets where defects actually live:

- Boundary values (0, 1, max, max+1, empty, very long, negative).
- Negative or error paths (invalid input, wrong type, missing fields, rejected).
- Empty and "first run" states (no data yet, no results, new account).
- Permissions and roles (logged out, wrong role, expired session, another user's resource).
- Concurrency and duplication (double submit, two users, stale data).
- Data lifecycle (creation, update, delete, and cleanup between runs).
- Cross-cutting: what happens on a slow network, an error response, a refresh mid-flow.

Name the specific missing case, not the bucket. "No test for submitting the form twice quickly (duplicate order risk)" beats "consider concurrency".

**3. Judge the quality of the tests that *do* exist.** Coverage on paper can still be hollow:

- Does each test assert an *observable outcome*, or does it just execute steps and never really check anything? A test with no meaningful assertion is a false sense of security.
- Is the test title honest about what it verifies?
- Are steps concrete and reproducible, or vague ("verify it works")?
- Is the test at the right layer? A slow UI test for something an API test would cover more reliably is a design smell.

**4. Weigh what's *over*-tested too.** Ten near-identical happy-path variations while the error paths go untested is a misallocation. Say so. Good review redirects effort, it doesn't only add to the pile.

## Pass B: Code-level review

For test *code*, run Pass A's coverage thinking plus a code-quality pass. For Playwright and TypeScript the high-value smells are in `references/playwright-code-smells.md`. The essentials:

**Flakiness smells.** Hard sleeps (`waitForTimeout`), `networkidle` used as a wait, one-shot assertions (`expect(await ...isVisible())`) instead of auto-retrying `expect(locator)`, structural CSS or XPath selectors, race conditions around navigation and responses.

**Isolation smells.** Shared mutable state between tests, order dependence, fixed data that collides under parallel workers, missing cleanup.

**Assertion smells.** Tests that act but never assert, assertions on implementation details rather than user-visible outcomes, swallowed errors.

**Maintainability smells.** Copy-pasted selectors that should be a page object, secrets hard-coded in the test, magic values with no meaning.

For each, point at the location and give the fix, briefly.

## Pass C: Beyond the rules

Passes A and B are conformance-checking against a shared standard. That's useful (most real defects are drift), but it will silently pass anything the standard doesn't already forbid. Pass C is the only step that steps outside the rulebook. Don't skip it.

For each acceptance criterion, feature, or notable test, force yourself to answer these deliberately, out loud, one at a time. If an answer is "nothing," write "nothing". Don't skip the question.

- **What could break in production that no rule in this skill or the author skill mentions?** A domain-specific concern, a business-logic edge, a subtle timing case, an integration nobody thought to test.
- **Which of these tests would still pass if the feature were quietly broken?** Mutation-testing instinct: if you inverted a condition or dropped a validation, would any assertion here notice?
- **If I shipped exactly what's tested and nothing more, what breaks in production?** The unwritten test is the most expensive one.
- **What's the worst input a hostile or careless user could send that no test mentions?** Not the obvious 400s, the awkward ones.
- **What happens if a step half-succeeds: request sent, response lost, database updated but UI not refreshed?** Partial-failure states are where real users lose data.
- **Where does the plan or code assume something is "fine" without proving it?** An unchecked seed status, a "should never happen" comment, a race that "hasn't come up."

Findings from Pass C are usually High severity even when they're short, because the other passes structurally can't find them. State them as concrete missing tests, not as musings. "No test covers what happens when a placed order's payment webhook arrives after the user has already logged out" beats "consider async ordering."

If Pass C produces nothing on a non-trivial suite, you probably didn't run it. Go back and answer each question by name.

## How to report findings

Report so the author can act immediately. Order by severity: a missing critical-path test or a guaranteed flake first, style nits last. Use this shape:

```
## Summary
<2-3 sentences: overall coverage state and the most important gap.>

## Coverage map
<Each requirement/criterion → covered / partially covered / NOT covered,
 with the test name or "none".>

## Findings
### 🔴 High: <short title>
- Where: <criterion name / file:line / test title>
- Problem: <what's missing or wrong>
- Why it matters: <the bug or false-confidence it allows>
- Fix: <the specific test to add or change>

### 🟡 Medium: ...
### 🟢 Low: ...

## What's done well
<Briefly. Honest reviewers acknowledge solid coverage so the signal on the
 problems stays credible.>
```

Severity guide. **High**: a real user-facing path or contract with no coverage, or a test that will flake or fail spuriously in CI. **Medium**: a meaningful edge case missing, or a weak or hollow assertion. **Low**: naming, structure, minor duplication.

## The two failure modes to avoid

**Rubber-stamping.** "All looks solid, nice work." If you produced no located findings on a non-trivial suite, you didn't review it. You skimmed it. Go back to the coverage map and the gap checklist.

**Noise.** Twenty style nitpicks that bury the one missing auth test. Severity-order exists so the important finding is read first. Prune the trivia or clearly mark it Low.

## Reference files

- `references/test-plan-rubric.md`. The full coverage and test-design checklist, with prompts for teasing out missing cases.
- `references/playwright-code-smells.md`. Playwright/TypeScript-specific smells with before/after examples. Aligned with the `playwright-test-author` skill so the two agree on what "good" looks like. It catches drift *from* that standard, not defects *in* it. That's what Pass C is for.
