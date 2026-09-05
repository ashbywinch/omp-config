---
name: loft-review-surface
description: How to sign into the Loft app and view the transcription review surface. Every agent must follow this before claiming a layout change works.
---

# Loft review surface — sign in and look at it

## The rule

Never claim a layout change works without opening the app and looking at
the rendered page with the boxes drawn. Unit tests and evals are not
enough — they test data, not the rendered UI.

## Steps

1. Start the server from the current branch of the Loft repo:

   ```
   cd <loft-repo>
   . ~/.secrets
   ./loft serve --host 0.0.0.0 --port 8000
   ```

   Run it in the background. The `loft` script sources the repo's
   `.env` itself (session secret, review identity) and inherits the
   shell secrets from `~/.secrets`.

2. Create a valid session cookie with the server's own secret:
   [make_session_cookie.py](skill://loft-review-surface/examples/make_session_cookie.py).
   Source `.env` (or export the secret) BEFORE calling the serializer —
   a different secret produces an invalid cookie that the server
   silently rejects with `authenticated: false`. The reviewed identity
   comes from `LOFT_REVIEW_EMAIL` (required) and `LOFT_REVIEW_NAME`
   (optional) — keep them in the loft repo's gitignored `.env`, never
   in this repo.

3. Set the cookie in the headless browser and open the review page:
   [open_review_page.mjs](skill://loft-review-surface/examples/open_review_page.mjs).
   Use Puppeteer's `page.setCookie()` — NOT `document.cookie` (the
   harness's `run` action executes in a Node.js context, not the
   page's DOM).

4. Inspect the screenshot from `open_review_page.mjs`. Check: do the
   boxes sit on the text? Are all lines covered? Are margin
   annotations separate?

## Common mistakes (each cost the agent a full session)

- **Wrong branch**: editing files while HEAD is on a different branch
  than the one you think you're on. Always check `git branch --show-current`.
- **Wrong session secret**: creating the cookie without sourcing `.env`
  first, so the serializer uses a different key than the server. The
  server rejects the cookie with `authenticated: false` and no error.
- **Not looking at the rendered output**: reporting "33 lines all boxed"
  from the layout JSON without checking that the boxes actually sit on
  the text in the rendered app.
- **Not running the real pipeline on real data**: testing evals against
  fixtures in tmp directories proves the code works in isolation but
  tells you nothing about whether it works on the family's actual scans.
- **Delegating the visual check to the user**: the user asked YOU to
  verify. Use the tools. Do not say "the user should look at it."
