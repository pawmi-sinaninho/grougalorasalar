import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Grougalorasalar Solver',
  description: 'Pré-live tactique, correction manuelle obligatoire.'
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
