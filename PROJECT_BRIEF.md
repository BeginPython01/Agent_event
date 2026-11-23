# Project Brief: Scout — Campus Event Agent (YAI Singapore 2026/27, quest AI Agents)

> วิธีใช้: เปิดไฟล์นี้ให้ AI อ่านก่อนเริ่มงานทุกครั้ง แล้วสั่งว่า "เริ่ม Phase X"
> อัปเดตล่าสุด: 23 Nov 2026 (เปลี่ยนทิศทางเป็น Agent-first)

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

**Scout** คือ AI agent ประจำตัวนักศึกษา ที่คอยตามกิจกรรมของมหาวิทยาลัยและงานที่ user สมัครไว้ แล้วจัดการปฏิทินให้

**สิ่งที่ Scout ทำเอง (ทุกวัน):**
1. อ่าน **เว็บข่าว/กิจกรรมของมหาวิทยาลัย** และเว็บอื่นที่ user เพิ่ม → แกะข้อมูลกิจกรรมด้วย LLM
2. อ่าน **อีเมลที่เกี่ยวกับงานที่ user สมัครไว้** (ยืนยันการสมัคร, เลื่อนวัน, ประกาศผล, ของที่ต้องเตรียม)
3. **เช็กคุณสมบัติ** ว่า user สมัครกิจกรรมใหม่ได้ไหม ตัดอันที่สมัครไม่ได้ออก
4. **จัดปฏิทินให้:** ใส่นัดเป็น "ร่าง", ย้ายนัดเมื่อผู้จัดแจ้งเลื่อน, ตั้งเตือน
5. **รายงานตัว** ว่าทำอะไรไปแล้ว และมีเรื่องไหน **รอ user ตัดสินใจ**
6. **เตือนล่วงหน้าเอง** ผ่านแอป / Telegram / LINE
7. รับ **คำสั่งภาษาคน** เช่น "หากิจกรรมที่ได้ชั่วโมงเดือนนี้", "เลื่อนเตือนเป็นพรุ่งนี้เช้า"

**ลำดับความสำคัญของข้อมูล:**
- **หลัก:** กิจกรรมมหาวิทยาลัย (เว็บมอ) + อีเมลงานที่ user สมัครไว้
- **เสริม:** hackathon, workshop, งานแข่งภายนอก, ทุน

### เกณฑ์การแข่งขันที่ต้องตอบให้ได้
- AI เป็นแกนหลัก + **ผลลัพธ์เป็นตัวเลข**
- ใช้กับคนนอกวงเพื่อนได้จริง
- คะแนน: Creativity 30%, Understanding 25%, Completeness 20%, Communication 20%, Responsible AI 5%
- **สมัครภายใน 2 Jan 2027 / ส่งงานภายใน 9 Jan 2027**

---

## 3. Tech stack

| ส่วน | เครื่องมือ | เหตุผล |
|---|---|---|
| Frontend | Next.js + TypeScript + Tailwind + shadcn/ui, ธีม dark glass (ดู `docs/prompts/frontend-glassy-dashboard.md`) | สวย ทำเร็ว เป็น PWA ได้ |
| แอปบนมือถือ | PWA | ติดตั้งลงมือถือได้ ไม่ต้องผ่าน App Store |
| Backend / agent | Python 3.11+ + FastAPI | ใช้โค้ด Phase 1 ต่อได้ |
| LLM | Claude API: `claude-haiku-5-5` + structured output สำหรับแกะข้อมูล/จัดหมวดอีเมล, tool use สำหรับคำสั่งภาษาคน (เปลี่ยน model ได้ใน `.env`) | ถูกและเร็ว |
| ดึงเว็บ | `requests` + `BeautifulSoup` (หน้ารวมข่าว → ตามลิงก์เข้าหน้าข่าว) | เว็บมอเป็น HTML ธรรมดา |
| อีเมล | Gmail API `gmail.readonly` โหมด Testing (≤100 test users) | อ่านอย่างเดียว |
| ปฏิทิน | Google Calendar API `calendar.events` | ต้อง **เขียน** ได้ เพื่อใส่นัดแบบร่าง/ย้ายนัด |
| Database + Login | Supabase (Postgres + Google login), ตอน dev ใช้ SQLite | free tier |
| แจ้งเตือน | Telegram bot (ทำก่อน) + LINE Messaging API (ถ้าทัน) | Telegram ฟรีไม่จำกัด |
| Hosting | Vercel (frontend), Render (backend), Supabase (DB) | free tier |
| รันอัตโนมัติ | GitHub Actions cron (วันละ 2 รอบ: 07:30 และ 20:00) | ฟรี |

