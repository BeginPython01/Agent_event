# Project Brief: Event Scout Agent (YAI Singapore 2026/27, quest AI Agents)

> วิธีใช้: เอาไฟล์นี้ไปไว้ใน root ของ repo แล้วพิมพ์ใน Claude Code ว่า
> "อ่าน PROJECT_BRIEF.md แล้วเริ่ม Phase 1"

---

## 1. บทบาทของ AI (อ่านก่อนเริ่มทุกครั้ง)

- เราเป็นนักศึกษา Software Engineering ปี 1 ยังกำลังเรียนรู้อยู่
- คุยเป็นภาษาไทย ใช้ศัพท์เทคนิคเป็นภาษาอังกฤษได้
- **ทุกครั้งที่เขียนโค้ด ให้อธิบายสั้น ๆ ว่าทำไมเขียนแบบนี้** และเลือกวิธีที่อ่านง่ายก่อนวิธีที่เท่
- ทำทีละ phase พอจบ phase ให้หยุด สรุปว่าทำอะไรไป ทดสอบยังไง แล้วรอเราสั่งต่อ
- ถ้าโจทย์ไม่ชัดหรือต้องตัดสินใจเรื่องใหญ่ ให้ถามก่อน ห้ามเดา
- ห้าม commit ไฟล์ `.env` หรือ key ใด ๆ ลง git

---

## 2. โปรเจกต์คืออะไร

Agent ที่ช่วยนักศึกษาหาอีเวนต์ในอนาคต (hackathon, workshop, ค่าย, งานแข่งขัน) จาก **เว็บที่ user เลือกเอง** และ **อีเมล** แล้ว:

1. แกะข้อมูลอีเวนต์ด้วย LLM
2. **เช็กคุณสมบัติ** ว่า user สมัครได้ไหม (ตัดอันที่สมัครไม่ได้ออก ประหยัดเวลา)
3. แนะนำตามความสนใจ พร้อมบอกเหตุผล
4. ส่งให้ user ตัดสินใจผ่าน Telegram (สนใจ / ข้าม / ใส่ปฏิทิน)
5. ส่ง **Weekly digest** ทุกวันอาทิตย์

### เกณฑ์การแข่งขันที่ต้องตอบให้ได้
- AI เป็นแกนหลัก + **ผลลัพธ์เป็นตัวเลข**
- ใช้กับคนนอกวงเพื่อนได้จริง
- คะแนน: Creativity 30%, Understanding 25%, Completeness 20%, Communication 20%, Responsible AI 5%
- **ส่งงานภายใน 9 Jan 2027** / สมัครภายใน 2 Jan 2027

---

## 3. Tech stack (ค่าเริ่มต้น เปลี่ยนได้)

| ส่วน | เครื่องมือ | เหตุผล |
|---|---|---|
| ภาษา | Python 3.11+ | อ่านง่าย library ครบ |
| LLM | Claude API, model `claude-haiku-5-5` + structured output (JSON) | ถูกและเร็ว เหมาะกับงานแกะข้อมูล |
| ดึงเว็บ | `requests` + `BeautifulSoup` (ถ้าเว็บใช้ JS ค่อยเพิ่ม `Playwright`) | เริ่มจากง่ายสุด |
| อีเมล | Gmail API scope `gmail.readonly` (โหมด Testing ไม่เกิน 100 test users) | อ่านอย่างเดียว ปลอดภัย |
| ปฏิทิน | Google Calendar API | ใส่อีเวนต์ให้อัตโนมัติ |
| Database | SQLite | ไม่ต้องตั้ง server |
| แจ้งเตือน | Telegram bot (`python-telegram-bot`) | ฟรี มีปุ่มกดได้ |
| รันอัตโนมัติ | GitHub Actions (cron) หรือ cron บนเครื่อง | ฟรี |
| Config | `.env` + `python-dotenv` | เก็บ key แยกจากโค้ด |

---

## 4. สถาปัตยกรรม

```
[เว็บที่ user เพิ่ม] ─┐
                    ├─> Source text ─> LLM extract (JSON) ─> Dedupe ─> Eligibility check ─> Rank ─> DB
[อีเมล (Gmail)] ─────┘                                                                            │
                                                                     Telegram (ทันที + Weekly digest) <┘
                                                                     User กด สนใจ/ข้าม/ใส่ปฏิทิน ─> feedback ─> ใช้ rank ครั้งถัดไป
```

