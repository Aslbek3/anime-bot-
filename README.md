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

Butun interfeys **reply (oddiy) tugmalarda** — inline tugma yo'q. Bot hech
qanday xabarni o'chirmaydi, klaviaturani esa faqat u o'zgarganda qayta
yuboradi — shuning uchun tugmalar har xabarda "sakramaydi".

## Admin panel

- ➕ **Serial qo'shish** — nom → tavsif → poster → janr → yil
- 🎬 **Qism qo'shish** — serial tanlanadi, arxiv kanaldan video forward qilinadi
- ✏️ **Tahrirlash / o'chirish** — maydonlar, qismlar, serialning o'zi
- 📊 **Statistika** — userlar, bugungi faollar, top 10 serial
- 📨 **Tarqatish** — chunked yuborish, bloklaganlar hisoblanadi
- 💬 **Murojatlar** — javob berilmaganlar; xabarga reply qilsangiz javob userga ketadi

## Qo'shimcha modullar

Hammasi `.env` dagi bayroq bilan **o'chiq** turadi, kerakligini `true` qiling
va botni qayta ishga tushiring:

| Bayroq | Nima beradi |
|---|---|
| `FEATURE_YUKLASH` | saytdan yuklab arxiv kanalga saqlash (parser kerak) |
| `FEATURE_TAKLIF` | foydalanuvchi kino taklif qiladi, admin tasdiqlaydi |
| `FEATURE_BILDIRISHNOMA` | yangi qism chiqqanda tomoshabinlarga xabar |
| `FEATURE_RAQAM` | serial ekranida "45" deb yozsa — 45-qism |
| `FEATURE_ROYXATIM` | "📺 Mening ro'yxatim" |
| `FEATURE_ULASHISH` | "🔗 Ulashish" — deeplink havola |
| `FEATURE_JANR` | "🏷 Janrlar" |
| `FEATURE_OBUNA` | majburiy obuna (`OBUNA_KANALLAR`) |
| `FEATURE_AVTOPOST` | yangi serial/qismni kanalga e'lon (`POST_CHANNEL_ID`) |
| `FEATURE_ZAXIRA` | bazani davriy zaxiralash |
| `FEATURE_ANTIFLOOD` | tez bosishdan himoya |
| `FEATURE_KANAL_IMPORT` | kanalga tashlangan videoni caption bo'yicha avtomatik qo'shish |
| `FEATURE_FUZZY` | xato yozilsa ham topadigan qidiruv |
| `FEATURE_BUYRUQLAR` | Telegram "/" menyusi |
| `FEATURE_INLINE` | boshqa chatda `@bot <nom>` |
| `FEATURE_JURNAL` | xatolar log kanaliga (`LOG_CHANNEL_ID`) |
| `FEATURE_SQLITE_FSM` | restartdan keyin kontekst saqlanadi |
| `FEATURE_KORILGAN` | ko'rilgan qismga ✓ |
| `FEATURE_QIDIRUV_JURNALI` | nima qidirilgan-u topilmagan |
| `FEATURE_KUZATISH` | 🔔 kuzatish, yangi qismda xabar |
| `FEATURE_FASL` | fasl (season) |
| `FEATURE_TUR` | kino va serialni ajratish |
| `FEATURE_MANBA` | `?start=ref_<manba>` — reklama manbasi |
| `FEATURE_QISM_ALMASH` | qism videosini almashtirish |
| `FEATURE_REJA` | rejalashtirilgan tarqatish |
| `FEATURE_BAHO` | 👍/👎 va ⭐ eng yaxshilar |
| `FEATURE_KASHFIYOT` | 🎲 tasodifiy, 🆕 yangilar |
| `FEATURE_TIL` | uz/ru (qisman tarjima) |
| `FEATURE_CSV` | CSV import/eksport |

## Havolalar (deeplink)

- `t.me/<bot>?start=serial_<id>` — serial kartochkasi
- `t.me/<bot>?start=qism_<id>_<n>` — to'g'ridan-to'g'ri qism
- `t.me/<bot>?start=ref_<manba>` — reklama manbasini sanash (FEATURE_MANBA)

## Kanal importi (FEATURE_KANAL_IMPORT)

Arxiv kanalga videoni tashlab, captionga yozasiz:

```
Spartak | 5          5-qism
Spartak | 2x5        2-fasl, 5-qism
Spartak | 5 | Nomi   qism nomi bilan
Avatar               kino (FEATURE_TUR yoqiq bo'lsa)
```

Serial bazada bo'lmasa, o'zi yaratiladi.

## Sinovlar

```bash
python tests/run.py
```

Loyiha tuzilishi va yangi modul qo'shish qoidasi: [CLAUDE.md](CLAUDE.md).
