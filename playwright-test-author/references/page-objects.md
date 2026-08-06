# Page Objects — Lightweight

A page object puts a page's locators and actions in one place, so when the UI
changes you fix it once instead of in every spec. That's the whole value. The
failure mode is over-engineering: deep inheritance, a method for every
conceivable action, assertions buried inside the object. Keep it thin.

## When to create one

Create a page object when the same page's selectors are used across several
specs. Don't wrap a page you touch in a single test — the indirection costs more
than it saves.

## Template

```ts
import { type Page, type Locator, expect } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly email: Locator;
  readonly password: Locator;
  readonly submit: Locator;

  constructor(page: Page) {
    this.page = page;
    this.email = page.getByLabel('Email');
    this.password = page.getByLabel('Password');
    this.submit = page.getByRole('button', { name: 'Sign in' });
  }

  async goto() {
    await this.page.goto('/login');
  }

  async login(email: string, password: string) {
    await this.email.fill(email);
    await this.password.fill(password);
    await this.submit.click();
  }
}
```

Usage keeps the test readable and the intent obvious:

```ts
test('valid login reaches the dashboard', async ({ page }) => {
  const login = new LoginPage(page);
  await login.goto();
  await login.login('user@example.com', 'correct-horse');
  await expect(page).toHaveURL('/dashboard');
});
```

## Guidelines

- **Expose locators as readonly fields**, defined once in the constructor, so
  they're reused and easy to update.
- **Model actions, not assertions.** Let the test own `expect(...)` so the same
  page object serves both positive and negative tests. A small number of
  assertion helpers (e.g. `expectError(message)`) is fine when a check is
  genuinely repeated; just don't turn the page object into a test.
- **No sleeps inside page objects** — the same anti-flake rules apply. Actions
  rely on auto-waiting; callers assert with web-first expectations.
- **Prefer composition over inheritance.** A shared `BaseComponent` for a nav
  bar reused across pages is fine; a tall class hierarchy is a smell.
