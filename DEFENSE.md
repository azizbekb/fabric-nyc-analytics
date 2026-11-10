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
