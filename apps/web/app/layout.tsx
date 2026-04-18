import type { Metadata } from 'next';
import './globals.css';
import { Providers } from './providers';
import { inter, interDisplay, jetbrainsMono } from './fonts';

export const metadata: Metadata = {
  title: 'Axis — Workbench',
  description: 'The cross-tool agent workbench for startup teams.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      data-theme="dark"
      className={`${inter.variable} ${interDisplay.variable} ${jetbrainsMono.variable}`}
      suppressHydrationWarning
    >
      <body className="min-h-screen bg-canvas text-ink antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
