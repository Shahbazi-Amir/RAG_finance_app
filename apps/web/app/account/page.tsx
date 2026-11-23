import Link from 'next/link';
import '../history/history.css';
export const metadata={title:'حساب و حریم خصوصی | راگ مالی'};
export default function AccountPage(){
  return <main className="history-shell" dir="rtl">
    <section className="history-main" aria-labelledby="account-title">
      <header className="history-heading">
        <h1 id="account-title">حساب و حریم خصوصی</h1>
        <p>این صفحه وضعیت قابلیت‌های مربوط به حساب را نشان می‌دهد؛
          هیچ اقدام ثبت رضایت، حذف داده یا ارسال بازخورد از این صفحه انجام نمی‌شود.</p>
      </header>
      <nav aria-label="مسیرهای حساب" className="history-recovery">
        <Link className="history-link" href="/login">ورود، مشاهدهٔ نشست و خروج امن</Link>
        <Link className="history-link" href="/">بازگشت به گفت‌وگو</Link>
      </nav>
      <section aria-labelledby="consent-title" className="history-answer account-policy">
        <h2 id="consent-title">رضایت و حریم خصوصی</h2>
        <p>متن، نسخه و قرارداد ثبت یا پس‌گرفتن رضایت هنوز برای اتصال این رابط تصویب نشده است.</p>
        <p role="status">وضعیت ثبت رضایت: نامعلوم؛ پذیرش خودکار انجام نمی‌شود.</p>
      </section>
      <section aria-labelledby="deletion-title" className="history-answer account-policy">
        <h2 id="deletion-title">درخواست حذف داده و حساب</h2>
        <p>ثبت درخواست، پیگیری وضعیت و ابطال نشست پس از حذف نیازمند
          قرارداد و سیاست تأییدشدهٔ سرور است. این صفحه تأیید حذف صادر نمی‌کند.</p>
        <p role="status">امکان درخواست حذف از این رابط هنوز فعال نیست.</p>
      </section>
      <section aria-labelledby="export-title" className="history-answer account-policy">
        <h2 id="export-title">خروجی داده و بازخورد</h2>
        <p>خروجی ساخت‌یافته منوط به تصویب مستقل دامنه است.
          بازخورد نیز فقط بعد از وجود شناسهٔ معتبر پاسخ و رسید ذخیرهٔ سرور متصل می‌شود.</p>
        <p role="status">Export و Feedback در این نسخه فعال نیستند.</p>
      </section>
    </section>
  </main>;
}