**ประมาณค่าใช้จ่าย (20 users):** hosting 0 บาท, Claude API หลักสิบบาท/เดือน

---

## 4. สถาปัตยกรรม

```
[เว็บมอ + เว็บที่ user เพิ่ม] ─┐
                              ├─> RawDocument ─> LLM extract ─> Dedupe ─> Eligibility ─┐
[Gmail: อีเมลงานที่สมัคร] ─────┘        └─> LLM จัดหมวดอีเมล (ยืนยัน/เลื่อน/ผล/อื่น ๆ) ─┤
                                                                                     ▼
                                                          Agent decision (ตารางความอิสระ ข้อ 4.1)
                                                            │            │              │
                                                     ทำเองได้เลย    รอ user ตัดสินใจ    ไม่ทำ
                                                            │            │
                                     Google Calendar (ร่าง/ย้าย/เตือน)    การ์ด "รอคุณตัดสินใจ"
                                                            └─────┬──────┘
                                                                  ▼
                                    AgentAction log (ไทม์ไลน์ + undo) ─> Web app / Telegram / LINE
```

**หลักสำคัญ:**
- ทุก source คืนค่าเป็น `RawDocument` ทุกช่องทางแจ้งเตือนใช้ interface เดียวกัน `send(user, message)`
- **ทุกอย่างที่ Scout ทำต้องลง `AgentAction` log** มีเหตุผล ลิงก์ต้นฉบับ และ undo ได้ (ตรงนี้คือหัวใจของ Responsible AI)
- Frontend คุยกับ backend ผ่าน REST API เท่านั้น

### 4.1 ตารางความอิสระของ Scout

| ระดับ | ตัวอย่าง |
|---|---|
| **ทำเองได้ แล้วแจ้งทีหลัง (undo ได้)** | ใส่นัดเป็น "[ร่าง]" จากอีเมลยืนยันการสมัคร, ย้ายนัดเมื่อผู้จัดแจ้งเลื่อน, ตั้ง/เลื่อนเตือน, ข้ามหน้าเว็บที่ไม่เปลี่ยน |
| **ต้องถามก่อน** | ยืนยันนัดร่างให้เป็นนัดจริง, ใส่กิจกรรมใหม่ที่เพิ่งเจอลงปฏิทิน, ลบนัด, ใช้ข้อความในใบสมัครที่ร่างไว้ |
| **ไม่ทำเด็ดขาด** | ส่งใบสมัคร, ส่งอีเมลแทน user, login เข้าเว็บแทน user, แก้นัดที่ user สร้างเอง |

### 4.2 แหล่งข้อมูลเริ่มต้น
- ข่าวมหาวิทยาลัย: `https://mfu.ac.th/news/news-search.html` (หน้ารวม) → หน้าข่าว `mfu.ac.th/news/news-detail/...`
- ปฏิทินการศึกษา: `https://reg.mfu.ac.th/th/academic-calendar` (ใช้ทีหลังสำหรับเช็กชนสอบ)
- เว็บคณะ/ชมรมที่ user เพิ่มเอง
- ⚠️ ประกาศที่อยู่ใน Facebook / IG / LINE OA ดึงไม่ได้ (ไม่ login แทน user) ให้บอก user ตรง ๆ

### 4.3 หน้าเว็บหลัก (ดู mockup v3)
1. **Scout (หน้าหลัก):** รายงานตัว, รอคุณตัดสินใจ, ปฏิทินสัปดาห์, ไทม์ไลน์ Scout, ช่องสั่งงาน
2. **ปฏิทิน:** นัดที่ยืนยันแล้ว / ร่างโดย Scout / deadline
3. **ค้นพบ:** กิจกรรมใหม่ที่สมัครได้ (มหาลัยก่อน งานเสริมทีหลัง)
4. **สมัครไว้:** board สนใจ → กำลังร่าง → สมัครแล้ว → รอประกาศผล
5. **ร่างใบสมัคร** (เสริม), **Settings** (เชื่อม Gmail/Calendar/Telegram/LINE, ลบบัญชี), **สถิติ**

