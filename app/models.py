from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CATEGORIES = (
    "Employment",
    "Self-employment",
    "Business",
    "Investment",
    "Rental",
    "Agriculture & forestry",
    "Other",
    "Unclassified",
)
Category = Literal[
    "Employment",
    "Self-employment",
    "Business",
    "Investment",
    "Rental",
    "Agriculture & forestry",
    "Other",
    "Unclassified",
]


class Extraction(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    document_id: str = Field(default="", max_length=200)
    client_name: str = Field(default="", max_length=200)
    client_number: str = Field(default="", max_length=100)
    language: str = Field(default="", max_length=20)
    translated_text: str = Field(default="", max_length=60000)
    document_type: str = Field(default="", max_length=100)
    document_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    tax_year: int | None = Field(default=None, ge=1900, le=2200)
    original_amount: Decimal | None = Field(default=None, max_digits=16, decimal_places=2)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    party: str = Field(default="", max_length=200)
    purpose: str = Field(default="", max_length=1000)
    tax_deduction: Decimal | None = Field(default=None, max_digits=16, decimal_places=2)
    tax_types: list[str] = Field(default_factory=list, max_length=20)
    periodicity: str = Field(default="", max_length=100)
    warnings: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("original_amount", "tax_deduction")
    @classmethod
    def finite_amount(cls, value):
        if value is not None and not value.is_finite():
            raise ValueError("Amounts must be finite")
        return value


class Classification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    income_type: Category = "Unclassified"
    relevance: Literal["Relevant", "Possibly relevant", "Not relevant"] = "Possibly relevant"
    assessment: str = Field(default="", max_length=2000)
    evidence: list[str] = Field(default_factory=list, max_length=15)
    warnings: list[str] = Field(default_factory=list, max_length=30)


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    document_id: str = Field(max_length=200)
    client_name: str = Field(max_length=200)
    party: str = Field(max_length=200)
    purpose: str = Field(max_length=1000)
    document_date: date
    original_amount: Decimal = Field(max_digits=16, decimal_places=2)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    income_type: Category
    notes: str = Field(default="", max_length=2000)


class RunInput(BaseModel):
    scenario_id: str = Field(pattern=r"^[a-z-]+$", max_length=60)


class ImportInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: Literal["drive", "gmail"]
    limit: int = Field(default=5, ge=1, le=10)
