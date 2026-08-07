# API Testing with Playwright

Playwright ships an HTTP client (`APIRequestContext`, exposed as the `request` fixture), so API tests need no extra library. Use it for two jobs: testing APIs directly, and setting up or tearing down state for UI tests much faster than clicking through the app.

## Table of contents

- A basic API test
- Assert status AND body
- Cover the unhappy paths
- Auth headers and a reusable context
- Hybrid: seed via API, verify via UI
- Cleanup

## A basic API test

```ts
import { test, expect } from '@playwright/test';

test('GET /users/:id returns the user', async ({ request }) => {
  const res = await request.get('/api/users/42');
  expect(res.status()).toBe(200);

  const body = await res.json();
  expect(body).toMatchObject({ id: 42, email: expect.any(String) });
});
```

Set `use: { baseURL: '...' }` in the config so tests use relative paths and you switch environments by config, not by editing tests.

## Assert status AND body

A 200 with the wrong payload is still a bug. Check both the status and the shape of the response. `toMatchObject` with `expect.any(...)` verifies structure without pinning volatile values like timestamps or generated IDs:

```ts
expect(body).toMatchObject({
  id: expect.any(Number),
  status: 'active',
  createdAt: expect.any(String),
});
```

For stronger contract checks, validate against a schema (e.g. with `zod` or `ajv`). Keep it about the contract, not incidental data.

## Cover the unhappy paths

The happy path is the easy half. Most real defects hide in the error paths, so assert them deliberately:

```ts
test('POST /users rejects a duplicate email', async ({ request }) => {
  const res = await request.post('/api/users', {
    data: { email: 'taken@example.com', password: 'x' },
  });
  expect(res.status()).toBe(409);
  expect(await res.json()).toMatchObject({ error: expect.stringContaining('exists') });
});

test('POST /users validates required fields', async ({ request }) => {
  const res = await request.post('/api/users', { data: {} });
  expect(res.status()).toBe(422);
});

test('GET /admin requires auth', async ({ request }) => {
  const res = await request.get('/api/admin', { headers: {} });
  expect(res.status()).toBe(401);
});
```

## Auth headers and a reusable context

For token auth, build a request context with default headers once:

```ts
import { test as base } from '@playwright/test';

export const test = base.extend<{ api: import('@playwright/test').APIRequestContext }>({
  api: async ({ playwright }, use) => {
    const api = await playwright.request.newContext({
      baseURL: process.env.API_URL,
      extraHTTPHeaders: { Authorization: `Bearer ${process.env.API_TOKEN}` },
    });
    await use(api);
    await api.dispose();
  },
});
```

Keep tokens in environment variables, never in the test source.

## Hybrid: seed via API, verify via UI

This is the highest-value pattern in a real suite. Creating state through the UI is slow and flaky. Creating it through the API is fast and reliable. Do the setup via API and let the browser test cover only the step you actually care about:

```ts
test('a placed order appears in the order history UI', async ({ page, request }) => {
  // Arrange via API, not by clicking through checkout
  const res = await request.post('/api/orders', {
    data: { sku: 'ABC-1', qty: 2 },
  });
  // Seed must succeed before the UI assertion is meaningful. A failed
  // seed otherwise masquerades as a UI bug.
  expect(res.ok(), `order seed failed: ${res.status()}`).toBeTruthy();
  const { id } = await res.json();

  // Act + Assert. Only the UI behaviour under test.
  await page.goto('/account/orders');
  await expect(page.getByRole('row', { name: new RegExp(id) })).toBeVisible();
});
```

## Cleanup

State that leaks between runs is a slow-building flake. If a test creates a record, delete it afterward so the environment stays clean and repeatable:

```ts
test.afterEach(async ({ request }) => {
  if (createdId) await request.delete(`/api/orders/${createdId}`);
});
```

Per-test cleanup beats a big teardown, because a failure in one test won't strand data for the others.
