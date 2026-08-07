# Anti-Flake Patterns

Flakiness almost always comes from one thing: the test racing the application. It acts or asserts before the app has caught up. The fix is never a longer sleep. It's waiting for the *specific* condition. Below is the replacement for each common case.

## Table of contents

- Replace every sleep
- Wait for a network response, not for time
- Auth once, reuse everywhere
- Dynamic / unique test data
- Animations and transitions
- Retries and traces (config)
- Strict locators and the "resolved to N elements" error

## Replace every sleep

`page.waitForTimeout(...)` is never the right answer in committed test code.

```ts
// ❌ Flaky and slow
await page.getByRole('button', { name: 'Save' }).click();
await page.waitForTimeout(2000);
await expect(page.getByText('Saved')).toBeVisible();

// ✅ Wait for the actual outcome. Auto-retries until it appears or times out.
await page.getByRole('button', { name: 'Save' }).click();
await expect(page.getByText('Saved')).toBeVisible();
```

Playwright auto-waits for an element to be attached, visible, stable, and enabled before acting on it, and web-first assertions poll until the condition holds. Between those two, an explicit sleep is redundant at best and a race at worst.

## Wait for a network response, not for time

When an action triggers a request whose result you care about, wait for the response explicitly. Set up the wait *first*, then trigger the action, then await the wait — otherwise the response can arrive before you begin listening, and you'll spend an afternoon working out why.

```ts
const orderResponse = page.waitForResponse(r =>
  r.url().includes('/api/orders') && r.status() === 201);
await page.getByRole('button', { name: 'Place order' }).click();
const response = await orderResponse;

expect(response.ok()).toBeTruthy();
await expect(page.getByText('Order confirmed')).toBeVisible();
```

You'll see the same pattern written as `Promise.all([page.waitForResponse(...), click()])` in older code and in some parts of the Playwright docs — same guarantee, just wraps the two calls together. Both are correct; the form above is easier to read and easier to add extra assertions to between the click and the await.

## Auth once *per worker*, reuse everywhere

Logging in through the UI in every test is slow and a common flake source. Do it once in a setup project and reuse the saved session — but do it **per worker**, not once for the whole suite.

Why per worker matters: if every parallel test uses the same storageState, every parallel test is acting as the same user. The moment one test mutates that user's state (deletes an order, changes a setting) while another asserts on it, you re-create the shared-mutable-state flake this skill is trying to prevent. Per-worker auth gives each parallel worker its own account, so per-test isolation actually holds under parallelism.

```ts
// auth.setup.ts
import { test as setup, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

setup('authenticate per worker', async ({ page, request }, testInfo) => {
  const workerIndex = testInfo.parallelIndex;
  const authFile = path.resolve(`playwright/.auth/user-${workerIndex}.json`);
  fs.mkdirSync(path.dirname(authFile), { recursive: true });

  // Provision a dedicated user for this worker via API. Assert the seed.
  const email = `worker_${workerIndex}_${crypto.randomUUID()}@example.com`;
  const password = 'correct-horse';
  const created = await request.post('/api/users', { data: { email, password } });
  expect(created.ok(), 'seed user must be created before we log in as them').toBeTruthy();

  await page.goto('/login');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).toHaveURL('/dashboard');
  await page.context().storageState({ path: authFile });
});
```

```ts
// playwright.config.ts (excerpt)
projects: [
  { name: 'setup', testMatch: /auth\.setup\.ts/ },
  {
    name: 'e2e',
    use: {
      ...devices['Desktop Chrome'],
      // Function form: resolved per worker at test start.
      storageState: ({}, use) =>
        use(`playwright/.auth/user-${test.info().parallelIndex}.json`),
    },
    dependencies: ['setup'],
  },
]
```

Keep secrets in environment variables, never hard-coded. Add `playwright/.auth/` to `.gitignore`. If seeding a fresh user per worker is expensive against your environment, promote the setup into a `worker`-scoped fixture instead (pattern in `fixtures-config-and-ci.md`) so the account is provisioned once per worker process rather than once per suite run.

## Dynamic / unique test data

Parallel workers collide when tests share the same fixed data. Generate unique values per test so any number of workers can run at once:

```ts
const email = `user_${crypto.randomUUID()}@example.com`;
```

`crypto.randomUUID()` is bulletproof against collision — timestamps can collide when two tests in the same worker start within the same millisecond, and appending a worker index only papers over that. UUID replaces both.

Create the data through the API where you can (fast, reliable) and delete it afterward so runs don't accumulate state. If a test creates a record, it should be responsible for removing it.

## Animations and transitions

An element mid-animation can be "visible" without being clickable at its final position. Playwright waits for stability, but you can also disable animations for determinism:

```ts
await page.addStyleTag({ content: `*, *::before, *::after {
  animation-duration: 0s !important;
  transition-duration: 0s !important;
}` });
```

For visual snapshots, Playwright's `toHaveScreenshot()` already freezes CSS animations.

## Retries and traces (config)

Retries paper over some flakiness in CI, but they're a safety net, not a fix. A test that only passes on retry is telling you something. Turn on traces so you can actually diagnose the first failure:

```ts
// playwright.config.ts (excerpt)
retries: process.env.CI ? 2 : 0,
use: {
  trace: 'on-first-retry',
  screenshot: 'only-on-failure',
  video: 'retain-on-failure',
},
```

If a test needs retries to pass locally, treat that as a bug to investigate, not a setting to raise.

## Strict locators and the "resolved to N elements" error

Playwright locators are strict: if one matches more than one element, the action throws instead of silently picking the first. That's the feature. It surfaces ambiguous selectors early. Fix it by narrowing (scope to a container, add an accessible name, or use `getByRole(..., { name })`), not by adding `.first()` reflexively. `.first()` hides the ambiguity and can mask a real duplicate in the UI.
