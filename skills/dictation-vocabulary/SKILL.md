---
name: dictation-vocabulary
description: Fix a jargon word, product name, person or acronym that speech-to-text keeps mis-spelling — where the per-repository and shared lexicons live, and how to prove a term earns its slot.
---

# Dictation vocabulary

## When to use this

The user reports that a dictated message came out with the wrong word for a name they use. That
covers a repository, a product, a service, a person, or an acronym: `LiteLLM` heard as `Light LLM`,
`Vaultwarden` as `Fault Warden`, `floorplan` as `floor plan`.

Do not use it for substitutions of ordinary English (`build` heard as `brought`) or for dropped
words. Those are not vocabulary faults and no lexicon fixes them.

## Where the terms live

| File | Holds | Committed |
|---|---|---|
| `<repo>/.lexicon` | terms specific to that repository | with that repo |
| `lexicon/central.lexicon` in `omp-config`, installed to `~/.paseo/lexicon.central` | names shared across repositories | in `omp-config`, via `make install` |

The transcription shim merges them at request time: repository terms first, then the central list,
de-duplicated, truncated at the provider's 100-term cap. Repository terms lead so the specific ones
are never crowded out by the general list.

Ask which file: a term that appears in more than one repository belongs in the central list;
anything else belongs in the repository's own file.

## Prove the term before adding it

Add a term only after it fails without the list and is fixed with it. An unnecessary term consumes a
slot and dilutes the boost every other term receives, and a plain English word cannot be boosted at
all — `main` and `rebase` were tested and changed nothing.

1. Take the utterance that failed, which is the take that brought you here.
2. Transcribe that audio twice: once with no `keyterm` parameter, once with the term. The shim speaks
   the OpenAI shape, so any OpenAI-compatible client can send a WAV to it.
3. Keep the term only if the first transcript is wrong and the second is right.

## Adding one

- Repository term: append it to `<repo>/.lexicon`, one per line, `#` starts a comment.
- Shared term: append it to `lexicon/central.lexicon`, run `make install`, then branch and open a PR.
- Write the term as it should read. Case is preserved in the output, so `LiteLLM` transcribes as
  `LiteLLM` rather than `litellm`.
- Never add a term that already transcribes correctly, an ordinary English word, or an identifier
  containing digits or underscores. None of them can be boosted usefully.

## What the terms can and cannot fix

| Fault | Example | Fixed by a term |
|---|---|---|
| Substitution of the term itself | `Brightmove` → `Rightmove` | yes |
| Split compound | `floor plan` → `floorplan` | yes |
| Substitution of an ordinary word | `build` → `brought` | no |
| Omission | `refetch the certificate` → `refit certificate` | no |

