---
name: learn-from-this-session
description: Reflect on the session — what went wrong, what could be better, and codify improvements
---

# Learn From This Session

Take a moment to reflect on what happened in this session.

1. **What went wrong?** — What mistake, bad pattern, or incorrect suggestion did you make that the user corrected?
2. **What could have been better?** — Were there better or more effective ways you could have achieved the user's aims?
3. **What should change?** — Would updating an agent prompt, rule, or skill prevent this next time?

**Translate lessons into generic principles.** Strip out codebase-specific details (file names, module names, project jargon). A lesson about "rename `_KNOWN_COUNTIES` → `KNOWN_COUNTIES`" should become "renaming a private constant is cosmetic, prefer structural extractions." A lesson about "enricher.py is 1650 lines" should become "long files are a signal to extract modules."

Discuss your thoughts with the user and see if they agree. When you've reached consensus:

Create or update the relevant rule, SKILL.md, or APPEND_SYSTEM.md to codify the improvement.

## Strip project specifics from everything you update

Before you finish any codification — a skill, a rule, an APPEND_SYSTEM — audit
it for project-specific content and remove it: residue makes a skill
unusable in another domain. Run this checklist:

- **Named incidents and examples** — "when the old building failed to
  geocode under its former name…", "the invented heirloom object…" —
  become generic lessons ("a claimed precision that was never checked",
  "an artifact no source attests").
- **File and doc names** — the flow's spec file, the integrity-eval test
  file — are stripped; the *pattern* (the flow spec, the eval) stays.
- **Domain principles and standards** — "material must be authentic",
  "a link asserts something" — are the project's, not the skill's; where
  they belong is `skill://process-interview` step 6 (link, don't
  restate).
- **Eval categories and rule names** — a project's specific eval set or
  its named rules (A, B, C…) are its own; the generic pattern is "each
  rule gets a guard over the real data".
- **The test: would a reader in an unrelated domain follow this?** If the
  skill only makes sense to someone who knows the project it came from, it
  is not a skill yet.

The skill holds the method; the standards hold the domain.

**Process-design lessons are codified in `skill://process-interview`** —
added to its accumulated methodology, not written as a one-off in a
project doc. When the session's lesson is about how a *process* was
specified — the flow rules, the interview discipline, the integrity
guards — it belongs there: the skill is the methodology for
requirements-by-doing.
