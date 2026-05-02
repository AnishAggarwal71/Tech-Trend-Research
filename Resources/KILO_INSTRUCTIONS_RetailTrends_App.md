# Kilo Build Instructions — Retail Trends Analysis App
**Version:** 1.0  
**Stack:** Python · Streamlit · Anthropic Claude API · openpyxl · python-docx  
**Deployment target (v1):** Local / Streamlit Community Cloud (free tier)  
**Scaling path (v2+):** Noted inline — look for `[SCALE-UP]` tags

---

## 1. What This App Does

A step-by-step hybrid analysis tool. A user enters three parameters (country, timeline, retailers), then moves through a guided workflow where Claude assists with each analytical step — the user reviews and edits before advancing. At the end, the app generates two downloadable files:

- **Excel workbook** — all six appendix tables (Pulse Ledger, Whisper Tags, Macro Trend Map, CIPHER Map, Attribute-Led Map, Tech Trend Map)
- **Word document** — structured Front Section executive readout

The app does **not** persist data between sessions. Everything lives in `st.session_state`.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   Streamlit UI                      │
│  Sidebar: Step Navigator + Run Parameters           │
│  Main Area: Active Step (input → Claude → review)   │
└──────────────────────┬──────────────────────────────┘
                       │
         ┌─────────────▼─────────────┐
         │     claude_client.py      │
         │  Anthropic API wrapper    │
         │  (claude-sonnet-4, web    │
         │   search tool enabled)    │
         └─────────────┬─────────────┘
                       │
         ┌─────────────▼─────────────┐
         │     state_manager.py      │
         │  All session state R/W    │
         │  Single source of truth   │
         └─────────────┬─────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼──────┐             ┌────────▼───────┐
│excel_gen.py  │             │word_gen.py     │
│openpyxl      │             │python-docx     │
│6 appendix    │             │Front Section   │
│sheets        │             │template        │
└──────────────┘             └────────────────┘
```

### Session State Shape (single dictionary in `st.session_state["run"]`)

```python
{
  "params": {
    "country": str,
    "timeline_start": str,   # YYYY-MM-DD
    "timeline_end": str,
    "retailers": list[str]
  },
  "retailer_map": str,       # Step A — free text, editable
  "pulses": list[dict],      # Step B — 100 pulse objects
  "whisper_tags": list[dict],# Steps C/D — tag objects
  "macro_trends": list[dict],# Step E — 6 macro objects
  "cipher_map": list[dict],  # Step F
  "attribute_map": list[dict],# Step G
  "falsification": str,      # Step H — free text notes
  "tech_trends": list[dict], # Step I
  "step": int                # which step the user is on (0–9)
}
```

---

## 3. Folder and File Structure

Build exactly this structure. Do not deviate.

```
retail_trends_app/
│
├── app.py                      ← Streamlit entry point
├── requirements.txt
├── .env                        ← API key (never commit this)
├── .gitignore
│
├── config.py                   ← Constants, model name, step labels
│
├── utils/
│   ├── __init__.py
│   ├── claude_client.py        ← Anthropic API calls
│   ├── state_manager.py        ← All session_state read/write helpers
│   └── validators.py           ← QA checklist checks
│
├── prompts/
│   ├── __init__.py
│   ├── step_a.py               ← Retailer structure map prompt
│   ├── step_b.py               ← Pulse ledger prompt (web search ON)
│   ├── step_c_d.py             ← Whisper Tag clustering + formatting
│   ├── step_e.py               ← Macro Trends synthesis
│   ├── step_f.py               ← CIPHER regrouping
│   ├── step_g.py               ← Attribute-led regrouping
│   ├── step_h.py               ← Falsification check
│   └── step_i.py               ← Technology extraction
│
├── generators/
│   ├── __init__.py
│   ├── excel_generator.py      ← Builds the .xlsx appendix workbook
│   └── word_generator.py       ← Builds the .docx front section
│
└── steps/                      ← One file per step, called by app.py
    ├── __init__.py
    ├── step_0_params.py
    ├── step_1_retailer_map.py
    ├── step_2_pulse_ledger.py
    ├── step_3_whisper_tags.py
    ├── step_4_macro_trends.py
    ├── step_5_cipher.py
    ├── step_6_attribute_led.py
    ├── step_7_falsification.py
    ├── step_8_tech_trends.py
    └── step_9_export.py