**หลักสำคัญ:** แยกส่วน "ดึงข้อมูล" (sources) ออกจาก "ประมวลผล" (pipeline) ทุก source ต้องคืนค่าเป็นรูปแบบเดียวกัน (`RawDocument`) เพื่อให้ภายหลังเพิ่ม source ใหม่ (RSS, รูปโปสเตอร์) ได้ง่าย

### โครงสร้างโฟลเดอร์ที่แนะนำ
```
event-scout/
├── src/
│   ├── sources/        # web.py, gmail.py  -> คืนค่า RawDocument
│   ├── extract.py      # เรียก Claude แกะเป็น Event
│   ├── eligibility.py  # เทียบเงื่อนไขกับ profile (โค้ดล้วน ไม่ใช้ LLM)
│   ├── rank.py
│   ├── dedupe.py
│   ├── db.py
│   ├── notify/         # telegram_bot.py, digest.py
│   ├── calendar.py
│   └── models.py       # Pydantic models
├── tests/
├── data/               # sample HTML/อีเมล สำหรับทดสอบ
├── metrics/            # สคริปต์วัดผล
├── .env.example
└── README.md
```

---

## 5. Data models

### RawDocument (ข้อมูลดิบ)
- `source_type`: `"web"` | `"email"`
- `source_ref`: URL หรือ message id
- `title`: ชื่อหน้า หรือ subject
- `sender`: (อีเมลเท่านั้น)
- `text`: เนื้อหาที่ตัด HTML แล้ว
- `links`: list ของลิงก์
- `fetched_at`

### Event (ให้ LLM แกะออกมา)
- `name`, `category` (hackathon / workshop / camp / competition / talk / other)
- `event_start`, `event_end`
- `registration_deadline` ← สำคัญที่สุด
- `location`, `is_online`
- `fee_amount`, `fee_currency`
- `register_url`
- `eligibility`: `age_min`, `age_max`, `birth_year_min`, `birth_year_max`, `student_only`, `allowed_levels` (uni/poly/pre-U/...), `allowed_majors`, `nationality`, `team_size_min`, `team_size_max`, `other_conditions` (text)
- `prizes_or_benefits`
- `source_ref`
- `confidence` (0–1) ต่อ field ที่สำคัญ

**กฎ:** ถ้าไม่เจอข้อมูลในข้อความ ให้เป็น `null` **ห้ามเดา**

### UserProfile
- `birth_year`, `university`, `level`, `year_of_study`, `major`, `nationality`, `max_fee`, `interests` (list), `telegram_chat_id`

### Eligibility result
- `status`: `"eligible"` | `"not_eligible"` | `"unsure"`
- `reasons`: list ของเหตุผลเป็นภาษาคน
- **ถ้าข้อมูลไม่พอหรือ confidence ต่ำ ให้เป็น `unsure` ห้ามตัดทิ้ง**

---

## 6. แผนงาน (Phases)

### Phase 1: Web → Extract MVP (23–29 Nov)
- ตั้ง project, `.env.example`, `models.py`
- `sources/web.py`: รับ URL → โหลด → แปลงเป็น text
- `extract.py`: ส่ง text ให้ Claude → ได้ list ของ `Event`
- CLI: `python -m src.main --url <URL>` แล้ว print ผลออกมา
- ✅ เสร็จเมื่อ: ใส่ URL หน้าอีเวนต์จริง 3 เว็บแล้วแกะได้ถูก

### Phase 2: Database + Change detection + Eligibility (30 Nov–6 Dec)
- SQLite: ตาราง `users`, `watched_urls`, `events`, `feedback`
- เก็บ hash ของ text ถ้าไม่เปลี่ยนให้ข้าม ไม่เรียก LLM
- `eligibility.py` พร้อม unit tests (ทดสอบทั้ง 3 status)
- ✅ เสร็จเมื่อ: รันซ้ำแล้วไม่เรียก LLM กับหน้าที่ไม่เปลี่ยน และ tests ผ่าน

### Phase 3: Gmail source + Dedupe (7–13 Dec)
- OAuth แบบ `gmail.readonly` โหมด Testing
- ดึงเฉพาะอีเมลที่ผ่าน query กรอง เช่น `newer_than:1d (สมัคร OR register OR deadline OR hackathon OR workshop)`
- **ไม่เก็บเนื้อหาอีเมลทั้งฉบับ** เก็บแค่ Event ที่แกะได้
- `dedupe.py`: รวมอีเวนต์ซ้ำจากหลายแหล่ง (เทียบชื่อ + วันจัด)
- ✅ เสร็จเมื่อ: อีเวนต์เดียวกันที่มาจากเว็บและอีเมลแสดงแค่ครั้งเดียว

