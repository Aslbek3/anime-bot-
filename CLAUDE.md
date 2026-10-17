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
  kino.py        /start, deeplink, asosiy menyu, serial kartochkasi, qism yuborish
  qidiruv.py     erkin matn -> LIKE qidiruv
  murojat.py     user -> admin xabar, admin reply -> user javob
  admin.py       admin panel (FSM: serial, qism, tahrir, tarqatish)
  yuklash.py     FEATURE_YUKLASH: link -> navbat -> arxiv kanal (o'chiq)
  taklif.py      FEATURE_TAKLIF: user taklifi -> admin tasdig'i (o'chiq)
parsers/
  base.py        parser shartnomasi (qidir / yuklab_ol)
  namuna.py      namuna parser — ishlamaydi, NotImplementedError
```

## Yangi modul qo'shish

1. `handlers/<nom>.py` yarating va unda `router = Router(name="<nom>")` e'lon qiling.
2. `main.py` dagi `ROUTERS` ro'yxatiga modulni qo'shing — **bitta qator**.

Tartib muhim: `admin` birinchi turadi — uning ekranlaridagi tugmalar (masalan
`🎬 <nom>` yoki `⬅️`) user handlerlariga tushib ketmasligi uchun. `qidiruv` esa
har doim oxirgi: u boshqa hech kim olmagan matnni qidiruv deb qabul qiladi.

## Modul bayroqlari

`config.py` dagi `FEATURE_YUKLASH` va `FEATURE_TAKLIF` (.env dan o'qiladi,
standart `false`). Bayroq o'chiq bo'lsa:

- `main.py` modulni **import ham qilmaydi** va routerni ulamaydi;
- `ui.main_menu_kb()` va `admin.menu_kb()` mos tugmani chizmaydi.

Shu sababli o'chiq modul mavjud ishlashga umuman tegmaydi — yangi bog'liqlik
(masalan `yt-dlp`) ham yuklanmaydi.

### Yoqish tartibi

**FEATURE_TAKLIF:**
1. `.env` da `FEATURE_TAKLIF=true`.
2. Botni qayta ishga tushiring (`pm2 restart qogoz-bot`).
3. Tekshiring: `/start` da "➕ Kino taklif qilish", admin panelda "📥 Takliflar".
   Yangi jadval kerak emas — `serials` dagi `holat`, `qoshgan_user_id`,
   `manba_url` ustunlari ishlatiladi.

**FEATURE_YUKLASH:**
1. `pip install -r requirements.txt` (yt-dlp kerak bo'ladi).
2. Aniq sayt uchun parser yozing: `parsers/<sayt>.py` — `base.py` dagi
   `qidir(nom)` va `yuklab_ol(url, fayl_yoli)` shartnomasi bo'yicha.
3. `handlers/yuklash.py` dagi bitta importni almashtiring:
   `from parsers import namuna as parser` -> `from parsers import <sayt> as parser`.
4. `.env` da `FEATURE_YUKLASH=true`, kerak bo'lsa `TMP_DIR` ni ko'rsating.
5. Botni qayta ishga tushiring: startupda navbat ishchisi avtomatik yonadi.

Namuna parser ataylab `NotImplementedError` qaytaradi: bayroq yoqilsa-yu
parser yozilmagan bo'lsa, vazifa `holat='xato'` bo'lib yoziladi, navbat
to'xtamaydi.

## Yuklash navbati

`yuklash_navbat` jadvali: `manba_url`, `holat`
(navbatda/yuklanmoqda/tayyor/xato), `kanal_msg_id`, `xato_matni`.

- Kesh: shu URL bo'yicha `holat='tayyor'` yozuv bo'lsa qayta yuklanmaydi,
  bazadagi `kanal_msg_id` ishlatiladi.
- Fon vazifasi `router.startup` da ishga tushadi va **bir vaqtda bitta**
  yuklaydi. Parser sinxron bo'lgani uchun `asyncio.to_thread` ichida
  chaqiriladi. Yuklangan fayl arxiv kanalga yuborilgach `TMP_DIR` dan
  darhol o'chiriladi (`finally` bloki).
- Bot qayta ishga tushganda `navbat_tiklash()` yarim qolgan
  'yuklanmoqda' yozuvlarni 'navbatda' ga qaytaradi.

## Deeplink

`t.me/<bot>?start=<payload>` — `handlers/kino.py` dagi
`CommandStart(deep_link=True)` handleri (oddiy `/start` dan OLDIN turadi):

- `serial_<id>` — serial kartochkasi;
- `qism_<serial_id>_<n>` — to'g'ridan-to'g'ri o'sha qism videosi.

Noto'g'ri yoki ko'rinmaydigan (tasdiqlanmagan) payload bo'lsa asosiy menyu
ochiladi. Havolani admin panelidan olish mumkin: serialni tahrirlash
ekranida "🔗 Havola". Havola `ui.havola(bot, payload)` bilan yasaladi.

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
  🏠 asosiy menyu tugmasi bor. Bot hech qachon xabar o'chirmaydi —
  na foydalanuvchinikini, na o'zinikini: yozishma oddiy chatdek ketadi.
- **Klaviatura faqat o'zgarganda yuboriladi** — `ui.screen()` `kb_if_new()`
  orqali oxirgi yuborilgan klaviatura imzosini (`kb_imzo`) solishtiradi va
  bir xil bo'lsa `reply_markup` ni umuman qo'shmaydi. Telegram bunday holda
  mavjud klaviaturani o'z joyida qoldiradi, shuning uchun tugmalar
  yopilib-ochilmaydi. Xabarni `message.answer(...)` bilan to'g'ridan-to'g'ri
  yubormang — `ui.screen()` dan o'ting, aks holda klaviatura bekorga qayta chiziladi.
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

Jadvallar: yuqoridagilarga qo'shimcha `yuklash_navbat` (FEATURE_YUKLASH).

`serials.manba_url`, `serials.qoshgan_user_id`, `serials.holat` ustunlarini
`taklif` moduli ishlatadi. `holat` bo'yicha muhim qoida: foydalanuvchiga
ko'rinadigan seriallar sharti `db.KORINADI` konstantasida —
`holat IS NULL OR holat = '' OR holat = 'tasdiqlangan'` (eski yozuvlarda
holat bo'sh bo'lishi mumkin). Foydalanuvchiga serial qaytaradigan har bir
yangi so'rovga shu shartni qo'shing.

Migratsiya mexanizmi yo'q: sxema `CREATE TABLE IF NOT EXISTS` bilan yaratiladi.
Yangi ustun kerak bo'lsa `SCHEMA` ga qo'shing va mavjud bazaga qo'lda
`ALTER TABLE ... ADD COLUMN` qiling.

## Murojaat javobi

Botdan adminga ketgan xabar matnida `#m<id>` belgisi bo'ladi. Admin o'sha xabarga
reply qilsa, `handlers/murojat.py` dagi `admin_javobi` filtri id ni ajratib oladi
va javobni userga yuboradi. Shuning uchun murojaat xabarlaridan `#m<id>` ni olib
tashlamang.

