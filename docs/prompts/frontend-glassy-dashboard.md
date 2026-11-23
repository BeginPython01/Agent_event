# Prompt: Event Scout frontend shell (adapted from glassy-dashboard)

> ใช้ตอน Phase 3 วาง prompt นี้ใน Claude Code แล้วแนบโค้ดต้นฉบับ `glassy-dashboard.tsx` (จาก 21st.dev) ต่อท้าย
> ไม่ได้เก็บโค้ดต้นฉบับไว้ใน repo เพราะเป็นโค้ดของคนอื่น

---

You are given a task to integrate an existing React component (`glassy-dashboard.tsx`, attached below) into the Event Scout frontend and adapt it into the app shell.

## 0. Project setup

The frontend lives in `frontend/` and must use:
- Next.js (App Router) + TypeScript
- Tailwind CSS
- shadcn project structure (components in `frontend/components/ui`)

If `frontend/` does not exist yet, set it up with `npx shadcn@latest init` (Next.js template). If the default components path is not `components/ui`, explain why it matters (shadcn CLI installs and imports from there) and create it.

Copy the component to `frontend/components/ui/glassy-dashboard.tsx`, then make the changes below. Explain each change briefly; the developer is a first-year student.

Install:
```bash
npm i gsap @gsap/react lucide-react @fontsource-variable/manrope @fontsource/ibm-plex-sans-thai
```

## 1. Style direction: "mixed glass"

- Keep the glass look for the **top bar, dock, dialogs and stage frame**.
- Event cards, board cards and form areas use a **near-solid surface** (`--gd-card` with alpha ≥ 0.85) so text is easy to read.
- Below 760px: cap `backdrop-filter` blur at 8px and make panels solid, so mid-range phones stay smooth.
- Keep all existing accessibility behaviour: focus rings, `prefers-reduced-motion`, `prefers-reduced-transparency`, `forced-colors`.

## 2. Theme: dark first, cool indigo palette

- `initialTheme` defaults to `"dark"`. Keep the light/dark toggle in the top bar and remember the choice in `localStorage` (wrap in try/catch).
- Replace the warm brown palette with these tokens:

| token | dark (default) | light |
|---|---|---|
| app background | `#0E1222` | `#EEF1FA` |
| `--gd-ink` | `#EEF0FF` | `#14161F` |
| `--gd-muted` | `#B4BAD6` | `#4A5068` |
| `--gd-surface` | `#1B2038` | `#F7F8FC` |
| `--gd-card` | `rgb(30 35 60 / 88%)` | `rgb(255 255 255 / 88%)` |
| `--gd-primary` / `--gd-primary-ink` | `#8E9BFF` / `#0E1226` | `#3D4ED8` / `#FFFFFF` |
| `--gd-teal` (eligible / สมัครได้) | `#6EE0B8` | `#0E6A3B` |
| `--gd-ochre` (unsure / ไม่แน่ใจ) | `#F5C35B` | `#8A5A00` |
| `--gd-coral` (deadline soon) | `#FF9A85` | `#B23A1E` |
| `--gd-focus` | `#A9B4FF` | `#2F3DB0` |

  Derive the remaining glass tokens (`--gd-rim`, `--gd-gloss`, `--gd-rail`, `--gd-inner`, `--gd-raised`, `--gd-line`, `--gd-track`) from the same cool indigo hue. Check every text/background pair meets 4.5:1 contrast.

## 3. Background: soft gradient, no photo

- Remove the background `<img>`, the Unsplash photo URL and the photo credit in the footer.
- Use a CSS-only gradient behind the glass:
  - dark: `radial-gradient(1200px 800px at 15% 10%, #2B2F6B, transparent 60%), radial-gradient(900px 700px at 85% 30%, #1E4A5C, transparent 55%), radial-gradient(800px 600px at 50% 100%, #3A2357, transparent 60%), #0E1222`
  - light: the same shapes with `#C9D0FF`, `#BFE7EF`, `#E3D2F5` on `#EEF1FA`

