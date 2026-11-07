import type { Metadata } from 'next';
import localFont from 'next/font/local';
import './globals.css';

// Only official v33.003 Vazirmatn WOFF2, self-hosted by Next.js.
// Actual variable weight axis: 100–900; no synthetic bold or third-party font request.
const vazirmatn = localFont({
  src: '../fonts/Vazirmatn-Variable.woff2',
  weight: '100 900',
  style: 'normal',
  display: 'swap',
  variable: '--font-vazirmatn',
  preload: true,
});
export const metadata: Metadata = {
  title: 'راگ مالی | رابط آزمایشی فارسی',
  description: 'نمایش مستقل و مصنوعی مسیر چت فارسی. بدون اتصال به موتور یا API واقعی.',
  robots: { index: false, follow: false }
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="fa" dir="rtl" className={vazirmatn.variable}><body>{children}</body></html>;
}
