
import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

// Define ESLint rules and settings for the frontend project.
export default defineConfig([
  // Ignore the production build output during linting.
  globalIgnores(['dist']),

  {
    // Apply these linting settings to JavaScript and JSX files.
    files: ['**/*.{js,jsx}'],

    // Extend recommended rules for JavaScript, React Hooks, and React Fast Refresh.
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],

    languageOptions: {
      // Make browser global variables available to ESLint.
      globals: globals.browser,

      // Enable JSX syntax parsing in JavaScript files.
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
  },
])
