# Himoyaga tayyorgarlik (Defense notes)

Har bir bosqichda nima qilinganini, nima uchun shunday qilinganini va savol-javoblarni shu yerda yig'amiz.

---

## Step A — Repo strukturasi va config

### Fayllar

- **`config/sources.json`**: barcha manbalarning **yagona manbasi** (single source of truth): URL'lar, taxi oylari, koordinatalar, pollutantlar, jadval nomlari. Uni Pipeline (Lookup activity) ham, notebook'lar ham, lokal testlar ham o'qiydi. Kodda hech qanday URL yoki jadval nomi qattiq yozilmaydi (no hard-coded literals).
- **`.gitignore`**: `.env` (kalit), `data/` (yuklangan fayllar) va `.venv/` Git'ga tushmaydi.
- **`.env` / `.env.example`**: lokal sir (secret) `.env` da turadi. `.env.example` esa faqat kalit nomini ko'rsatadi, qiymatsiz.
- **`drafts/`**: Fabric hali yo'qligi uchun library funksiyalari vaqtincha shu yerda yoziladi. Fabric'da notebook yaratilgach, kod u yerga bir marta ko'chiriladi va draft o'chiriladi.
- **`fabric/`**: Fabric Git integration papkasi. Fabric item'larni (`*.Notebook`, `*.DataPipeline`) o'zi shu yerga yozadi.
- **`docs/`**: data dictionary, lineage (Mermaid), governance.

### Nega JSON, YAML emas?
Pipeline **Lookup** activity JSON'ni o'qiy oladi, YAML'ni o'qiy olmaydi. Bitta formatda bitta fayl bo'lsa, hamma uni bir xil o'qiydi va ikki nusxa yuzaga kelmaydi.

### Config Fabric'ga qanday yetib boradi?
Fabric Git Lakehouse `Files/` papkasini sinxronlamaydi. Shuning uchun pipeline'ning birinchi qadami (Copy activity) public repo'dan `https://raw.githubusercontent.com/azizbekb/fabric-nyc-analytics/main/config/sources.json` ni oladi va Lakehouse `Files/config/` ga yozadi. Keyin Lookup va notebook'lar shu faylni o'qiydi. Natijada faylning yagona joyi Git bo'lib qoladi, qo'lda nusxa ko'chirish yo'q.
E'tibor bering: pipeline GitHub'dagi `main` branch'ni o'qiydi. Config o'zgarsa, avval **push** qiling, keyin pipeline'ni ishga tushiring.

### Nega config-driven? (Extendability)
Yangi oy qo'shish uchun `months` ro'yxatiga 1 ta qator qo'shiladi. Yangi manba (masalan, weather) qo'shish uchun 1 ta JSON blok + 1 ta library notebook + 1 ta Gold jadval yetarli. Mavjud kod o'zgarmaydi.

### Kod Fabric'da qanday ishlaydi: `%run` (B variant)

Uchta variantni solishtirdik:

| Variant | Kamchiligi |
|---|---|
| Wheel (`.whl`) + Environment | Har o'zgarishda build, upload va Environment **publish** (bir necha daqiqa) kerak. Live change uchun sekin |
| Lakehouse Files + `sys.path` | Fabric Git Lakehouse fayllarini sinxronlamaydi, natijada qo'lda yuklangan ikkinchi nusxa paydo bo'ladi |
| **`%run` + library notebook** ✅ | Git sinxronlaydi, o'zgarish darhol ishlaydi, nusxa bitta |

**`%run` qanday ishlaydi:**
- Ishchi notebook'da (worker notebook) `%run nb_lib_taxi` yozilsa, `nb_lib_taxi` **o'sha Spark sessiyada** bajariladi va uning funksiyalari chaqiruvchi notebook ichida paydo bo'ladi. Bu xuddi kodni nusxalab qo'yganday ishlaydi.
- `%run` **o'z cell'ida yolg'iz** turishi kerak (bitta cell = faqat `%run`).
- Chaqirilayotgan notebook **shu workspace'da** bo'lishi kerak.

