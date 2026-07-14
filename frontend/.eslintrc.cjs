// ─── frontend/.eslintrc.cjs ───────────────────────────────────────────────────
// ESLint configuration for React + TypeScript frontend.
// Compatible with ESLint 8.x flat-config not yet adopted.

/** @type {import("eslint").Linter.Config} */
module.exports = {
  root: true,
  env: {
    browser: true,
    es2022: true,
    node: true,
  },
  parser: "@typescript-eslint/parser",
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
    ecmaFeatures: { jsx: true },
    project: "./tsconfig.json",
  },
  plugins: [
    "@typescript-eslint",
    "react",
    "react-hooks",
    "jsx-a11y",
  ],
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react/recommended",
    "plugin:react/jsx-runtime",
    "plugin:react-hooks/recommended",
    "plugin:jsx-a11y/recommended",
  ],
  settings: {
    react: { version: "detect" },
  },
  rules: {
    // TypeScript
    "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
    "@typescript-eslint/no-explicit-any": "warn",
    "@typescript-eslint/explicit-function-return-type": "off",
    "@typescript-eslint/no-non-null-assertion": "warn",
    "@typescript-eslint/consistent-type-imports": ["error", { prefer: "type-imports" }],

    // React
    "react/prop-types": "off",        // TypeScript handles this
    "react/display-name": "warn",
    "react-hooks/exhaustive-deps": "warn",

    // Accessibility
    "jsx-a11y/alt-text": "error",
    "jsx-a11y/anchor-is-valid": "error",

    // General
    "no-console": ["warn", { allow: ["warn", "error"] }],
    "prefer-const": "error",
    "no-var": "error",
    "eqeqeq": ["error", "always"],
  },
  overrides: [
    {
      // Relax rules in test files
      files: ["**/*.test.{ts,tsx}", "**/*.spec.{ts,tsx}", "**/tests/**"],
      rules: {
        "@typescript-eslint/no-explicit-any": "off",
        "no-console": "off",
      },
    },
  ],
  ignorePatterns: [
    "dist/",
    "node_modules/",
    "coverage/",
    "*.config.{js,cjs,mjs}",
    "vite.config.ts",
    "vitest.config.ts",
    "tailwind.config.*",
    "postcss.config.*",
  ],
};
