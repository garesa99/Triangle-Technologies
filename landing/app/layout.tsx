import type { Metadata } from 'next';
import { inter, jetbrainsMono } from './fonts';
import './globals.css';

export const metadata: Metadata = {
  title: 'Triangle Mesh — Passive drone detection for the uncooperative airspace',
  description:
    'A passive, distributed, attritable drone-detection mesh. Detect drones that do not want to be seen.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <head>
        <meta name="robots" content="noindex, nofollow" />
      </head>
      <body>{children}</body>
    </html>
  );
}
