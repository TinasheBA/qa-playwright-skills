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

When an action triggers a request whose result you care about, wait for the response explicitly. Set up the wait *first*, then trigger the action, then await the wait. Otherwise the response can arrive before you begin listening, and you'll spend an afternoon working out why.

```ts
const orderResponse = page.waitForResponse(r =>
  r.url().includes('/api/orders') && r.status() === 201);
await page.getByRole('button', { name: 'Place order' }).click();
const response = await orderResponse;

expect(response.ok()).toBeTruthy();
await expect(page.getByText('Order confirmed')).toBeVisible();
```

You'll see the same pattern written as `Promise.all([page.waitForResponse(...), click()])` in older code and in some parts of the Playwright docs. Same guarantee, just wraps the two calls together. Both are correct; the form above is easier to read and easier to add extra assertions to between the click and the await.

## Auth once *per worker*, reuse everywhere

Logging in through the UI in every test is slow and a common flake source. Log in once and reuse the saved session, but do it **per worker**, not once for the whole suite.

Why per worker matters: if every parallel test uses the same storageState, every parallel test is acting as the same user. The moment one test mutates that user's state (deletes an order, changes a setting) while another asserts on it, you re-create the shared-mutable-state flake this skill is trying to prevent. Per-worker auth gives each parallel worker its own account, so per-test isolation actually holds under parallelism.

Do this with a **worker-scoped fixture**, not a `setup` project. This one trips people up, so it's worth being exact. A `setup` project runs its test once, on a single worker, so it can only ever write one storage-state file. Point three parallel workers at `user-${parallelIndex}.json` and workers 1 and 2 read a file that was never written. A worker-scoped fixture runs once inside *each* worker process, which is the granularity you actually want: one account, one login, one saved session per worker.

```ts
// fixtures/auth.ts
import { test as base, expect, request } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

export const test = base.extend<{}, { workerStorageState: string }>({
  // Runs once per worker. Each worker gets its own account and its own file.
  workerStorageState: [async ({ browser }, use, workerInfo) => {
    const authFile = path.resolve(`playwright/.auth/user-${workerInfo.parallelIndex}.json`);
    fs.mkdirSync(path.dirname(authFile), { recursive: true });

    // Provision a dedicated user for this worker via API, and assert the seed
    // so a failed setup doesn't later read as a login bug.
    const email = `worker_${workerInfo.parallelIndex}_${randomUUID()}@example.com`;
    const password = 'correct-horse';
    const api = await request.newContext({ baseURL: process.env.BASE_URL });
    const created = await api.post('/api/users', { data: { email, password } });
    expect(created.ok(), 'seed user must be created before we log in as them').toBeTruthy();
    await api.dispose();

    // Log in through the UI once, save the session for this worker.
    const page = await browser.newPage();
    await page.goto('/login');
    await page.getByLabel('Email').fill(email);
    await page.getByLabel('Password').fill(password);
    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(page).toHaveURL('/dashboard');
    await page.context().storageState({ path: authFile });
    await page.close();

    await use(authFile);
  }, { scope: 'worker' }],

  // Every test in the worker starts from that saved session.
  storageState: async ({ workerStorageState }, use) => {
    await use(workerStorageState);
  },
});
```

Import this `test` in your specs and each one starts already logged in, with no per-test UI login and no shared account across workers. Keep secrets in environment variables, never hard-coded, and add `playwright/.auth/` to `.gitignore`. The same fixture wired into `playwright.config.ts` is in `fixtures-config-and-ci.md`.

One footgun in the snippet above: `randomUUID` comes from `node:crypto`. It's also there as a global, `crypto.randomUUID()`, on Node 18.17+ and 20+, but importing it works on any version and won't throw a `ReferenceError` on an older CI runner.

## Dynamic / unique test data

Parallel workers collide when tests share the same fixed data. Generate unique values per test so any number of workers can run at once:

```ts
import { randomUUID } from 'node:crypto';

const email = `user_${randomUUID()}@example.com`;
```

`randomUUID()` is bulletproof against collision. Timestamps can collide when two tests in the same worker start within the same millisecond, and appending a worker index only papers over that. UUID replaces both.

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
