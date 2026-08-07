---
name: playwright-test-author
description: >-
  Write reliable, maintainable end-to-end and API tests with Playwright in
  TypeScript. Use this skill whenever the user is writing, scaffolding, or
  extending Playwright tests, `.spec.ts` files, page objects, fixtures, or API
  request tests, even if they don't say "Playwright" by name but describe
  automating browser flows, checking API responses, or building a UI/E2E test
  suite in TypeScript. Pairs with the `qa-test-reviewer` skill, which should
  review anything written here in a separate pass.
---

# Playwright Test Author (TypeScript, E2E + API)

The goal here isn't to produce tests that pass once. It's to produce tests a team will still trust in six months. Tests that fail only when the product is actually broken, and that a new engineer can read without a tour.

Flaky, over-coupled tests are worse than no tests at all. People learn to ignore red, and then a real regression sails through. Everything below exists to prevent that.

## Before writing a single test

Ask (or work out from the task) three things, because tests written without them tend to assert the wrong thing.

First, what user-visible behaviour or contract am I protecting? A test should map to something a real user or API consumer depends on. "A logged-out user who submits a valid login lands on the dashboard" is real. "The button has class `btn-primary`" is not. If the task references acceptance criteria, turn each one into at least one test, and name the test after it.

Second, what layer is cheapest to catch this at? Not everything belongs in a browser test. Reach for an API test when you're checking business logic or data, and reserve full E2E for flows that genuinely cross the whole stack. A suite that's 80% slow UI tests will be flaky and slow. See "Choosing the layer" below.

Third, what has to be true before this test runs, and what has to be cleaned up after? Every test must be able to run alone, in any order, in parallel. If a test depends on another test having run first, that's a bug waiting to happen.

## Choosing the layer

Write the test at the lowest layer that still proves the thing you care about.

An **API test** (using the `request` fixture) is right for status codes, payloads, validation rules, auth, business logic, or setting up and tearing down data for a UI test. Fast and stable. See `references/api-testing.md`.

An **E2E / browser test** (using the `page` fixture) is for a flow that genuinely crosses the UI. Forms, navigation, rendering, client-side behaviour a user would see.

The **hybrid** pattern is the most useful in practice: seed state via the API, then drive only the UI step you actually want to test through the browser. Keeps browser tests short and reliable. Example in `references/api-testing.md`.

## The reliability non-negotiables

These are the habits that kill most flakiness. They matter enough to state plainly, with the reason attached, so you can apply judgment instead of following them blindly.

**Use web-first, auto-retrying assertions.** `await expect(locator).toBeVisible()` polls until the condition is met or times out. A raw check like `expect(await locator.isVisible()).toBe(true)` samples once and races the app. Use the `expect(locator)` form for anything the UI has to catch up to.

**Never sleep for time.** `page.waitForTimeout(3000)` is the single biggest cause of both flakiness and slowness. Too short and it flakes, too long and the suite crawls, and it's the wrong tool either way. Playwright auto-waits for elements to be actionable before acting, and web-first assertions wait for state. If you think you need a sleep, you actually need to wait for a specific condition (a response, an element, a URL). `references/anti-flake.md` shows the replacement for every common case.

**Locate by what the user perceives, not by DOM structure.** In order: `getByRole`, `getByLabel`, `getByPlaceholder`, `getByText`, then `getByTestId` for things with no accessible handle. Skip CSS or XPath selectors tied to markup shape (`.container > div:nth-child(2)`). They break on cosmetic refactors and test nothing a user cares about. Role-based locators double as a light accessibility check, which is a nice side effect.

**Make every test independent and parallel-safe.** No shared mutable state between tests, no ordering assumptions. Create the data a test needs inside that test (ideally via API), and generate unique values (a unique email per run, for example) so parallel workers don't collide. Playwright isolates browser context per test by default. Don't defeat that with module-level globals.

**Don't wait on `networkidle` as a synchronisation crutch.** It's discouraged for a reason. Modern apps poll and stream, so "network is idle" may never happen, or it may happen before your data arrives. Wait for the actual thing: `await expect(row).toBeVisible()` or `await page.waitForResponse(...)`.

## Use fixtures, not raw hooks

Playwright's recommended way to give a test what it needs is a **fixture**, not a pile of `beforeEach` and `afterEach` hooks. Fixtures are built on demand (only what a test asks for is created), they compose, they work across files, and they're type-safe. Each one is isolated per test, which is the isolation property the whole suite leans on. A hook runs for every test in scope whether it needs the setup or not. A fixture runs only for the tests that request it.

Use custom fixtures to hand a test a ready page object, or a **data factory** that creates a record via the API and deletes it afterward (no `afterEach` cleanup to forget). Worker-scoped fixtures share genuinely expensive, read-mostly resources across a worker. Automatic fixtures handle cross-cutting concerns like attaching a trace on failure. Patterns and full examples live in `references/fixtures-config-and-ci.md`.

## Don't test what you don't control

