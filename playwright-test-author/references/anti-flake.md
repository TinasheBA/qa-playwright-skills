# Anti-Flake Patterns

Flakiness almost always comes from a test racing the application: the test acts
or asserts before the app has reached the state it expects. The fix is never a
longer sleep — it's waiting for the *specific* condition. Below is the
replacement for each common case.

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

// ✅ Wait for the actual outcome — auto-retries until it appears or times out
await page.getByRole('button', { name: 'Save' }).click();
await expect(page.getByText('Saved')).toBeVisible();
```

Playwright auto-waits for an element to be attached, visible, stable, and
enabled before acting on it, and web-first assertions poll until the condition
holds. Between those two mechanisms, an explicit sleep is redundant at best and
a race at worst.

## Wait for a network response, not for time

When an action triggers a request whose result you care about, wait for the
response explicitly:

```ts
const [response] = await Promise.all([
  page.waitForResponse(r => r.url().includes('/api/orders') && r.status() === 201),
  page.getByRole('button', { name: 'Place order' }).click(),
]);
expect(response.ok()).toBeTruthy();
await expect(page.getByText('Order confirmed')).toBeVisible();
```

Start the wait *before* the click (that's why `Promise.all` wraps both), or the
response can arrive before you begin listening.

## Auth once, reuse everywhere

Logging in through the UI in every test is slow and a common flake source. Do it
once in a setup project and reuse the saved session.

```ts
// auth.setup.ts
import { test as setup, expect } from '@playwright/test';

const authFile = 'playwright/.auth/user.json';

setup('authenticate', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill(process.env.TEST_USER!);
  await page.getByLabel('Password').fill(process.env.TEST_PASS!);
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
    use: { ...devices['Desktop Chrome'], storageState: 'playwright/.auth/user.json' },
    dependencies: ['setup'],
  },
]
```

Keep secrets in environment variables, never hard-coded. Add
`playwright/.auth/` to `.gitignore`.

## Dynamic / unique test data

Parallel workers collide when tests reuse the same fixed data. Generate unique
values per test so any number of workers can run at once:

```ts
const email = `user_${Date.now()}_${test.info().workerIndex}@example.com`;
```

Prefer creating the data through the API (fast, reliable) and deleting it
afterwards so runs don't accumulate state. If a test creates a record, it should
be responsible for removing it.

## Animations and transitions

An element mid-animation can be "visible" but not yet clickable at its final
position. Playwright waits for stability, but you can also disable animations
for determinism:

```ts
await page.addStyleTag({ content: `*, *::before, *::after {
  animation-duration: 0s !important;
  transition-duration: 0s !important;
}` });
```

For visual snapshots, Playwright's `toHaveScreenshot()` already freezes CSS
animations.

## Retries and traces (config)

Retries paper over some flakiness in CI, but they are a safety net, not a fix —
a test that only passes on retry is telling you something. Turn on traces so you
can actually diagnose the first failure:

```ts
// playwright.config.ts (excerpt)
retries: process.env.CI ? 2 : 0,
use: {
  trace: 'on-first-retry',
  screenshot: 'only-on-failure',
  video: 'retain-on-failure',
},
```

If a test needs retries to pass locally, treat that as a bug to investigate, not
a setting to raise.

## Strict locators and the "resolved to N elements" error

Playwright locators are strict: if a locator matches more than one element, the
action throws instead of silently picking the first. That's a feature — it
surfaces ambiguous selectors early. Fix it by narrowing (scope to a container,
add an accessible name, or use `getByRole(..., { name })`), not by adding
`.first()` reflexively, which hides the ambiguity and can mask a real duplicate
in the UI.
