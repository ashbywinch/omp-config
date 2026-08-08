# omp-config — the house conventions repo (skills, rules, standards).
# Single dev entry point per the house standard: every check goes through
# make. No code lives here, so there is no lint/typecheck/coverage —
# `test` is the repo's self-check (docs links + skill well-formedness).

.PHONY: help setup install uninstall test

APPEND_DIR := $(HOME)/.omp/agent
RULES_DIR  := $(HOME)/.agent/rules
SKILLS_DIR := $(APPEND_DIR)/skills
HOOKS_DIR  := .githooks

help:
	@echo "omp-config — available commands:"
	@echo "  ${GREEN}make setup${NC}          Symlink rules/skills/APPEND_SYSTEM + install git hooks"
	@echo "  ${GREEN}make install${NC}        Symlink rules/skills/APPEND_SYSTEM (restart omp to pick up)"
	@echo "  ${GREEN}make uninstall${NC}      Remove the symlinks"
	@echo "  ${GREEN}make test${NC}           Repo self-check: doc links resolve + skills well-formed"

setup:
	@$(MAKE) install
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
	done
	@echo "Installed omp-config. Restart omp to pick up changes."

uninstall:
	rm -f $(APPEND_DIR)/APPEND_SYSTEM.md
	for f in $(CURDIR)/rules/*.md; do \
		rm -f $(RULES_DIR)/$$(basename $$f); \
	done
	for skill_dir in $(CURDIR)/skills/*/; do \
		name=$$(basename $$skill_dir); \
		rm -f $(SKILLS_DIR)/$$name/SKILL.md; \
		rmdir $(SKILLS_DIR)/$$name 2>/dev/null || true; \
	done
	@echo "Removed omp-config symlinks."

test:
	@python3 tools/check_docs_links.py
	@python3 tools/check_missed_classes.py
	@python3 -m unittest discover -s tools/tests
