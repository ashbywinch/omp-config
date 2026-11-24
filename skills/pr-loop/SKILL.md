---
name: pr-loop
description: |
  Drive a PR through review rounds until it is clean: land the code, answer every
  thread on the current head, push once, wait for the next review. Load when a PR
  has findings to answer, or before deciding whether to push again.
---

# The review loop

The reviewer reviews every push. One pass per review, in this order:

1. Land every code change first.
2. Run `pr-threads <pr>`. Answer every thread on the current head.
3. Push once.
4. Run `pr-threads --wait <pr>`. Answer the batch it lists.
5. Push again only when an answer needed a code change.
