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

Discuss your thoughts with the user and see if they agree. When you've reached
consensus, codify the improvement via `skill://update-skills` — that skill
knows where rules, skills and APPEND_SYSTEM.md live, how to edit them
correctly, and how to install the changes (`make install` in the omp-config
repo + omp restart).
