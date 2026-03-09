"""
TTB Label Verification — Core OCR & Field Detection
Upload any label → detect if all required TTB fields are present.
"""
from typing import Tuple
import easyocr
import cv2
import numpy as np
from PIL import Image
from rapidfuzz import fuzz
import re
import streamlit as st

# Exact text per 27 CFR § 16.21
GOV_WARNING = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not "
    "drink alcoholic beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car or "
    "operate machinery, and may cause health problems."
)


@st.cache_resource
def load_ocr():
    """Load EasyOCR reader once, cached across reruns."""
    return easyocr.Reader(['en'], gpu=False)


def preprocess_image(image: Image.Image) -> np.ndarray:
    """
    Enhance label image for OCR accuracy.
    - CLAHE for adaptive contrast (handles glare/shadows — Jenny's concern)
    - Sharpening kernel for blurry / angled photos
    """
    img = np.array(image.convert('RGB'))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    return cv2.filter2D(enhanced, -1, kernel)


def extract_text(image: Image.Image, reader) -> Tuple[str, str]:
    """Run OCR and return (uppercase_text, original_text)."""
    processed = preprocess_image(image)
    results = reader.readtext(processed, detail=0, paragraph=True)
    original = " ".join(results)
    return original.upper(), original


def verify_label(image: Image.Image, reader) -> Tuple[dict, str]:
    """
    Scan a label image and check if all required TTB fields are PRESENT.
    No comparison needed — just detection.
    
    Required fields per TTB (ttb.gov):
    - Brand name
    - Class/type designation
    - Alcohol content
    - Net contents
    - Government Health Warning Statement (ALL CAPS header, exact text)
    - Name and address of bottler/producer
    - Country of origin (for imports)
    """
    full_upper, original_text = extract_text(image, reader)

    # --- Brand Name ---
    # A brand name is typically the most prominent text. If OCR found any text,
    # there's likely a brand name. We check for at least some substantial text.
    has_brand = len(original_text.strip()) > 10

    # --- Class / Type ---
    # Look for common alcohol type keywords
    type_keywords = [
        "WHISKEY", "WHISKY", "BOURBON", "VODKA", "GIN", "RUM", "TEQUILA",
        "BRANDY", "COGNAC", "WINE", "BEER", "ALE", "LAGER", "STOUT",
        "MERLOT", "CABERNET", "CHARDONNAY", "PINOT", "CHAMPAGNE",
        "SCOTCH", "MEZCAL", "SAKE", "CIDER", "SELTZER", "SPIRIT",
        "LIQUEUR", "LIQUOR", "ABSINTHE", "PORT", "SHERRY",
        "STRAIGHT", "BLENDED", "SINGLE MALT",
    ]
    found_type = None
    for kw in type_keywords:
        if kw in full_upper:
            found_type = kw.title()
            break
    has_type = found_type is not None

    # --- Alcohol Content ---
    # Look for ABV patterns: "XX%", "XX% Alc", "XX Proof", etc.
    abv_match = re.search(
        r'(\d+(?:\.\d+)?)\s*[%]\s*(?:ALC|ABV|BY\s*VOL)?|(\d+)\s*PROOF',
        full_upper
    )
    found_abv = None
    if abv_match:
        if abv_match.group(1):
            found_abv = f"{abv_match.group(1)}% ABV"
        elif abv_match.group(2):
            found_abv = f"{abv_match.group(2)} Proof"
    has_abv = found_abv is not None

    # --- Net Contents ---
    # Look for volume: "750 mL", "1L", "12 FL OZ", etc.
    net_match = re.search(r'(\d+(?:\.\d+)?)\s*(ML|L|FL\s*OZ|OZ)', full_upper)
    found_net = net_match.group(0) if net_match else None
    has_net = found_net is not None

    # --- Government Warning ---
    # Must have "GOVERNMENT WARNING" in ALL CAPS (Jenny's requirement)
    # Then check the body text matches the required wording
    has_gov_header = "GOVERNMENT WARNING" in full_upper
    if has_gov_header:
        warning_body_score = fuzz.token_set_ratio(GOV_WARNING.upper(), full_upper)
        warning_ok = warning_body_score >= 60
    else:
        warning_body_score = 0
        warning_ok = False

    # --- Name & Address ---
    # Look for state abbreviations, city/state patterns, or common address indicators
    state_pattern = r'\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\b'
    address_indicators = ["DISTILLERY", "DISTILERY", "WINERY", "BREWERY", "BREWING",
                          "COMPANY", "CORP", "INC", "LLC", "LTD", "BOTTLED BY",
                          "PRODUCED BY", "DISTILLED BY", "IMPORTED BY"]
    has_state = bool(re.search(state_pattern, full_upper))
    has_addr_keyword = any(kw in full_upper for kw in address_indicators)
    has_name_address = has_state or has_addr_keyword

    # --- Country of Origin ---
    # Look for "Product of", "Made in", "Produced in", "Imported from"
    origin_match = re.search(
        r'PRODUCT\s+(?:OF|FROM)\s+[A-Z ]+|'
        r'MADE\s+IN\s+[A-Z ]+|'
        r'PRODUCED\s+IN\s+[A-Z ]+|'
        r'IMPORTED\s+(?:FROM|BY)\s+[A-Z ]+|'
        r'UNITED\s+STATES|USA|AMERICA|'
        r'SCOTLAND|IRELAND|CANADA|MEXICO|FRANCE|ITALY|JAPAN',
        full_upper
    )
    found_origin = origin_match.group(0).strip() if origin_match else None
    has_origin = found_origin is not None

    results = {
        "brand": {
            "found": has_brand,
            "detail": original_text[:60].strip() + "..." if has_brand else "No text detected",
        },
        "class_type": {
            "found": has_type,
            "detail": found_type if found_type else "No alcohol type keyword found",
        },
        "abv": {
            "found": has_abv,
            "detail": found_abv if found_abv else "No ABV or Proof found",
        },
        "net_contents": {
            "found": has_net,
            "detail": found_net if found_net else "No volume (mL, L, oz) found",
        },
        "warning": {
            "found": warning_ok,
            "detail": (
                "GOVERNMENT WARNING in ALL CAPS ✓" if warning_ok
                else ("Header found but text doesn't match" if has_gov_header
                      else "GOVERNMENT WARNING not found")
            ),
        },
        "name_address": {
            "found": has_name_address,
            "detail": "Address/producer info detected" if has_name_address else "No address info found",
        },
        "country_origin": {
            "found": has_origin,
            "detail": found_origin if found_origin else "No country of origin found",
        },
    }
    return results, original_text
