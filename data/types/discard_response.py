# return discard decision with reasoning
from pydantic import BaseModel, validator

class DiscardResponse(BaseModel):
  discard: List[int] = None
  reasoning: str = None
