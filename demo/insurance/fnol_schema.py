"""
Structured-extraction schema for the FNOL (First Notice of Loss) claim.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Submitted document types the Document Processing agent can classify.

    Kept distinct from `input_channel` — channel is *how* the claim arrived
    (app/pdf/voice), document_type is *what* the PDF actually is.
    """

    CLAIM_FORM = "claim_form"
    POLICE_REPORT = "police_report"
    MEDICAL_BILL = "medical_bill"
    REPAIR_ESTIMATE = "repair_estimate"
    OTHER = "other"


class DocumentExtraction(BaseModel):
    """Result of processing one submitted document (PDF channel).

    Wraps `ClaimExtraction` with a document-type classification and a
    confidence signal so low-confidence fields (e.g. from a noisy OCR pass
    on a scanned form) can be flagged for human confirmation instead of
    silently trusted.
    """

    document_type: DocumentType = Field(description="What kind of document this is")
    fields: "ClaimExtraction" = Field(description="Claim fields extracted from the document")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Overall confidence that the extracted fields are accurate"
    )
    low_confidence_fields: List[str] = Field(
        default_factory=list,
        description="Names of extracted fields the model is unsure about (e.g. garbled OCR text) — should be confirmed with the claimant rather than trusted outright",
    )


class ClaimExtraction(BaseModel):
    """Claim fields mentioned in a single message.

    Only fields explicitly stated should be filled — leave the rest null
    so the extractor never overwrites previously collected data with guesses.
    """

    policy_number: Optional[str] = Field(None, description="Policy number the claim is filed against")
    claimant_name: Optional[str] = Field(None, description="Full name of the person filing the claim")
    date_of_loss: Optional[str] = Field(None, description="Date the loss occurred, format YYYY-MM-DD")
    loss_type: Optional[str] = Field(
        None, description="Type of loss: collision, theft, fire, weather, liability, or vandalism"
    )
    loss_description: Optional[str] = Field(None, description="Narrative description of what happened")
    location_of_loss: Optional[str] = Field(None, description="Where the loss occurred")
    injuries_reported: Optional[bool] = Field(None, description="Whether any injuries were reported")
    police_report_number: Optional[str] = Field(None, description="Police report number, if one was filed")
    estimated_damage_amount: Optional[float] = Field(
        None, description="Claimant's estimate of damage/loss cost in USD"
    )


DocumentExtraction.model_rebuild()


# Stage A: identifying info needed before we can even look the policy up
# (mirrors the diagram's Ingest -> Verify Policy ordering — no point asking
# for loss details before confirming there's a real, in-force policy).
STAGE_A_FIELDS = ["policy_number", "claimant_name"]

# Stage B: full loss-detail fields, collected once the policy is verified.
STAGE_B_FIELDS = [
    "date_of_loss",
    "loss_type",
    "loss_description",
    "location_of_loss",
    "injuries_reported",
    "estimated_damage_amount",
]

REQUIRED_FIELDS = STAGE_A_FIELDS + STAGE_B_FIELDS

FIELD_PROMPTS = {
    "policy_number": "What is your policy number?",
    "claimant_name": "What is your full name?",
    "date_of_loss": "What date did the loss occur? (YYYY-MM-DD)",
    "loss_type": "What type of loss is this? (collision, theft, fire, weather, liability, vandalism)",
    "loss_description": "Please describe what happened.",
    "location_of_loss": "Where did the loss occur?",
    "injuries_reported": "Were any injuries reported? (yes/no)",
    "estimated_damage_amount": "What's your estimate of the damage cost, in USD?",
    "additional_details_requested_by_reviewer": (
        "The reviewer needs more information before deciding on your claim — "
        "please provide any additional details."
    ),
}

VALID_LOSS_TYPES = {"collision", "theft", "fire", "weather", "liability", "vandalism"}
