# NetSage AI — Implementation Plan

Build an AI-assisted network troubleshooting tool for Cisco Packet Tracer labs with human review.

---

## Open Questions

> [!NOTE]
> **Demo video** is listed as a deliverable (5–10 min). I can build everything else, but you'll need to screen-record the demo yourself once the project is working. I can guide you on what to show.

---

## Requirement Checklist (from the document)

Every row below maps directly to something in the problem statement. Nothing is skipped.

| # | Document Requirement | How We'll Cover It | Deliverable |
|---|---|---|---|
| 1 | 30+ cases across VLAN, gateway, DHCP, DNS, routing, ACL, NAT, wireless | `cases.csv` with 32 cases, 4 per fault type | `cases.csv` |
| 2 | Evidence per case: symptom, topology note, show outputs, expected fault, OSI layer, concept tag | CSV columns for all these fields + severity | `cases.csv` |
| 3 | Structured prompts → JSON with root_cause, confidence, evidence, next_command, fix_steps | `prompts/diagnose_prompt.md` with 2–3 worked examples | Prompt files |
| 4 | Rule checker: duplicate IPs, wrong masks, gateway mismatch, interface down, missing VLAN, missing routes | `rule_checker.py` — standalone Python script | Python checker |
| 5 | AI diagnosis: feed cases, save response, compare with known answer | `run_diagnosis.py` — batch script that calls Gemini API | AI responses JSON |
| 6 | Human review: Accept / Edit / Reject + log wrong AI answers | Web UI with review buttons + log saved to JSON | Reviewer log |
| 7 | Dashboard: issue type counts, severity, AI vs human agreement rate | Web page with Chart.js charts | Dashboard |
| 8 | Responsible AI log: 5+ cases where AI was corrected | Dedicated page + `responsible_ai_log.json` | Responsible AI log |
| 9 | Demo video | You screen-record the working app | Demo video |

---

## Tech Stack (beginner-friendly)

| Layer | Tool | Why |
|---|---|---|
| Language | Python 3 | Simple, you already have it |
| Web framework | Flask | Minimal setup, beginner-friendly |
| Frontend | HTML + vanilla CSS + vanilla JS | No frameworks to learn |
| Charts | Chart.js (CDN) | One script tag, easy bar/pie/doughnut charts |
| AI API | OpenRouter (`openai` SDK) | You already have an account, cheap models, OpenAI-compatible |
| AI Model | `google/gemini-2.0-flash-001` | ~$0.01 for all 32 cases, great at JSON output |
| Data storage | CSV + JSON files | No database needed |

---

## Project Structure

```
netcad/
├── .env                          # API key + model config (not committed to git)
├── app.py                        # Flask web app (main entry point)
├── cases.csv                     # 30+ troubleshooting cases
├── rule_checker.py               # Deterministic rule-checking script
├── run_diagnosis.py              # Batch AI diagnosis runner
├── requirements.txt              # pip dependencies
│
├── prompts/
│   ├── diagnose_prompt.md        # Main structured prompt with examples
│   └── followup_prompt.md        # Helper prompt for follow-up questions
│
├── data/
│   ├── ai_responses.json         # Saved AI diagnosis outputs
│   ├── human_reviews.json        # Accept/Edit/Reject log
│   └── responsible_ai_log.json   # 5+ corrected AI cases with explanations
│
├── templates/                    # Flask HTML templates
│   ├── base.html                 # Shared layout (nav, footer)
│   ├── dashboard.html            # Dashboard with charts
│   ├── cases.html                # Browse all cases
│   ├── diagnose.html             # Run AI diagnosis on a case
│   ├── review.html               # Human review interface
│   └── responsible_ai.html       # Responsible AI log viewer
│
└── static/
    ├── style.css                 # All styling
    └── script.js                 # Chart rendering + UI interactions
```

---

## Proposed Changes

### Component 1 — Case Dataset

#### [NEW] [cases.csv](file:///c:/Users/prati/OneDrive/Documents/netcad/cases.csv)

A CSV file with **32 cases** (4 per fault type × 8 fault types):

**Fault types covered:** VLAN (4), Gateway/Routing (4), DHCP (4), DNS (4), ACL (4), NAT (4), Wireless (4), Interface/Layer 1 (4)

