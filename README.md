# QA Playwright Skills

Two paired [Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)
that make an AI assistant behave like a senior test-automation engineer when
**writing** Playwright tests, and like a ruthless reviewer when **checking**
them. They are designed to be used together but work independently.

Both target **Playwright + TypeScript** and cover **E2E (browser) and API**
testing. The guidance is distilled from
[Playwright's official best practices](https://playwright.dev/docs/best-practices).

## The two skills

### `playwright-test-author`
Writes reliable, maintainable tests. It encodes the habits that separate a suite
people trust from one they mute:

- Web-first, auto-retrying assertions — never `waitForTimeout` sleeps.
- Role/label/test-id locators, not brittle CSS/XPath.
- Real test isolation; data seeded via API and cleaned up automatically.
- Fixtures over copy-pasted hooks; page objects kept lightweight.
- Mocking third-party dependencies with `page.route`.
- Linting for missing `await`, plus config/parallelism/CI guidance.

### `qa-test-reviewer`
Adversarially reviews a test plan **or** test code — ideally as a separate pass
over whatever the author skill just produced. It refuses to rubber-stamp:

- Maps every requirement/acceptance criterion to a test (or flags it NOT covered).
- Runs a fixed gap checklist (boundaries, error paths, permissions, concurrency,
  empty states).
- Detects Playwright flakiness/isolation/assertion code smells.
- Reports specific, located, severity-ordered findings — not "looks good".

## Why two skills instead of one

An author reviewing its own work shares the blind spots that produced the gap.
Running the reviewer as a fresh, separate pass — checklist in hand, told to break
things — catches what self-review rationalises away. The two skills share a
definition of "good," so tests the author writes should survive the reviewer,
and any disagreement is a real signal.

## How to use them

**Install:** drop each skill folder into your assistant's skills directory (for
Claude, the `.skill` files can be saved directly via the **Save skill** button;
or copy the folders into your skills path). Each folder — its `SKILL.md` plus its
`references/` — is a self-contained skill.

**Write:** ask in plain language, e.g.
> "We just shipped a forgot-password flow (enter email → reset link → set new
> password). Write me Playwright tests for it."

The author skill triggers on requests to write Playwright/E2E/API tests.

**Review:** in a fresh conversation, ask
> "Here's our test plan and the Playwright tests. Poke holes in them — what's
> missing?"

The reviewer skill triggers on requests to review/critique/find gaps in test
plans or test code.

## Repository layout

```
playwright-test-author/
  SKILL.md
  references/
    anti-flake.md
    api-testing.md
    page-objects.md
    fixtures-config-and-ci.md
qa-test-reviewer/
  SKILL.md
  references/
    test-plan-rubric.md
    playwright-code-smells.md
```

## License

MIT — see `LICENSE`.
