from typing import List
from .base import BaseModel
from .competency import CompetencyItem

class RoleMappingResponse(BaseModel):
    organization: str
    role_title: str
    mapped_competencies: List[CompetencyItem]
    mapping_rationale: str

class ProfanityCheckResponse(BaseModel):
    status: str
    message: str
    responseData: dict
