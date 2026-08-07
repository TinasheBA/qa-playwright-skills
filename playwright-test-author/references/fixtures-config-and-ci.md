# Fixtures, Config, Mocking & CI

This file covers the suite-architecture pieces that keep a growing test suite fast, isolated, and diagnosable. The parts Playwright's official best-practices guidance emphasises, but that are easy to skip when you're just trying to make one test pass. Read it when scaffolding a project, adding shared setup, dealing with external services, or wiring tests into CI.

## Table of contents

- Prefer fixtures over `beforeEach`/`afterEach`
- Custom fixtures: page objects and data factories
- Worker-scoped and automatic fixtures
- Mock external / third-party dependencies
- Config essentials
- Linting guardrails (catches missing `await`)
- Parallelism and sharding
- Running on CI

## Prefer fixtures over `beforeEach`/`afterEach`

Playwright's fixture system is the recommended way to set up what a test needs. Fixtures beat hooks because they're built on demand (only what a test asks for gets created), they compose (a fixture can depend on another), they work across files, and they're type-safe. They also let you drop the `describe` block you were only using to share setup. Each fixture is isolated per test by default, which is the isolation property good suites depend on.

A hook runs for every test in its scope whether that test needs the setup or not. A fixture runs only for the tests that request it. That difference keeps tests honest ("this test needs a logged-in todoPage") and fast.

## Custom fixtures: page objects and data factories

Extend the base `test` to provide ready-to-use objects. The pattern has three phases: set up before `use`, hand the value to the test at `await use(...)`, tear down after.

```ts
// fixtures/test.ts
import { test as base, expect } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import { LoginPage } from '../pages/login-page';

type Fixtures = {
  loginPage: LoginPage;
  freshUser: { email: string; password: string };
};

export const test = base.extend<Fixtures>({
  loginPage: async ({ page }, use) => {
    await use(new LoginPage(page));
  },

  // A data factory that creates a user via API and cleans it up afterwards.
  freshUser: async ({ request }, use) => {
    const email = `user_${randomUUID()}@example.com`;
    const password = 'correct-horse';
    const created = await request.post('/api/users', { data: { email, password } });
    // Seed must succeed before the test runs. Otherwise failures downstream
    // look like product bugs when they're really "the user was never created".
    expect(created.ok(), `seed user create failed: ${created.status()}`).toBeTruthy();
    await use({ email, password });          // <- test runs here
    await request.delete(`/api/users/${encodeURIComponent(email)}`);
  },
});

export { expect } from '@playwright/test';
```

Tests then import this `test` instead of the base one, and declare what they need:

```ts
import { test, expect } from '../fixtures/test';

test('a fresh user can log in', async ({ loginPage, freshUser, page }) => {
  await loginPage.goto();
  await loginPage.login(freshUser.email, freshUser.password);
  await expect(page).toHaveURL('/dashboard');
});
```

The teardown (deleting the user) runs automatically after every test that used the fixture. No `afterEach` bookkeeping, no leaked data.

## Worker-scoped and automatic fixtures

Worker-scoped fixtures initialise once per worker process and are shared across the tests that worker runs. Mark with `{ scope: 'worker' }`, and don't put per-test mutable state there.

The highest-value use for worker scope is **per-worker auth**. If every parallel test reuses one shared storageState, every parallel test is acting as the same user. One test mutating that user's state while another asserts on it is exactly the shared-mutable-state flake the isolation rules are meant to prevent. Give each worker its own account instead. This is the same fixture shown in `anti-flake.md` under "Auth once per worker, reuse everywhere", with the config wiring alongside it:

