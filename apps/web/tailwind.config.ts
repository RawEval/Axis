import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
    '../../packages/design-system/src/**/*.{ts,tsx}',
  ],
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        canvas: {
          DEFAULT: 'var(--color-bg-canvas)',
          surface: 'var(--color-bg-surface)',
          elevated: 'var(--color-bg-elevated)',
          sunken: 'var(--color-bg-sunken)',
        },
        edge: {
          DEFAULT: 'var(--color-border-default)',
          subtle: 'var(--color-border-subtle)',
          strong: 'var(--color-border-strong)',
        },
        ink: {
          DEFAULT: 'var(--color-text-primary)',
          secondary: 'var(--color-text-secondary)',
          tertiary: 'var(--color-text-tertiary)',
          inverse: 'var(--color-text-inverse)',
        },
        accent: {
          DEFAULT: 'var(--color-accent-primary)',
          hover: 'var(--color-accent-hover)',
          subtle: 'var(--color-accent-subtle)',
          on: 'var(--color-accent-on)',
        },
        success: 'var(--color-success)',
        warning: 'var(--color-warning)',
        danger: 'var(--color-danger)',
        info: 'var(--color-info)',
        agent: {
          thinking: 'var(--color-agent-thinking)',
          running: 'var(--color-agent-running)',
          awaiting: 'var(--color-agent-awaiting)',
          recovered: 'var(--color-agent-recovered)',
          blocked: 'var(--color-agent-blocked)',
          background: 'var(--color-agent-background)',
        },
      },
      fontFamily: {
        display: ['var(--font-display)', 'Inter Display', '-apple-system', 'sans-serif'],
        sans: ['var(--font-sans)', 'Inter', '-apple-system', 'sans-serif'],
        mono: ['var(--font-mono)', 'JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        'display-xl': ['48px', { lineHeight: '1.05', letterSpacing: '-0.03em', fontWeight: '500' }],
        'display-l':  ['36px', { lineHeight: '1.10', letterSpacing: '-0.025em', fontWeight: '500' }],
        'display-m':  ['28px', { lineHeight: '1.15', letterSpacing: '-0.02em', fontWeight: '500' }],
        'heading-1':  ['22px', { lineHeight: '1.25', letterSpacing: '-0.015em', fontWeight: '600' }],
        'heading-2':  ['18px', { lineHeight: '1.30', letterSpacing: '-0.01em', fontWeight: '600' }],
        'heading-3':  ['15px', { lineHeight: '1.35', letterSpacing: '-0.005em', fontWeight: '600' }],
        'body-l':     ['16px', { lineHeight: '1.55' }],
        'body':       ['14px', { lineHeight: '1.50' }],
        'body-s':     ['13px', { lineHeight: '1.45' }],
        'caption':    ['12px', { lineHeight: '1.40' }],
        'micro':      ['11px', { lineHeight: '1.35', letterSpacing: '0.04em', fontWeight: '500' }],
        'mono-l':     ['14px', { lineHeight: '1.50' }],
        'mono':       ['13px', { lineHeight: '1.50' }],
        'mono-s':     ['12px', { lineHeight: '1.45' }],
        'kbd':        ['11px', { lineHeight: '1.00', letterSpacing: '0.02em', fontWeight: '500' }],
      },
      spacing: {
        '0.5': '2px',
        '1': '4px',
        '2': '8px',
        '3': '12px',
        '4': '16px',
        '5': '20px',
        '6': '24px',
        '8': '32px',
        '10': '40px',
        '14': '56px',
        '20': '80px',
      },
      borderRadius: {
        none: '0',
        xs: '4px',
        sm: '6px',
        md: '8px',
        lg: '12px',
        xl: '16px',
        full: '999px',
      },
      boxShadow: {
        'e1': '0 1px 2px rgba(14,14,16,0.05)',
        'e2': '0 1px 2px rgba(14,14,16,0.05), 0 2px 4px rgba(14,14,16,0.04)',
        'e3': '0 20px 40px rgba(14,14,16,0.12)',
      },
      keyframes: {
        breathe: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.92' },
        },
        shimmer: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
      },
      animation: {
        breathe: 'breathe 2400ms ease-in-out infinite',
        shimmer: 'shimmer 1400ms linear infinite',
      },
    },
  },
  plugins: [],
};

export default config;
