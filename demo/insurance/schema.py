"""
Structured-extraction schema for the auto insurance policy application.

`ApplicantExtraction` is what the extractor agent fills in (partially) from
each user message. `REQUIRED_FIELDS` / `FIELD_PROMPTS` drive the validator
and the ask-user follow-up questions.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ApplicantExtraction(BaseModel):
    """Applicant/vehicle fields mentioned in a single message.

    Only fields explicitly stated should be filled — leave the rest null
    so the extractor never overwrites previously collected data with guesses.
    """

    full_name: Optional[str] = Field(None, description="Applicant's full legal name")
    date_of_birth: Optional[str] = Field(None, description="Date of birth, format YYYY-MM-DD")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    address: Optional[str] = Field(None, description="Mailing/home address")
    driver_license_number: Optional[str] = Field(None, description="Driver's license number")
    vehicle_make: Optional[str] = Field(None, description="Vehicle make, e.g. Toyota")
    vehicle_model: Optional[str] = Field(None, description="Vehicle model, e.g. Camry")
    vehicle_year: Optional[int] = Field(None, description="Vehicle model year")
    vehicle_vin: Optional[str] = Field(None, description="17-character VIN")


REQUIRED_FIELDS = [
    "full_name",
    "date_of_birth",
    "email",
    "phone",
    "address",
    "driver_license_number",
    "vehicle_make",
    "vehicle_model",
    "vehicle_year",
    "vehicle_vin",
]

FIELD_PROMPTS = {
    "full_name": "What is your full legal name?",
    "date_of_birth": "What is your date of birth? (YYYY-MM-DD)",
    "email": "What is your email address?",
    "phone": "What is your phone number?",
    "address": "What is your home/mailing address?",
    "driver_license_number": "What is your driver's license number?",
    "vehicle_make": "What is the make of the vehicle to insure (e.g. Toyota)?",
    "vehicle_model": "What is the model of the vehicle?",
    "vehicle_year": "What model year is the vehicle?",
    "vehicle_vin": "What is the 17-character VIN of the vehicle?",
}