### 4.4 โครงสร้างโฟลเดอร์ (ย้าย `src/` เข้า `backend/` ตอนเริ่ม Phase 2)
```
Agent_event/
├── backend/
│   ├── src/
│   │   ├── sources/        # web.py, gmail.py -> RawDocument
│   │   ├── extract.py      # แกะกิจกรรม
│   │   ├── email_triage.py # จัดหมวดอีเมล + จับคู่กับงานที่สมัคร
│   │   ├── eligibility.py  # โค้ดล้วน ไม่ใช้ LLM
│   │   ├── agent/          # decide.py (ตาราง 4.1), actions.py (log + undo), commands.py (tool use)
│   │   ├── calendar.py, dedupe.py, rank.py, db.py
│   │   ├── notify/         # base.py, telegram.py, line.py, digest.py
│   │   ├── api/            # FastAPI routes
│   │   └── models.py
│   ├── tests/
│   └── data/
├── frontend/
├── docs/
├── metrics/
└── .github/workflows/
```

---

## 5. Data models

### RawDocument (ข้อมูลดิบ) ✅ มีแล้ว
- `source_type` (`web` | `email`), `source_ref`, `title`, `sender`, `text`, `links`, `fetched_at`

### Event (กิจกรรม) ✅ มีแล้ว
- `name`, `category`, `event_start`, `event_end`, `registration_deadline`, `location`, `is_online`, `fee_amount`, `fee_currency`, `register_url`, `eligibility` (อายุ, ระดับ, สาขา, สัญชาติ, ทีม, เงื่อนไขอื่น), `prizes_or_benefits`, `source_ref`, `confidence`
- เพิ่ม: `organizer` (คณะ/หน่วยงาน/ชมรม), `is_campus` (กิจกรรมในมหาลัยไหม), `activity_hours` (ถ้าประกาศบอก)
- **กฎ:** ถ้าไม่เจอในข้อความ ให้เป็น `null` **ห้ามเดา**

### EmailInsight (ใหม่)
- `message_id`, `category`: `registration_confirmed` | `schedule_changed` | `result_announced` | `organizer_reminder` | `new_opportunity` | `unrelated`
- `event_match` (จับคู่กับ Application/Event ที่มีอยู่), `changes` (เช่น วันเดิม → วันใหม่), `things_to_bring`, `confidence`
- **ไม่เก็บเนื้อหาอีเมลดิบ** เก็บแค่สิ่งที่แกะได้ + `message_id` ไว้ลิงก์กลับ

### Application (ใหม่)
- `user_id`, `event_id`, `lane`: `interested` | `drafting` | `applied` | `awaiting_result` | `done`, `source` (`email` | `manual`)

### AgentAction (ใหม่, ใช้ทำไทม์ไลน์)
- `id`, `user_id`, `created_at`, `kind` (read_source, extract, filter_out, skip_unchanged, calendar_add_draft, calendar_move, reminder_set, command, ...)
- `summary` (ภาษาไทย), `reason`, `source_ref`
- `autonomy`: `auto` | `asked` | `approved` | `rejected` | `undone`
- `undo_payload` (ข้อมูลที่ใช้ย้อนกลับ)

### UserProfile
- `birth_year`, `university`, `level`, `year_of_study`, `major`, `nationality`, `max_fee`, `interests`
- ช่องทางแจ้งเตือนเก็บแยกในตาราง `notification_channels`

### EligibilityResult
- `status`: `eligible` | `not_eligible` | `unsure`, `reasons`
- **ข้อมูลไม่พอหรือ confidence ต่ำ → `unsure` ห้ามตัดทิ้ง**

---

## 6. แผนงาน (Phases)