Third-party sites and APIs you don't own make a suite flaky and slow, and a failure there isn't your bug anyway. Don't drive them in a test. Intercept the call with `page.route` and serve controlled data so the test exercises *your* app against a known response. Mock the error responses too (500s, timeouts, empty bodies) to prove your UI degrades gracefully. Those paths are painful to trigger against a real service and trivial to fake. Use real requests only when the integration itself is what you're testing. Example in `references/fixtures-config-and-ci.md`.

## File and naming conventions

Keep the shape predictable so any QA can navigate a suite they didn't write.

```
tests/
  e2e/            # browser flows         -> *.spec.ts
  api/            # API-level tests       -> *.spec.ts
  fixtures/       # custom test fixtures  -> auth, data factories
  pages/          # page objects (UI only)
playwright.config.ts
```

Name the spec after the feature (`login.spec.ts`), and name each test after the behaviour: `test('rejects login with an unregistered email', ...)`. A good test title reads like a sentence in a bug report. Group related tests with `test.describe('Login', ...)`.

## Structure inside a test

Follow Arrange, Act, Assert, and let it breathe visually so the intent is obvious:

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

Keep assertions about *observable* outcomes (URL, visible text, API response). Not internal implementation details.

When a single test legitimately checks several independent things about one rendered page, use **soft assertions** (`await expect.soft(locator).toBeVisible()`) so one failure doesn't hide the others. The test still fails at the end, and the report shows every problem at once. Keep using hard assertions for preconditions that make the rest of the test meaningless if they fail.

## Page Object Model, used lightly

POM keeps selectors and page actions in one place, so a UI change is a one-line fix instead of a hundred. But heavy, over-abstracted page objects turn into their own maintenance burden. Reach for a page object when a page's selectors are reused across several specs. Don't wrap a page you touch once. Keep page objects free of assertions where you can. They model the page. The test owns the expectations. Template and guidance in `references/page-objects.md`.

## Authentication

Logging in through the UI at the start of every test is slow and flaky. Log in once **per worker**, save the storage state, and reuse it — a single shared storageState across parallel workers puts every test into the same user account, which re-creates the shared-mutable-state flake this suite otherwise avoids. Pattern in `references/anti-flake.md` (the "Auth once per worker, reuse everywhere" section), or as a worker-scoped fixture in `references/fixtures-config-and-ci.md`.

## API testing essentials

Use the built-in `request` fixture and `APIRequestContext`. No extra HTTP library needed. Assert on status *and* body, cover the unhappy paths (400s, 401s, 422s alongside the 200s), and use the API to arrange and clean up data for browser tests. Full patterns, including schema-shape checks and auth headers, in `references/api-testing.md`.

## Tooling and guardrails

A few low-cost habits from Playwright's own recommendations prevent whole categories of bug.

`npx playwright codegen <url>` records a flow and emits role, text, and test-id locators. Good starting point that you then refine, rather than hand-guessing selectors.

Lint for missing `await`. A forgotten `await` on a click or `expect` is the most common Playwright bug: the promise floats and the test races, or it silently passes. Enable ESLint's `@typescript-eslint/no-floating-promises`, and run `tsc --noEmit` in CI to catch type-level mistakes. This removes the whole bug class mechanically instead of by eye.

Run across browsers in CI. Configure Chromium, Firefox, and WebKit projects so engine-specific breakage surfaces before users hit it. A single browser locally is fine.

Rely on parallelism, shard in CI. Tests run in parallel by default (safe precisely because they're isolated), and you shard large suites across machines to keep CI fast.

Config, project setup, mocking, linting, and CI details all live in `references/fixtures-config-and-ci.md`.

## Before you hand it over

A quick self-check that catches the usual regressions:

- No `waitForTimeout` or hard sleeps, and no `networkidle` used as a wait.
- Every assertion on UI state uses the auto-retrying `expect(locator)` form.
- Locators are role, label, or test-id based, not structural CSS or XPath.
- Each test creates its own data and could run alone, in any order.
- Every Playwright call is awaited (the linter should enforce this).
- Third-party services the test doesn't own are mocked, not hit for real.
- Shared setup is a fixture where it makes sense, not copy-pasted hooks.
- Negative and edge cases exist alongside the happy path.
- Test titles describe behaviour and would make sense in a failure report.

This self-check doesn't replace real review. Tests are exactly the kind of code where the author's blind spots hide, so hand the output to the `qa-test-reviewer` skill for an independent, adversarial pass. A fresh reader with a checklist catches gaps the author talks themselves out of.

## Reference files

- `references/anti-flake.md`. Every common flakiness cause and its concrete fix (waiting for responses, auth reuse, dynamic data, animations, retries).
- `references/api-testing.md`. API request patterns, hybrid seed-via-API tests, auth, and negative-path coverage.
- `references/page-objects.md`. A lightweight page object template, and when to use one.
- `references/fixtures-config-and-ci.md`. Fixtures over hooks (with data-factory and page-object examples), mocking third-party dependencies with `page.route`, config essentials, linting for missing `await`, and parallelism, sharding, and CI.