**Columns:**
| Column | Example |
|---|---|
| `case_id` | `CASE-001` |
| `symptom` | "PC1 in VLAN 10 cannot ping PC2 in VLAN 20" |
| `topology_note` | "2 switches, 1 router, router-on-a-stick config" |
| `show_outputs` | Multi-line show command outputs (show vlan brief, show ip route, etc.) |
| `expected_fault` | "Trunk port not configured between switch and router" |
| `expected_osi_layer` | "Layer 2" |
| `concept_tag` | "VLAN" |
| `severity` | "High" / "Medium" / "Low" |

All show outputs will be realistic Cisco CLI output (e.g., `show vlan brief`, `show ip route`, `show running-config`, `show interfaces`, etc.).

---

### Component 2 — Prompt Files

#### [NEW] [diagnose_prompt.md](file:///c:/Users/prati/OneDrive/Documents/netcad/prompts/diagnose_prompt.md)

The main structured prompt that:
- Accepts symptom, topology note, and show outputs as input
- Forces **JSON output** with these exact fields:
  - `root_cause` — what is likely wrong
  - `confidence` — "high" / "medium" / "low"
  - `evidence` — quotes from the show output that support the diagnosis
  - `next_command` — what command to run next for more info
  - `fix_steps` — ordered list of commands to fix the issue
  - `osi_layer` — which OSI layer the fault belongs to
- Includes **3 worked examples** (one VLAN, one DHCP, one ACL) showing full input → JSON output

#### [NEW] [followup_prompt.md](file:///c:/Users/prati/OneDrive/Documents/netcad/prompts/followup_prompt.md)

A helper prompt for when additional show output is available after running the suggested `next_command`.

---

### Component 3 — Rule Checker (Python)

#### [NEW] [rule_checker.py](file:///c:/Users/prati/OneDrive/Documents/netcad/rule_checker.py)

A standalone Python script with **6 deterministic checks**. Each function parses show-command text and returns findings:

```python
def check_duplicate_ips(show_output) -> list        # Finds repeated IP addresses
def check_wrong_subnet_mask(show_output) -> list     # Detects mismatched masks
def check_gateway_mismatch(show_output) -> list      # PC gateway ≠ router interface IP
def check_interface_down(show_output) -> list        # Interfaces in down/down state
def check_missing_vlan(show_output) -> list          # VLAN referenced but not in show vlan brief
def check_missing_route(show_output) -> list         # Destination network not in routing table
```

- Can be run standalone: `python rule_checker.py` (processes all cases from `cases.csv` and prints findings)
- Also imported by `app.py` to show rule-check results in the web UI
- Uses only **standard library** (`re`, `csv`, `json`) — no extra installs

---

### Component 4 — AI Diagnosis Runner

#### [NEW] [run_diagnosis.py](file:///c:/Users/prati/OneDrive/Documents/netcad/run_diagnosis.py)

Batch script that:
1. Reads all cases from `cases.csv`
2. For each case, builds the prompt from `diagnose_prompt.md` + case data
3. Calls Gemini API → gets JSON response
4. Saves each response to `data/ai_responses.json`
5. Compares AI's `root_cause` with `expected_fault` from CSV
6. Prints a summary: how many matched, how many didn't

Can be run standalone: `python run_diagnosis.py`

---

### Component 5 — Flask Web App

#### [NEW] [app.py](file:///c:/Users/prati/OneDrive/Documents/netcad/app.py)

Simple Flask app with these routes:

| Route | Page | What it does |
|---|---|---|
| `/` | Dashboard | Charts: cases by fault type, severity distribution, AI agreement rate |
| `/cases` | Case Browser | Table of all 32 cases, click to view details |
| `/diagnose/<case_id>` | AI Diagnosis | Shows case info → runs rule checker → calls AI → shows JSON result |
| `/review` | Human Review | Lists cases with AI responses. Buttons: Accept / Edit / Reject. Saves to `human_reviews.json` |
| `/responsible-ai` | Responsible AI Log | Shows the 5+ corrected cases with explanations |

---

### Component 6 — HTML Templates

#### [NEW] `templates/base.html`
Shared layout: navigation bar across the top (Dashboard · Cases · Diagnose · Review · Responsible AI), clean content area, footer.

#### [NEW] `templates/dashboard.html`
- **Bar chart**: Case count by fault type (VLAN, DHCP, DNS, etc.)
- **Pie chart**: Severity distribution (High / Medium / Low)
- **Doughnut chart**: AI vs Human agreement (Accepted / Edited / Rejected)
- **Stats cards**: Total cases, total reviewed, AI accuracy %

