# Fixtures, Config, Mocking & CI

This file covers the suite-architecture pieces that keep a growing test suite
fast, isolated, and diagnosable — the parts Playwright's official best-practices
guidance emphasises but that are easy to skip when you're just making one test
pass. Read it when scaffolding a project, adding shared setup, dealing with
external services, or wiring tests into CI.

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

Playwright's fixture system is the recommended way to set up what a test needs.
Fixtures beat hooks because they're **on-demand** (only what a test asks for is
built), **composable** (a fixture can depend on another), **reusable across
files**, and **type-safe** — and they remove the need to wrap tests in a
`describe` block just to share setup. Each fixture is isolated per test by
default, which is exactly the isolation property good suites depend on.

A hook runs for every test in its scope whether that test needs the setup or
not; a fixture runs only for the tests that request it. That difference keeps
tests honest ("this test needs a logged-in todoPage") and fast.

## Custom fixtures: page objects and data factories

Extend the base `test` to provide ready-to-use objects. The pattern has three
phases: set up before `use`, hand the value to the test at `await use(...)`,
tear down after.

```ts
// fixtures/test.ts
import { test as base } from '@playwright/test';
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
    const email = `user_${Date.now()}@example.com`;
    const password = 'correct-horse';
    await request.post('/api/users', { data: { email, password } });
    await use({ email, password });          // <- test runs here
    await request.delete(`/api/users/${encodeURIComponent(email)}`);
  },
});

export { expect } from '@playwright/test';
```

Tests then import this `test` instead of the base one and just declare what they
need:

```ts
import { test, expect } from '../fixtures/test';

test('a fresh user can log in', async ({ loginPage, freshUser, page }) => {
  await loginPage.goto();
  await loginPage.login(freshUser.email, freshUser.password);
  await expect(page).toHaveURL('/dashboard');
});
```

The teardown (deleting the user) runs automatically after every test that used
the fixture — no `afterEach` bookkeeping, no leaked data.

## Worker-scoped and automatic fixtures

- **Worker-scoped** fixtures initialise once per worker process and are shared
  across the tests that worker runs — use them for genuinely expensive,
  read-mostly resources (a seeded database, a started server). Mark with
  `{ scope: 'worker' }`. Don't put per-test mutable state here.
- **Automatic** fixtures (`{ auto: true }`) run for every test without being
  requested — good for cross-cutting concerns like attaching logs or a trace on
  failure.

```ts
account: [async ({ browser }, use, workerInfo) => {
  const account = await createAccount(workerInfo.workerIndex);
  await use(account);
}, { scope: 'worker' }],
```

## Mock external / third-party dependencies

Don't test servers you don't control — third-party sites and APIs make your
suite flaky and slow, and a failure there isn't your bug. Intercept those calls
and serve controlled data with `page.route`, so your test exercises *your* app
against a known response:

```ts
await page.route('**/api/third-party/rates', async route => {
  await route.fulfill({ json: { usd: 18.2, eur: 19.9 } });
});
await page.goto('/pricing');
await expect(page.getByText('R18.20')).toBeVisible();
```

Mock the unhappy responses too (500s, timeouts, empty payloads) to prove your UI
degrades gracefully — those paths are hard to trigger against a real service but
trivial to fake here. Use real requests when the thing under test *is* your own
integration; mock when the dependency is incidental to what you're verifying.

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
  projects: [
    { name: 'setup', testMatch: /auth\.setup\.ts/ },
    { name: 'chromium', use: { ...devices['Desktop Chrome'], storageState: 'playwright/.auth/user.json' }, dependencies: ['setup'] },
    { name: 'firefox',  use: { ...devices['Desktop Firefox'], storageState: 'playwright/.auth/user.json' }, dependencies: ['setup'] },
    { name: 'webkit',   use: { ...devices['Desktop Safari'],  storageState: 'playwright/.auth/user.json' }, dependencies: ['setup'] },
  ],
});
```

With `baseURL` set, tests use relative paths (`page.goto('/login')`) and you
switch environments by changing config, never by editing tests. Testing across
Chromium, Firefox, and WebKit catches engine-specific breakage before users do —
though it's fine to run the full matrix only in CI and a single browser locally.

## Linting guardrails (catches missing `await`)

The most common Playwright bug is a forgotten `await` — the action or assertion
returns a promise that never resolves, so the test races or silently passes.
Catch it mechanically rather than by eye:

- Enable the ESLint rule **`@typescript-eslint/no-floating-promises`** — it flags
  any un-awaited promise, which in a Playwright test almost always means a
  missing `await` on a click, fill, or `expect`.
- Run **`tsc --noEmit`** in CI so type errors (wrong fixture names, bad argument
  shapes) fail the build instead of surfacing as confusing runtime errors.

These two together remove a whole category of flaky/false tests for near-zero
ongoing cost.

## Parallelism and sharding

Playwright runs test files in parallel by default; within a file you can opt in
with `test.describe.configure({ mode: 'parallel' })`. This is only safe because
tests are isolated — which is why the isolation rules elsewhere in this skill
matter. To go faster in CI, shard across machines and merge the reports:

```bash
npx playwright test --shard=1/3
```

## Running on CI

Run the suite on every push and pull request so regressions are caught at the
source. Practical guidance from Playwright's own recommendations:

- Prefer **Linux** runners for cost; developers can use any OS locally.
- Install only what you need: `npx playwright install chromium --with-deps`
  (add other browsers when the CI job actually runs them).
- Turn on `retries` and `trace: 'on-first-retry'` in CI so a first failure is
  fully diagnosable from the trace viewer, without masking persistent flakes.
- Shard large suites to keep wall-clock time down.
- Keep `@playwright/test` reasonably current (`npm install -D @playwright/test@latest`)
  to stay on supported browser builds.
