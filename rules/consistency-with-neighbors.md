---
description: Before extending a module, read how existing functions handle auth, error handling, caching, and logging — then match those patterns.
---

# Consistency With Neighbors

When adding a function to an existing file, the file's existing code IS the style guide.

## Before writing, read

- **Auth**: Do sibling functions pass tokens, API keys, or other credentials? If one does, yours should too.
- **Error handling**: Do they raise, return None, return Attempt.impossible, or swallow exceptions?
- **Caching**: Is there a cache layer? What key do they use? Do they go through `get_cached`/`set_cached`?
- **Logging**: What level (info/warning/error) for what conditions?
- **DI pattern**: Do they call `get_services()` or accept dependencies directly?
- **Return type**: Do they return raw values, `Attempt[T]`, or something else?

## When in doubt, match the majority

If four functions in a file pass `Authorization` headers and one doesn't, yours passes the header. The outlier is either wrong or has a specific reason — investigate before following it.

## Why

A function that deviates from its file's conventions is:
- Harder to review — every inconsistency is a question
- More likely to be wrong — the convention exists because the API/service requires it
- A maintenance trap — the next person extending the file copies the wrong pattern
