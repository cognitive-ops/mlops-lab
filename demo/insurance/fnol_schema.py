"""
Structured-extraction schema for the FNOL (First Notice of Loss) claim.
"""

from typing import Optional

from pydantic import BaseModel, Field


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


REQUIRED_FIELDS = [
    "policy_number",
    "claimant_name",
    "date_of_loss",
    "loss_type",
    "loss_description",
    "location_of_loss",
    "injuries_reported",
    "estimated_damage_amount",
]

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
