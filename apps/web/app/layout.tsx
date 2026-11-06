import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {
  title: 'راگ مالی | رابط آزمایشی فارسی',
  description: 'نمایش مستقل و مصنوعی مسیر چت فارسی. بدون اتصال به موتور یا API واقعی.',
  robots: { index: false, follow: false }
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="fa" dir="rtl"><body>{children}</body></html>;
}
