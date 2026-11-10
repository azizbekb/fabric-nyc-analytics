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
