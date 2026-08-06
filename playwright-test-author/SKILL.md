---
name: playwright-test-author
description: >-
  Write reliable, maintainable end-to-end and API tests with Playwright in
  TypeScript. Use this skill whenever the user is writing, scaffolding, or
  extending Playwright tests, `.spec.ts` files, page objects, fixtures, or API
  request tests — even if they don't say "Playwright" by name but describe
  automating browser flows, checking API responses, or building a UI/E2E test
  suite in TypeScript. Prefer this skill over writing tests from memory: it
  encodes the anti-flake and isolation patterns that separate a suite people
  trust from one they mute. Pairs with the `qa-test-reviewer` skill, which
  should review anything written here in a separate pass.
---

# Playwright Test Author (TypeScript, E2E + API)

The goal of this skill is not to produce tests that pass once. It is to produce
tests a team will still trust in six months — tests that fail only when the
product is actually broken, and that a new engineer can read without a tour.

Flaky, over-coupled tests are worse than no tests: people learn to ignore red,
and then a real regression sails through. Everything below exists to prevent
that outcome.

## Before writing a single test

Ask (or infer from the task) three things, because tests written without them
tend to assert the wrong thing:

1. **What user-visible behaviour or contract am I protecting?** A test should
   map to something a real user or a real API consumer depends on — "a
   logged-out user who submits a valid login lands on the dashboard", not "the
   button has class `btn-primary`". If the task references acceptance criteria,
   turn each criterion into at least one test and name the test after it.
2. **What layer is cheapest to catch this at?** Not everything belongs in a
   browser test. Prefer an API test when you're checking business logic or data;
   reserve full E2E (browser) tests for genuinely end-to-end journeys. A suite
   that is 80% slow UI tests is a suite that will be flaky and slow. See
   "Choosing the layer" below.
3. **What has to be true before this test runs, and what must it clean up?**
   Every test must be able to run alone, in any order, in parallel. If a test
   depends on another test having run first, that is a bug waiting to happen.

## Choosing the layer

Write the test at the lowest layer that still proves the thing you care about:

- **API test** (`request` fixture) — validating status codes, payloads,
  validation rules, auth, business logic, or setting up/tearing down data for a
  UI test. Fast and stable. See `references/api-testing.md`.
- **E2E / browser test** (`page` fixture) — a journey that genuinely crosses the
  UI: forms, navigation, rendering, client-side behaviour a user would see.
- **Hybrid** — the most valuable real-world pattern: seed state via the API,
  then drive only the UI step you actually want to test through the browser.
  This keeps browser tests short and reliable. Example in
  `references/api-testing.md`.

## The reliability non-negotiables

These are the handful of habits that eliminate most flakiness. They matter
enough to state plainly, with the reason attached so you can apply judgment
rather than follow them blindly.

**Use web-first, auto-retrying assertions.** `await expect(locator).toBeVisible()`
polls until the condition is met or times out. A raw check like
`expect(await locator.isVisible()).toBe(true)` samples once and races the app.
Assert on the `expect(locator)` form for anything the UI has to catch up to.

**Never sleep for time.** `page.waitForTimeout(3000)` is the single biggest
source of both flakiness and slowness — too short and it flakes, too long and
the suite crawls, and it's always the wrong tool. Playwright auto-waits for
elements to be actionable before acting, and web-first assertions wait for
state. If you think you need a sleep, you actually need to wait for a specific
condition (a response, an element, a URL). `references/anti-flake.md` shows the
replacement for every common case.

**Locate by what the user perceives, not by DOM structure.** Prefer, in order:
`getByRole`, `getByLabel`, `getByPlaceholder`, `getByText`, and `getByTestId`
for things with no accessible handle. Avoid CSS/XPath selectors tied to markup
structure (`.container > div:nth-child(2)`) — they break on cosmetic refactors
and test nothing a user cares about. Role-based locators double as a light
accessibility check.

**Make every test independent and parallel-safe.** No shared mutable state
between tests, no ordering assumptions. Create the data a test needs in that
test (ideally via API), and generate unique values (e.g. a unique email per
run) so parallel workers don't collide. Playwright isolates browser context per
test by default — don't defeat that with module-level globals.

**Don't wait on `networkidle` as a synchronisation crutch.** It's discouraged
for a reason: modern apps poll and stream, so "network is idle" may never
happen or may happen before your data arrives. Wait for the actual thing —
`await expect(row).toBeVisible()` or `await page.waitForResponse(...)`.

## Set up with fixtures, not just hooks

Playwright's recommended way to give a test what it needs is a **fixture**, not a
pile of `beforeEach`/`afterEach` hooks. Fixtures are built on demand (only what a
test asks for is created), compose with each other, are reusable across files,
and are type-safe — and each is isolated per test, which is the isolation
property the whole suite leans on. A hook runs for every test in scope whether it
needs the setup or not; a fixture runs only for the tests that request it.

Use custom fixtures to hand a test a ready page object, or a **data factory** that
creates a record via the API and deletes it automatically afterwards (no
`afterEach` cleanup to forget). Worker-scoped fixtures share genuinely expensive,
read-mostly resources across a worker; automatic fixtures handle cross-cutting
concerns like attaching a trace on failure. Patterns and full examples in
`references/fixtures-config-and-ci.md`.

## Don't test what you don't control