**Qoidalar:**
- Library notebook'larda faqat **sof funksiyalar** (pure functions) bo'ladi. Import paytida hech narsa bajarilmaydi (no side effects) va `spark` yoki `notebookutils` chaqirilmaydi.
- `spark` sessiyasi va `notebookutils` faqat ishchi notebook'larda ishlatiladi. Shuning uchun funksiyalarni lokal Spark bilan test qilish mumkin.
- Lokal testlar `notebook-content.py` faylini (yoki u hali yo'q bo'lsa, draft `.py` ni) `importlib.util.spec_from_file_location` bilan yuklaydi. `notebook-content.py` oddiy Python fayl: Fabric faqat `# CELL`, `# METADATA` kabi **izoh** qatorlarini qo'shadi. Demak, `src/` da ikkinchi nusxa kerak emas.

### Asosiy tushunchalar
- **Medallion architecture**: Bronze (xom ma'lumot, o'zgarishsiz) → Silver (tozalangan, tiplangan) → Gold (biznes uchun model, star schema).
- **Single source of truth**: har bir ma'lumot (config, kod) faqat bir joyda turadi.
- **Secrets management**: kalit Git'ga hech qachon tushmaydi.

### Ehtimoliy savollar
1. **Nega config JSON'da?** Pipeline Lookup JSON'ni o'qiydi, YAML'ni emas. Natijada bitta format va bitta fayl.
2. **Yangi oy qanday qo'shiladi?** `config/sources.json` → `taxi.months` ga qator qo'shiladi, kod o'zgarmaydi.
3. **Nega wheel emas?** Har o'zgarishda Environment publish kerak, sekin. `%run` darhol ishlaydi va Git bilan sinxron.
4. **API kalit qayerda?** Lokal `.env` da (git-ignored). Fabric'da qayerda turishini Phase 1'da hal qilamiz.
5. **Library notebook'da nega `spark` yo'q?** Funksiyalar sof bo'lishi uchun, shunda ularni lokal test qilish mumkin. Sessiyani ishchi notebook beradi.

### Live change mashqlari
1. **Yangi taxi oyi qo'shish:** `config/sources.json` → `"months"` ga `"2024-07"` qo'shing → commit + push → Fabric'da Source control → **Update all** → pipeline'ni ishga tushiring.
2. **Yangi pollutant qo'shish:** `openaq.parameters` ga masalan `"pm10"` qo'shing → commit + push → Update all → dataflow va silver notebook'ni ishga tushiring.
3. **Yangi manba qo'shish:** `config/sources.json` ga yangi blok qo'shing (`type`, `url`, `bronze_table`, `silver_table`, `library`) → yangi `nb_lib_<name>` notebook yarating → Gold jadval qo'shing.

---

## Step B — Taxi ma'lumotini tahlil qilish (data profiling)

