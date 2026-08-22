# omp-config — the house conventions repo (skills, rules, standards).
# Single dev entry point per the house standard: every check goes through
# make. The repo carries a few tools under `tools/` (self-checks, the tree
# generator, the gh shim) — they are make-adjacent, not a product; there is
# no lint/typecheck/coverage pipeline here. `test` is the repo's self-check
# (docs links + lucidlint gate + skill well-formedness).

.PHONY: help setup install uninstall install-gh-shim install-git-shim install-lucidlint test

# Home may be unset or wrong when run from a daemon/bare env; resolve it.
H := $(if $(HOME),$(HOME),$(shell getent passwd $$(id -u) | cut -d: -f6))
APPEND_DIR := $(H)/.omp/agent
RULES_DIR  := $(H)/.agent/rules
SKILLS_DIR := $(APPEND_DIR)/skills
HOOKS_DIR  := .githooks
GH_SHIM_DST := $(H)/.local/bin/gh
GIT_SHIM_DST := $(H)/.local/bin/git
GIT_HELPER_DST := $(H)/.local/libexec/omp-bot-credential-helper
GIT_AGENT_CFG := $(H)/.local/etc/gitconfig-agent
FETCH_FINDINGS_DST := $(H)/.local/bin/fetch-pr-findings.sh

help:
	@echo "omp-config — available commands:"
	@echo "  ${GREEN}make setup${NC}          Symlink rules/skills/APPEND_SYSTEM + install git hooks + gh/git shims"
	@echo "  ${GREEN}make install${NC}        Symlink rules/skills/APPEND_SYSTEM (restart omp to pick up)"
	@echo "  ${GREEN}make install-gh-shim${NC} Symlink tools/gh-app-shim -> ~/.local/bin/gh; create ~/.secrets from template if missing"
	@echo "  ${GREEN}make install-git-shim${NC} Symlink tools/git-app-shim -> ~/.local/bin/git + bot credential helper (agents auth as omp-harness[bot])"
	@echo "  ${GREEN}make uninstall${NC}      Remove the symlinks"
	@echo "  ${GREEN}make install-lucidlint${NC} Fetch the pinned lucidlint release bundle into .tools/lucidlint"
	@echo "  ${GREEN}make test${NC}           Repo self-check: doc links resolve + lucidlint gate + skills well-formed"

setup:
	@$(MAKE) install
	@$(MAKE) install-gh-shim
	@$(MAKE) install-git-shim
	@git config core.hooksPath $(HOOKS_DIR)
	@echo "Hooks installed ($(HOOKS_DIR)/pre-commit)."

install:
	mkdir -p $(APPEND_DIR) $(RULES_DIR) $(SKILLS_DIR) $(dir $(FETCH_FINDINGS_DST))
	ln -sf $(CURDIR)/APPEND_SYSTEM.md $(APPEND_DIR)/APPEND_SYSTEM.md
	for f in $(CURDIR)/rules/*.md; do \
		ln -sf $$f $(RULES_DIR)/$$(basename $$f); \
	done
	for skill_dir in $(CURDIR)/skills/*/; do \
		name=$$(basename $$skill_dir); \
		mkdir -p $(SKILLS_DIR)/$$name; \
		ln -sf $$skill_dir/SKILL.md $(SKILLS_DIR)/$$name/SKILL.md; \
		if [ -d $$skill_dir/examples ]; then \
			ln -sfn $$skill_dir/examples $(SKILLS_DIR)/$$name/examples; \
		fi; \
	done
	ln -sf $(CURDIR)/tools/fetch-pr-findings.sh $(FETCH_FINDINGS_DST)
	chmod +x $(FETCH_FINDINGS_DST)
	@echo "Installed omp-config. Restart omp to pick up changes."

install-gh-shim:
	@mkdir -p $(dir $(GH_SHIM_DST))
	@ln -sf $(CURDIR)/tools/gh-app-shim $(GH_SHIM_DST)
	@if [ ! -f $(H)/.secrets ]; then \
		cp $(CURDIR)/tools/secrets.template $(H)/.secrets && chmod 600 $(H)/.secrets; \
		echo "Created ~/.secrets from template — fill in the values, then chmod 600."; \
	else \
		echo "~/.secrets exists — leaving it alone."; \
	fi
	@chmod 700 $(GH_SHIM_DST)
	@echo "gh shim installed -> $(GH_SHIM_DST)"

install-git-shim:
	@mkdir -p $(dir $(GIT_SHIM_DST)) $(dir $(GIT_HELPER_DST)) $(dir $(GIT_AGENT_CFG))
	@ln -sf $(CURDIR)/tools/git-app-shim $(GIT_SHIM_DST)
	@ln -sf $(CURDIR)/tools/omp-bot-credential-helper $(GIT_HELPER_DST)
	@chmod 700 $(GIT_SHIM_DST) $(GIT_HELPER_DST)
	@python3 $(CURDIR)/tools/gen-agent-gitconfig.py $(GIT_AGENT_CFG) $(GIT_HELPER_DST)
	@if [ ! -f $(H)/.secrets ]; then \
		cp $(CURDIR)/tools/secrets.template $(H)/.secrets && chmod 600 $(H)/.secrets; \
		echo "Created ~/.secrets from template — fill in the values, then chmod 600."; \
	else \
		echo "~/.secrets exists — leaving it alone."; \
	fi
	@echo "git shim installed -> $(GIT_SHIM_DST) (+ $(GIT_HELPER_DST), $(GIT_AGENT_CFG))"

uninstall:
	rm -f $(APPEND_DIR)/APPEND_SYSTEM.md
	for f in $(CURDIR)/rules/*.md; do \
		rm -f $(RULES_DIR)/$$(basename $$f); \
	done
	for skill_dir in $(CURDIR)/skills/*/; do \
		name=$$(basename $$skill_dir); \
		rm -f $(SKILLS_DIR)/$$name/SKILL.md; \
		rm -rf $(SKILLS_DIR)/$$name/examples; \
		rmdir $(SKILLS_DIR)/$$name 2>/dev/null || true; \
	done
	rm -f $(GH_SHIM_DST) $(GIT_SHIM_DST) $(GIT_HELPER_DST) $(GIT_AGENT_CFG)
	@echo "Removed omp-config symlinks."

# lucidlint consumption per the bundle's own README: unpack to .tools/lucidlint
# and drive via `make -C`; the orchestrator finds its sibling scan binary by
# itself. Pinned to a release tag — never main (house rule).
LUCIDLINT_DIR ?= .tools/lucidlint
LUCIDLINT_PIN ?= v0.3.0

install-lucidlint:
	mkdir -p .tools
	curl -fsSL -o /tmp/lucidlint-$(LUCIDLINT_PIN).tar.gz \
	  https://github.com/ashbywinch/lucidlint/releases/download/$(LUCIDLINT_PIN)/lucidlint-$(LUCIDLINT_PIN)-x86_64-unknown-linux-musl.tar.gz
	tar xzf /tmp/lucidlint-$(LUCIDLINT_PIN).tar.gz -C .tools
	rm -rf $(LUCIDLINT_DIR)
	mv .tools/lucidlint-$(LUCIDLINT_PIN)-x86_64-unknown-linux-musl $(LUCIDLINT_DIR)

test:
	@python3 tools/check_docs_links.py
	@$(MAKE) -C $(LUCIDLINT_DIR) lucidlint REPO=../.. BASELINE= || \
	  (echo "lucidlint gate failed or is not installed — run 'make install-lucidlint' first" && exit 1)
	@python3 -m unittest discover -s tools/tests
