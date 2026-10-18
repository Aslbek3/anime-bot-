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
  yuklash.py     FEATURE_YUKLASH: link -> navbat -> arxiv kanal
  taklif.py      FEATURE_TAKLIF: user taklifi -> admin tasdig'i
  bildirishnoma.py FEATURE_BILDIRISHNOMA: yangi qism -> tomoshabinlarga (routersiz)
  qism_raqam.py  FEATURE_RAQAM: "45" deb yozsa 45-qism
  royxatim.py    FEATURE_ROYXATIM: "Mening ro'yxatim"
  ulashish.py    FEATURE_ULASHISH: serial/qism havolasi
  janrlar.py     FEATURE_JANR: janr bo'yicha ro'yxat
  obuna.py       FEATURE_OBUNA: majburiy obuna (middleware + router)
  avtopost.py    FEATURE_AVTOPOST: kanalga e'lon (routersiz)
  zaxira.py      FEATURE_ZAXIRA: bazani zaxiralash (faqat startup ilgagi)
  kanal_import.py FEATURE_KANAL_IMPORT: arxiv kanal captionidan avtomatik qo'shish
  buyruqlar.py   FEATURE_BUYRUQLAR: "/" menyusi (setMyCommands)
  inline.py      FEATURE_INLINE: inline rejim (@bot <nom>)
  jurnal.py      FEATURE_JURNAL: xatolar va hodisalar log kanali
  qidiruv_jurnali.py FEATURE_QIDIRUV_JURNALI: topilmagan so'rovlar
  kuzatish.py    FEATURE_KUZATISH: 🔔 kuzatish (sevimlilar)
  baho.py        FEATURE_BAHO: 👍/👎 va eng yaxshilar
  kashfiyot.py   FEATURE_KASHFIYOT: tasodifiy / yangilar
  fasl.py        FEATURE_FASL: fasl (season)
  tur.py         FEATURE_TUR: kino va serialni ajratish
  til.py         FEATURE_TIL: uz/ru (cheklovi bilan — pastga qarang)
  manba.py       FEATURE_MANBA: ?start=ref_<manba> kuzatuvi
  qism_almash.py FEATURE_QISM_ALMASH: qism videosini almashtirish
  reja.py        FEATURE_REJA: rejalashtirilgan tarqatish
  csv_almash.py  FEATURE_CSV: CSV import/eksport
fuzzy.py         FEATURE_FUZZY: xatoga chidamli qidiruv (routersiz)
korilgan.py      FEATURE_KORILGAN: ko'rilgan qismga ✓ (routersiz)
storage.py       FEATURE_SQLITE_FSM: FSM holatini SQLite da saqlash
parsers/
  base.py        parser shartnomasi (qidir / yuklab_ol)
  namuna.py      namuna parser — ishlamaydi, NotImplementedError
tests/
  run.py         hamma sinovni uchta bayroq holatida ishga tushiradi
  test_ochiq.py  bayroqlar o'chiq — asosiy oqimlar
  test_yoqiq.py  yuklash + taklif
  test_hammasi.py  birinchi to'plam modullari yoqiq
  test_toplam2.py  ikkinchi to'plam modullari yoqiq
