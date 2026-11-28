from typing import Literal, Any
from pydantic import BaseModel, EmailStr, Field, model_validator


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    organization_name: str | None = Field(default=None, min_length=2, max_length=150)
    mode: Literal["agency", "inhouse"] = "agency"


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class ClientIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    sector: str = ""


class BrandIn(BaseModel):
    client_id: str
    name: str = Field(min_length=2, max_length=160)
    brand_guidelines: str = ""
    product_truth: str = ""


class CampaignIn(BaseModel):
    brand_id: str
    name: str = Field(min_length=2, max_length=160)
    brief: str = Field(min_length=10, max_length=25000)
    objective: str = Field(min_length=5, max_length=3000)


class AddMemberIn(BaseModel):
    email: EmailStr
    role: Literal["viewer", "editor", "admin", "client_viewer"]
    client_id: str | None = Field(default=None, min_length=1, max_length=36)

    @model_validator(mode="after")
    def validate_scope(self):
        if (self.role == "client_viewer") != (self.client_id is not None):
            raise ValueError("client_viewer requires one client_id; internal roles have no client_id")
        return self


class ClientScopeIn(BaseModel):
    client_id: str = Field(min_length=1, max_length=36)


class DeliverableIn(BaseModel):
    campaign_id: str
    title: str = Field(min_length=2, max_length=160)
    content: dict[str, Any]


class ReviewIn(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str = Field(default="", max_length=1000)


class GuideOrderAssessment(BaseModel):
    model_config = {"extra": "forbid"}
    order_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    sequence: Literal["ordered", "independent", "unclear"]
    obligations: dict[str, Literal["met", "unsupported", "needs_information"]] = Field(max_length=100)


class DeliverableReviewIn(ReviewIn):
    guide_review: GuideOrderAssessment | None = None
    expected_qa_revision: int = Field(ge=1, strict=True)
    expected_content_digest: str = Field(pattern=r'^[0-9a-f]{64}$')


class ActionIn(BaseModel):
    campaign_id: str
    action_kind: Literal["publish_social", "send_email", "adjust_ads_budget", "delete_asset", "write_crm"]
    payload: dict[str, Any]


class StrategyDraft(BaseModel):
    positioning: str
    target_audiences: list[str]
    recommended_channels: list[str]
    kpis: list[str]
    proposed_actions: list[str]
    assumptions_and_missing_data: list[str]
    risks_to_review: list[str]
