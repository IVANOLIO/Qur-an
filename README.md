تمام يا IVANOLIO ✨
رح أعطيك كل الملفات الجاهزة للنسخ والرفع مباشرة على GitHub 🚀


---

📌 README.md

# 📖 Quran Auto Poster Bot

بوت تيلجرام يقوم بنشر آيات من القرآن الكريم بشكل تلقائي إلى القنوات التي تحددها.  
سهل التحكم، مفتوح المصدر، وقابل للتخصيص.

---

## ✨ المميزات
- نشر آيات من القرآن الكريم بشكل دوري إلى القنوات.
- دعم **إضافة قنوات** بعدد غير محدود.
- إمكانية **تحديد الفاصل الزمني** لكل قناة على حدة.
- تفعيل/إيقاف النشر بسهولة.
- أوامر للتحكم بالجميع دفعة واحدة.
- قاعدة بيانات SQLite مدمجة (بدون تعقيد).
- إعداد عبر ملف `.env` بسيط.

---

## ⚙️ المتطلبات
- Python **3.9+**
- مكتبات:
  - `python-telegram-bot`
  - `requests`
  - `python-dotenv`

---

## 🚀 التثبيت

### 1️⃣ استنساخ المشروع
```bash
git clone https://github.com/IVANOLIO/quran-bot.git
cd quran-bot

2️⃣ إنشاء بيئة افتراضية وتثبيت المكتبات

python3 -m venv venv
source venv/bin/activate   # Linux / macOS
venv\Scripts\activate      # Windows

pip install -r requirements.txt

3️⃣ إعداد ملف البيئة

انسخ .env.example إلى .env وعدّل القيم:

cp .env.example .env


---

▶️ التشغيل

python qu.py

سيبدأ البوت في العمل والرد على الأوامر.


---

🛠️ الأوامر

أوامر المالك:

/addchannel @channel 30 → إضافة/تحديث قناة بفاصل 30 دقيقة.

/setinterval @channel 45 → تغيير الفاصل لقناة محددة.

/enable @channel → تفعيل النشر في قناة.

/disable @channel → إيقاف النشر في قناة.

/list → استعراض جميع القنوات المخزنة.

/testpost @channel → إرسال آية تجريبية للقناة.


أوامر عامة:

/setinterval_all 30 → ضبط الفاصل للجميع.

/enable_all → تفعيل النشر للجميع.

/disable_all → إيقاف النشر للجميع.



---

📦 التشغيل في الخلفية (باستخدام pm2)

npm install -g pm2
pm2 start qu.py --name quran-bot --interpreter python3
pm2 save
pm2 startup

أوامر مفيدة:

pm2 logs quran-bot
pm2 restart quran-bot
pm2 stop quran-bot


---

📁 هيكل المشروع

quran-bot/
│── qu.py              # الكود الرئيسي للبوت
│── requirements.txt   # المكتبات المطلوبة
│── .env.example       # مثال لملف البيئة
│── .gitignore         # تجاهل الملفات
│── README.md          # هذا الملف


---

🧑‍💻 المساهمة

مرحبًا بأي Pull Request أو Issue.
سواء كانت:

إصلاح أخطاء 🐛

إضافة مميزات جديدة ✨

تحسين الكود ⚡



---

📜 الترخيص

هذا المشروع مرخّص تحت MIT License.

