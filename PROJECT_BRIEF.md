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

## 3. Tech stack (อัปเดต 23 Nov: เปลี่ยนเป็น Web app + PWA)

| ส่วน | เครื่องมือ | เหตุผล |
|---|---|---|
| Frontend | **Next.js (React) + TypeScript + Tailwind CSS + shadcn/ui** | สวยแบบมืออาชีพได้เร็ว มี component สำเร็จรูป (card, dialog, form) และเป็นที่นิยมที่สุด หาตัวอย่างง่าย |
| แอปบนมือถือ | **PWA** (manifest + service worker) | กด "ติดตั้ง" ลงหน้าจอมือถือได้เหมือนแอป ไม่ต้องผ่าน App Store ฟรี |
| Backend / pipeline | **Python 3.11+ + FastAPI** | ใช้โค้ด Phase 1 ต่อได้เลย FastAPI ใช้ Pydantic ตัวเดียวกัน และสร้างหน้า API docs ให้อัตโนมัติ |
| LLM | Claude API, model `claude-haiku-5-5` + structured output (JSON) | ถูกและเร็ว เหมาะกับงานแกะข้อมูล |
| ดึงเว็บ | `requests` + `BeautifulSoup` (ถ้าเว็บใช้ JS ค่อยเพิ่ม `Playwright`) | เริ่มจากง่ายสุด |
| Database + Login | **Supabase** (Postgres + Auth แบบ Google login) | free tier พอ, login ด้วย Google ได้ทันที (ตอนพัฒนาบนเครื่องใช้ SQLite ได้) |
| อีเมล | Gmail API scope `gmail.readonly` (โหมด Testing ไม่เกิน 100 test users) | อ่านอย่างเดียว ปลอดภัย |
| ปฏิทิน | Google Calendar API | ใส่อีเวนต์ให้อัตโนมัติ |
| แจ้งเตือน | **Telegram bot + LINE Messaging API** (user เลือกได้ หรือใช้ทั้งคู่) | Telegram ฟรีไม่จำกัด / LINE คนไทยใช้เยอะ แต่ free plan จำกัดจำนวน push ต่อเดือน (เช็กตัวเลขตอนสมัคร) จึงใช้ LINE ส่งเฉพาะ digest + deadline ใกล้ (หมายเหตุ: LINE Notify ปิดไปแล้ว ต้องใช้ Messaging API) |
| Hosting | Vercel (frontend), Render (backend), Supabase (DB) | free tier ทั้งหมด (Render free จะหลับเมื่อไม่มีคนใช้ ตื่นช้า ~30-60 วิ) |
| รันอัตโนมัติ | GitHub Actions (cron) | ฟรี ใช้รัน pipeline ทุกวัน + digest วันอาทิตย์ |
| Config | `.env` + `python-dotenv` / `.env.local` (Next.js) | เก็บ key แยกจากโค้ด |

**ประมาณค่าใช้จ่าย (20 users):** hosting 0 บาท, Claude API หลักสิบบาท/เดือน, LINE ฟรีถ้าไม่เกินโควตา

---

## 4. สถาปัตยกรรม

```
[เว็บที่ user เพิ่ม] ─┐
                    ├─> Source text ─> LLM extract (JSON) ─> Dedupe ─> Eligibility check ─> Rank ─> DB (Supabase)
[อีเมล (Gmail)] ─────┘                                                                                │
                                                     ┌──────────────────────────────────────────────┤
                                                     ▼                                              ▼
                                       Web app / PWA (Next.js)                         Telegram / LINE
                                       feed, profile, URLs, สถิติ                       (ทันที + Weekly digest)
                                                     │                                              │
                                                     └── User กด สนใจ/ข้าม/ใส่ปฏิทิน ─> feedback ─> ใช้ rank ครั้งถัดไป
```

**หลักสำคัญ:**
- แยกส่วน "ดึงข้อมูล" (sources) ออกจาก "ประมวลผล" (pipeline) ทุก source ต้องคืนค่าเป็น `RawDocument` เพื่อเพิ่ม source ใหม่ได้ง่าย
- แจ้งเตือนก็เหมือนกัน: ทุกช่องทางต้อง implement interface เดียวกัน (`send(user, message)`) เพื่อเพิ่มช่องทางใหม่ได้ง่าย
- Frontend คุยกับ backend ผ่าน REST API เท่านั้น ไม่แตะ DB ตรง

### หน้าเว็บหลัก
1. **Landing + Login** (Google) พร้อม privacy notice / consent
2. **Onboarding / Profile**: ปีเกิด, ระดับการศึกษา, สาขา, สัญชาติ, งบค่าสมัคร, ความสนใจ
3. **Feed อีเวนต์**: card แสดง deadline, สถานะ eligible/unsure, เหตุผล, confidence, ปุ่ม สนใจ/ข้าม/ใส่ปฏิทิน, ลิงก์ต้นฉบับ
4. **เว็บที่ติดตาม**: เพิ่ม/ลบ URL, ดูว่าดึงล่าสุดเมื่อไหร่
5. **Settings**: เชื่อม Telegram / LINE, เชื่อม Gmail, ลบบัญชี
6. **สถิติ** (ของ user + ภาพรวมระบบ): จำนวนอีเวนต์ที่เจอ/ถูกกรอง, เวลาที่ประหยัด (ใช้ตอนพรีเซนต์)