## Qilingan ishlar

**2026-10-17 — loyiha noldan qurildi**
- aiogram 3 + aiosqlite + PM2 skeleti: `main.py`, `config.py`, `db.py`, `ui.py`,
  `middlewares.py` va 4 ta handler moduli (kino, qidiruv, murojat, admin).
- Baza: 5 jadval (`serials`, `episodes`, `users`, `progress`, `murojat`).
  `manba_url`, `qoshgan_user_id`, `holat` ustunlari kelajak uchun bo'sh qoldirildi.
- Foydalanuvchi qismi: davom ettirish tugmasi, 8 tadan sahifalangan ro'yxat,
  serial kartochkasi (poster + tavsif + qismlar), arxiv kanaldan `copy_message`
  bilan video, progress yozuvi, LIKE qidiruv, murojaat oqimi.
- Admin panel: serial qo'shish FSM, forward orqali qism qo'shish,
  tahrirlash/o'chirish, statistika, chunked tarqatish, murojatlar.
- `.env.example`, `requirements.txt`, `ecosystem.config.js`, `README.md`.

**2026-10-17 — interfeys to'liq reply tugmalarga o'tkazildi**
- Inline tugmalar va callback data butunlay olib tashlandi (foydalanuvchi talabi).
- Callback o'rniga ekran konteksti FSM da: `nav_ekran`, `nav_page`, `nav_serial`,
  `nav_qism`. Bir xil tugma (`⬅️`, `🎬 <nom>`) turli ekranda turlicha ishlashi
  `ui.ekran(...)` filtri orqali hal qilindi.
