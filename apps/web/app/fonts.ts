import { Inter, Inter_Tight, JetBrains_Mono } from 'next/font/google';

/** Body font — covers ~85% of the UI. */
export const inter = Inter({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-sans',
  display: 'swap',
});

/**
 * Display cut for Display M/L/XL sizes only.
 * (Inter Display is not on Google Fonts as a separate family;
 * Inter Tight is the closest published cut and reads similarly at large sizes.
 * See spec deviation note in plan header.)
 */
export const interDisplay = Inter_Tight({
  subsets: ['latin'],
  weight: ['500', '600'],
  variable: '--font-display',
  display: 'swap',
});

/** Mono — used selectively (~15% of text per artifact §2b). */
export const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-mono',
  display: 'optional',
});
