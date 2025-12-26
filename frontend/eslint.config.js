import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import vueTsEslintConfig from '@vue/eslint-config-typescript'
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'

export default [
  {
    name: 'app/files-to-lint',
    files: ['**/*.{ts,mts,tsx,vue}'],
  },
  {
    name: 'app/files-to-ignore',
    ignores: ['**/dist/**', '**/dist-ssr/**', '**/coverage/**', '**/node_modules/**'],
  },
  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  ...vueTsEslintConfig(),
  skipFormatting,
  {
    name: 'app/custom-rules',
    rules: {
      // Vue specific
      'vue/multi-word-component-names': 'off',
      'vue/no-v-html': 'warn',
      'vue/require-default-prop': 'off',
      'vue/no-unused-vars': 'error',
      'vue/valid-v-slot': ['error', { allowModifiers: true }], // Allow Vuetify data table slot syntax (#item.name)
      'vue/block-order': ['error', {
        order: ['template', 'script', 'style']
      }],
      'vue/block-lang': ['error', {
        script: { lang: 'ts' }
      }],
      'vue/define-macros-order': ['error', {
        order: ['defineOptions', 'defineModel', 'defineProps', 'defineEmits', 'defineSlots']
      }],
      'vue/no-empty-component-block': 'error',
      'vue/prefer-true-attribute-shorthand': ['warn', 'always', {
        except: ['model-value', 'value', 'aria-hidden', 'aria-modal', 'aria-atomic', 'aria-busy']
      }],

      // TypeScript
      '@typescript-eslint/no-unused-vars': ['warn', {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
        caughtErrorsIgnorePattern: '^_?'  // Allow unused caught errors
      }],
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/explicit-function-return-type': 'off',
      '@typescript-eslint/no-non-null-assertion': 'warn',
      '@typescript-eslint/ban-ts-comment': 'warn',  // Allow @ts-ignore for now
      '@typescript-eslint/no-empty-object-type': 'warn',  // Allow empty interfaces for now
      '@typescript-eslint/no-unsafe-function-type': 'warn',  // Allow Function type for now

      // General
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      'no-debugger': 'warn',
      'prefer-const': 'error',
      'no-var': 'error',
      'eqeqeq': ['warn', 'always', { null: 'ignore' }],  // Allow != null for nullish checks
      'no-case-declarations': 'warn',  // Downgrade case declarations
      'no-control-regex': 'warn',  // Downgrade control regex
      'no-useless-escape': 'warn',  // Downgrade useless escape

      // Accessibility - disabled, many intentional inline styles for Vuetify components
      'vue/no-static-inline-styles': 'off',
    }
  },
  // Relaxed rules for test files
  {
    name: 'app/test-files',
    files: ['**/*.test.ts', '**/*.spec.ts', '**/tests/**/*.ts'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-non-null-assertion': 'off',
      'no-console': 'off',  // Tests often mock console
    }
  },
  // Allow console in logger implementation
  {
    name: 'app/logger-files',
    files: ['**/useLogger.ts', '**/useLogger.example.ts'],
    rules: {
      'no-console': 'off',
    }
  }
]
