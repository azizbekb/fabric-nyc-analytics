# Himoyaga tayyorgarlik (Defense notes)

Har bir bosqichda nima qilinganini, nima uchun shunday qilinganini va savol-javoblarni shu yerda yig'amiz.

---

## Step A — Repo strukturasi va config

### Fayllar

- **`config/sources.json`**: barcha manbalarning **yagona manbasi** (single source of truth): URL'lar, taxi oylari, koordinatalar, pollutantlar, jadval nomlari. Uni Pipeline (Lookup activity) ham, notebook'lar ham, lokal testlar ham o'qiydi. Kodda hech qanday URL yoki jadval nomi qattiq yozilmaydi (no hard-coded literals).
- **`.gitignore`**: `.env` (kalit), `data/` (yuklangan fayllar) va `.venv/` Git'ga tushmaydi.
- **`.env` / `.env.example`**: lokal sir (secret) `.env` da turadi. `.env.example` esa faqat kalit nomini ko'rsatadi, qiymatsiz.
- **`drafts/`** (endi yo'q): Fabric item'lari yaratilguncha kod vaqtincha shu yerda turdi. Har bir kod Fabric item'iga ko'chirilgach, draft o'chirildi, shuning uchun kodning ikkinchi nusxasi qolmadi.
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
- **`fabric/nb_lib_common.Notebook/notebook-content.py`**: umumiy yordamchi funksiyalar:
  - `to_snake_case` / `snake_case_columns`: ustun nomlarini bir xil ko'rinishga keltiradi (`PULocationID` → `pu_location_id`);
  - `split_by_rules`: qoidalar ro'yxati bo'yicha qatorni Silver'ga yoki quarantine'ga ajratadi, **birinchi mos kelgan qoida** `reject_reason` bo'ladi;
  - `keep_first`: har bir kalit bo'yicha bitta qatorni qoldiradi, qolganlarini `duplicate` sababi bilan qaytaradi.
- **`fabric/nb_lib_taxi.Notebook/notebook-content.py`**: `transform_trips(df, month, quality)` funksiyasi: normalizatsiya → vaqt ustunlari → void juftliklarni belgilash → quarantine qoidalari → dedup → flag'lar. Bundan tashqari `transform_zones`.
- **`fabric/nb_lib_openaq.Notebook/notebook-content.py`**: `transform_air_quality` (mahalliy sana, null/manfiy qiymatlar, dedup, `is_low_coverage`) va `transform_monitor_zones`.
- **`fabric/nb_lib_worldbank.Notebook/notebook-content.py`**: `transform_gdp` (yilni int'ga o'tkazish, null qiymatni quarantine'ga yuborish).
- **`fabric/nb_lib_ecb.Notebook/notebook-content.py`**: `transform_fx`: kalendar to'ldiriladi va dam olish kuni oxirgi mavjud kursni oladi (`is_filled`).
- **`tests/notebook_loader.py`**: library fayllarni **`%run` kabi** yuklaydi: tartib bilan, bitta umumiy namespace'ga. Manba: `fabric/<nom>.Notebook/notebook-content.py`. Kodning ikkinchi nusxasi yo'q.
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

---

## Gold: nega to'liq qayta yuklash (full reload)?

**Savol:** "Nega DELETE + INSERT, incremental emas? Ma'lumot ko'paysa nima o'zgaradi?"

**Javob:**
- Hozir ma'lumot kichik: `FactTaxiDaily` ≈ 7 ming qator/oy, 6 oyda ≈ 42 ming qator. To'liq qayta yuklash bir necha soniya oladi.
- To'liq qayta yuklash **eng sodda va xavfsiz** usul: qayta ishga tushirsak, natija bir xil chiqadi (idempotent). Dublikat paydo bo'lmaydi, Silver'da tuzatilgan qoida esa eski kunlarga ham avtomatik qo'llanadi.
- **Ma'lumot ko'paysa** (masalan, ko'p yillik taxi), endi faqat yangi qismni yuklaymiz:
  1. **Oy bo'yicha almashtirish:** `DELETE FROM dbo.FactTaxiDaily WHERE date_key BETWEEN <oy boshi> AND <oy oxiri>`, keyin faqat shu oy uchun `INSERT ... SELECT ... WHERE pickup_date` shu oy ichida. Oy ro'yxati config'dan keladi (`taxi.months`, yoki faqat yangi qo'shilgan oy).
  2. Yoki **`MERGE`** (Fabric Warehouse'da GA): kalit `(date_key, zone_id)`. Mavjud bo'lsa `UPDATE`, bo'lmasa `INSERT`.
  3. Silver ham shunday: butun jadvalni emas, faqat yangi oyning partition'ini qayta yozish (Delta `replaceWhere`).
- Taxi uchun oy bo'yicha almashtirish ma'qulroq: TLC fayli **butun oy uchun** qayta chiqishi mumkin, demak oyni to'liq almashtirish to'g'ri. Kichik dimension jadvallar (zona, FX, GDP) esa doim to'liq yuklanaveradi.

---

## Fabric setup (Phase 0–1 rejasi) — `docs/setup_fabric.md`

### Fayllar
- **`docs/setup_fabric.md`**: Phase 0 (capacity, workspace, Runtime 2.0, lakehouse'lar, warehouse, Git) va Phase 1 (pipeline, dataflow'lar) uchun click-by-click qo'llanma. Har bir menyu nomi Microsoft Learn bilan tekshirilgan, M kod draft'lari ham shu yerda.
- **`config/sources.json`** (yangilandi): har bir manbada `base_url` + `path` bor, chunki pipeline'dagi HTTP connection "base URL + relative URL" bilan ishlaydi. Yangi bo'limlar: `repo`, `warehouse`, `gold.load_procedures`.

### Asosiy qarorlar
- **2 ta Lakehouse (`lh_bronze`, `lh_silver`) + 1 ta Warehouse (`wh_gold`).** Har bir layer alohida item bo'lgani uchun chegaralar aniq ko'rinadi va ruxsatlarni layer bo'yicha berish mumkin.
- **Lakehouse schemas o'chirilgan.** Schema'li Lakehouse'da Dataflow destination uchun qo'shimcha "Navigate using full hierarchy" opsiyasi kerak bo'ladi. Schema'siz ham Warehouse jadvalni `lh_silver.dbo.<jadval>` deb ko'radi.
- **Config pipeline'ga qanday yetadi:** birinchi Copy activity `sources.json` ni GitHub'dan `lh_bronze/Files/config/` ga ko'chiradi. Keyin Lookup uni o'qiydi, ForEach esa `taxi.months` bo'yicha aylanadi. Config faylining manzili yagona "bootstrap" literal, chunki config o'zini o'qilishidan oldin ko'rsata olmaydi.
- **OpenAQ kaliti (Key Vault'siz):** Azure obunasi yo'q, shuning uchun Key Vault ham yo'q. Fabric'ning "Web API" credential'i kalitni URL ichida yuboradi, OpenAQ esa uni faqat header'da qabul qiladi (401). Yechim:
  1. kalit `lh_bronze/Files/secrets/openaq_api_key.txt` faylida turadi (bir marta qo'lda yuklanadi);
  2. `df_openaq` faylni Lakehouse connector bilan o'qiydi va `X-API-Key` header'iga qo'yadi.

  **Nega xavfsiz:** Fabric Git faqat item ta'rifini saqlaydi, Lakehouse'dagi fayl va jadvallar Git'ga **hech qachon** tushmaydi. Kalit parametr ham emas, shuning uchun run log'larida ko'rinmaydi.

  **Kamchiligi (trade-off):** fayl OneLake'da oddiy matn ko'rinishida turadi. `lh_bronze` ni o'qiy oladigan har kim uni ochishi mumkin, kim o'qiganini ko'rsatadigan audit yo'q, kalitni almashtirish uchun yangi fayl yuklash kerak. Key Vault buning hammasini beradi, lekin Azure obunasini talab qiladi. Bitta foydalanuvchili kurs workspace'i uchun bu maqbul.

### Asosiy tushunchalar
- **Lakehouse vs Warehouse:** Lakehouse'da fayllar va Delta jadvallar bo'ladi va asosan Spark bilan ishlanadi; SQL endpoint faqat o'qish uchun. Warehouse esa to'liq T-SQL beradi (CREATE, INSERT, UPDATE, procedure). Ikkalasi ham ma'lumotni OneLake'da Delta formatida saqlaydi.
- **Pipeline vs Dataflow Gen2:** Pipeline **orkestratsiya** qiladi: fayl ko'chirish, tartib, ForEach, schedule. Dataflow Gen2 esa **Power Query** bilan ma'lumotni o'zgartiradi: API'dan JSON yoki CSV olib, uni jadvalga aylantiradi.
- **Power Query M asoslari:** `let ... in` ichida har bir qadam nomlanadi. `Web.Contents` so'rov yuboradi, `Json.Document` va `Csv.Document` javobni o'qiydi. `List.Generate` sahifalab (paging) olish uchun ishlatiladi, `Table.FromRecords` esa yozuvlardan jadval yasaydi. M ham Spark kabi "lazy": qiymat kerak bo'lgandagina hisoblanadi.
- **Secure input/output:** activity log'ida kirish yoki chiqish qiymati yashiriladi. Bu zaxira variantda kerak bo'ladi: notebook kalitni o'qib, Dataflow parametriga uzatsa.

### Tuzoqlar (himoyada aytish foydali)
- Lakehouse destination **DateTimeZone** tipini qabul qilmaydi, shuning uchun `load_ts` UTC `datetime` bo'ladi.
- Git'dan **Update all** qilingandan keyin Dataflow'ni bir marta ochib, **saqlash** kerak, aks holda refresh eski versiya bilan ishlaydi.
- Dataflow destination jadval nomini parametr qilib bo'lmaydi, uni UI'da yozamiz. U config'dagi nom bilan bir xil bo'lishi kerak.
- M'da sonlarni `en-US` formatida matnga aylantiramiz (`Num`), aks holda 40.7128 qiymati "40,7128" bo'lib qolishi mumkin.

---

## Gold layer (Phase 3, Fabric'da bajarildi 2026-11-20) — `fabric/wh_gold.Warehouse/`

### Fayllar
- **`dbo/Tables/*.sql`**: 5 ta dimension va 2 ta fact jadval (har bir obyekt alohida faylda, Fabric o'zi shunday saqlaydi), kalitlar bilan (`NOT ENFORCED`).
- **`dbo/StoredProcedures/*.sql`**: har jadval uchun bitta procedure (`load_dim_date`, …, `load_fact_taxi_daily`). Har biri jadvalni to'liq qayta yuklaydi (`DELETE + INSERT`). `TRUNCATE` ishlatilmaydi: Fabric Warehouse FK (hatto NOT ENFORCED) bilan bog'langan jadvalni TRUNCATE qilishga ruxsat bermaydi (Msg 4712).
- **`config/sources.json` → `gold.load_procedures`**: procedure'lar tartibi. Pipeline shu ro'yxat bo'yicha ketma-ket (Sequential) ForEach qiladi.

### Star schema
```
             DimDate ─────┬──────────────┐
                │          │              │
DimZone ── FactTaxiDaily   FactAirQualityDaily ── DimLocation ── (zone_id) DimZone
                │
              DimFX (kun bo'yicha kurs)      DimGDP (yil bo'yicha)
```
- **Fact** jadvalda o'lchovlar (raqamlar) bor: trips, summalar, o'rtacha qiymatlar. Fact uzun bo'ladi va ko'p qator saqlaydi.
- **Dimension** jadvalda tavsif bor: sana, zona nomi, borough. Dimension qisqa bo'ladi, unda filtr va guruhlash uchun atributlar saqlanadi.
- **Grain**: fact jadvaldagi bitta qator nimani anglatishi. `FactTaxiDaily` uchun bu "kun × pickup zona", `FactAirQualityDaily` uchun "kun × monitor × pollutant".

### Muhim qarorlar
- **Fabric T-SQL cheklovlari:** `nvarchar`, `datetime`, `tinyint` yo'q, ularning o'rniga `varchar`, `date`, `smallint`. PK/FK faqat `ALTER TABLE … NOT ENFORCED` bilan qo'shiladi: kalit tekshirilmaydi, lekin model uchun hujjat va bog'liqlik vazifasini bajaradi. Recursive CTE ham yo'q, shuning uchun DimDate `GENERATE_SERIES` bilan quriladi.
- **FX taxi revenue'ga qanday ulanadi:** avval taxi kun × zona bo'yicha agregatsiya qilinadi, keyin `silver_fx_daily` bilan **sana bo'yicha** join qilinadi. Formula: `total_amount_eur = total_amount_usd / usd_per_eur`. Dam olish kunlarida oxirgi mavjud kurs olinadi (`is_filled`).
- **Void juftliklar trip emas** (`is_void = 0` filtri). Outlier'lar trip sifatida hisoblanadi, lekin o'rtacha qiymatlarga kirmaydi. `clean_trips` ustuni Power BI'da to'g'ri tortilgan o'rtacha (weighted average) hisoblash uchun kerak.
- **Xavf:** Warehouse Git'da database project sifatida saqlanadi, lekin Microsoft hujjatiga ko'ra Warehouse ↔ Lakehouse SQL endpoint cross-item bog'liqligi hali to'liq qo'llab-quvvatlanmaydi. Commit muvaffaqiyatsiz bo'lsa, zaxira yo'l bor: o'sha SQL'ni pipeline'ning **Script** activity'si orqali ishga tushiramiz.

---

## Lokal Gold tekshiruvi — `scripts/check_gold.py`

`python scripts/check_gold.py 2024-01` buyrug'i Silver'ni quradi, uni Gold SQL'i bilan bir xil agregatsiya qiladi va 8 ta tekshiruvni bajaradi:
- jamilar Silver bilan teng: 2 896 290 trip va $79 563 881.08;
- (kun, zona) grain'i takrorlanmaydi;
- barcha kunlar fayl oyi ichida;
- chetki kunlarda 24 soatning hammasi bor;
- chetki kunlarda soxta pik yoki tushish yo'q;
- har kun uchun EUR kursi bor;
- `clean_trips ≤ trips`.

Biror tekshiruv o'tmasa, skript `exit 1` bilan tugaydi.

### "Nega 1–2 yanvar past?" (grafik savoli)
- **Javob:** bu **haqiqiy ma'lumot**, qisman yuklanish emas. 1-yanvar Yangi yil bayrami (dushanba), 2-yanvar esa bayramdan keyingi kun, shahar hali to'liq ishga qaytmagan.
- **Isbot (`check_gold.py`):**
  1. 01-01 va 01-02 kunlarida **24 soatning hammasida** safar bor. Qisman yuklangan kunda soatlar kam bo'lardi (masalan, faqat 23:00–23:59).
  2. Ularning median kunga nisbati 0.83 va 0.78. Bu soxta kun emas: masalan, 2023-12-31 kunida jami 10 ta trip bo'lardi, bu median'ning 0.0001 qismi.
  3. Xuddi shunday "past" kunlar boshqa joyda ham bor: yakshanba 01-07 (67 543 trip) va Martin Luther King kuni 01-15 (77 033 trip). Bu bayram va dam olish kunlari uchun odatiy holat.
- Soxta kunlar (2023-12-31, 2024-02-01, 2002, 2009) faqat xom faylda bor. Silver ularni `pickup_outside_file_month` sababi bilan quarantine'ga yuboradi.

### Ehtimoliy savollar
1. **Fact va dimension farqi nima?** Fact'da o'lchovlar (raqamlar, ko'p qator), dimension'da tavsif (filtr va guruhlash uchun atributlar).
2. **Nega PK/FK `NOT ENFORCED`?** Fabric Warehouse kalitlarni faqat shu rejimda qabul qiladi. Ma'lumot to'g'riligini load mantiqi ta'minlaydi, kalitlar esa model va hujjat uchun.
3. **EUR summa qanday hisoblanadi?** USD summa o'sha kunning `usd_per_eur` kursiga bo'linadi. Dam olish kunida juma kungi kurs ishlatiladi.
4. **Kalit qanday himoyalangan?** U `lh_bronze/Files/secrets/` dagi faylda turadi. Lakehouse ma'lumoti Git'ga sinxron bo'lmaydi va kalit parametr sifatida uzatilmaydi, shuning uchun log'da ham ko'rinmaydi. Key Vault'ga nisbatan kamchiligi: oddiy matn, audit yo'q, almashtirish qo'lda.
5. **Gold jamilari to'g'ri ekanini qanday bilasiz?** `check_gold.py` fact jamilarini Silver bilan solishtiradi (2 896 290 = 2 896 290) va grain'ni tekshiradi.

### Live change mashqlari
1. **FactTaxiDaily'ga yangi ustun (`total_tip_usd`) qo'shish:**
   - `fabric/wh_gold.Warehouse/dbo/Tables/FactTaxiDaily.sql`: `total_tip_usd decimal(18, 2) NULL` qatorini qo'shing (mavjud jadval uchun `ALTER TABLE dbo.FactTaxiDaily ADD total_tip_usd decimal(18,2) NULL;`);
   - `load_fact_taxi_daily`: ichki SELECT'ga `CAST(SUM(t.tip_amount) AS decimal(18, 2)) AS total_tip_usd`, INSERT ro'yxatiga esa ustun nomini qo'shing;
   - `check_gold.py` dagi `fact_taxi_daily` ga `F.sum("tip_amount")` ni qo'shing;
   - pipeline'ni ishga tushiring.
2. **Kunlikdan soatlikka o'tish:** `GROUP BY` ga `t.pickup_hour` ni qo'shing, yangi `hour` ustuni yarating va grain'ni "kun × soat × zona" deb o'zgartiring. Data dictionary'ni ham yangilang. Silver'da `pickup_hour` allaqachon bor.
3. **Yangi Gold jadval qo'shish (extendability):** Warehouse'da yangi `CREATE TABLE` va yangi `load_<nom>` procedure yarating (Git'da `dbo/Tables/` va `dbo/StoredProcedures/` ga fayl bo'lib tushadi) va `config/sources.json` → `gold.load_procedures` ro'yxatiga nomini qo'shing. Pipeline'ni o'zgartirish shart emas.

---

## Phase 1 — Bronze ingestion (Fabric'da bajarildi, 2026-11-12)

### Fayllar (Fabric Git'ga o'zi yozgan)
- **`fabric/pl_daily.DataPipeline/pipeline-content.json`** (Phase 1 da nomi `pl_ingest` edi): pipeline JSON ko'rinishida. Activity'lar va ularning `dependsOn` bog'lanishlari:
  `Copy config` → `Lookup config` → (`ForEach taxi month`, `Copy taxi zones`, `Copy monitor zones`); `Copy config` → (`Run df_ecb`, `Run df_worldbank`, `Run df_openaq`).
- **`fabric/df_*.Dataflow/mashup.pq`**: Dataflow'ning M kodi (Power Query). `queryMetadata.json`: query nomlari va connection havolalari (parol yoki kalit yo'q). `.platform`: item turi va id.

### Pipeline qanday ishlaydi
1. **Copy config**: GitHub'dagi `config/sources.json` → `lh_bronze/Files/config/`. Bu yagona "bootstrap" literal: config o'qilishidan oldin o'ziga ishora qila olmaydi.
2. **Lookup config**: faylni o'qiydi. Natija `activity('Lookup config').output.firstRow` orqali olinadi.
3. **ForEach taxi month**: `taxi.months` ro'yxatidagi har bir oy uchun parquet faylni yuklaydi (`batch count 2`, parallel). Fayl nomi `replace(path_template, '{month}', item())` va `last(split(..., '/'))` bilan hosil qilinadi.
4. **Copy taxi zones / monitor zones**: ikki kichik CSV.
5. **Run df_***: uch Dataflow. Ular faqat config faylga muhtoj, Lookup natijasiga emas, shuning uchun `Copy config` dan keyin ishga tushadi.

Bronze fayllari baytma-bayt o'zgarmaydi (xom holda). API jadvallariga faqat `source` va `load_ts` qo'shiladi. Update method **Replace**: qayta ishga tushirilganda dublikat paydo bo'lmaydi.

### Natija (2026-11-12)
6 ta taxi parquet, `taxi_zone_lookup.csv`, `monitor_zones.csv`; jadvallar: `bronze_openaq_measurements` 4 274, `bronze_worldbank_gdp` 66, `bronze_ecb_fx` 7 196 qator.
OpenAQ 24 × 182 = 4 368 emas, chunki API o'lchov bo'lmagan kunlarni qaytarmaydi.

### Muhim qarorlar
- **Dataflow'lar config'ni Lakehouse'dan o'qiydi, GitHub'dan emas.** GitHub raw URL Fabric'da eski versiyani qaytardi (`locations_path` yo'q edi). Lakehouse nusxasini esa pipeline har safar yangilaydi, ya'ni tartib aniq: avval config, keyin Dataflow.
- **Kalit** `lh_bronze/Files/secrets/openaq_api_key.txt` da turadi. Dataflow uni **o'sha query ichida** o'qiydi va `X-API-Key` header'ida yuboradi. Kalit Git'da ham, kodda ham yo'q. Key Vault yo'q, chunki Azure obunasi yo'q. Trade-off: fayl OneLake'da ochiq matn, audit yo'q, kalit qo'lda almashtiriladi.
- **Privacy level: hammasi Organizational.** Lakehouse (Organizational) ma'lumoti Public web manbaga yuborilsa, Power Query *Formula.Firewall* bilan bloklaydi.
- **Connection URL'lari** (`http_github_raw`, `http_tlc`) connection'da qattiq yozilgan, chunki Fabric connection URL'ini parametrlab bo'lmaydi. Yo'l (relative URL) esa config'dan olinadi.

### Tuzoqlar (himoyada aytish foydali)
- Activity nomi ifodadagi nomga **harfma-harf** mos kelishi kerak (`Lookup1` ≠ `Lookup config`). Ifoda faqat **ulangan oldingi** activity'ga murojaat qila oladi.
- M tili katta-kichik harfni farqlaydi: `configUrl` ≠ `ConfigUrl`.
- Dataflow **Succeeded** bo'lishi ma'lumot yozilganini anglatmaydi: destination bo'lmasa, hech narsa yozilmaydi. Natijani doim jadvaldan tekshiramiz.
- Yangi jadval bir necha daqiqa **Unidentified** da turishi mumkin, keyin **Refresh** qilinadi.
- Saqlanmagan pipeline refresh'dan keyin yo'qoladi: **Ctrl+S**.

### Asosiy tushunchalar
- **Pipeline** = orkestratsiya (nima, qachon, qaysi tartibda). **Dataflow Gen2** = Power Query bilan low-code transformatsiya va ingestion.
- **Lookup** config'ni o'qiydi, **ForEach** ro'yxat bo'yicha takrorlaydi, `item()` joriy element.
- **Dynamic content** (`@...` ifodalar) qiymatlarni ish vaqtida hisoblaydi.
- **Privacy levels** (Public < Organizational < Private) ma'lumot manbalar orasida qanday oqishini nazorat qiladi.

### Ehtimoliy savollar
1. *Nega taxi fayllari Pipeline bilan, API'lar Dataflow bilan yuklanadi?* Taxi: tayyor fayl, uni o'zgartirmasdan ko'chirish kifoya (Copy, Binary). API: JSON yoki CSV javob, sahifalash va header kerak, natija jadval bo'ladi (Power Query).
2. *Yangi oy qanday qo'shiladi?* `config/sources.json` → `taxi.months` ga `"2024-07"` qo'shiladi → push → pipeline Run. Kod o'zgarmaydi.
3. *Pipeline ikki marta ishlasa, dublikat bo'ladimi?* Yo'q. Fayllar ustiga yoziladi, jadvallar **Replace**.
4. *Kalit qayerda va nega Git'da yo'q?* (yuqoridagi qarorga qarang).
5. *Nega Dataflow'lar Lookup'ga emas, Copy config'ga ulangan?* Ular Lookup natijasini ishlatmaydi, faqat faylni o'qiydi. Bog'lanish haqiqiy ehtiyojni ko'rsatadi.

### Live change mashqlari
1. Config'ga yangi oy qo'shing (`2024-07`), push qiling, pipeline'ni ishga tushiring va `Files/taxi` da 7-fayl paydo bo'lganini ko'rsating.
2. OpenAQ'ga yangi pollutant qo'shing: `openaq.parameters` ga `"pm10"`, push qiling, `df_openaq` ni ishga tushiring va `SELECT DISTINCT parameter` bilan tekshiring.
3. ForEach'ni ketma-ket rejimga o'tkazing (**Sequential** ✓) va nima o'zgarishini tushuntiring (tezlik va resurs).

---

## Phase 2 — Silver (Fabric'da bajarildi, 2026-11-20)

### Fayllar
- **`fabric/nb_lib_*.Notebook/notebook-content.py`** (5 ta): faqat funksiyalar (pure functions). Ular Spark sessiyasini ishlatmaydi va import qilinganda hech narsa bajarmaydi. Testlar (`tests/`) aynan shu fayllarni o'qiydi, ya'ni kodning ikkinchi nusxasi yo'q.
- **`fabric/nb_silver.Notebook/notebook-content.py`**: ishchi notebook. `%run` bilan 5 ta library'ni yuklaydi, config'ni `Files/config/sources.json` dan o'qiydi, har bir manbani o'qib, transform qilib, `lh_silver` ga yozadi.
  Default lakehouse `lh_bronze`, shuning uchun `Files/...` qisqa yo'li ishlaydi. Silver'ga esa to'liq nom bilan yoziladi: `lh_silver.<jadval>`.
- Notebook'larni men Fabric'ning haqiqiy formatida (Fabric commit qilgan bo'sh notebook'dan olingan) yozdim. Fabric'ga ular **Source control → Update all** orqali tushdi.

### Natija (2026-11-20, 6 oy)
| Jadval | Qatorlar |
|---|---|
| silver_taxi_trips / quarantine_taxi_trips | 20 237 796 / 94 297 |
| silver_taxi_zones | 265 |
| silver_air_quality / quarantine_air_quality | 4 271 / 3 |
| silver_monitor_zones | 25 |
| silver_gdp / quarantine_gdp | 66 / 0 |
| silver_fx_daily / quarantine_fx | 10 182 / 62 |

`save_split` har bir manba uchun **Bronze qatorlari = silver + quarantine** ekanini `assert` bilan tekshiradi. Bitta qator yo'qolsa yoki ikki marta yozilsa, notebook xato bilan to'xtaydi. ECB'da bu tekshiruv yo'q, chunki Silver to'liq kalendar: dam olish kunlari qo'shiladi va `is_filled = true` bo'ladi.

Taxi qatorlariga lineage ustunlari qo'shiladi: `source_file` (`_metadata.file_path`) va `load_ts` (`_metadata.file_modification_time`, ya'ni fayl Bronze'ga yozilgan vaqt).

### Muhim qarorlar
- **Full reload** (`mode("overwrite")`): har safar hamma narsa qayta hisoblanadi. Natija har doim bir xil (idempotent), dublikat bo'lmaydi. 20 mln qator taxminan 2,5 daqiqada qayta ishlanadi, bu bizning hajm uchun yetarli.
- **Har bir oy alohida transform qilinadi**, chunki `pickup_outside_file_month` qoidasi faylning oyini bilishi kerak. Keyin oylar `unionByName(allowMissingColumns=True)` bilan birlashtiriladi: oylar orasida ustun nomi yoki tartibi farq qilsa ham ishlaydi.
- **Library va ishchi notebook alohida**: funksiyalarni lokal PySpark'da test qilish mumkin, ishchi notebook esa faqat o'qish va yozish bilan shug'ullanadi.

### Ehtimoliy savollar
1. *Qator yo'qolmaganini qanday isbotlaysiz?* `save_split` dagi assert: bronze = silver + quarantine. Natija notebook chiqishida ko'rinadi.
2. *`%run` nima qiladi?* Boshqa notebook'ni **shu sessiyada** bajaradi va uning funksiyalari shu notebook'da paydo bo'ladi (xuddi kodni nusxalaganday).
3. *Nega OpenAQ'da 3 ta qator quarantine'da?* `value` bo'sh yoki manfiy bo'lgan kunlar (`reject_reason` ustunida sababi yozilgan). `SELECT reject_reason, COUNT(*) FROM quarantine_air_quality GROUP BY reject_reason`.
4. *Notebook ikki marta ishlasa nima bo'ladi?* Overwrite, natija o'sha-o'sha.
5. *Nega Silver ECB'da qatorlar Bronze'dan ko'p?* Kalendar to'ldirilgan: har bir kun uchun kurs bor, bayram va dam olish kunlari oldingi kursni oladi.

### Live change mashqlari
1. `config/sources.json` → `taxi.quality.max_distance_mi` ni 100 dan 50 ga o'zgartiring → push → `pl_daily` (config nusxasi) → `nb_silver`. `is_outlier` soni ortadi, kod o'zgarmaydi.
2. Yangi quarantine qoidasi: `nb_lib_taxi.rejection_rules` ga `("zero_distance_long_trip", (F.col("trip_distance") == 0) & (F.col("trip_duration_min") > 60))` qo'shing, test yozing, natijani ko'rsating.
3. `silver_air_quality` ga `is_weekend` ustunini qo'shing (`F.dayofweek("date").isin(1, 7)`).

### Phase 3 natija (2026-11-20)
DimDate 182, DimZone 265, DimLocation 25, DimFX 182, DimGDP 66, FactTaxiDaily 41 745, FactAirQualityDaily 4 271.
**Tekshiruv:** `SUM(trips)` (FactTaxiDaily) = void bo'lmagan Silver qatorlari = **19 791 824**. Demak aggregatsiyada hech narsa yo'qolmagan va hech narsa ikki marta sanalmagan.
Silver'da 20 237 796 qator bor. Farq (~446 ming) void juftliklar: to'lov va uning bekor qilinishi. Ular safar emas, shuning uchun Gold'ga kirmaydi.

---

## Phase 4 — Power BI (Fabric'da bajarildi, 2026-11-20)

### Fayllar
- **`fabric/sm_nyc_analytics.SemanticModel/`**: semantic model TMDL formatida (matn ko'rinishida). `definition/relationships.tmdl` da 6 ta bog'lanish, `definition/tables/*.tmdl` da jadvallar va 16 ta DAX measure (format bilan).
- **`fabric/rpt_nyc_analytics.Report/`**: hisobot PBIR formatida. Har bir sahifa va har bir vizual alohida JSON faylda saqlanadi.
- Measure'larni avval DAX query view'da sinab ko'rdik (`DEFINE MEASURE … EVALUATE`), keyin modelga qo'shdik. Endi ular faqat TMDL'da turadi, alohida `.dax` fayl yo'q.

### Model
- **Direct Lake on SQL**: Power BI Warehouse'dagi Delta fayllarni nusxa olmasdan o'qiydi. Rejim Import kabi tez ishlaydi, lekin alohida import refresh kerak emas. Ma'lumot yoki model tuzilmasi o'zgarsa, model **refresh** (framing) qilinadi.
- Bog'lanishlar dimension'dan fakt tomonga, **bir yo'nalishda** ishlaydi: FactTaxiDaily → DimDate, DimZone; FactAirQualityDaily → DimDate, DimLocation; DimFX → DimDate (*:1); DimDate → DimGDP (yil bo'yicha *:1). Avval DimFX 1:1 va ikki tomonlama edi, uni *:1 va bir yo'nalishli qilib o'zgartirdik: ikki tomonlama filtr noaniq filtr yo'llarini yaratadi.
- `DimDate` **date table** sifatida belgilangan (`dataCategory: Time`), `month_name` esa `month` bo'yicha saralanadi.

### Measure'lar (asosiylari)
- `Total Trips`, `Revenue USD/EUR`, `Trips per Day`, `Trips 7d Avg` (`DATESINPERIOD`), `Trips MoM %` (`DATEADD`).
- `Avg Fare/Distance/Duration`: **og'irlikli o'rtacha**. Kunlik o'rtacha shu kunning `clean_trips` soniga ko'paytiriladi. Oddiy o'rtachada 3 ta safarli zona 3 000 ta safarli zona bilan bir xil vaznga ega bo'lib qolardi. Outlier'lar (`clean_trips` dan tashqari) o'rtachaga kirmaydi.
- `GDP USD bn`: `TREATAS(VALUES(DimDate[year]), DimGDP[year])` bilan tanlangan sanalarning yiliga filtrlanadi. Bog'lanish DimDate → DimGDP bo'lgani uchun filtr sanadan GDP tomonga o'tmaydi. TREATAS'siz kartochka 66 yilning yig'indisini (607K bn) ko'rsatgan edi.
- `PM2.5/NO2/O3 Avg`: `is_low_coverage` kunlar hisobga olinmaydi.
- `Trips vs PM2.5 Correlation`: kunlar bo'yicha Pearson koeffitsienti (−1 … 1), DAX'da qo'lda hisoblangan (kovariatsiya / standart og'ishlar).

### Hisobot (3 sahifa)
1. **Taxi**: kartochkalar, kunlik safarlar va 7 kunlik o'rtacha, borough bo'yicha, **Top 10 pickup zones** (Top N filtri), oy slicer'i.
2. **Air quality**: PM2.5 (µg/m³) va NO2/O3 (ppm) **alohida** grafiklarda, chunki birliklar har xil va bitta o'qda NO2/O3 nolga o'xshab ko'rinardi. Monitorlar jadvali.
3. **Taxi, air & economy**: safarlar (ustun) + PM2.5 (chiziq) bitta grafikda, korrelyatsiya, Revenue EUR, GDP, USD/EUR kursi.

### Tekshiruvlar
- Yanvar: DAX `Total Trips` = 2 896 290, `Revenue USD` = 79 563 881.08. Bu lokal `scripts/check_gold.py` natijasi bilan bir xil.
- Slicer'dagi "(Blank)": SQL (FK `NOT ENFORCED` bo'lgani uchun "yetim" kalitlarni tekshirdik) va DAX bilan bog'lanmagan qatorlar 0 ekanini isbotladik. Demak bu Direct Lake'ning texnik "noma'lum a'zo" qatori, unga hech qanday qator bog'lanmagan. Slicer'da **is not blank** filtri bilan yashirildi.

### Natija (6 oy, 2024-01 … 06)
- Revenue EUR €517M, GDP (2024) ~29 000 bn USD.
- **Trips vs PM2.5 korrelyatsiyasi: −0.04 (6 oy)**: amalda bog'liqlik yo'q. Oylar bo'yicha qiymat har xil: fevral +0.20, aprel −0.15, ya'ni yo'nalishi ham o'zgarib turadi. Xulosa: kunlik taksi safarlari soni PM2.5 ni tushuntirmaydi. Havo sifatiga ob-havo (shamol, yomg'ir, harorat) va boshqa manbalar ko'proq ta'sir qiladi. Korrelyatsiya sabab-oqibatni isbotlamaydi.

### Ehtimoliy savollar
1. *Nega Direct Lake, Import emas?* Ma'lumot nusxasi yo'q, Gold yangilangach model refresh (framing) bilan darhol yangi holatni ko'radi.
2. *Nega o'rtacha narx og'irlikli?* (yuqoriga qarang).
3. *Korrelyatsiya qanday hisoblanadi va nimani ko'rsatadi?* Kunlik juftliklar (safarlar, PM2.5) bo'yicha Pearson. Korrelyatsiya sabab-oqibatni isbotlamaydi.
4. *Nega NO2 ko'p monitorda bo'sh?* NYC atrofidagi NO2 monitorlari faqat New Jersey'da (Phase 1 da aniqlangan).
5. *Model va hisobot Git'da qanday saqlanadi?* TMDL va PBIR, ya'ni matn fayllari. O'zgarishlarni diff qilib ko'rish mumkin.

### Live change mashqlari
1. Yangi measure: `Avg Tip USD` (Gold'ga `tip_amount` qo'shib) yoki `Revenue per Trip = DIVIDE([Revenue USD], [Total Trips])`. Uni DAX query view'da yozing → **Update model**.
2. Taxi sahifasiga `DimDate[day_name]` bo'yicha safarlar grafigini qo'shing (`day_name` ni `day_of_week` bo'yicha saralang).
3. Top 10 zonani Top 5 ga o'zgartiring (Filters → Top N).

---

## Phase 5 — Orkestratsiya va kunlik schedule (2026-11-20)

### Fayllar
- **`fabric/pl_daily.DataPipeline/pipeline-content.json`**: butun oqim bitta pipeline'da. `pl_ingest` nomi `pl_daily` ga o'zgartirildi (Git buni rename deb ko'rsatadi).
- **`fabric/pl_daily.DataPipeline/.schedules`**: kunlik 06:00, `West Asia Standard Time` (= Toshkent, UTC+5), 2026-11-21 … 2026-12-31.

### Ketma-ketlik
Bronze (6 activity) → `Run nb_silver` → `Refresh silver endpoint` → `ForEach gold procedure` (7 procedure, **Sequential**) → `Refresh model`. Hamma strelkalar **On success**.

### Muhim qarorlar
- **Nega notebook'ga 6 ta strelka?** `nb_silver` **barcha** Bronze ma'lumotlarini o'qiydi. Bitta strelka bo'lsa, u boshqa yuklashlar tugamasdan boshlanib, eski yoki yarim ma'lumotni o'qib qolishi mumkin.
- **Nega SQL endpoint refresh?** Notebook Delta jadvallarni yozadi, lekin SQL endpoint ularni biroz kechikib ko'radi. Gold procedure'lari `lh_silver.dbo.*` ni SQL orqali o'qiydi, shuning uchun avval endpoint yangilanadi.
- **Nega Sequential?** Tartib config'da: avval Dim'lar, keyin Fact'lar. `load_dim_fx` esa `DimDate` ni o'qiydi.
- **Nega procedure nomlari config'da?** Yangi Gold jadval qo'shilsa, faqat config'ga nom qo'shiladi, pipeline o'zgarmaydi.
- **Nega kuniga bir marta qayta ishga tushirish xavfsiz?** Har bir qadam o'z natijasini qayta yozadi (Replace, overwrite, `DELETE`+`INSERT`), shuning uchun dublikat paydo bo'lmaydi.
- **Xato bo'lsa nima bo'ladi?** Keyingi qadamlar ishlamaydi, shuning uchun Gold hech qachon chala Silver'dan yuklanmaydi. Masalan, `df_openaq` xato bersa, Gold va hisobot kechagi holatida qoladi. Xatolar **Monitor** da ko'rinadi. Email xabarnoma faqat tenant ichidagi manzilga ishlaydi.

### Asosiy tushunchalar
- **Delta Lake (Delta jadval)**: Parquet fayllar va `_delta_log` papkasi. Log har bir yozishni tranzaksiya sifatida saqlaydi (ACID), shuning uchun yozish yarmida to'xtasa, o'quvchi eski to'liq versiyani ko'radi. Sxema ham log'da turadi va tarix (time travel) saqlanadi. Lakehouse jadvallari ham, Warehouse ham OneLake'da shu formatda saqlanadi, shuning uchun Warehouse `lh_silver` ni nusxa olmasdan o'qiy oladi.
- **Refresh qanday ishlaydi**: schedule har kuni soat 06:00 da `pl_daily` ni ishga tushiradi. Pipeline avval config'ni GitHub'dan oladi, keyin Bronze'ni qayta yozadi (fayllar ustidan yozish, dataflow'lar **Replace**). Shundan so'ng `nb_silver` Silver'ni to'liq qayta yozadi (overwrite). Keyin SQL endpoint yangilanadi, procedure'lar Gold'ni `DELETE` + `INSERT` bilan qayta yuklaydi. Oxirida Direct Lake modeli yangi Delta versiyaga ulanadi (framing).
- **Idempotency**: bir xil kirish ma'lumoti bilan necha marta ishlatilsa ham, natija bir xil bo'ladi (dublikat paydo bo'lmaydi).

### Tuzoq (haqiqatda bo'lgan)
Birinchi commit'da `Run df_openaq` → `Run nb_silver` strelkasi yo'q edi. Run vaqtlari buni ko'rsatdi: notebook 11:45:59 da boshlandi, `df_openaq` esa 11:46:58 da tugadi. Bu Git'dagi `dependsOn` ni o'qib topildi va tuzatildi. Saboq: commit'dan keyin pipeline JSON'ini tekshirish kerak.

### Natija
Birinchi to'liq run (2026-11-20) taxminan 8 daqiqa davom etdi, hammasi **Succeeded**: `nb_silver` 4m 54s, 7 procedure 45s.

### Ehtimoliy savollar
1. Pipeline'ning qaysi qismi parallel, qaysi qismi ketma-ket ishlaydi va nega?
2. Agar `df_openaq` xato bersa, Power BI'da nima ko'rinadi?
3. Schedule vaqtini qayerdan o'zgartirasiz va bu Git'da qayerda ko'rinadi?
4. Nega har kuni to'liq qayta yuklash (full reload), incremental emas? (Javob: 6 oy kichik hajm, oddiy va idempotent. Ma'lumot ko'paysa, oy bo'yicha `replaceWhere` qilinadi, Phase 2 ga qarang.)
5. Pipeline sizning akkauntingiz nomidan ishlaydi. Siz kompaniyadan ketsangiz nima bo'ladi? (Javob: connection'lar ishlamay qoladi. Production'da service principal yoki workspace identity ishlatiladi.)

### Live change mashqlari
1. Schedule'ni 06:00 dan 07:30 ga o'zgartiring (**Run → Schedule → Edit**) → commit → `.schedules` faylidagi o'zgarishni ko'rsating.
2. `taxi.months` ga `2024-07` ni qo'shing → push → `pl_daily` → **Run**. Pipeline ham, kod ham o'zgarmaydi.
3. Pipeline'ga xato qo'shib ko'ring: `nb_silver` dagi config yo'lini vaqtincha noto'g'ri qiling → **Run** → keyingi qadamlar (`Refresh silver endpoint`, Gold) ishlamaganini Monitor'da ko'rsating → qaytarib tuzating.