### Phase 4: Telegram bot + Calendar + Weekly digest (14–20 Dec)
- คำสั่ง: `/start` (สมัคร + กรอก profile), `/addurl`, `/listurls`, `/removeurl`, `/profile`, `/deleteme`
- ส่งอีเวนต์ใหม่พร้อมปุ่ม **สนใจ / ข้าม / ใส่ปฏิทิน**
- กด "ใส่ปฏิทิน" → สร้าง event + reminder ก่อน deadline
- Weekly digest วันอาทิตย์: 🔥 deadline ใกล้ / ⭐ แนะนำ / 📋 อื่น ๆ ที่สมัครได้
- ✅ เสร็จเมื่อ: ใช้งานครบ flow ผ่าน Telegram ได้

### Phase 5: Personalization + ทดสอบกับ user จริง (21–27 Dec)
- `rank.py`: ใช้ interests + feedback (สนใจ/ข้าม) ให้คะแนน และให้ LLM เขียนเหตุผลสั้น ๆ ว่าทำไมเหมาะ
- ตั้ง GitHub Actions ให้รันทุกวัน
- หา user นอกวงเพื่อนอย่างน้อย 10–20 คน มาทดลองใช้
- ✅ เสร็จเมื่อ: มีคนใช้จริงและเก็บ log ได้

### Phase 6: Metrics + Responsible AI + Polish (28 Dec–3 Jan)
- สคริปต์วัดผล (ดูหัวข้อ 7)
- Privacy notice / consent ตอน `/start` และ `/deleteme` ลบข้อมูลได้จริง
- README + วิธีติดตั้ง
- ⚠️ **สมัครแข่งภายใน 2 Jan**

### Phase 7: Demo + Submit (4–9 Jan)
- วิดีโอ demo, สไลด์พรีเซนต์ 10 นาที
- **ส่งงานภายใน 9 Jan**

---

## 7. ตัวเลขที่ต้องเก็บ (ผลลัพธ์เป็นตัวเลข)

- **Extraction accuracy**: ทำ test set ประมาณ 30 หน้า/อีเมล ที่เราเฉลยเอง แล้ววัด % ที่แกะ deadline / วันจัด / เงื่อนไขถูก
- **Eligibility accuracy**: % ที่ตัดสินถูกเทียบกับเฉลย และ % ที่เป็น `unsure`
- **Filter rate**: % ของอีเวนต์ที่ถูกตัดออกเพราะสมัครไม่ได้
- **Time saved**: เวลาที่ user ใช้หาอีเวนต์เองต่อสัปดาห์ เทียบกับตอนใช้ agent (ถามจากแบบสอบถาม)
- **Engagement**: จำนวน user, % ที่กด "สนใจ", จำนวนที่ใส่ปฏิทิน
- **Cost**: ค่า API ต่อ user ต่อเดือน (ดูจาก usage ใน response)

---

## 8. Responsible AI และกฎหมาย (ต้องทำ)

- **PDPA**: ขอ consent ชัดเจน, เก็บข้อมูลเท่าที่จำเป็น, มีคำสั่งลบข้อมูล, ระวัง user อายุต่ำกว่า 20
- **Gmail**: ใช้ `gmail.readonly` เท่านั้น, กรองก่อนส่ง LLM, ไม่เก็บเนื้อหาอีเมลดิบ, โหมด Testing (≤100 test users)
- **Scraping อย่างมีมารยาท**: เช็ก `robots.txt`, ดึงไม่เกินวันละครั้งต่อ URL, ตั้ง User-Agent ที่บอกตัวตน, ไม่ login เข้าเว็บเพื่อดึงข้อมูล (ไม่รองรับ Facebook/IG ใน MVP), แกะแค่ข้อเท็จจริงแล้วลิงก์กลับต้นฉบับ
- **AI อาจผิด**: แสดง confidence, ใช้สถานะ `unsure`, มีลิงก์ต้นฉบับให้ user เช็กเองเสมอ
- **Security**: key อยู่ใน `.env`, ไม่ commit secrets, ป้องกัน SQL injection (ใช้ parameterized query)

---

## 9. Future roadmap (พูดตอนพรีเซนต์ ยังไม่ต้องทำ)
- อ่านโปสเตอร์จากรูป (vision)
- เช็กตารางชนกับ Google Calendar
- สรุปความคุ้มค่า (ค่าใช้จ่าย vs สิ่งที่ได้)
- Team matching
- ให้ผู้จัดงานส่งอีเวนต์เข้ามาเอง
