# omp-config — the house conventions repo (skills, rules, standards).
# Single dev entry point per the house standard: every check goes through
# make. The repo carries a few tools under `tools/` (self-checks, the tree
# generator, the gh shim) — they are make-adjacent, not a product; there is
# no lint/typecheck/coverage pipeline here. `test` is the repo's self-check
# (docs links + skill well-formedness).

.PHONY: help setup install uninstall install-gh-shim test

# Home may be unset or wrong when run from a daemon/bare env; resolve it.
H := $(if $(HOME),$(HOME),$(shell getent passwd $$(id -u) | cut -d: -f6))
APPEND_DIR := $(H)/.omp/agent
RULES_DIR  := $(H)/.agent/rules
SKILLS_DIR := $(APPEND_DIR)/skills
HOOKS_DIR  := .githooks
GH_SHIM_DST := $(H)/.local/bin/gh

help:
	@echo "omp-config — available commands:"
	@echo "  ${GREEN}make setup${NC}          Symlink rules/skills/APPEND_SYSTEM + install git hooks + gh shim"
	@echo "  ${GREEN}make install${NC}        Symlink rules/skills/APPEND_SYSTEM (restart omp to pick up)"
	@echo "  ${GREEN}make install-gh-shim${NC} Symlink tools/gh-app-shim -> ~/.local/bin/gh; create ~/.secrets from template if missing"
	@echo "  ${GREEN}make uninstall${NC}      Remove the symlinks"
	@echo "  ${GREEN}make test${NC}           Repo self-check: doc links resolve + skills well-formed"

setup:
	@$(MAKE) install
	@$(MAKE) install-gh-shim
	@git config core.hooksPath $(HOOKS_DIR)
	@echo "Hooks installed ($(HOOKS_DIR)/pre-commit)."

install:
	mkdir -p $(APPEND_DIR) $(RULES_DIR) $(SKILLS_DIR)
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
	@echo "Removed omp-config symlinks."

test:
	@python3 tools/check_docs_links.py
	@python3 tools/check_missed_classes.py
	@python3 -m unittest discover -s tools/tests
