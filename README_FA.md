# Football Pass Analyzer Pro – Android project

این پروژه نسخه اندرویدی بازنویسی‌شده از منطق v26 است. رابط PySide6 مستقیماً روی Android اجرا نمی‌شود؛ این نسخه با Kivy ساخته شده است.

## امکانات پیاده‌سازی‌شده
- داشبورد آمار پاس‌ها و درصد موفقیت
- ثبت پاس با پاس‌دهنده، گیرنده، نتیجه، طول، جهت، تعداد و دقیقه
- مدیریت بازیکنان و پست‌ها
- ایجاد و انتخاب مسابقه
- ماتریس پاس، شبکه پاس و مقایسه بازیکنان
- نمایش رویدادهای موجود در جدول match_events
- نمای شماتیک زمین
- چهار پوسته رنگی
- پایگاه داده SQLite در فضای خصوصی برنامه
- حفظ نام جدول‌ها و ستون‌های اصلی v25/v26 و مهاجرت افزایشی ستون‌ها

## ساخت APK روی Linux
نیازمند Python 3، Java JDK، Android SDK/NDK و Buildozer است.

```bash
python3 -m pip install --user buildozer
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk autoconf libtool pkg-config \
  zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo6 cmake libffi-dev libssl-dev
buildozer android debug
```

پس از ساخت موفق، APK در پوشه `bin/` قرار می‌گیرد. برای نصب:
```bash
adb install -r bin/*.apk
```

## ساخت خودکار با GitHub Actions
پروژه شامل workflow است. یک repository بسازید، محتویات این پوشه را push کنید و از تب Actions گزینه Android APK Build را اجرا کنید. فایل APK به‌صورت Artifact قابل دریافت خواهد بود.

## نکات مهم درباره سازگاری داده
- فایل پایتون آپلودشده شامل کد برنامه است، نه خود فایل SQLite دیتابیس.
- بنابراین سوابق قبلی شما در این بسته وجود ندارند. اگر فایل `football_pass_analyzer.db` نسخه دسکتاپ را هم بدهید، می‌توان مسیر انتقال/درون‌ریزی داده‌های واقعی را اضافه کرد.
- نسخه اصلی دسکتاپ در بخش زمین، مختصات پاس را در رابط کاربری ثبت نمی‌کرد؛ در این نسخه هم نقشه حرارتی واقعی ادعا نشده است.
- رویدادهای جدول match_events نمایش داده می‌شوند، اما فرم افزودن رویداد در نسخه دسکتاپ وجود نداشت.
- این نسخه یک بازنویسی اندرویدی اولیه و قابل توسعه است؛ قبل از انتشار نهایی باید روی چند گوشی واقعی تست شود.

## فایل‌های اصلی
- `main.py`: اپلیکیشن Kivy و منطق SQLite
- `buildozer.spec`: تنظیمات بسته‌بندی Android
- `.github/workflows/android.yml`: ساخت APK در GitHub Actions
