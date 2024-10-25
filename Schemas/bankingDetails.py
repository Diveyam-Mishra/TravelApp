from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class BInfo(BaseModel):
    account_no: str
    ifsc_code: str
    PAN: str
    GST_no: str
    bank_name: str
    state: bool = False

class PInfo(BaseModel):
    Name_on_Pan: str
    account_no: str
    Ifsc_Code: str
    Pan_card: str
    state: bool = False

class BankingDetail(BaseModel):
    personal: Optional[PInfo] = None
    business: Optional[BInfo] = None
    Is_business: bool = False

    def to_dict(self):
        return {
            "personal": self.personal.dict() if self.personal else None,
            "business": self.business.dict() if self.business else None,
            "Is_business": self.Is_business
        }
