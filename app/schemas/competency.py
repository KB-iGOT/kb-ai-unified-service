from typing import List, Optional

from pydantic import Field
from .base import BaseModel

class CompetencyItem(BaseModel):
    category: str
    theme: str
    sub_themes: List[str]
    relevance: Optional[str] = Field(default=None, description="Critical/High/Medium/Low")