```

## Sinovlar

```bash
python tests/run.py
```

Uchta holat alohida jarayonda ishlaydi (bayroqlar import vaqtida o'qiladi),
baza vaqtinchalik papkada — `qogoz.db` ga tegilmaydi. Soxta Telegram sessiyasi
(`FakeSession`) API chaqiruvlarini ushlab qoladi, hech narsa tarmoqqa chiqmaydi.
**Har o'zgarishdan keyin shuni ishga tushiring.**

## Yangi modul qo'shish

1. `handlers/<nom>.py` yarating va unda `router = Router(name="<nom>")` e'lon qiling.
2. `main.py` dagi `ROUTERS` ro'yxatiga modulni qo'shing — **bitta qator**.

Tartib muhim: `admin` birinchi turadi — uning ekranlaridagi tugmalar (masalan
`🎬 <nom>` yoki `⬅️`) user handlerlariga tushib ketmasligi uchun. `qidiruv` esa
har doim oxirgi: u boshqa hech kim olmagan matnni qidiruv deb qabul qiladi.

## Modul bayroqlari

Hammasi `config.py` da, `.env` dan o'qiladi, standarti `false`:

| Bayroq | Fayl | Nima qiladi |
|---|---|---|
| `FEATURE_YUKLASH` | `handlers/yuklash.py` | saytdan yuklab arxiv kanalga saqlash |
| `FEATURE_TAKLIF` | `handlers/taklif.py` | user taklifi + admin tasdig'i |
| `FEATURE_BILDIRISHNOMA` | `handlers/bildirishnoma.py` | yangi qism chiqqanda tomoshabinlarga xabar |
| `FEATURE_RAQAM` | `handlers/qism_raqam.py` | qism raqamini yozib o'tish |
| `FEATURE_ROYXATIM` | `handlers/royxatim.py` | "Mening ro'yxatim" |
| `FEATURE_ULASHISH` | `handlers/ulashish.py` | serial/qism havolasini ulashish |
| `FEATURE_JANR` | `handlers/janrlar.py` | janr bo'yicha ro'yxat |
| `FEATURE_OBUNA` | `handlers/obuna.py` | majburiy obuna (`OBUNA_KANALLAR` kerak) |
| `FEATURE_AVTOPOST` | `handlers/avtopost.py` | kanalga e'lon (`POST_CHANNEL_ID` kerak) |
| `FEATURE_ZAXIRA` | `handlers/zaxira.py` | bazani davriy zaxiralash |
| `FEATURE_ANTIFLOOD` | `middlewares.py` | tez bosishdan himoya |
| `FEATURE_KANAL_IMPORT` | `handlers/kanal_import.py` | kanal captionidan avtomatik qo'shish |
| `FEATURE_FUZZY` | `fuzzy.py` | xatoga chidamli qidiruv |
| `FEATURE_BUYRUQLAR` | `handlers/buyruqlar.py` | "/" menyusi |
| `FEATURE_INLINE` | `handlers/inline.py` | inline rejim |
| `FEATURE_JURNAL` | `handlers/jurnal.py` | xatolar + hodisalar jurnali (`LOG_CHANNEL_ID`) |
| `FEATURE_SQLITE_FSM` | `storage.py` | FSM holati restartdan keyin saqlanadi |
| `FEATURE_KORILGAN` | `korilgan.py` | ko'rilgan qismga ✓ |
| `FEATURE_QIDIRUV_JURNALI` | `handlers/qidiruv_jurnali.py` | topilmagan so'rovlar ro'yxati |
| `FEATURE_KUZATISH` | `handlers/kuzatish.py` | 🔔 kuzatish, bildirishnoma shularga |
| `FEATURE_FASL` | `handlers/fasl.py` | fasl (season) |
| `FEATURE_TUR` | `handlers/tur.py` | kino / serial ajratuvi |
| `FEATURE_MANBA` | `handlers/manba.py` | `?start=ref_<manba>` kuzatuvi |
| `FEATURE_QISM_ALMASH` | `handlers/qism_almash.py` | qism videosini almashtirish |
| `FEATURE_REJA` | `handlers/reja.py` | rejalashtirilgan tarqatish |
| `FEATURE_BAHO` | `handlers/baho.py` | 👍/👎 va eng yaxshilar |
| `FEATURE_KASHFIYOT` | `handlers/kashfiyot.py` | tasodifiy / yangilar |
| `FEATURE_TIL` | `handlers/til.py` | uz/ru (qisman) |
| `FEATURE_CSV` | `handlers/csv_almash.py` | CSV import/eksport |

Bayroq o'chiq bo'lsa:

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

**Oddiy modullar** (`FEATURE_RAQAM`, `FEATURE_ROYXATIM`, `FEATURE_ULASHISH`,
`FEATURE_JANR`, `FEATURE_BILDIRISHNOMA`, `FEATURE_ANTIFLOOD`): `.env` da `true`
qilib, botni qayta ishga tushiring — boshqa sozlama kerak emas.

**FEATURE_OBUNA:** `OBUNA_KANALLAR=@kanal1,@kanal2` (bot o'sha kanallarda
admin bo'lishi shart). Tekshirib bo'lmasa (bot admin emas) foydalanuvchi
bloklanmaydi — ataylab shunday, hammani qamab qo'ymaslik uchun.

**FEATURE_AVTOPOST:** `POST_CHANNEL_ID=-100...`, bot o'sha kanalda admin.

**FEATURE_ZAXIRA:** `ZAXIRA_SOAT` (standart 24) va `ZAXIRA_SAQLASH` (7).
Nusxalar `backup/` ga tushadi, eskilari avtomatik o'chadi.

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

## Ikkinchi to'plam: diqqat qiladigan joylar

**Kanal import** (`FEATURE_KANAL_IMPORT`) — arxiv kanaldagi video captioni:

```
Spartak | 5          -> Spartak serialining 5-qismi
Spartak | 2x5        -> 2-fasl, 5-qism
Spartak | 5 | Nomi   -> qism nomi bilan
Avatar               -> FEATURE_TUR yoqiq bo'lsa: kino (bitta qism)
```

Serial topilmasa o'zi yaratiladi. Caption formatga tushmasa — tegilmaydi.

**Fasl va yagonalik kaliti.** `episodes` jadvalining UNIQUE kaliti
`(serial_id, fasl, qism_raqami)`. Eski bazalarda u `(serial_id, qism_raqami)`
edi va 2-faslning 1-qismi 1-faslnikini ustiga yozib yuborardi; `db.migratsiya()`
jadvalni qayta qurib, ma'lumotni ko'chiradi (`_episodes_kaliti`). Shuning uchun
`get_episode`, `prev_next_episode`, `episode_page` larga ixtiyoriy `fasl`
parametri berilgan: `None` bo'lsa raqam bo'yicha birinchi mos qism olinadi.

**Kino va serial** (`FEATURE_TUR`) — farq faqat `serials.turi` ustunida
('kino' / 'serial', standart 'serial'). Kino kartochkasida qismlar ro'yxati
o'rniga bitta "▶️ Ko'rish" tugmasi chiqadi.

**Til** (`FEATURE_TIL`) — bu TO'LIQ i18n emas: tugma matnlari o'zbekcha qoladi,
chunki routing aynan matn bo'yicha ketadi. Hozircha salomlashuv va bir nechta
asosiy xabar tarjima qilinadi (`handlers/til.py` dagi `TARJIMA`). To'liq i18n
uchun tugmalarni kalit bo'yicha yo'naltirish kerak — alohida ish.

**Qidiruv jurnali** — har bir qidiruv `qidiruvlar` jadvaliga yoziladi.
Admin paneldagi "🔎 So'ralganlar" eng ko'p so'ralgan, lekin topilmagan
so'rovlarni ko'rsatadi; bu kontent rejasi uchun eng foydali ro'yxat.

**SQLite FSM** (`FEATURE_SQLITE_FSM`) — aiogram da tayyor SQLite storage yo'q,
shuning uchun `storage.py` da BaseStorage ning ixcham amalga oshirilishi bor
(`fsm` jadvali). Yoqilsa, restartdan keyin ham nav konteksti saqlanadi va
"eskirgan ekran" xabari deyarli chiqmaydi.

**Bir nechta admin** — `.env` da `ADMIN_IDS=111,222`. `AdminOnly` middleware
shu ro'yxat bo'yicha tekshiradi; bildirishnoma/zaxira kabi xabarlar esa asosiy
`ADMIN_ID` ga ketadi.

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
- `qism_<serial_id>_<n>` — to'g'ridan-to'g'ri o'sha qism videosi;
- `ref_<manba>` — reklama manbasini sanaydi (FEATURE_MANBA), so'ng asosiy menyu.

Noto'g'ri yoki ko'rinmaydigan (tasdiqlanmagan) payload bo'lsa asosiy menyu
ochiladi. Havolani admin panelidan olish mumkin: serialni tahrirlash
ekranida "🔗 Havola". Havola `ui.havola(bot, payload)` bilan yasaladi.

## Doimiy yoqiq yaxshilanishlar (bayroqsiz)

Bular tuzatish/mayda yaxshilanish bo'lgani uchun bayroqqa bog'lanmagan:

- **Eskirgan ekran** — bot qayta ishga tushsa `nav_*` konteksti yo'qoladi.
  Avval eski tugma qidiruvga tushib "topilmadi" deyilardi; endi `kino.py`
  oxiridagi `eskirgan_ekran` handleri (`ui.ekran_yoq()` filtri bilan) uni
  ushlab, asosiy menyuni qaytaradi.
- **`upload_video` holati** — video yuborishdan oldin ko'rsatiladi.
- **Qidiruv natijalari sahifalanadi** (`nav_soz` + `nav_page`).
- **Migratsiya** — `db.migratsiya()` yetishmayotgan ustunlarni avtomatik
  qo'shadi (`YANGI_USTUNLAR` lug'ati), `init_db()` da chaqiriladi.
- **`users.faol`** — tarqatish/bildirishnomada bloklaganlar belgilanadi,
  keyingi yuborishlarda ular o'tkazib yuboriladi, statistikada ko'rinadi.

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

**2026-10-17 — qulaylik va funksionallik to'plami**
- 9 ta yangi modul, har biri alohida fayl va alohida bayroq (hammasi `false`):
  bildirishnoma, qism_raqam, royxatim, ulashish, janrlar, obuna, avtopost,
  zaxira, antiflood.
- Bayroqsiz tuzatishlar: eskirgan ekran, `upload_video`, qidiruv sahifalash,
  avtomatik migratsiya, `users.faol` bayrog'i.
- `tests/` repoga ko'chirildi: `python tests/run.py` — uchta bayroq holati.

**2026-10-18 — ikkinchi to'plam: 18 ta modul**
- Foydalanuvchi: ko'rilgan ✓, kuzatish (sevimlilar), baho va eng yaxshilar,
  tasodifiy/yangilar, janr emas — kino/serial ajratuvi, fasl, til (qisman),
  chidamli qidiruv, inline rejim, "/" menyusi.
- Admin: kanaldan avtoimport, qidiruv jurnali ("so'ralgan, topilmagan"),
  manba kuzatuvi, qism almashtirish, rejalashtirilgan tarqatish, CSV
  import/eksport, xatolar jurnali, zaxirani adminga yuborish, bir nechta admin.
- Barqarorlik: SQLite FSM storage, `episodes` yagonalik kaliti
  `(serial_id, fasl, qism_raqami)` ga ko'chirildi (ma'lumot yo'qolishi
  tuzatildi), `db.migratsiya()` jadvalni o'zi qayta quradi.
- `tests/test_toplam2.py` qo'shildi; `python tests/run.py` endi 4 holatni
  tekshiradi.
