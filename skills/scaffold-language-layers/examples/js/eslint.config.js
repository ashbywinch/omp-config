import js from "@eslint/js";
import tseslint from "typescript-eslint";
import prettier from "eslint-config-prettier";

// Prettier LAST: it turns off the style rules so the two never disagree about the same file.
export default tseslint.config(
    { ignores: ["node_modules/**", "dist/**", "coverage/**"] },
    js.configs.recommended,
    ...tseslint.configs.recommended,
    prettier,
);
