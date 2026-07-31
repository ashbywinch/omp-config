---
description: When the user greets you, run the PA Coordination skill to start the session.
---

# Greeting Trigger

When the user says a greeting like "good morning", "good afternoon", "good evening", "hey", "hi", "hello", or any session-starting phrase:

1. Recognize this as a session trigger
2. Run `skill://pa-coordination` to start the coordinated session flow

Do not respond directly to the greeting. Delegate to the PA Coordination skill, which will handle routing, schedule checks, and session coordination.
