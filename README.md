# pr-agent-config

Maintainer-controlled branch holding omp-config's `.pr_agent.toml` for the
"AI Code Review" workflow. PR-Agent reads its repo config from this branch
(`PR_AGENT_CONFIG_BRANCH` in `.github/workflows/pr-agent.yml`), never from PR
head branches — a PR branch's `.pr_agent.toml` could point `api_base` at an
attacker endpoint and exfiltrate `OPENCODE_GO_OMP_CONFIG_API_KEY`.

Keep this file in sync with the repo-root `.pr_agent.toml` on `main`; the
workflow applies whichever wins on this branch.
