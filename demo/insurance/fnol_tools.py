"""
Mock external-system integrations and deterministic scoring for the FNOL
claims intake pipeline:
  - Guidewire-style policy lookup (verify_policy)
  - Multi-modal ingestion helpers (PDF text, voice transcription, damage photo)
  - Fraud/severity risk scoring (compute_risk_score)
  - Core CMS submission + adjuster/SIU assignment

All external calls here are mocked or use the OpenAI API directly (no other
paid services required). Swap points for real Guidewire/Duck Creek/NeMo
integrations are called out in each function's docstring.
"""

import base64
import os
from datetime import date, datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Guidewire-style policy verification (mock PolicyCenter)
# ---------------------------------------------------------------------------
MOCK_POLICIES = {
    "POL-100001": {
        "status": "active",
        "effective_date": date(2024, 1, 1),
        "covered_losses": {"collision", "theft", "weather", "vandalism"},
        "policyholder": "Jane Carter",
        "prior_claims_count": 0,
    },
    "POL-100002": {
        "status": "lapsed",
        "effective_date": date(2022, 6, 1),
        "covered_losses": {"collision", "fire"},
        "policyholder": "Sam Lee",
        "prior_claims_count": 2,
    },
    "POL-100003": {
        "status": "active",
        "effective_date": date(2025, 12, 1),
        "covered_losses": {"collision", "theft", "fire", "weather", "liability", "vandalism"},
        "policyholder": "Alex Kim",
        "prior_claims_count": 3,
    },
}

ADJUSTERS = ["A. Reyes", "B. Chen", "C. Okafor", "D. Patel"]
SIU_INVESTIGATORS = ["SIU-M. Ortiz", "SIU-R. Fallon"]


def parse_date(value: str) -> Optional[date]:
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def lookup_policy(policy_number: str) -> Optional[dict]:
    return MOCK_POLICIES.get(policy_number)


def verify_policy(policy_number: str) -> dict:
    """Mock Guidewire PolicyCenter lookup — just policy identity/status.
    Real deployment: call the Guidewire PolicyCenter REST API here."""

    policy = lookup_policy(policy_number)
    if not policy:
        return {"status": "unknown", "reason": f"Policy '{policy_number}' not found", "prior_claims_count": 0}
    if policy["status"] != "active":
        return {
            "status": "lapsed",
            "reason": f"Policy status is '{policy['status']}'",
            "prior_claims_count": policy["prior_claims_count"],
        }
    return {
        "status": "active",
        "reason": "Policy is active",
        "policyholder": policy["policyholder"],
        "effective_date": policy["effective_date"],
        "covered_losses": policy["covered_losses"],
        "prior_claims_count": policy["prior_claims_count"],
    }


def check_loss_coverage(policy_number: str, loss_type: str, date_of_loss: str) -> dict:
    """Full coverage determination once loss details are known: does this
    specific loss type, on this date, fall inside what the policy covers?"""

    policy = lookup_policy(policy_number)
    if not policy or policy["status"] != "active":
        # verify_policy already returns "unknown" or "lapsed" in this case
        return verify_policy(policy_number)

    if loss_type not in policy["covered_losses"]:
        return {
            "status": "excluded",
            "reason": f"Loss type '{loss_type}' is not covered by this policy",
            "prior_claims_count": policy["prior_claims_count"],
        }

    dol = parse_date(date_of_loss)
    effective_date = policy["effective_date"]
    if dol and dol < effective_date:
        return {
            "status": "excluded",
            "reason": "Date of loss precedes the policy's effective date",
            "prior_claims_count": policy["prior_claims_count"],
        }

    days_since_start = (dol - effective_date).days if dol else None
    return {
        "status": "in_force",
        "reason": "Coverage confirmed",
        "prior_claims_count": policy["prior_claims_count"],
        "days_since_policy_start": days_since_start,
    }


# ---------------------------------------------------------------------------
# Multi-modal ingestion: PDF / voice / photo
# ---------------------------------------------------------------------------
def extract_pdf_text(pdf_path: str) -> str:
    """PDF text extraction for claim forms/police reports/medical bills
    submitted as PDF attachments.

    Tries the embedded text layer first (pypdf, fast/exact for typed PDFs).
    Falls back to OCR when that yields ~nothing — i.e. the PDF is a scan or
    photo of a paper form with no text layer at all."""

    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(pages).strip()

    if len(text) < 20:
        text = _ocr_pdf_text(pdf_path)

    return text


def _ocr_pdf_text(pdf_path: str) -> str:
    """OCR fallback for scanned/image-only PDFs (no embedded text layer).

    Requires poppler (for pdf2image) and a tesseract install on PATH; set
    TESSERACT_CMD in the environment if tesseract isn't on PATH."""

    import pytesseract
    from pdf2image import convert_from_path

    if os.getenv("TESSERACT_CMD"):
        pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD")

    images = convert_from_path(pdf_path)
    pages = [pytesseract.image_to_string(image) for image in images]
    return "\n".join(pages).strip()