#### [NEW] `templates/cases.html`
- Sortable/filterable table of all cases
- Click a case → expands to show full details + show outputs

#### [NEW] `templates/diagnose.html`
- Dropdown to pick a case (or show the selected case)
- "Run Rule Check" button → shows deterministic findings
- "Run AI Diagnosis" button → shows formatted JSON response
- Side-by-side: AI response vs expected answer

#### [NEW] `templates/review.html`
- Lists each case with its AI diagnosis
- Three buttons per case: **Accept** ✅ / **Edit** ✏️ / **Reject** ❌
- Edit opens a text area to type corrections
- All decisions saved to `data/human_reviews.json`

#### [NEW] `templates/responsible_ai.html`
- Shows 5+ cases where the AI was wrong
- For each: what AI said, what was correct, why AI was wrong

---

### Component 7 — Static Assets

#### [NEW] [style.css](file:///c:/Users/prati/OneDrive/Documents/netcad/static/style.css)
Clean, professional styling. No frameworks. Light color scheme with:
- Muted blue/teal accent palette
- Clean card-based layout
- Readable monospace for show-command outputs
- Responsive layout (works on laptop screens)

#### [NEW] [script.js](file:///c:/Users/prati/OneDrive/Documents/netcad/static/script.js)
- Chart.js initialization for dashboard charts
- Review button click handlers (AJAX calls to Flask)
- Case expand/collapse in cases page

---

### Component 8 — Data Files

#### [NEW] `data/ai_responses.json`
Auto-generated by `run_diagnosis.py`. Structure:
```json
{
  "CASE-001": {
    "root_cause": "...",
    "confidence": "high",
    "evidence": "...",
    "next_command": "...",
    "fix_steps": ["..."],
    "osi_layer": "Layer 2"
  }
}
```

#### [NEW] `data/human_reviews.json`
Populated by the review page. Structure:
```json
{
  "CASE-001": {
    "status": "accepted",
    "reviewer_notes": "",
    "timestamp": "2026-08-18T11:00:00"
  }
}
```

#### [NEW] `data/responsible_ai_log.json`
Pre-populated with 5+ entries. Structure:
```json
[
  {
    "case_id": "CASE-005",
    "ai_said": "DHCP pool exhaustion",
    "correct_answer": "DHCP pool network mismatch",
    "why_ai_was_wrong": "AI focused on pool size but missed that the network statement didn't match the VLAN subnet",
    "lesson_learned": "Always verify DHCP pool network matches the interface subnet"
  }
]
```

---

### Component 9 — Dependencies

#### [NEW] [requirements.txt](file:///c:/Users/prati/OneDrive/Documents/netcad/requirements.txt)
```
flask
openai
python-dotenv
```
Just 3 lightweight dependencies.

#### [NEW] `.env`
```env
OPENROUTER_API_KEY=your-key-here
MODEL=google/gemini-2.0-flash-001
```
Configurable — swap the model anytime without changing code. The `.env` file keeps your API key out of the source code.

---

## Build Order

I will build the project in this order (dependencies first):

| Step | What | Why first |
|---|---|---|
| 1 | `cases.csv` | Everything depends on the case data |
| 2 | `prompts/` | AI diagnosis needs the prompt templates |
| 3 | `rule_checker.py` | Standalone, no web dependency |
| 4 | `run_diagnosis.py` + data files | Generates AI responses |
| 5 | `requirements.txt` | Need Flask installed before web app |
| 6 | `static/style.css` | Design system before templates |
| 7 | `templates/` (all HTML) | UI pages |
| 8 | `static/script.js` | Dashboard charts + interactions |
| 9 | `app.py` | Ties everything together |
| 10 | Test & verify | Make sure everything works |

---

## Verification Plan

### Automated Tests
```bash
# 1. Rule checker runs without errors on all cases
python rule_checker.py

# 2. AI diagnosis runs (at least 1 case) — requires API key
python run_diagnosis.py --test

# 3. Flask app starts without errors
python app.py
```

### Manual Verification
- Open dashboard → all 3 charts render with correct data
- Browse cases → all 32 cases visible with correct fields
- Run diagnosis on 1 case → JSON response displayed correctly
- Review a case → Accept/Edit/Reject saves to `human_reviews.json`
- Responsible AI page → shows 5+ corrected entries
- Rule checker standalone → prints findings for sample cases
