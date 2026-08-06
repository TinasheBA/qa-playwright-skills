# Playwright / TypeScript Code Smells

Concrete, locatable smells to look for when reviewing Playwright test code, each
with the fix. These mirror the `playwright-test-author` skill, so a suite that
follows the author skill should pass this review, and vice versa. For each smell
you find, cite the location and give the one-line fix.

## Flakiness smells (usually High severity — they fail spuriously in CI)

**Hard sleeps.** Any `page.waitForTimeout(...)` in committed test code.

```ts
// ❌ smell
await page.click('text=Save');
await page.waitForTimeout(2000);
// ✅ fix
await page.getByRole('button', { name: 'Save' }).click();
await expect(page.getByText('Saved')).toBeVisible();
```

**`networkidle` as a wait.** `waitForLoadState('networkidle')` used to
synchronise — unreliable on apps that poll or stream. Fix: wait for the specific
element or response the test needs.

**One-shot assertions instead of auto-retrying ones.** The single biggest
correctness-of-test smell.

```ts
// ❌ samples once, races the app
expect(await page.getByText('Saved').isVisible()).toBe(true);
// ✅ polls until true or times out
await expect(page.getByText('Saved')).toBeVisible();
```

**Structural selectors.** CSS/XPath tied to DOM shape
(`.card > div:nth-child(3)`, `//div[2]/span`). Brittle and meaningless to a
user. Fix: `getByRole` / `getByLabel` / `getByText` / `getByTestId`.

**Race around navigation or responses.** A click that triggers a request,
followed by an assertion that assumes the response already landed. Fix: wrap the
trigger and `page.waitForResponse(...)` in `Promise.all`, starting the wait
before the action.

**Reflexive `.first()` / `.nth(0)`** to dodge a strict-mode "resolved to N
elements" error. It hides ambiguity and can mask a duplicate in the UI. Fix:
narrow the locator (scope, accessible name) so it matches exactly one.

**Missing `await` / floating promise.** A click, fill, or `expect` whose promise
isn't awaited — the action races the rest of the test or the assertion never
actually runs, so a broken feature can pass green. Often invisible on read, which
is why it's dangerous.

```ts
// ❌ smell — assertion never awaited, always "passes"
expect(page.getByText('Saved')).toBeVisible();
// ✅ fix
await expect(page.getByText('Saved')).toBeVisible();
```

Flag it wherever you see it, and recommend the ESLint rule
`@typescript-eslint/no-floating-promises` so it can't recur.

**Driving real third-party services.** A test that hits an external site/API the
team doesn't control — a source of flakiness and failures that aren't the app's
bug. Fix: intercept with `page.route` and serve controlled data (including the
error responses). Use real calls only when the integration itself is under test.

## Isolation smells (High/Medium — flaky under parallelism)

- **Shared mutable state** across tests: module-level variables mutated in one
  test and read in another; ordering assumptions (`test('step 2'...)` depending
  on `step 1`).
- **Fixed data that collides** when workers run in parallel (same email/username
  every run). Fix: generate unique values per test/worker.
- **No cleanup** of created records — state leaks between runs and eventually
  causes intermittent failures. Fix: delete in `afterEach`, ideally via API.
- **UI login in every test** instead of reusing saved storage state — slow and a
  common flake source.

## Assertion smells (Medium — false confidence)

- **Acts but never asserts** — a test that clicks through a flow and ends without
  an `expect`. It only proves nothing threw.
- **Asserts implementation details** — a CSS class, a data attribute, internal
  state — instead of what the user or API consumer observes.
- **Swallowed failures** — `try/catch` around an assertion, or `.catch(() => {})`
  that hides a real error.
- **Soft assertions left unchecked** — `expect.soft` used without ever failing
  the test on the accumulated errors.

## Maintainability smells (Low/Medium)

- **Copy-pasted selectors** across specs that should live in a page object.
- **Hard-coded secrets / URLs / tokens** in the test source instead of env vars
  or config `baseURL`.
- **Magic values** with no explanation (`waitFor(4173)`, `expect(count).toBe(7)`
  with no context).
- **Over-built page objects** — deep inheritance, assertions buried inside,
  a method per micro-action. Note it; heavy abstraction is its own maintenance
  cost.
- **Copy-pasted `beforeEach` setup** that would be cleaner and more reusable as a
  Playwright fixture — especially data setup/teardown repeated across files.
  Suggest a fixture; keep it a Low unless the duplication is causing real drift.

## Config-level checks

- `retries` masking real flakiness (a test that only passes on retry is a bug,
  not a setting).
- No `trace` / `screenshot` / `video` on failure, so CI failures can't be
  diagnosed.
- No `baseURL`, forcing absolute URLs and environment edits inside tests.