def transcribe_voice(audio_path: str) -> str:
    """Real speech-to-text via OpenAI's transcription API. Used for claims
    filed over a phone call / voice memo."""

    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    with open(audio_path, "rb") as f:
        transcript = client.audio.transcriptions.create(model="whisper-1", file=f)
    return transcript.text.strip()


def analyze_damage_photo(photo_path: str) -> dict:
    """Real damage-photo analysis via OpenAI vision (gpt-4o-mini). Returns a
    structured description used by the fraud/risk node — e.g. to catch a
    'minor damage' narrative contradicted by a severe-looking photo."""

    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    with open(photo_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    ext = os.path.splitext(photo_path)[1].lstrip(".").lower() or "jpeg"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "You are assessing a vehicle/property damage photo for an "
                            "insurance claim. In 2-3 sentences describe the visible damage, "
                            "then on a new line output exactly one of: "
                            "SEVERITY: minor | SEVERITY: moderate | SEVERITY: severe"
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/{ext};base64,{image_b64}"},
                    },
                ],
            }
        ],
        temperature=0,
    )

    content = response.choices[0].message.content or ""
    severity = "moderate"
    for level in ("minor", "moderate", "severe"):
        if f"severity: {level}" in content.lower():
            severity = level
            break

    return {"photo_provided": True, "description": content.strip(), "severity_estimate": severity}


def no_photo_analysis() -> dict:
    return {"photo_provided": False, "description": "", "severity_estimate": "unknown"}


# ---------------------------------------------------------------------------
# Fraud / severity risk scoring
# ---------------------------------------------------------------------------
NARRATIVE_RED_FLAGS = ("cash only", "no witnesses", "staged", "paid in full", "desperate")
SEVERITY_WEIGHT = {"minor": 0.0, "moderate": 0.1, "severe": 0.25, "unknown": 0.0}


def compute_risk_score(claim_data: dict, coverage_context: dict, damage_analysis: dict, transcript: str) -> tuple:
    """Mock fraud/severity scoring. Returns (risk_flags, risk_score in [0,1]).

    Real deployment: replace with a trained fraud model / rating engine;
    the return contract (flags + a single 0-1 score) is what the router
    downstream actually depends on, so the model can be swapped freely.
    """

    flags = []
    score = 0.0

    days_since_start = coverage_context.get("days_since_policy_start")
    if days_since_start is not None and 0 <= days_since_start < 14:
        flags.append("very_recent_policy")
        score += 0.25

    loss_type = claim_data.get("loss_type", "")
    if loss_type in ("theft", "collision") and not claim_data.get("police_report_number"):
        flags.append("no_police_report")
        score += 0.15

    amount = claim_data.get("estimated_damage_amount") or 0
    if amount > 20000:
        flags.append("high_value_claim")
        score += 0.3
    elif amount > 10000:
        flags.append("elevated_value_claim")
        score += 0.15

    if coverage_context.get("prior_claims_count", 0) >= 2:
        flags.append("prior_claims_history")
        score += 0.15

    transcript_lower = transcript.lower()
    if any(phrase in transcript_lower for phrase in NARRATIVE_RED_FLAGS):
        flags.append("narrative_red_flag")
        score += 0.2

    score += SEVERITY_WEIGHT.get(damage_analysis.get("severity_estimate", "unknown"), 0.0)

    flags = list(dict.fromkeys(flags))
    return flags, round(min(score, 1.0), 2)


# ---------------------------------------------------------------------------
# Core CMS submission + human assignment
# ---------------------------------------------------------------------------
def assign_adjuster(claim_id: str) -> str:
    """Deterministic round-robin assignment (stand-in for a real claims queue)."""
    idx = abs(hash(claim_id)) % len(ADJUSTERS)
    return ADJUSTERS[idx]


def assign_siu_investigator(claim_id: str) -> str:
    """Deterministic round-robin SIU (Special Investigations Unit) assignment."""
    idx = abs(hash(claim_id)) % len(SIU_INVESTIGATORS)
    return SIU_INVESTIGATORS[idx]


def submit_to_cms(final_claim: dict, backend: str = "guidewire") -> str:
    """Mock Core CMS (Guidewire ClaimCenter / Duck Creek) submission. Returns
    a generated claim ID standing in for the system-of-record's response.

    Real deployment: POST final_claim to the CMS's claims-intake endpoint
    and return the ID it assigns.
    """

    prefix = "GW" if backend == "guidewire" else "DC"
    seed = f"{final_claim.get('policy_number', '')}{final_claim.get('claimant_name', '')}"
    return f"{prefix}-CLM-{abs(hash(seed)) % 1_000_000:06d}"