```

---

## 4. Dependencies

**requirements.txt — write exactly this:**

```
streamlit>=1.35.0
anthropic>=0.28.0
openpyxl>=3.1.2
python-docx>=1.1.0
python-dotenv>=1.0.0
```

No other dependencies. Do not add pandas, numpy, or any data science libraries — they are not needed and increase cold-start time.

---

## 5. config.py

```python
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 8192

STEPS = [
    (0, "Parameters"),
    (1, "Retailer Map"),
    (2, "Pulse Ledger"),
    (3, "Whisper Tags"),
    (4, "Macro Trends"),
    (5, "CIPHER View"),
    (6, "Attribute View"),
    (7, "Falsification"),
    (8, "Tech Trends"),
    (9, "Export"),
]

ATTRIBUTES = [
    "AI Operations", "Emerging capabilities", "Network operations",
    "Workforce Operations", "Sustainable operations", "Belonging among groups",
    "B2B service partnerships", "B2C Service partnerships",
    "Fulfillment partnerships", "Other Partnerships", "Investment activity",
    "Disinvestments", "Corporate governance", "Digital Stores", "Loyalty",
    "Pricing & promotion", "Physical stores", "Owned Brands", "Marketplaces"
]

CIPHER_BUCKETS = [
    "Contradictions", "Inflections", "Practices", "Hacks", "Extremes", "Rarities"
]
```

---

## 6. utils/claude_client.py

This is the only place where the Anthropic API is called. All steps call this module.

```python
import anthropic
import os
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def call_claude(system_prompt: str, user_message: str, use_web_search: bool = False) -> str:
    """
    Single function for all Claude calls.
    Returns the full text response as a string.
    use_web_search=True only for Step B (pulse collection).
    """
    kwargs = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 8192,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
    }
    if use_web_search:
        kwargs["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]

    response = client.messages.create(**kwargs)
    return "".join(
        block.text for block in response.content if hasattr(block, "text")
    )
```

**Important notes for Kilo:**
- `use_web_search=True` only for Step B. All other steps use Claude's reasoning over the data already in session state — no more web calls needed after pulse collection.
- Always extract `.text` only (ignore tool_use blocks in the response).
- Wrap every call in `app.py` with a Streamlit `st.spinner("Claude is working...")`.

---

## 7. utils/state_manager.py

```python
import streamlit as st

def init_run():
    """Call once at app startup to initialise session state."""
    if "run" not in st.session_state:
        st.session_state["run"] = {
            "params": {},
            "retailer_map": "",
            "pulses": [],
            "whisper_tags": [],
            "macro_trends": [],
            "cipher_map": [],
            "attribute_map": [],
            "falsification": "",
            "tech_trends": [],
            "step": 0,
        }

def get(key: str):
    return st.session_state["run"].get(key)

def set(key: str, value):
    st.session_state["run"][key] = value

def advance_step():
    st.session_state["run"]["step"] += 1

def go_to_step(n: int):
    st.session_state["run"]["step"] = n

def reset():
    del st.session_state["run"]
    init_run()
```

---

## 8. app.py — Main Entry Point

```python
import streamlit as st
from utils.state_manager import init_run, get, go_to_step, reset
from config import STEPS
import steps.step_0_params as s0
import steps.step_1_retailer_map as s1
import steps.step_2_pulse_ledger as s2
import steps.step_3_whisper_tags as s3
import steps.step_4_macro_trends as s4
import steps.step_5_cipher as s5
import steps.step_6_attribute_led as s6
import steps.step_7_falsification as s7
import steps.step_8_tech_trends as s8
import steps.step_9_export as s9

st.set_page_config(
    page_title="Retail Trends Analyser",
    page_icon="📊",
    layout="wide"
)

init_run()

# --- Sidebar: navigation + reset ---
with st.sidebar:
    st.title("Retail Trends")
    current_step = get("step")
    for idx, label in STEPS:
        icon = "✅" if idx < current_step else ("▶" if idx == current_step else "○")
        if idx <= current_step:
            if st.button(f"{icon} {label}", key=f"nav_{idx}", use_container_width=True):
                go_to_step(idx)
                st.rerun()
    st.divider()
    if st.button("🔄 Start New Run", use_container_width=True):
        reset()
        st.rerun()

# --- Main area: render active step ---
STEP_MAP = {0: s0, 1: s1, 2: s2, 3: s3, 4: s4,
            5: s5, 6: s6, 7: s7, 8: s8, 9: s9}

active = get("step")
STEP_MAP[active].render()
```

---

## 9. Step Files — Pattern to Follow

Every step file in `steps/` must follow this exact pattern. Kilo should repeat this pattern for all 10 step files.

```python
# steps/step_X_name.py

import streamlit as st
from utils.state_manager import get, set, advance_step
from utils.claude_client import call_claude
from prompts.step_x import SYSTEM_PROMPT, build_user_message

def render():
    st.header("Step X — Step Name")
    st.caption("What this step does — one sentence description.")

    # 1. Show current saved output if it exists
    existing = get("key_for_this_step")
    display_value = st.text_area(
        "Claude's output (edit freely before confirming):",
        value=existing or "",
        height=400,
        key="step_x_textarea"
    )

    col1, col2 = st.columns([1, 4])

    # 2. Run Claude button
    with col1:
        if st.button("▶ Run Claude", type="primary"):
            with st.spinner("Claude is working..."):
                result = call_claude(
                    system_prompt=SYSTEM_PROMPT,
                    user_message=build_user_message(get("params"), get("previous_data")),
                    use_web_search=False  # True only for step 2
                )
            set("key_for_this_step", result)
            st.rerun()

    # 3. Confirm & Next button
    with col2:
        if st.button("Confirm & Next →"):
            set("key_for_this_step", display_value)
            advance_step()
            st.rerun()
```

**Rules for all step files:**
- Always show the editable text area whether Claude has run or not.
- "Run Claude" saves to session state and reruns — it does not auto-advance.
- "Confirm & Next" saves whatever is in the text area (human edits included) and advances.
- User can always go back via the sidebar and re-run Claude or re-edit.

---

## 10. Prompts — How to Write Them

Each file in `prompts/` has two things: a `SYSTEM_PROMPT` string and a `build_user_message()` function.

**Structure for every prompt file:**

```python
# prompts/step_b.py  (example: pulse collection)

SYSTEM_PROMPT = """
You are a senior retail sector expert with 40+ years experience.
[Full role + rules from the master prompt — paste verbatim from the methodology document]

SOURCE HIERARCHY: [paste verbatim]
NON-NEGOTIABLE OUTPUT RULES: [paste verbatim]
...

Return your output as plain text following the exact schema below.
Do not add commentary before or after the schema output.
"""

def build_user_message(params: dict, previous_data: dict = None) -> str:
    return f"""
Country: {params['country']}
Timeline: {params['timeline_start']} to {params['timeline_end']}
Retailers in scope: {', '.join(params['retailers'])}

[Any previous step data needed — e.g. retailer map for context]

Execute Step B: Pulse Ledger. Return exactly 100 pulses.
Format each pulse as:
PULSE_ID | RETAILER_PARENT | BANNER | DATE | ACTION_SUMMARY | ATTRIBUTES | SOURCE_NAME | URL
"""
```

**Key instruction to Kilo:** The SYSTEM_PROMPT for each step must paste in the relevant section of the master methodology verbatim. Do not paraphrase or summarise the methodology rules. The governing document is `01_Retail_Trends_Master_Prompt_Template_v2.pdf` (uploaded to this project).

**Prompt file index:**

| File | Step | Web Search | Input data needed |
|------|------|-----------|-------------------|
| step_a.py | Retailer structure map | No | params |
| step_b.py | Pulse ledger | **Yes** | params, retailer_map |
| step_c_d.py | Whisper Tags | No | params, pulses |
| step_e.py | Macro Trends | No | params, whisper_tags |
| step_f.py | CIPHER regrouping | No | whisper_tags |
| step_g.py | Attribute-led | No | whisper_tags |
| step_h.py | Falsification | No | pulses, whisper_tags, macro_trends |
| step_i.py | Tech trends | No | pulses |

---

## 11. generators/excel_generator.py

Use `openpyxl`. Build a workbook with exactly these sheets in this order. Apply basic styling: bold headers, auto-width columns, freeze top row on every sheet.

```
Sheet name          Columns (in order)
────────────────────────────────────────────────────────────────────────
Run_Parameters      Field | Value
Pulse_Ledger        Pulse_ID | Retailer_Parent | Banner_Unit | Date_Published | Action_Summary | Attributes | Primary_WhisperTag_ID | Primary_MacroTrend_ID | Source_Name | Source_URL
Whisper_Tags        WhisperTag_ID | WhisperTag_Name | Primary_MacroTrend_ID | MicroStory | Pulse_IDs_Used
Macro_Trend_Map     MacroTrend_ID | MacroTrend_Name | WhisperTag_IDs_Used | ProofPoint_Pulse_IDs
WhisperTag_CIPHER   WhisperTag_ID | WhisperTag_Name | Primary_CIPHER_Bucket | Why_Assigned
WhisperTag_Attr     WhisperTag_ID | WhisperTag_Name | AttributeLed_Macro_Name | Linked_Attribute_Buckets | Why_Assigned
Technology_Trends   TechTrend_ID | TechTrend_Name | Primary_CIPHER_Bucket | Pulse_IDs_Used | Source_URLs
```

**Parsing strategy:** Each step stores its output as a pipe-delimited string (one row per line). The generator splits each line on `|` and writes rows. Do not use JSON for intermediate storage — pipe-delimited text is readable and editable by the user in the text area.

```python
def parse_pipe_table(text: str) -> list[list[str]]:
    rows = []
    for line in text.strip().split("\n"):
        if "|" in line and not line.startswith("---"):
            rows.append([cell.strip() for cell in line.split("|") if cell.strip()])
    return rows

def generate_excel(run_data: dict) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from io import BytesIO

    wb = Workbook()
    # ... build each sheet from run_data
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
```

Return `bytes` from `generate_excel()`. In `step_9_export.py` use `st.download_button(data=bytes_value, ...)`.

---

## 12. generators/word_generator.py

Use `python-docx`. The Word doc must follow the Front Section template structure from `02_Front_Section_Executive_Readout_Template_v2.pdf`.

Section order:
1. Cover block: Country, Timeline, Retailers in scope, Date
2. A) Summary (max 200 words)
3. B) Macro Trends 1–6 (for each: name, narrative, driver table, proof points table)
4. C) CIPHER regrouping table
5. D) Attribute-led regrouping table
6. E) Technology trends table
7. F) Unassigned Whisper Tags (if any)
8. Reference list

```python
def generate_word(run_data: dict) -> bytes:
    from docx import Document
    from docx.shared import Pt, RGBColor
    from io import BytesIO

    doc = Document()
    # Set styles, add cover, iterate sections...
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()
```

Keep the Word doc clean and professional. Use Heading 1 for section letters (A, B, C...), Heading 2 for Macro Trend names. Use built-in `doc.add_table()` for all tabular data.

---

## 13. steps/step_9_export.py

This is the final step. It runs the QA checklist, then offers two download buttons.

```python
def render():
    st.header("Step 9 — Export")
    
    run = st.session_state["run"]
    
    # QA checks (from validators.py)
    from utils.validators import run_qa
    issues = run_qa(run)
    
    if issues:
        st.warning("QA issues found. Review before exporting:")
        for issue in issues:
            st.write(f"⚠ {issue}")
    else:
        st.success("All QA checks passed.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        from generators.excel_generator import generate_excel
        xlsx = generate_excel(run)
        country = run["params"].get("country", "output").replace(" ", "_")
        st.download_button(
            "📥 Download Excel Appendix",
            data=xlsx,
            file_name=f"{country}_Retail_Trends_Appendix_v1.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with col2:
        from generators.word_generator import generate_word
        docx = generate_word(run)
        st.download_button(
            "📥 Download Word Front Section",
            data=docx,
            file_name=f"{country}_Retail_Trends_Front_Section_v1.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
```

---

## 14. utils/validators.py

QA checks mirror the checklist in `04_Retail_Trends_Run_Guide_QA_Checklist_v2.pdf`.

```python
def run_qa(run: dict) -> list[str]:
    issues = []
    pulses = run.get("pulses", [])
    whisper_tags = run.get("whisper_tags", [])
    macro_trends = run.get("macro_trends", [])

    if not pulses:
        issues.append("No pulses found. Step 2 may not have been completed.")
    elif len(pulses) < 80:
        issues.append(f"Only {len(pulses)} pulses found — target is 100.")

    if not whisper_tags:
        issues.append("No Whisper Tags found.")

    if len(macro_trends) != 6:
        issues.append(f"{len(macro_trends)} Macro Trends found — exactly 6 required.")

    if not run.get("tech_trends"):
        issues.append("Technology trends section is empty.")

    return issues
```

Note: These are soft warnings only — the user can still export even if issues exist.

---

## 15. .env file

```
ANTHROPIC_API_KEY=your_key_here
```

**.gitignore must include:**
```
.env
__pycache__/
*.pyc
.streamlit/secrets.toml
```

---

## 16. Build Order for Kilo

Build in this exact sequence. Test each layer before moving to the next.

1. Create folder structure and `requirements.txt`
2. Build `config.py` and `.env`
3. Build `utils/state_manager.py`
4. Build `utils/claude_client.py` — test with a single hello-world call
5. Build `app.py` with sidebar + step routing (stub `render()` in each step file first)
6. Build `steps/step_0_params.py` fully — test parameter entry and session state
7. Build all `prompts/` files — paste methodology text verbatim
8. Build remaining `steps/` files one by one, testing each
9. Build `generators/excel_generator.py` — test with dummy data
10. Build `generators/word_generator.py` — test with dummy data
11. Build `steps/step_9_export.py` and `utils/validators.py`
12. End-to-end smoke test with one short run

---

## 17. Scaling Path (v2+)

These changes are isolated and can be made without rewriting the core app. They are clearly marked here so a non-technical person can hand them to an AI assistant later.

| What to add | Where to change | Effort |
|-------------|----------------|--------|
| Save run history | Add `SQLite` via `sqlite3` (stdlib). Add `save_run()` to `state_manager.py`. Add a "Past Runs" page. | Low |
| Login / user accounts | Add `streamlit-authenticator`. Wrap `app.py` with auth check. | Low |
| Faster pulse collection (parallel) | Replace sequential Claude call in step_b with `asyncio` + `anthropic.AsyncAnthropic`. | Medium |
| Cloud deployment | Deploy to Streamlit Community Cloud (free) by connecting GitHub repo. Set `ANTHROPIC_API_KEY` in Streamlit Secrets. No code changes needed. | Very Low |
| Paid cloud + custom domain | Migrate to AWS EC2 t3.small + nginx + `gunicorn`. One Dockerfile needed. | Medium |
| Multiple language output | Add `output_language` param. Append language instruction to each SYSTEM_PROMPT. | Low |

---

## 18. Non-Technical Maintenance Guide

Things the app owner may want to change, and how to do it with AI help:

**Change the Claude model:** Open `config.py`. Change the `MODEL` string. Ask AI: "Update MODEL in config.py to [new model name]."

**Change step prompts:** Open the relevant file in `prompts/`. The `SYSTEM_PROMPT` variable is the instruction Claude receives. Ask AI: "In prompts/step_b.py, add this rule to SYSTEM_PROMPT: [your rule]."

**Add a new retailer to the default list:** Not needed — retailers are entered fresh each run on Step 0.

**Change the Excel column order:** Open `generators/excel_generator.py`. Find the sheet you want. Reorder the column name list. Ask AI: "In excel_generator.py, move the Source_URL column to be the second column in Pulse_Ledger sheet."

**Change the Word doc styling:** Open `generators/word_generator.py`. Ask AI: "In word_generator.py, change all Heading 1 styles to use font size 16 and colour #1a1a2e."

---

## 19. Final Notes for Kilo

- Never hardcode the Anthropic API key anywhere except `.env`.
- Never import from `steps/` inside other `steps/` files — all shared data goes through `state_manager`.
- Every Claude response is stored as a raw string in session state. The generators are responsible for parsing.
- Keep Streamlit reruns minimal — only rerun after a state-changing action (Claude run or Confirm click).
- If a step's Claude output looks wrong, the user can edit it directly in the text area. The app trusts whatever is in the text area at "Confirm & Next" time.
