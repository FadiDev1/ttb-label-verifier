"""
TTB AI-Powered Label Verification App

Upload any alcohol label → AI checks that all required TTB fields are present.
No data entry needed. Just upload and verify.
"""
import streamlit as st
import json
from datetime import datetime
from PIL import Image

from utils import load_ocr, verify_label, GOV_WARNING

# ── Config ───────────────────────────────────────────────────────────────────
st.set_page_config(page_title="TTB Label Verifier", page_icon="🍾", layout="wide")

reader = load_ocr()

FIELD_DISPLAY = [
    ("brand", "Brand Name"),
    ("class_type", "Class / Type"),
    ("abv", "Alcohol Content"),
    ("net_contents", "Net Contents"),
    ("warning", "GOVERNMENT WARNING"),
    ("name_address", "Bottler Name & Address"),
    ("country_origin", "Country of Origin"),
]


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("ℹ️ About This Tool")
    st.markdown(
        "Upload any alcohol label and this tool uses AI "
        "to check that all **required TTB fields** are present."
    )
    st.markdown("**Required fields checked:**")
    st.markdown(
        "1. Brand Name\n"
        "2. Class / Type\n"
        "3. Alcohol Content\n"
        "4. Net Contents\n"
        "5. **GOVERNMENT WARNING**\n"
        "6. Bottler Name & Address\n"
        "7. Country of Origin"
    )
    st.divider()
    st.markdown(
        "- ⚡ Under 5 seconds\n"
        "- 📷 Handles glare & angles\n"
        "- 🔒 Fully local — no data sent anywhere"
    )
    st.divider()
    st.caption("[TTB.gov Label Reference](https://www.ttb.gov/labeling/beverage-alcohol-manual)")


# ── Results ──────────────────────────────────────────────────────────────────

def render_results(results: dict, raw_text: str):
    """Simple checklist — does the label have each required field?"""
    all_found = all(v["found"] for v in results.values())

    # ── Government Warning — biggest, first (Jenny's emphasis) ──
    warning = results["warning"]
    st.markdown("---")
    if warning["found"]:
        st.success("## ✅ GOVERNMENT WARNING — FOUND IN ALL CAPS")
    else:
        st.error("## ❌ GOVERNMENT WARNING — MISSING OR INCORRECT")
        st.error(
            "Per 27 CFR § 16.21, **\"GOVERNMENT WARNING:\"** must appear "
            "in **ALL CAPS**, word-for-word exact."
        )
        with st.expander("📋 Required warning text"):
            st.code(GOV_WARNING, language=None)

    st.markdown("---")

    # ── Overall ──
    if all_found:
        st.success("# ✅ LABEL APPROVED — All required fields found")
    else:
        missing = [dn for fk, dn in FIELD_DISPLAY if not results[fk]["found"]]
        st.error(f"# ⚠️ LABEL NEEDS REVIEW — Missing: {', '.join(missing)}")

    # ── Simple checklist with what was found ──
    for field_key, display_name in FIELD_DISPLAY:
        r = results[field_key]
        if r["found"]:
            st.markdown(f"✅ **{display_name}** — {r['detail']}")
        else:
            st.markdown(f"❌ **{display_name}** — {r['detail']}")

    with st.expander("🔍 View what the AI read from the label"):
        st.code(raw_text, language=None)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN PAGE
# ══════════════════════════════════════════════════════════════════════════════

st.title("🍾 TTB Label Verification")
st.markdown("Upload a label image and click Verify. That's it.")

tab1, tab2 = st.tabs(["📋 Single Label", "📦 Batch Upload"])

# ── Single Label ─────────────────────────────────────────────────────────────
with tab1:
    uploaded_file = st.file_uploader(
        "Upload label image",
        type=["jpg", "jpeg", "png"],
        key="single_upload",
    )

    if st.button("🔍  Verify Label", type="primary", use_container_width=True):
        if not uploaded_file:
            st.warning("Please upload a label image first.")
        else:
            try:
                image = Image.open(uploaded_file)
                st.image(image, caption="Uploaded Label", width=300)

                with st.spinner("Reading label…"):
                    results, raw_text = verify_label(image, reader)

                render_results(results, raw_text)

                report = {
                    "results": {k: v for k, v in results.items()},
                    "raw_ocr_text": raw_text,
                    "timestamp": datetime.now().isoformat(),
                }
                st.download_button(
                    "📥 Download Report",
                    json.dumps(report, indent=2),
                    f"ttb_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                )
            except Exception as e:
                st.error(f"Error processing image: {e}")

# ── Batch Upload ─────────────────────────────────────────────────────────────
with tab2:
    st.markdown("Upload multiple label images at once.")

    batch_files = st.file_uploader(
        "Select label images",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="batch_upload",
    )

    if batch_files and st.button("📦  Verify All", type="primary", use_container_width=True):
        try:
            passed_count = 0
            progress = st.progress(0, text="Processing…")

            for i, uploaded in enumerate(batch_files):
                try:
                    image = Image.open(uploaded)
                    res, _ = verify_label(image, reader)
                    all_found = all(v["found"] for v in res.values())
                    if all_found:
                        st.markdown(f"✅ **{uploaded.name}** — All fields present")
                        passed_count += 1
                    else:
                        missing = [dn for fk, dn in FIELD_DISPLAY if not res[fk]["found"]]
                        st.markdown(f"❌ **{uploaded.name}** — Missing: {', '.join(missing)}")
                except Exception:
                    st.markdown(f"⚠️ **{uploaded.name}** — Error reading image")

                progress.progress((i + 1) / len(batch_files), text=f"{i+1}/{len(batch_files)}")

            progress.empty()
            total = len(batch_files)
            if passed_count == total:
                st.success(f"## ✅ All {total} labels have all required fields")
            else:
                st.error(f"## ⚠️ {passed_count}/{total} complete — {total - passed_count} missing fields")
        except Exception as e:
            st.error(f"Error: {e}")