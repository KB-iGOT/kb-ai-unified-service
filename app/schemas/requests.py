from typing import Optional
from .base import BaseModel

class RoleMappingRequest(BaseModel):
    organization: str
    role_title: str
    department: Optional[str] = None

class ProfanityCheckRequest(BaseModel):
    text: str