## 4. Thai text support (important)

- Font stack: `"Manrope Variable", "IBM Plex Sans Thai", system-ui, sans-serif` (Manrope has no Thai glyphs, so Thai falls back to IBM Plex Sans Thai). Import `@fontsource/ibm-plex-sans-thai/400.css`, `500.css`, `600.css`, `700.css`.
- **Remove negative `letter-spacing`** on headings and numbers that can contain Thai: it breaks Thai vowels and tone marks.
- Set `line-height` ≥ 1.3 on headings (the original 1.03 clips Thai marks above and below the line).
- All UI copy is Thai, with English kept for tech words (Hackathon, Workshop, Feed).

## 5. Views (replace the 4 sales views)

| original view | new view | content |
|---|---|---|
| `command` | `feed` · "อีเวนต์สำหรับคุณ" | summary metrics (ใกล้ปิดรับ / สมัครได้ / กรองออกให้แล้ว), filter chips (ทั้งหมด / สมัครได้ / ไม่แน่ใจ / สนใจแล้ว), event cards |
| `operations` | `board` · "ใบสมัครของฉัน" | the lane board, lanes: **สนใจ → กำลังร่าง → สมัครแล้ว → รอประกาศผล** |
| `trends` + `metrics` | `stats` · "สถิติ" | time saved, filter rate, funnel (เจอ → สมัครได้ → สนใจ → ใส่ปฏิทิน), weekly bar chart, AI transparency (จำนวน unsure, ค่า AI) |
| new | `sources` · "แหล่งข้อมูล" | watched URLs with fetch status, add/remove URL, connect Gmail |

- Settings opens from a gear icon in the top bar (next to the theme toggle), not from the dock.
- Remove the CSV export buttons. The period switch becomes `สัปดาห์นี้ / เดือนนี้` and only shows on `stats`.

## 6. Event card (feed)

Each card shows: category chip, status chip (สมัครได้ = teal, ไม่แน่ใจ = ochre, with an icon, not color alone), deadline badge (coral when ≤ 7 days), name, dates, place (online/onsite), fee, "ทำไมแนะนำ" reason (or "ควรเช็กก่อน" reason when unsure), "ความมั่นใจของ AI xx%", links **ร่างใบสมัคร** and **ดูต้นฉบับ**, buttons **ข้าม / สนใจ / ใส่ปฏิทิน** (min 44px tall).

## 7. Board (application tracker)

- Cards show event name, deadline, and a draft progress like "พร้อม 4/8".
- Clicking a card opens the existing dialog with: status badge, deadline, links to the draft page and the source page, and a button to move it to the next lane.

## 8. AI search bar (orb)

- Keep the orb + typing prompt animation. Prompts rotate per view, in Thai, e.g. "มี hackathon สาย AI ที่ปิดรับเดือนนี้ไหม?", "ใบสมัครไหนใกล้ deadline?".
- For now the dialog filters the local sample events by text. Leave a clear `TODO` where it will later call the backend API.

## 9. Animation

Keep the GSAP animations (count-up numbers, bars growing, line reveal, blur on view change, dock indicator). Keep the reduced-motion fallback.

## 10. Data

- Move sample data into `frontend/lib/sample-data.ts` with TypeScript types matching the backend models: `Event` (name, category, registration_deadline, event_start, event_end, location, is_online, fee_amount, register_url, confidence), `EligibilityResult` (status: eligible / not_eligible / unsure, reasons), `Application` (event id, lane, progress).
- Label sample numbers as sample data (a small "ข้อมูลตัวอย่าง" pill in the footer).
- No real names, emails or other personal data in the sample data.

## Done when

- `npm run dev` shows the shell in dark mode with all 4 views working, on both a 390px phone width and desktop.
- Thai text renders without clipped vowels.
- `npm run build` and `npx tsc --noEmit` pass.

---

(แนบโค้ด `glassy-dashboard.tsx` และ `demo.tsx` ต้นฉบับต่อจากบรรทัดนี้)
