# Qogoz bot

Serial/kino tarqatuvchi Telegram bot. Videolar arxiv kanalda yotadi, bot
ularni `copy_message` orqali foydalanuvchiga yuboradi.

Stack: Python 3.11+, aiogram 3, aiosqlite, PM2.

## O'rnatish

```bash
cd qogoz_bot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # token, ADMIN_ID, ARCHIVE_CHANNEL_ID ni to'ldiring
python main.py
```

## Arxiv kanal

1. Yopiq kanal oching, botni admin qiling.
2. Kanal ID sini oling (`-100...`) va `.env` ga `ARCHIVE_CHANNEL_ID` qilib yozing.
3. Videolarni o'sha kanalga tashlang, keyin admin panel orqali botga **forward** qiling.

Video `file_id` orqali emas, kanaldan nusxalab yuboriladi — shuning uchun
bot tokeni almashsa ham qismlar ishlab turaveradi.

## PM2

```bash
mkdir -p logs
pm2 start ecosystem.config.js
pm2 logs qogoz-bot
pm2 save
```

## Buyruqlar

| Buyruq     | Kim uchun | Nima qiladi                     |
|------------|-----------|---------------------------------|
| `/start`   | hamma     | asosiy menyu, seriallar ro'yxati |
| `/murojat` | hamma     | adminga xabar yozish            |
| `/admin`   | admin     | admin panel                     |

Oddiy matn xabari qidiruv deb qabul qilinadi.

Butun interfeys **reply (oddiy) tugmalarda** — inline tugma yo'q. Bot har
bosishda oldingi ekranini va bosilgan tugma xabarini o'chiradi, shuning uchun
chatda bitta faol ekran qoladi.

## Admin panel

- ➕ **Serial qo'shish** — nom → tavsif → poster → janr → yil
- 🎬 **Qism qo'shish** — serial tanlanadi, arxiv kanaldan video forward qilinadi
- ✏️ **Tahrirlash / o'chirish** — maydonlar, qismlar, serialning o'zi
- 📊 **Statistika** — userlar, bugungi faollar, top 10 serial
- 📨 **Tarqatish** — chunked yuborish, bloklaganlar hisoblanadi
- 💬 **Murojatlar** — javob berilmaganlar; xabarga reply qilsangiz javob userga ketadi

Loyiha tuzilishi va yangi modul qo'shish qoidasi: [CLAUDE.md](CLAUDE.md).
