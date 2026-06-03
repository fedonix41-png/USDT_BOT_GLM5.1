from typing import Optional, List
from pydantic import BaseModel

class SupportMessageCreate(BaseModel):
    text: str

class SupportTicketCreate(BaseModel):
    subject: str = "General"
    message: str
    order_id: Optional[int] = None
