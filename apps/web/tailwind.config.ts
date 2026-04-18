import type { Config } from 'tailwindcss';

/**
 * Axis workbench theme — professional light palette.
 *
 * Inspiration: Tableau, Atlassian, Retool, Linear, Looker.
 * Principle: data-dense, high contrast, conservative, reliable.
 *
 * - Sidebar (navigation rail):  deep navy, always dark
 * - Content area:               near-white slate
 * - Text:                       near-black for body, slate for secondary
 * - Accent:                     single professional blue — used sparingly
 * - Semantic:                   green/amber/red at AA contrast against white
 *
 * No glass, no blur, no neon, no gradients on surfaces.
 */
const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    '../../packages/design-system/src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Content area — the "paper"
        canvas: {
          DEFAULT: '#f7f8fa',   // page background
          raised: '#ffffff',    // cards / panels
          subtle: '#eef1f6',    // hovers, zebra rows
          sunken: '#e5e9f0',    // input fields
        },
        // Text
        ink: {
          DEFAULT: '#0f172a',   // primary text — near-black
          secondary: '#475569', // secondary text — slate-600
          tertiary: '#64748b',  // labels, meta — slate-500
          disabled: '#94a3b8',  // disabled — slate-400
          onDark: '#e2e8f0',    // text on navy sidebar
          onDarkMuted: '#94a3b8',
        },
        // Borders
        edge: {
          DEFAULT: '#e2e8f0',   // standard border — slate-200
          strong: '#cbd5e1',    // input border, emphasized — slate-300
          subtle: '#eef1f6',    // hairline — slate-100
          onDark: '#1e293b',    // border on navy — slate-800
        },
        // Navy sidebar / header
        nav: {
          DEFAULT: '#0f1e3d',   // deep navy sidebar
          hover: '#1a2c52',
          active: '#243b6b',
          border: '#1e293b',
        },
        // Single professional accent — a conservative Tableau-ish blue
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          500: '#2563eb',       // primary — blue-600
          600: '#1d4ed8',       // hover — blue-700
          700: '#1e40af',
        },
        // Semantic colors — all AA-contrast against canvas
        success: {
          DEFAULT: '#16a34a',    // green-600
          bg: '#dcfce7',         // green-100
          fg: '#14532d',         // green-900
        },
        warning: {
          DEFAULT: '#d97706',    // amber-600
          bg: '#fef3c7',
          fg: '#78350f',
        },
        danger: {
          DEFAULT: '#dc2626',    // red-600
          bg: '#fee2e2',
          fg: '#7f1d1d',
        },
        info: {
          DEFAULT: '#0284c7',    // sky-600
          bg: '#e0f2fe',
          fg: '#0c4a6e',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          '"Helvetica Neue"',
          'Arial',
          'sans-serif',
        ],
        mono: [
          '"JetBrains Mono"',
          '"SF Mono"',
          'Menlo',
          'Monaco',
          'Consolas',
          'monospace',
        ],
      },
      fontSize: {
        'xs': ['11px', { lineHeight: '16px', letterSpacing: '0.01em' }],
        'sm': ['13px', { lineHeight: '20px' }],
        'base': ['14px', { lineHeight: '21px' }],
        'lg': ['16px', { lineHeight: '24px' }],
        'xl': ['18px', { lineHeight: '26px', letterSpacing: '-0.01em' }],
        '2xl': ['22px', { lineHeight: '30px', letterSpacing: '-0.015em' }],
        '3xl': ['28px', { lineHeight: '34px', letterSpacing: '-0.02em' }],
      },
      borderRadius: {
        none: '0',
        sm: '3px',
        DEFAULT: '4px',
        md: '6px',
        lg: '8px',
        xl: '12px',
      },
      spacing: {
        '0.5': '2px',
        '1': '4px',
        '1.5': '6px',
        '2': '8px',
        '2.5': '10px',
        '3': '12px',
        '4': '16px',
        '5': '20px',
        '6': '24px',
        '8': '32px',
        '10': '40px',
        '12': '48px',
      },
      boxShadow: {
        'sm-strong': '0 1px 2px 0 rgba(15, 23, 42, 0.08)',
        'panel': '0 1px 3px 0 rgba(15, 23, 42, 0.06), 0 1px 2px 0 rgba(15, 23, 42, 0.04)',
        'popover': '0 8px 16px -4px rgba(15, 23, 42, 0.1), 0 4px 8px -2px rgba(15, 23, 42, 0.06)',
      },
    },
  },
  plugins: [],
};

export default config;
