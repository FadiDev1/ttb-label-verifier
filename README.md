# TTB AI-Powered Label Verification Prototype

An AI-powered tool that scans any alcohol label image and verifies that all mandatory TTB fields are present — including the Government Warning statement.

---

## Setup & Run Instructions

### Prerequisites

- **Python 3.8+** — Check if installed: `python3 --version`
  - **macOS:** `brew install python3` (requires [Homebrew](https://brew.sh))
  - **Windows:** Download from [python.org/downloads](https://www.python.org/downloads/) — check "Add to PATH" during install
  - **Linux:** `sudo apt install python3 python3-venv python3-pip`

### Run the App

```bash
# 1. Clone the repo and navigate into it
git clone <your-repo-url>
cd <your-project-folder>

# 2. Create a virtual environment
python3 -m venv venv

# 3. Activate it
# macOS / Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the app
streamlit run app.py
```

The app opens automatically at `http://localhost:8501`.

> **Note:** On first run, EasyOCR will download its language model (~100MB). This only happens once.

---

## Deployed Version

🌐 Live at: **[your-app-name.streamlit.app](https://your-app-name.streamlit.app)** *(update after deploying)*

---

## How It Works

1. **Upload** — Drag in any alcohol label image (JPG or PNG)
2. **Verify** — Click the Verify button
3. **Results** — See which required fields were found or missing

### What It Checks

The app scans the label for all mandatory TTB fields:

| Field | How It's Detected |
|---|---|
| Brand Name | Any substantial text present on label |
| Class / Type | Alcohol type keywords (Whiskey, Vodka, Wine, Beer, etc.) |
| Alcohol Content | ABV percentage or Proof patterns |
| Net Contents | Volume patterns (mL, L, FL OZ) |
| **Government Warning** | "GOVERNMENT WARNING" header in ALL CAPS + body text matching 27 CFR § 16.21 |
| Bottler Name & Address | State abbreviations and producer keywords (Distillery, Bottled by, etc.) |
| Country of Origin | "Product of", "Made in", or country name patterns |

---

## Approach & Tools Used

| Tool | Why |
|---|---|
| **EasyOCR** | Local ML-based OCR — works offline and behind firewalls (Marcus's concern), no API keys, no per-call cost |
| **OpenCV (CLAHE + sharpening)** | Adaptive contrast + sharpening handles glare, shadows, and angled photos (Jenny's feedback) |
| **RapidFuzz** | Fuzzy matching tolerates OCR imperfections in the Government Warning text |
| **Streamlit** | Rapid prototyping framework — one-click deploy via Streamlit Cloud |
| **Pillow** | Image loading and format handling |

### Verification Pipeline

```
Image → Preprocess (CLAHE + sharpen) → OCR (EasyOCR) → Field Detection (regex + keyword matching) → Results
```

1. **Preprocess** — CLAHE contrast enhancement + sharpening kernel to handle glare and poor lighting
2. **OCR** — EasyOCR extracts all text from the image
3. **Detect** — Regex patterns and keyword matching check for each required field
4. **Report** — Simple ✅/❌ checklist + downloadable JSON report

---

## Assumptions

- **English-only labels** — EasyOCR is configured for English. International labels would need multi-language support.
- **One label per image** — The OCR reads the entire image as one label. Multi-label composites aren't split.
- **Government Warning text** — Checked against the exact 27 CFR § 16.21 wording with fuzzy matching to tolerate minor OCR errors.

---

## Trade-offs & Limitations

| Decision | Trade-off |
|---|---|
| **Local OCR vs. cloud vision API** | Slower on very large batches, but works offline/behind firewalls and has zero cost — directly addresses Marcus's firewall and Sarah's vendor concerns |
| **Brand detection heuristic** | Currently checks for substantial text presence. A production version could use a TTB brand database for exact matching |
| **CPU-only** | EasyOCR runs on CPU for maximum compatibility. GPU mode could be enabled for faster batch processing |
| **No persistent storage** | Prototype uses in-memory processing only. Production version would need a database for audit trails |

---

## Test Labels

Sample test label images are included in `test_labels/` to demonstrate the verification tool. Upload any of them to see the app in action.

---

## Project Structure

```
.
├── app.py                  # Streamlit UI (upload → verify → results)
├── utils.py                # OCR engine, image preprocessing, field detection logic
├── requirements.txt        # Python dependencies
├── .gitignore              # Excludes venv/, __pycache__/, .DS_Store
├── test_labels/            # Sample label images for testing
└── README.md               # This file
```