### Phase 1: Web → Extract MVP (เหลือถึง 26 Nov)
- ✅ `models.py`, `sources/web.py`, `extract.py`, CLI
- เพิ่ม: ตามลิงก์จากหน้ารวมข่าวเข้าไปอ่านหน้าข่าว (จำกัดจำนวนต่อรอบ)
- แก้: ถ้า `robots.txt` redirect ไปหน้า HTML (เว็บมอเป็นแบบนี้) ให้ถือว่าไม่มีกฎ แทนที่จะเอา HTML ไปอ่านเป็นกฎ
- ✅ เสร็จเมื่อ: แกะกิจกรรมจากหน้าข่าวมอจริง 3 หน้าได้ถูก (ต้องมี API key)

### Phase 2: Backend + Database + Eligibility + Agent log (27 Nov–3 Dec)
- ย้ายโค้ดเข้า `backend/`, ตั้ง FastAPI
- ตาราง: `users`, `watched_urls`, `events`, `applications`, `agent_actions`, `notification_channels`
- เก็บ hash ของหน้าเว็บ ถ้าไม่เปลี่ยนให้ข้าม (และลง log ว่าข้าม)
- `eligibility.py` + unit tests ครบ 3 status
- ✅ เสร็จเมื่อ: เรียก API ผ่าน `/docs` ได้, รันซ้ำไม่เรียก LLM กับหน้าที่ไม่เปลี่ยน, tests ผ่าน

### Phase 3: Gmail + Calendar + Agent decisions (4–10 Dec)
- OAuth `gmail.readonly` + `calendar.events` (โหมด Testing)
- `email_triage.py`: จัดหมวดอีเมล + จับคู่กับงานที่สมัคร
- `agent/decide.py`: ทำตามตาราง 4.1 (ร่างนัด, ย้ายนัด, ตั้งเตือน, หรือส่งเข้า "รอคุณตัดสินใจ")
- undo ได้ทุก action ที่ทำเอง
- `dedupe.py`: รวมกิจกรรมเดียวกันจากเว็บและอีเมล
- ⚠️ เช็กก่อนว่าอีเมลนักศึกษาของมอเชื่อมได้ไหม ถ้า admin บล็อก ให้ใช้ Gmail ส่วนตัวแทน
- ✅ เสร็จเมื่อ: อีเมลยืนยันการสมัคร → นัดร่างในปฏิทิน, อีเมลแจ้งเลื่อน → นัดย้ายเอง และกด undo ได้

### Phase 4: Frontend + Login + PWA (11–17 Dec)
- หน้า Scout (รายงานตัว, รอคุณตัดสินใจ, ปฏิทินสัปดาห์, ไทม์ไลน์), ค้นพบ, สมัครไว้
- Google login + consent, PWA
- ✅ เสร็จเมื่อ: ใช้ครบ flow บนมือถือได้ (login → profile → เห็นรายงานตัว → กดอนุมัติ/undo)

### Phase 5: คำสั่งภาษาคน + แจ้งเตือน + cron (18–24 Dec)
- `agent/commands.py`: Claude tool use เรียกเครื่องมือของเราเอง เช่น `search_events`, `list_applications`, `add_draft_to_calendar`, `move_reminder`, `explain_action`
- Telegram (แจ้งเตือน + สั่งงานได้), LINE ถ้าทัน
- เตือนล่วงหน้าเอง + สรุปรายสัปดาห์
- GitHub Actions รันวันละ 2 รอบ
- ✅ เสร็จเมื่อ: พิมพ์สั่งในแอปหรือ Telegram แล้ว Scout ทำได้จริง และได้รับเตือนก่อน deadline

### Phase 6: Personalization + ทดสอบกับ user จริง (25–30 Dec)
- `rank.py`: ใช้ความสนใจ + feedback จัดลำดับ
- ร่างใบสมัคร (ถ้าทัน)
- หา user นอกวงเพื่อน 10–20 คน
- ✅ เสร็จเมื่อ: มีคนใช้จริงและเก็บ log ได้

### Phase 7: Metrics + Responsible AI + Polish (31 Dec–3 Jan)
- สคริปต์วัดผล (ข้อ 7) + หน้าสถิติ, PDPA consent, ลบบัญชีได้จริง, README
- ⚠️ **สมัครแข่งภายใน 2 Jan**

