// eslint.config.js
import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";

// Import Prettier related configurations
import pluginPrettierRecommended from "eslint-plugin-prettier/recommended"; // Includes plugin and recommended rules
import eslintConfigPrettier from "eslint-config-prettier"; // Disables conflicting rules

export default tseslint.config(
  { ignores: ["dist"] },

  // Base JS and TS configs
  js.configs.recommended,
  ...tseslint.configs.recommended,

  // React specific configs (keep these as they are relevant)
  {
    files: ["**/*.{ts,tsx}"], // Apply React rules only to TS/TSX files
    languageOptions: {
      parserOptions: {
        ecmaFeatures: { jsx: true }, // Enable JSX parsing
      },
      globals: {
        ...globals.browser, // Add browser globals
      },
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
      // Add any other React-specific rules here
    },
    settings: {
      react: {
        version: "detect", // Automatically detect React version
      },
    },
  },

  // Prettier configuration - MUST come after other configs that might conflict
  pluginPrettierRecommended, // Enables eslint-plugin-prettier and sets prettier/prettier rule to "error"
  // Add this object to override the Prettier rule severity
  {
    rules: {
      "prettier/prettier": "warn", // Set Prettier rule severity to warning
    },
  },
  eslintConfigPrettier, // Disables ESLint rules that conflict with Prettier
);
