import { defineConfig } from "vitest/config";

// Coverage is gated here rather than in prose: a drop below the floor fails the run, so CI cannot go
// green on untested code. Clover is the format the CI gate consumes.
export default defineConfig({
    test: {
        environment: "happy-dom",
        coverage: {
            provider: "istanbul",
            reporter: ["text", "clover"],
            reportsDirectory: "coverage",
            thresholds: { lines: 80, statements: 80, functions: 80, branches: 70 },
        },
    },
});