### Phase 8: Demo + Submit (4–9 Jan)
- วิดีโอ demo, สไลด์ 10 นาที
- **ส่งงานภายใน 9 Jan**

**ถ้าเวลาไม่พอ ตัดตามลำดับนี้:** LINE → ร่างใบสมัคร → แหล่งงานเสริม (hackathon) → personalization

---

## 7. ตัวเลขที่ต้องเก็บ (ผลลัพธ์เป็นตัวเลข)

- **Extraction accuracy:** test set ~30 หน้าข่าว/อีเมลที่เฉลยเอง วัด % ที่แกะวันจัด / deadline / เงื่อนไขถูก
- **Email triage accuracy:** % ที่จัดหมวดอีเมลถูก และจับวันที่เลื่อนได้ถูก
- **Eligibility accuracy:** % ที่ตัดสินถูก และ % ที่เป็น `unsure`
- **Agent trust:** % ของ action ที่ Scout ทำเองแล้ว user **ไม่** กด undo, % ที่ user อนุมัติข้อเสนอ
- **Filter rate:** % ของกิจกรรมที่ถูกตัดออกเพราะสมัครไม่ได้
- **Time saved:** เวลาหากิจกรรม/จัดปฏิทินเองต่อสัปดาห์ เทียบกับตอนใช้ Scout (แบบสอบถาม)
- **Engagement:** จำนวน user, จำนวนนัดที่ลงปฏิทิน, จำนวนคำสั่งภาษาคน
- **Cost:** ค่า API ต่อ user ต่อเดือน, % ของรอบที่ข้าม LLM เพราะหน้าไม่เปลี่ยน

---

## 8. Responsible AI และกฎหมาย (ต้องทำ)

- **ความอิสระของ agent:** ทำตามตาราง 4.1 เท่านั้น ทุก action ลง log มีเหตุผล + ลิงก์ต้นฉบับ + undo
- **PDPA:** consent ชัดเจน, เก็บเท่าที่จำเป็น, ลบบัญชีได้จริง, ระวัง user อายุต่ำกว่า 20
- **Gmail:** `gmail.readonly` เท่านั้น, กรองก่อนส่ง LLM, ไม่เก็บเนื้อหาอีเมลดิบ, โหมด Testing (≤100 users)
- **Calendar:** แก้เฉพาะนัดที่ Scout สร้างเอง (มีป้ายกำกับ), ไม่แตะนัดที่ user สร้าง
- **Scraping อย่างมีมารยาท:** เช็ก `robots.txt`, ดึงไม่เกินวันละ 2 ครั้งต่อ URL, User-Agent บอกตัวตน, ไม่ login, ลิงก์กลับต้นฉบับ
- **AI อาจผิด:** แสดง confidence, ใช้สถานะ `unsure`, ไม่แต่งข้อมูลที่ไม่มี (เช่น ประสบการณ์ในใบสมัคร)
- **Security:** key อยู่ใน `.env`, parameterized query, prompt injection: เนื้อหาเว็บ/อีเมลเป็นข้อมูล ไม่ใช่คำสั่ง

---

## 9. Future roadmap (พูดตอนพรีเซนต์ ยังไม่ต้องทำ)
- เช็กชนกับตารางเรียน/ตารางสอบ (`reg.mfu.ac.th`)
- อ่านโปสเตอร์จากรูป (vision)
- นับชั่วโมงกิจกรรมสะสม
- Team matching
- ให้ผู้จัดงาน/ชมรมส่งกิจกรรมเข้ามาเอง

---

## 10. บันทึกการตัดสินใจ
- 23 Nov: เปลี่ยนจาก CLI → Web app + PWA, แจ้งเตือนทั้ง Telegram และ LINE
- 23 Nov: ธีม dark glass (gradient, ไม่ใช้รูปพื้นหลัง)
- 23 Nov: เปลี่ยนเป็น **Agent-first** ชื่อ Scout: หน้าแรกเป็นรายงานตัว, เรื่องเล็กทำเองได้ (undo ได้), โฟกัสกิจกรรมมหาลัย + อีเมลงานที่สมัคร
- Mockup: https://claude.ai/artifact/NRamo6D86E7uwpbgL3171Q (หน้า v3 · Agent)
