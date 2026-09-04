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
   source .env
   ./.loft serve --host 0.0.0.0 --port 8000
   ```

   (Run in background. The `./loft` script loads the `.env` file and
   creates the session secret.)

2. Create a valid session cookie using the server's own secret.
   The secret is `THE_LOFT_SESSION_SECRET` from the `.env` file.
   You MUST source `.env` (or export the secret) BEFORE calling
   the serializer — a different secret produces an invalid cookie
   that the server silently rejects with `authenticated: false`.

   ```python
   # in .venv/bin/python (NOT .venv-htr — the main venv has the deps)
   import os, sys
   sys.path.insert(0, ".")
   # source .env first, or export the secret before calling this
   from tools.auth import _serializer
   cookie = _serializer().dumps({
       "email": "emily.winch@gmail.com",
       "name": "Emily Winch",
       "picture": "",
   })
   ```

3. Set the cookie in the headless browser using Puppeteer's
   `page.setCookie()` — NOT `document.cookie` (the headless browser's
   `run` action executes in a Node.js context, not the page's DOM).

   ```
   await page.setCookie({name: "session", value: <cookie>, domain: "localhost", path: "/"})
   await page.goto("http://localhost:8000/#/review/<batch_id>/<doc_index>/<page_index>", {waitUntil: "networkidle2"})
   ```

   The URL format: `#/review/<batch_id>/<doc_index>/<page_index>`
   (all 0-indexed). For example, page-01 of the first document in
   batch `adopt-20260813-201004`:
   `#/review/adopt-20260813-201004/0/0`

4. Take a screenshot with `page.screenshot({path: ...})` and inspect
   it. Check: do the boxes sit on the text? Are all lines covered?
   Are margin annotations separate?

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
