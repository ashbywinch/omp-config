APPEND_DIR    = $(HOME)/.omp/agent
RULES_DIR     = $(HOME)/.agent/rules
SKILLS_DIR    = $(APPEND_DIR)/skills

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