Third-party sites and APIs you don't own make a suite flaky and slow, and a
failure there isn't your bug. Don't drive them in a test — intercept the call
with `page.route` and serve controlled data, so the test exercises *your* app
against a known response. Mock the error responses too (500s, timeouts, empty
bodies) to prove your UI degrades gracefully — those paths are painful to trigger
against a real service and trivial to fake. Use real requests only when the
integration itself is what you're testing. Example in
`references/fixtures-config-and-ci.md`.

## File and naming conventions

Keep the shape predictable so any QA can navigate a suite they didn't write:

```
tests/
  e2e/            # browser journeys      -> *.spec.ts
  api/            # API-level tests       -> *.spec.ts
  fixtures/       # custom test fixtures  -> auth, data factories
  pages/          # page objects (UI only)
playwright.config.ts
```

Name the spec after the feature (`login.spec.ts`), and name each test after the
behaviour: `test('rejects login with an unregistered email', ...)`. A good test
title reads like a sentence in a bug report. Group related tests with
`test.describe('Login', ...)`.

## Structure inside a test

Follow Arrange–Act–Assert, and let it breathe visually so the intent is
obvious:

```ts
import { test, expect } from '@playwright/test';

test.describe('Login', () => {
  test('lands on the dashboard after a valid login', async ({ page }) => {
    // Arrange
    await page.goto('/login');

    // Act
    await page.getByLabel('Email').fill('user@example.com');
    await page.getByLabel('Password').fill('correct-horse');
    await page.getByRole('button', { name: 'Sign in' }).click();

    // Assert
    await expect(page).toHaveURL('/dashboard');
    await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
  });
});
```

Keep assertions about *observable* outcomes (URL, visible text, API response),
never internal implementation details.

When a single test legitimately checks several independent things about one
rendered page, use **soft assertions** (`await expect.soft(locator).toBeVisible()`)
so one failure doesn't hide the others — the test still fails at the end, but the
report shows every problem at once. Keep using hard assertions for preconditions
that make the rest of the test meaningless if they fail.

## Page Object Model — use it lightly

POM keeps selectors and page actions in one place so a UI change is a one-line
fix, not a hundred. But heavy, over-abstracted page objects become their own
maintenance burden. Reach for a page object when a page's selectors are reused
across several specs; don't wrap a page you touch once. Keep page objects free
of assertions where practical — they model the page; the test owns the
expectations. Template and guidance in `references/page-objects.md`.

## Authentication

Logging in through the UI at the start of every test is slow and flaky. Log in
once in a setup project, save the storage state, and reuse it. Pattern in
`references/anti-flake.md` (the "Auth once, reuse everywhere" section).

## API testing essentials

Use the built-in `request` fixture / `APIRequestContext` — no extra HTTP
library needed. Assert on status *and* body, cover the unhappy paths (400s,
401s, 422s, not just 200s), and use the API to arrange and clean up data for
browser tests. Full patterns, including schema-shape checks and auth headers,
in `references/api-testing.md`.

## Tooling and guardrails

A few low-cost habits from Playwright's own recommendations prevent whole
categories of bug:

- **Generate locators with codegen.** `npx playwright codegen <url>` records a
  flow and emits role/text/test-id locators — a good starting point that you
  then refine, rather than hand-guessing selectors.
- **Lint for missing `await`.** A forgotten `await` on a click or `expect` is
  the most common Playwright bug — the promise floats and the test races or
  silently passes. Enable ESLint's `@typescript-eslint/no-floating-promises`,
  and run `tsc --noEmit` in CI to catch type-level mistakes. This removes the
  bug class mechanically instead of by eye.
- **Run across browsers in CI.** Configure Chromium, Firefox, and WebKit
  projects so engine-specific breakage surfaces before users hit it; a single
  browser locally is fine.
- **Rely on parallelism, shard in CI.** Tests run in parallel by default (safe
  precisely because they're isolated); shard large suites across machines to
  keep CI fast.

Config, project setup, mocking, linting, and CI details all live in
`references/fixtures-config-and-ci.md`.

## Before you hand it over

A quick self-check that catches the usual regressions:

- No `waitForTimeout` / hard sleeps, and no `networkidle` used as a wait.
- Every assertion on UI state uses the auto-retrying `expect(locator)` form.
- Locators are role/label/testid based, not structural CSS/XPath.
- Each test creates its own data and could run alone, in any order.
- Every Playwright call is `await`ed — no floating promises (the linter should
  enforce this).
- Third-party services the test doesn't own are mocked, not hit for real.
- Shared setup is a fixture where it makes sense, not copy-pasted hooks.
- Negative and edge cases exist, not just the happy path.
- Test titles describe behaviour, and would make sense in a failure report.

This self-check is deliberately not a substitute for real review. Tests are
exactly the kind of code where the author's blind spots hide, so hand the output
to the `qa-test-reviewer` skill for an independent, adversarial pass — a fresh
reader with a checklist catches gaps the author rationalises away.

## Reference files

- `references/anti-flake.md` — every common flakiness cause and its concrete
  fix (waiting for responses, auth reuse, dynamic data, animations, retries).
- `references/api-testing.md` — API request patterns, hybrid seed-via-API tests,
  auth, and negative-path coverage.
- `references/page-objects.md` — a lightweight page object template and when to
  use one.
- `references/fixtures-config-and-ci.md` — fixtures over hooks (with data-factory
  and page-object examples), mocking third-party dependencies with `page.route`,
  config essentials, linting for missing `await`, and parallelism/sharding/CI.