- Router tartibi `admin → kino → murojat → qidiruv` ga o'zgardi: admin ekranidagi
  tugmalar user handlerlariga tushib ketmasligi uchun.
- Serial tugmasida id yo'q, shuning uchun `db.get_serial_by_name()` qo'shildi.

**2026-10-17 — navigatsiya "sakrashi" tuzatildi**
- Avvalgi versiya har bosishda eski ekranni va foydalanuvchi xabarini o'chirib,
  yangisini chizar edi — noqulay bo'ldi, butunlay olib tashlandi.
- `ui.kb_if_new()` qo'shildi: klaviatura imzosi (`kb_imzo`) bir xil bo'lsa
  `reply_markup` yuborilmaydi, Telegram esa mavjud klaviaturani joyida qoldiradi.

**Tekshirilgan**
Soxta Telegram sessiyasi bilan uchidan-uchiga sinov o'tkazildi (sinov fayli
repoda emas, vaqtinchalik papkada): /start, sahifalash, qism yuborish va
chekkadagi tugmalar, 📋 Qismlar, davom ettirish, qidiruv, murojaat → admin →
reply → userga javob, admin panelining barcha bo'limlari, oddiy userga admin
panel ko'rinmasligi, hech qanday xabar o'chirilmasligi.

**Ochiq ishlar**
- Repoda avtomatik test yo'q — o'zgartirgandan keyin qo'lda sinang.
- Tarqatishda bloklagan userlar faqat sanaladi; `users` da "faol" bayrog'i yo'q.
- MemoryStorage ishlatiladi: bot qayta ishga tushsa `nav_*` konteksti yo'qoladi
  (foydalanuvchi `/start` bossa tiklanadi).

**2026-10-17 — ikkita yangi modul (bayroq bilan o'chiq) va deeplink**
- `FEATURE_YUKLASH` / `FEATURE_TAKLIF` bayroqlari: o'chiq holatda modul import
  ham qilinmaydi, tugmalar ham chizilmaydi.
- `handlers/yuklash.py`: link -> `yuklash_navbat` -> fon ishchisi (bir vaqtda
  bitta) -> arxiv kanal; URL bo'yicha kesh; xato navbatni to'xtatmaydi.
  `parsers/base.py` shartnomasi va ishlamaydigan `parsers/namuna.py`.
- `handlers/taklif.py`: user taklifi `serials` ga `holat='kutilmoqda'` bilan
  tushadi, admin tasdiqlaydi/rad etadi, kuniga 3 ta limit. Foydalanuvchi
  so'rovlariga `db.KORINADI` sharti qo'shildi.
- Deeplink: `?start=serial_<id>` va `?start=qism_<id>_<n>`; admin tahrir
  ekranida "🔗 Havola" tugmasi.
- O'zgartirishdan oldin `backup/` ga baza va asosiy fayllar nusxasi olindi.
- Sinov: ikkala bayroq holatida ham uchidan-uchiga test o'tkazildi — o'chiq
  holatda eski oqimlar avvalgidek, yangi tugmalar ko'rinmaydi.