```ts
// fixtures/auth.ts
import { test as base, expect, request } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

export const test = base.extend<{}, { workerStorageState: string }>({
  // Runs once per worker: provision an account, log in, save the session.
  workerStorageState: [async ({ browser }, use, workerInfo) => {
    const authFile = path.resolve(`playwright/.auth/user-${workerInfo.parallelIndex}.json`);
    fs.mkdirSync(path.dirname(authFile), { recursive: true });

    const email = `worker_${workerInfo.parallelIndex}_${randomUUID()}@example.com`;
    const password = 'correct-horse';
    const api = await request.newContext({ baseURL: process.env.BASE_URL });
    const created = await api.post('/api/users', { data: { email, password } });
    expect(created.ok(), `worker seed failed: ${created.status()}`).toBeTruthy();
    await api.dispose();

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

  // Override the built-in storageState so every test in the worker reuses it.
  storageState: async ({ workerStorageState }, use) => {
    await use(workerStorageState);
  },
});
```

Because the fixture overrides the built-in `storageState`, tests that import this `test` start logged in with no extra wiring. Don't try to do this with a `setup` project: that project's test runs once, on one worker, so it writes a single storage-state file, and the other workers read a file that never got created. The fixture runs once per worker, which is the only place that per-worker granularity exists. A `setup` project is the right tool for a *single shared* account across the whole suite, not for one account per worker.

Automatic fixtures (`{ auto: true }`) run for every test without being requested. Good for cross-cutting concerns like attaching logs or a trace on failure.

## Mock external / third-party dependencies

Don't test servers you don't control. Third-party sites and APIs make your suite flaky and slow, and a failure there isn't your bug anyway. Intercept those calls and serve controlled data with `page.route`, so your test exercises *your* app against a known response:

```ts
await page.route('**/api/third-party/rates', async route => {
  await route.fulfill({ json: { usd: 18.2, eur: 19.9 } });
});
await page.goto('/pricing');
await expect(page.getByText('R18.20')).toBeVisible();
```

Mock the unhappy responses too (500s, timeouts, empty payloads) to prove your UI degrades gracefully. Those paths are hard to trigger against a real service but trivial to fake here. Use real requests when the thing under test *is* your own integration. Mock when the dependency is incidental to what you're verifying.

## Config essentials

Centralise anything environment-specific so tests never hard-code it:

```ts
// playwright.config.ts (excerpt)
export default defineConfig({
  use: {
    baseURL: process.env.BASE_URL ?? 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [['html'], ['github']] : 'list',
  // Per-worker auth is handled by the worker-scoped fixture above: specs import
  // that extended `test`, which overrides storageState, so there's no `setup`
  // project and no per-project storageState here.
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],
});
```

With `baseURL` set, tests use relative paths (`page.goto('/login')`) and you switch environments by changing config, never by editing tests. Testing across Chromium, Firefox, and WebKit catches engine-specific breakage before users do. Fine to run the full matrix only in CI and a single browser locally.

## Linting guardrails (catches missing `await`)

The most common Playwright bug is a forgotten `await`. The action or assertion returns a promise that never resolves, so the test races or silently passes. Catch it mechanically instead of by eye:

- Enable the ESLint rule `@typescript-eslint/no-floating-promises`. It flags any un-awaited promise, which in a Playwright test almost always means a missing `await` on a click, fill, or `expect`.
- Run `tsc --noEmit` in CI so type errors (wrong fixture names, bad argument shapes) fail the build instead of surfacing as confusing runtime errors.

These two together remove a whole category of flaky and false tests for near-zero ongoing cost.

## Parallelism and sharding

Playwright runs test files in parallel by default. Within a file you can opt in with `test.describe.configure({ mode: 'parallel' })`. That's only safe because tests are isolated, which is why the isolation rules elsewhere in this skill matter. To go faster in CI, shard across machines and merge the reports:

```bash
npx playwright test --shard=1/3
```

## Running on CI

Run the suite on every push and pull request so regressions are caught at the source. Practical guidance from Playwright's own recommendations:

- Prefer Linux runners for cost. Developers can use any OS locally.
- Install only what you need: `npx playwright install chromium --with-deps` (add other browsers when the CI job actually runs them).
- Turn on `retries` and `trace: 'on-first-retry'` in CI so a first failure is fully diagnosable from the trace viewer, without masking persistent flakes.
- Shard large suites to keep wall-clock time down.
- Keep `@playwright/test` reasonably current (`npm install -D @playwright/test@latest`) to stay on supported browser builds.
