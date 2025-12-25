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
      'vue/prefer-true-attribute-shorthand': 'warn',

      // TypeScript
      '@typescript-eslint/no-unused-vars': ['error', {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_'
      }],
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/explicit-function-return-type': 'off',
      '@typescript-eslint/no-non-null-assertion': 'warn',

      // General
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      'no-debugger': 'warn',
      'prefer-const': 'error',
      'no-var': 'error',
      'eqeqeq': ['error', 'always'],

      // Accessibility
      'vue/no-static-inline-styles': 'warn',
    }
  }
]
