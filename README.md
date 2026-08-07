# QA Playwright Skills

Two [Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) that make an AI assistant behave like a senior test-automation engineer when it's **writing** Playwright tests, and like a picky reviewer when it's **checking** them. They pair well, but each works on its own.

Both are aimed at **Playwright + TypeScript** and cover **E2E (browser) and API** testing. The advice comes from [Playwright's own best-practices docs](https://playwright.dev/docs/best-practices) plus a fair amount of real-world scar tissue.

## The two skills

### `playwright-test-author`

Writes tests that hold up. It encodes the habits that separate a suite people trust from one they mute after the third false failure:

- Web-first, auto-retrying assertions. No `waitForTimeout` sleeps.
- Role, label, and test-id locators instead of brittle CSS or XPath.
- Real test isolation, with data seeded via API and cleaned up on the way out.
- Fixtures instead of copy-pasted hooks, and page objects kept light.
- `page.route` for mocking third-party services.
- Linting for missing `await`, plus notes on config, parallelism, and CI.

### `qa-test-reviewer`

Reviews a test plan or the test code itself, ideally as a separate pass over whatever the author skill just produced. It won't rubber-stamp anything:

- Maps every requirement or acceptance criterion to a test (or names it as NOT covered).
- Runs a fixed gap checklist for boundaries, error paths, permissions, concurrency, and empty states.
- Spots Playwright flakiness, isolation, and assertion smells.
- Reports located, severity-ordered findings. Not "looks good."

## Why two skills instead of one

When an author reviews its own work, it shares the blind spots that caused the gap. A fresh reviewer with a checklist, told to break things, catches what self-review talks itself out of. The two skills share the same definition of "good," so if the reviewer finds something, that's a real signal worth acting on.

## How to use them

**Install:** copy each skill folder (`playwright-test-author/` and `qa-test-reviewer/`) into your assistant's skills directory. Each folder — its `SKILL.md` plus `references/` — is self-contained. If your setup wants a `.skill` archive instead of a folder, zip the folder (`zip -r playwright-test-author.skill playwright-test-author`) and save the archive with your assistant's "Save skill" flow.

**Write:** ask in plain language.

> "We just shipped a forgot-password flow (enter email, get reset link, set new password). Write me Playwright tests for it."

The author skill triggers on requests to write Playwright, E2E, or API tests.

**Review:** in a fresh conversation, ask something like:

> "Here's our test plan and the Playwright tests. Poke holes in them. What's missing?"

The reviewer skill triggers on requests to review, critique, or find gaps in test plans or test code.

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

MIT. See `LICENSE`.
