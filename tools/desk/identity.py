"""The login that counts as mine, as the command-line tools resolve it."""

from __future__ import annotations

import os


def answering_login() -> str:
    """The login whose last comment answers a thread.

    ``PR_THREADS_ME`` overrides it; the default is the GitHub App's bot login.
    Surrounding whitespace from a shell config is not part of the login.
    """
    return (os.environ.get("PR_THREADS_ME") or "").strip() or "omp-harness[bot]"