### โครงสร้างโฟลเดอร์ (ย้าย `src/` เข้า `backend/` ตอนเริ่ม Phase 2)
```
Agent_event/
├── backend/
│   ├── src/
│   │   ├── sources/        # web.py, gmail.py  -> RawDocument
│   │   ├── extract.py      # เรียก Claude แกะเป็น Event
│   │   ├── eligibility.py  # เทียบเงื่อนไขกับ profile (โค้ดล้วน ไม่ใช้ LLM)
│   │   ├── rank.py, dedupe.py, db.py, calendar.py
│   │   ├── notify/         # base.py, telegram.py, line.py, digest.py
│   │   ├── api/            # FastAPI routes
│   │   └── models.py
│   ├── tests/
│   └── data/
├── frontend/               # Next.js + Tailwind + shadcn/ui (PWA)
├── metrics/
├── .github/workflows/      # cron
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
- `birth_year`, `university`, `level`, `year_of_study`, `major`, `nationality`, `max_fee`, `interests` (list)
- ช่องทางแจ้งเตือนเก็บแยกในตาราง `notification_channels` (`telegram_chat_id`, `line_user_id`)

### Eligibility result
- `status`: `"eligible"` | `"not_eligible"` | `"unsure"`
- `reasons`: list ของเหตุผลเป็นภาษาคน
- **ถ้าข้อมูลไม่พอหรือ confidence ต่ำ ให้เป็น `unsure` ห้ามตัดทิ้ง**

---

## 6. แผนงาน (Phases) — อัปเดต 23 Nov

### Phase 1: Web → Extract MVP ✅ โค้ดเสร็จ (เหลือทดสอบกับเว็บจริง 3 เว็บเมื่อมี API key)
- `models.py`, `sources/web.py`, `extract.py`, CLI `python -m src.main --url <URL>`

### Phase 2: Backend + Database + Eligibility (24–30 Nov)
- ย้ายโค้ดเข้า `backend/`, ตั้ง FastAPI
- DB: ตาราง `users`, `watched_urls`, `events`, `user_events` (สถานะ/feedback), `notification_channels`
- เก็บ hash ของ text ถ้าไม่เปลี่ยนให้ข้าม ไม่เรียก LLM
- `eligibility.py` พร้อม unit tests (ทดสอบทั้ง 3 status)
- API: profile, watched URLs, events feed, feedback
- ✅ เสร็จเมื่อ: เรียก API ผ่านหน้า `/docs` ได้ครบ, รันซ้ำไม่เรียก LLM กับหน้าที่ไม่เปลี่ยน, tests ผ่าน

### Phase 3: Frontend + Login + PWA (1–7 Dec)
- Next.js + Tailwind + shadcn/ui, ออกแบบ UI ให้สวยและใช้บนมือถือได้ดี
- Google login (Supabase Auth) + consent, หน้า Profile, หน้าเว็บที่ติดตาม, หน้า Feed
- PWA manifest ให้ติดตั้งบนมือถือได้
- ✅ เสร็จเมื่อ: สมัคร → กรอก profile → เพิ่ม URL → เห็นอีเวนต์ใน feed ได้บนมือถือ

### Phase 4: Telegram + LINE + Weekly digest (8–14 Dec)
- หน้า Settings: เชื่อมบัญชี Telegram / LINE (กดลิงก์ → bot ผูกกับ user)
- แจ้งเตือนอีเวนต์ใหม่ (Telegram ทันที, LINE เฉพาะสำคัญ) พร้อมปุ่ม สนใจ/ข้าม
- Weekly digest วันอาทิตย์: 🔥 deadline ใกล้ / ⭐ แนะนำ / 📋 อื่น ๆ ที่สมัครได้
- GitHub Actions รัน pipeline ทุกวัน
- ✅ เสร็จเมื่อ: ได้รับแจ้งเตือนทั้งสองช่องทาง และกดปุ่มแล้วสถานะในเว็บเปลี่ยนตาม

### Phase 5: Gmail + Calendar + Dedupe (15–21 Dec)
- OAuth `gmail.readonly` โหมด Testing, ดึงเฉพาะอีเมลที่ผ่าน query กรอง, **ไม่เก็บเนื้อหาอีเมลดิบ**
- `dedupe.py`: รวมอีเวนต์ซ้ำจากหลายแหล่ง (เทียบชื่อ + วันจัด)
- ปุ่ม "ใส่ปฏิทิน" → Google Calendar + reminder ก่อน deadline
- ✅ เสร็จเมื่อ: อีเวนต์เดียวกันจากเว็บและอีเมลแสดงครั้งเดียว และใส่ปฏิทินได้

### Phase 6: Personalization + ทดสอบกับ user จริง (22–28 Dec)
- `rank.py`: interests + feedback ให้คะแนน + LLM เขียนเหตุผลสั้น ๆ
- หา user นอกวงเพื่อน 10–20 คน มาลองใช้ เก็บ log
- ✅ เสร็จเมื่อ: มีคนใช้จริงและเก็บ log ได้

### Phase 7: Metrics + Responsible AI + Polish (29 Dec–3 Jan)
- สคริปต์วัดผล (หัวข้อ 7) + หน้าสถิติ
- ลบบัญชีได้จริง, README + วิธีติดตั้ง
- ⚠️ **สมัครแข่งภายใน 2 Jan**

### Phase 8: Demo + Submit (4–9 Jan)
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
- **LINE / Telegram**: เก็บแค่ chat id / user id ที่จำเป็น, ลบออกเมื่อ user ยกเลิกการเชื่อม
- **Security**: key อยู่ใน `.env`, ไม่ commit secrets, ป้องกัน SQL injection (ใช้ parameterized query)

---

## 9. Future roadmap (พูดตอนพรีเซนต์ ยังไม่ต้องทำ)
- อ่านโปสเตอร์จากรูป (vision)
- เช็กตารางชนกับ Google Calendar
- สรุปความคุ้มค่า (ค่าใช้จ่าย vs สิ่งที่ได้)
- Team matching
- ให้ผู้จัดงานส่งอีเวนต์เข้ามาเอง