### Fayllar
- **`scripts/profile_taxi.py`**: bitta oylik taxi faylini lokal PySpark bilan tekshiradi va anomaliyalarni sanaydi. Fayl nomini config'dan oladi. Bu faqat tahlil uchun skript, Fabric'ga ko'chirilmaydi.
- **`docs/data_profile.md`**: natijalar (schema, null'lar, anomaliyalar sonlari) va Silver uchun taklif qilingan qoidalar.

### Eng muhim topilmalar (2024-01, 2 964 624 qator)
- **140 162 ta "bo'sh" qator**: 5 ta ustun bir vaqtda NULL va `payment_type = 0`. Vaqt, zona va pul ustunlari esa to'g'ri, demak bular haqiqiy safarlar. Ularni o'chirmaymiz, flag bilan saqlaymiz.
- **Void juftliklar (void pairs)**: 30 672 juft qator bor, ular bir xil safar bo'lib, +X va −X summalari yig'indisi 0 ga teng. Bu "to'lov olindi → bekor qilindi" degani. Faqat manfiy qatorni olib tashlasak, musbat qator qolib ketadi va ~30 ming safar va pul **ikki marta** hisoblanib qoladi. Shuning uchun **ikkala qatorni** `is_void` deb belgilaymiz va Gold'da hisoblamaymiz.
- **Oydan tashqari sanalar**: 2002, 2009, 2023-12-31 va 2024-02-01 sanalari, jami 18 qator. Ular grafikda soxta "kichik kunlar" hosil qiladi, shuning uchun quarantine'ga yuboramiz.
- **`trip_distance = 0`** (60 371): haqiqiy safarlar, saqlaymiz (lecturer qoidasi).
- **`Airport_fee`** katta harf bilan yozilgan. Turli oylarda ustun nomi farq qilishi mumkin, shuning uchun hamma ustun nomini snake_case'ga keltiramiz.

### Qoida: quarantine yoki flag?
- **Quarantine** (`reject_reason` bilan): qatorga ishonib bo'lmaydi, masalan noto'g'ri vaqt, juftligi yo'q manfiy summa, dublikat.
- **Flag** (Silver'da qoladi): qator haqiqiy safar, lekin hisob-kitobda ehtiyot bo'lish kerak, masalan `is_void`, `is_outlier`, `is_passenger_count_missing`.
- Har bir qator albatta **bittasiga** tushadi: Silver yoki quarantine. Hech narsa jim o'chirilmaydi (no silent drop).

### Asosiy tushunchalar
- **Data profiling**: ma'lumotni tozalashdan oldin uni sanab o'rganish. Qoidalarni taxmin bilan emas, raqamlar asosida yozamiz.
- **Natural key**: qatorni biznes ma'nosi bo'yicha aniqlaydigan ustunlar to'plami. Bu yerda: vendor, pickup vaqti, dropoff vaqti, PU zona, DO zona. Dublikat va void juftliklar shu kalit bo'yicha topildi.
- **`timestamp_ntz`**: time zone'siz vaqt, ya'ni Nyu-York mahalliy vaqti. Uni UTC'ga aylantirmaymiz.

### Ehtimoliy savollar
1. **Nega manfiy summali qatorlarni shunchaki o'chirmadingiz?** Ular void juftlikning bir qismi. Faqat manfiysini o'chirsak, musbati qolib, revenue oshib ketadi. Ikkalasini `is_void` deb belgilaymiz.
2. **`passenger_count` NULL bo'lsa nima qilasiz?** Qatorni saqlaymiz, qiymatni o'ylab topmaymiz (no imputation) va `is_passenger_count_missing` flag qo'yamiz. O'rtacha passenger hisobida ishtirok etmaydi.
3. **2002 yilgi safar qayerga ketadi?** `quarantine_taxi_trips` ga, `reject_reason = pickup_outside_file_month` bilan.
4. **Grafikda birinchi/oxirgi kunda soxta pasayish bo'lmasligini qanday ta'minladingiz?** Faqat fayl oyiga tegishli sanalar Silver'ga o'tadi, qolganlari quarantine'ga ketadi.
5. **Bu sonlarni qanday oldingiz?** `python scripts/profile_taxi.py 2024-01`.

### Live change mashqlari
1. **Boshqa oyni tahlil qilish:** faylni `data/` ga yuklab, `python scripts/profile_taxi.py 2024-02` ni ishga tushiring.
2. **Yangi tekshiruv qo'shish** (masalan `tip_amount > fare_amount`): `anomaly_checks()` lug'atiga bitta qator qo'shing.
3. **Outlier chegarasini o'zgartirish** (100 → 50 mil): Step D'dan keyin bu qiymat config'da bo'ladi, kodga tegilmaydi.

---

## Step C — API'larni o'rganish

### Fayllar
- **`docs/sources.md`**: 3 ta API bo'yicha endpoint'lar, parametrlar, paging, javob maydonlari va "tuzoqlar" (quirks). Barcha sonlar haqiqiy test so'rovlardan olingan.
- **`config/sources.json`** (yangilandi): OpenAQ uchun `monitors_only`, `locations_path`, `daily_path` va `min_coverage_pct` qo'shildi.

### OpenAQ: qanday ishlaydi
1. `GET /locations?coordinates=40.7128,-74.0060&radius=25000` so'rovi NYC atrofidagi 76 ta location'ni qaytaradi. Har birining ichida sensorlar ro'yxati ham bor.
2. Faqat **davlat monitorlari** (`isMonitor = true`) va kerakli pollutant'lar (pm25, no2, o3) olinadi.
3. Har bir sensor uchun `GET /sensors/{id}/days?date_from=...&date_to=...` so'rovi kunlik o'rtacha qiymatlarni qaytaradi.

### Tuzoqlar (quirks), himoyada albatta aytish kerak
- **Noto'g'ri parametr nomi indamay e'tiborsiz qoldiriladi.** `/days` endpoint'iga `datetime_from` yuborsak, API xato bermaydi, balki 2016-yildan beri hamma ma'lumotni qaytaradi. To'g'ri nomlar: `/days` uchun `date_from`/`date_to` (to inclusive), `/measurements/daily` uchun `datetime_from`/`datetime_to` (to exclusive).
- **Radius maksimal 25 000 m.** Koordinata tartibi: avval **latitude**, keyin longitude.
- **`meta.found` ba'zan matn** (`">1000"`) bo'ladi. Shuning uchun paging qaytgan sahifa `limit` dan kichik bo'lganda to'xtaydi.
- **Kalit faqat header'da** (`X-API-Key`) qabul qilinadi, query parameter orqali yuborilsa 401 qaytadi.
- **NO2 monitorlarining hammasi New Jersey'da.** NYC ichida 25 km radiusda NO2 monitori yo'q.
- Rate limit: daqiqasiga 60 ta, soatiga 2000 ta so'rov. Bizga ~25 ta so'rov kerak, bu bemalol sig'adi.

### World Bank
- Javob **2 elementli massiv**: `[meta, data]`. `meta.pages` sahifalar sonini ko'rsatadi. `date` (yil) **matn** ko'rinishida keladi va son (int) ga aylantirish kerak.

### ECB
- `OBS_VALUE` = **1 EUR uchun USD** (masalan 1.1065). EUR summasi = USD / kurs.
- **Dam olish va bayram kunlari kurs yo'q** (masalan 30-31 dekabr, 1 yanvar). Qoida: **oxirgi mavjud kurs** (last available, forward fill) va `is_filled = true` flag. To'liq tarixni (1999-yildan) yuklaymiz, shunda 1 yanvar uchun ham avvalgi kurs (29 dekabr) topiladi.

### Asosiy tushunchalar
- **Pagination**: katta javobni sahifalarga bo'lib olish (`page` + `limit`).
- **Rate limit**: vaqt birligida ruxsat etilgan so'rovlar soni. Oshib ketsa, HTTP 429 qaytadi.
- **Forward fill**: bo'sh kunni oldingi mavjud qiymat bilan to'ldirish.
- **Coverage**: kun davomida kutilgan 24 ta soatlik o'lchovdan nechtasi bor. 75% dan kam bo'lsa, `is_low_coverage` flag qo'yiladi.

### Ehtimoliy savollar
1. **Nega low-cost sensorlarni olmadingiz?** Ular rasmiy kalibrlangan asboblar emas va ko'pchiligida 2024 uchun ma'lumot yo'q. Davlat monitorlari (AirNow) ishonchliroq.
2. **Shanba kuni EUR kursi qayerdan olinadi?** Juma kungi kursdan (last available), `is_filled = true` belgisi bilan.
3. **OpenAQ uchun qaysi sanalarni olasiz?** `taxi.months` dan hisoblanadi: birinchi oyning 1-kunidan oxirgi oyning oxirgi kunigacha. Yangi oy qo'shilsa, avtomatik kengayadi.
4. **NO2 nega faqat New Jersey'dan?** 25 km radius ichidagi barcha NO2 monitorlari NJ'da joylashgan. Havo hududiy (regional) bo'lgani uchun ular NYC uchun ham ma'noli. Bu cheklov hujjatda yozilgan.
5. **API kalit qanday yuboriladi?** Faqat `X-API-Key` header'da. Kod uni environment'dan oladi va hech qachon ekranga chiqarmaydi.

### Cheklovlar (limitations), lecturer so'rashi mumkin
- **NO2 faqat New Jersey monitorlaridan olinadi.** NYC ichida NO2 monitori yo'q, shuning uchun NO2 trendi borough emas, hududiy havoni ko'rsatadi.
- **Faqat kunlik ma'lumot** (`/days`). Havo sifatida "kunning qaysi soati" degan tahlil yo'q. Soatlik tahlil faqat taxi uchun mumkin. Kerak bo'lsa `/sensors/{id}/hours` ni yuklash mumkin, lekin u ~24 baravar ko'p qator beradi.
- Fakt jadval **monitor darajasida**. Taxi bilan korrelyatsiya uchun **butun shahar bo'yicha kunlik o'rtacha** ishlatiladi.

### Live change mashqlari
1. **Yangi pollutant (pm10) qo'shish:** `openaq.parameters` ga `"pm10"` qo'shing. Hech qanday kod o'zgarmaydi, Dataflow mos sensorlarni o'zi topadi.
2. **Radiusni o'zgartirish:** `openaq.radius_m` ni 15000 qiling (25000 dan katta qiymat bo'lishi mumkin emas, API 422 qaytaradi).
3. **Coverage chegarasini o'zgartirish:** `openaq.min_coverage_pct` ni 75 dan 90 ga o'zgartiring.

---

## Step D — Silver funksiyalari va testlar

### Fayllar
- **`drafts/nb_lib_common.py`**: umumiy yordamchi funksiyalar:
  - `to_snake_case` / `snake_case_columns`: ustun nomlarini bir xil ko'rinishga keltiradi (`PULocationID` → `pu_location_id`);
  - `split_by_rules`: qoidalar ro'yxati bo'yicha qatorni Silver'ga yoki quarantine'ga ajratadi, **birinchi mos kelgan qoida** `reject_reason` bo'ladi;
  - `keep_first`: har bir kalit bo'yicha bitta qatorni qoldiradi, qolganlarini `duplicate` sababi bilan qaytaradi.
- **`drafts/nb_lib_taxi.py`**: `transform_trips(df, month, quality)` funksiyasi: normalizatsiya → vaqt ustunlari → void juftliklarni belgilash → quarantine qoidalari → dedup → flag'lar. Bundan tashqari `transform_zones`.
- **`drafts/nb_lib_openaq.py`**: `transform_air_quality` (mahalliy sana, null/manfiy qiymatlar, dedup, `is_low_coverage`) va `transform_monitor_zones`.
- **`drafts/nb_lib_worldbank.py`**: `transform_gdp` (yilni int'ga o'tkazish, null qiymatni quarantine'ga yuborish).
- **`drafts/nb_lib_ecb.py`**: `transform_fx`: kalendar to'ldiriladi va dam olish kuni oxirgi mavjud kursni oladi (`is_filled`).
- **`tests/notebook_loader.py`**: library fayllarni **`%run` kabi** yuklaydi: tartib bilan, bitta umumiy namespace'ga. Avval `fabric/<nom>.Notebook/notebook-content.py` qidiriladi, u bo'lmasa `drafts/<nom>.py` olinadi. Kodning ikkinchi nusxasi yo'q.
- **`tests/test_*.py`**: 16 ta kichik test, har biri bir nechta qatorli namunalar bilan.
- **`scripts/map_monitors_to_zones.py`** va **`reference/monitor_zones.csv`**: monitorni taxi zonasiga bog'lash, faqat lokal geopandas bilan.

### Nega `nb_lib_taxi` alohida `%run nb_lib_common` qilmaydi?
Ishchi notebook ikkalasini tartib bilan chaqiradi: avval `%run nb_lib_common`, keyin `%run nb_lib_taxi`. Ikkalasi bitta namespace'ga tushadi, shuning uchun `nb_lib_taxi` ichida `split_by_rules` ni to'g'ridan-to'g'ri ishlatish mumkin. `notebook_loader.load_libs("nb_lib_common", "nb_lib_taxi")` lokal muhitda xuddi shuni takrorlaydi.

### Monitorni zonaga bog'lash: nega lokal skript?
TLC shapefile NY State Plane (feet) proyeksiyasida, uni ishlatish uchun geopandas, shapely va pyproj kerak. Fabric Runtime 2.0'da bu kutubxonalar yo'q, Environment'ga qo'shilsa esa notebook sessiyasi sekin ishga tushadi. Shuning uchun mapping **bir marta lokal** qilinadi va natija kichik CSV fayl sifatida commit qilinadi. Fabric uni boshqa CSV kabi o'qiydi. Yangi monitor qo'shilsa, skript qayta ishga tushiriladi (README'da yozilgan).

### Haqiqiy faylda tekshiruv (2024-01)
`silver 2 957 630 + quarantine 6 994 = raw 2 964 624`. Hech bir qator yo'qolmadi, quarantine sonlari esa profiling bilan bir xil chiqdi.

### Fabric Runtime 2.0
Runtime 1.3 qo'llab-quvvatlashdan chiqarilmoqda (EOSA), standart runtime endi 2.0 (Spark 4.1, Python 3.13). Lokal muhitda ham `pyspark 4.1.1` va Java 17 ishlatiladi (Spark 4 uchun Java 17+ kerak). Shunda lokal testlar Fabric bilan bir xil Spark versiyasida ishlaydi.

### Asosiy tushunchalar
- **Spark lazy evaluation**: `filter`, `withColumn`, `join` kabi buyruqlar darhol bajarilmaydi, Spark faqat reja (plan) tuzadi. Haqiqiy hisob faqat **action** bo'lganda boshlanadi: `count()`, `collect()`, `write`. Shuning uchun `transform_trips` tez qaytadi, og'ir ish esa `write` paytida bajariladi.
- **Window function**: qatorlarni guruhlab, har bir qatorga guruh bo'yicha qiymat beradi (`count`, `sum`, `row_number`), `groupBy` dan farqli o'laroq qatorlar soni kamaymaydi. Void juftlik va dedup shu usulda topiladi.
- **Deduplication strategy**: natural key bo'yicha `row_number()` hisoblanadi, birinchi qator qoladi, qolganlari `duplicate` sababi bilan quarantine'ga ketadi.
- **Forward fill**: `last(..., ignorenulls=True)` va boshidan joriy qatorgacha bo'lgan window yordamida bo'sh kunga oxirgi kurs yoziladi.
- **Pure function**: natija faqat kirish ma'lumotiga bog'liq va hech qanday tashqi ta'sir (side effect) yo'q. Shuning uchun uni test qilish oson.

### Ehtimoliy savollar
1. **Qator yo'qolmaganini qanday isbotlaysiz?** `split_by_rules` har bir qatorni yo Silver'ga, yo quarantine'ga yuboradi. Test `silver + quarantine = input` tengligini tekshiradi. Haqiqiy faylda ham shunday chiqdi.
2. **Bitta qator ikkita qoidaga mos kelsa-chi?** Ro'yxatdagi **birinchi** qoida sabab bo'ladi (`coalesce(when...)`).
3. **Outlier chegarasini qayerda o'zgartirasiz?** `config/sources.json` → `taxi.quality.max_distance_mi`. Kod o'zgarmaydi.
4. **Testlar Fabric notebook kodini qanday test qiladi?** `notebook_loader` aynan `notebook-content.py` faylini yuklaydi. Fabric bu faylga faqat izoh qatorlari qo'shadi, demak u oddiy Python fayl.
5. **Nega library'da `spark.read` yo'q?** O'qish va yozish ishchi notebook'da qilinadi. Library faqat DataFrame qabul qiladi va DataFrame qaytaradi, shuning uchun uni lokal test qilish mumkin.

### Live change mashqlari
1. **Yangi quarantine qoidasi** (masalan `tip_amount < 0`): `rejection_rules()` ro'yxatiga `("negative_tip", F.col("tip_amount") < 0)` qatorini qo'shing → `tests/test_taxi.py` ga qator qo'shing → `pytest`.
2. **Yangi ustun** (masalan `pickup_weekday`): `add_trip_attributes` ichiga `"pickup_weekday": F.dayofweek(pickup)` qo'shing.
3. **Coverage chegarasini o'zgartirish:** `openaq.min_coverage_pct` ni 90 qiling → `pytest` (test chegarani config'dan oladi).
