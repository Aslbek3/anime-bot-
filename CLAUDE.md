# CLAUDE.md

Telegram bot (aiogram 3 + aiosqlite). Kod oddiy va tekis bo'lsin:
ortiqcha abstraksiya, servis/repozitoriy qatlamlari, DI konteynerlari — kerak emas.

## Tuzilishi

```
main.py          kirish nuqtasi, ROUTERS ro'yxati, middleware ulanishi
config.py        .env dan sozlamalar (BOT_TOKEN, ADMIN_ID, ARCHIVE_CHANNEL_ID, sahifa o'lchamlari)
db.py            SQLite: SCHEMA + barcha so'rovlar (bitta ochiq ulanish)
ui.py            reply tugmalar (matn konstantalari, pager, menyular) va `screen()` — ekran chizish
middlewares.py   ActivityMiddleware (user yozish), AdminOnly (admin filtri)
handlers/
  kino.py        /start, asosiy menyu, serial kartochkasi, qism yuborish
  qidiruv.py     erkin matn -> LIKE qidiruv
  murojat.py     user -> admin xabar, admin reply -> user javob
  admin.py       admin panel (FSM: serial, qism, tahrir, tarqatish)
```

## Yangi modul qo'shish

1. `handlers/<nom>.py` yarating va unda `router = Router(name="<nom>")` e'lon qiling.
2. `main.py` dagi `ROUTERS` ro'yxatiga modulni qo'shing — **bitta qator**.

Tartib muhim: `admin` birinchi turadi — uning ekranlaridagi tugmalar (masalan
`🎬 <nom>` yoki `⬅️`) user handlerlariga tushib ketmasligi uchun. `qidiruv` esa
har doim oxirgi: u boshqa hech kim olmagan matnni qidiruv deb qabul qiladi.

## Konvensiyalar

- **Faqat reply tugmalar** — inline tugma ishlatilmaydi. Tugma bosilishi oddiy
  matn xabari bo'lib keladi, shuning uchun routing `ui.py` dagi matn
  konstantalari bo'yicha ketadi (`ui.HOME`, `ui.NEXT`, `ui.SERIAL_PREFIX`, ...).
  Yangi tugma qo'shsangiz, matnini `ui.py` da konstanta qilib e'lon qiling —
  handlerda matnni qo'lda yozmang.
- **Ekran konteksti** — callback data yo'q, shuning uchun joriy ekran FSM
  ma'lumotida saqlanadi: `nav_ekran`, `nav_page`, `nav_serial`, `nav_qism`,
  `nav_msg`. `ui.set_nav()` bilan yoziladi, `ui.ekran("serials", ...)` filtri
  bilan o'qiladi — bir xil tugma (`⬅️`, `➡️`, `🎬 <nom>`) turli ekranlarda
  turlicha ishlashi shu orqali hal qilinadi. `state.clear()` ishlatmang
  (u `nav_*` ni ham o'chiradi) — `state.set_state(None)` yetarli.
- **Navigatsiya** — tupik ekran bo'lmaydi: har bir ekranda orqaga yoki
  🏠 asosiy menyu tugmasi bor. Reply tugmada xabarni edit qilib bo'lmagani
  uchun `ui.screen()` oldingi ekranni va foydalanuvchi bosgan tugma xabarini
  o'chirib, yangisini yuboradi — chatda bitta faol ekran qoladi.
  Tarqatish uchun yuborilgan xabar o'chirilmaydi (`incoming=False`).
- **Videolar** `file_id` orqali saqlanmaydi (u bot tokeniga bog'langan).
  `episodes.kanal_msg_id` da arxiv kanaldagi `message_id` turadi, yuborishda
  `bot.copy_message(from_chat_id=ARCHIVE_CHANNEL_ID, ...)` ishlatiladi.
  Poster esa oddiy `file_id` — uni bot o'zi yuklaydi, shuning uchun muammo yo'q.
- **Admin tekshiruvi** faqat `AdminOnly` middleware orqali. U admin bo'lmasa
  `UNHANDLED` qaytaradi — shunda update keyingi routerlarga o'tib ketadi.
- **Matn** HTML parse_mode da. Bazadan kelgan qiymatlarni `ui.esc()` bilan o'rang.
- **Til** — interfeys va o'zgaruvchi nomlari o'zbekcha.

## Baza

Jadvallar: `serials`, `episodes`, `users`, `progress`, `murojat` (sxema `db.py` da).

`serials.manba_url`, `serials.qoshgan_user_id`, `serials.holat` ustunlari
**ataylab ishlatilmaydi** — keyingi funksiyalar (user tomonidan serial taklif qilish,
moderatsiya) uchun joy. O'chirmang.

Migratsiya mexanizmi yo'q: sxema `CREATE TABLE IF NOT EXISTS` bilan yaratiladi.
Yangi ustun kerak bo'lsa `SCHEMA` ga qo'shing va mavjud bazaga qo'lda
`ALTER TABLE ... ADD COLUMN` qiling.

## Murojaat javobi

Botdan adminga ketgan xabar matnida `#m<id>` belgisi bo'ladi. Admin o'sha xabarga
reply qilsa, `handlers/murojat.py` dagi `admin_javobi` filtri id ni ajratib oladi
va javobni userga yuboradi. Shuning uchun murojaat xabarlaridan `#m<id>` ni olib
tashlamang.
