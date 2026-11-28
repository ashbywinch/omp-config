"""The login that counts as mine, as the command-line tools resolve it."""

from __future__ import annotations

import os


def answering_login() -> str:
    """The login whose last comment answers a thread.

    ``PR_THREADS_ME`` overrides it, defaulting to this harness's bot login in
    the CLI form. Surrounding whitespace from a shell config is not part of a
    login.
    """
    return (os.environ.get("PR_THREADS_ME") or "").strip() or "omp-harness[bot]"


def account(login: str) -> str:
    """The account behind a login, as both surfaces spell it.

    GraphQL reports a bot without the ``[bot]`` suffix the CLI shows, so the
    comparison drops it: ``omp-harness`` and ``omp-harness[bot]`` are one login.
    """
    return login.removesuffix("[bot]")
