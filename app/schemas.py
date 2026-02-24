from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, List

# ============= Cassette Master Schemas =============

class CassetteBase(BaseModel):
    cassette_code: str = Field(..., min_length=1, max_length=100, description="Unique cassette code")
    desc: str = Field(..., min_length=1, max_length=200, description="Cassette description")
    
    @validator('cassette_code')
    def validate_cassette_code(cls, v):
        if not v.strip():
            raise ValueError('Cassette code cannot be empty')
        return v.strip()
    
    @validator('desc')
    def validate_desc(cls, v):
        if not v.strip():
            raise ValueError('Description cannot be empty')
        return v.strip()

class CassetteCreate(CassetteBase):
    rfid_number: Optional[str] = Field(None, max_length=100, description="RFID number (optional, can be updated later)")
    gpio_output: Optional[str] = Field(None, max_length=10, description="Relay output: RELAY1-RELAY8")
    
    @validator('rfid_number')
    def validate_rfid_number(cls, v):
        if v is not None and not v.strip():
            return None  # Convert empty string to None
        return v.strip() if v else None
    
    @validator('gpio_output')
    def validate_gpio_output(cls, v):
        valid_outputs = [f'RELAY{i}' for i in range(1, 9)]
        if v is not None and v.strip() and v.strip().upper() not in valid_outputs:
            raise ValueError('Relay output must be RELAY1 through RELAY8')
        return v.strip().upper() if v and v.strip() else None

class CassetteUpdate(BaseModel):
    cassette_code: Optional[str] = Field(None, min_length=1, max_length=100)
    desc: Optional[str] = Field(None, min_length=1, max_length=200)
    rfid_number: Optional[str] = Field(None, max_length=100)
    gpio_output: Optional[str] = Field(None, max_length=10)
    
    @validator('cassette_code', 'desc', 'rfid_number')
    def validate_not_empty(cls, v):
        if v is not None and not v.strip():
            return None
        return v.strip() if v else None
    
    @validator('gpio_output')
    def validate_gpio_output(cls, v):
        valid_outputs = [f'RELAY{i}' for i in range(1, 9)]
        if v is not None and v.strip() and v.strip().upper() not in valid_outputs:
            raise ValueError('Relay output must be RELAY1 through RELAY8')
        return v.strip().upper() if v and v.strip() else None

class CassetteResponse(BaseModel):
    id: int
    cassette_code: str
    desc: str
    rfid_number: Optional[str] = None
    gpio_output: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class CassetteListResponse(BaseModel):
    total: int
    items: List[CassetteResponse]


# ============= RFID Transaction Schemas =============

class RFIDTransactionBase(BaseModel):
    rfid_number: str
    event_type: str  # 'scan', 'assign', 'unassign'
    status: str  # 'success', 'error', 'pending'
    message: Optional[str] = None
    extra_data: Optional[str] = None

class RFIDTransactionCreate(RFIDTransactionBase):
    cassette_id: Optional[int] = None
    cassette_code: Optional[str] = None

class RFIDTransactionResponse(BaseModel):
    id: int
    rfid_number: str
    cassette_id: Optional[int] = None
    cassette_code: Optional[str] = None
    event_type: str
    status: str
    message: Optional[str] = None
    extra_data: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class RFIDTransactionListResponse(BaseModel):
    total: int
    items: List[RFIDTransactionResponse]



# ============= Production Log Schemas =============

class ProductionLogCreate(BaseModel):
    """Auto-created by RFID service when a new cassette/RFID is detected"""
    cassette_id: Optional[int] = None
    cassette_code: Optional[str] = None
    rfid_number: str
    relay_output: Optional[str] = None
    from_date: Optional[datetime] = None

class ProductionLogUpdate(BaseModel):
    """User updates sheet_length_cut and coil_length_run"""
    sheet_length_cut: Optional[float] = Field(None, ge=0, description="Total sheet length cut")
    coil_length_run: Optional[float] = Field(None, ge=0, description="Total coil length run")

class ProductionLogResponse(BaseModel):
    id: int
    cassette_id: Optional[int] = None
    cassette_code: Optional[str] = None
    rfid_number: str
    from_date: datetime
    to_date: Optional[datetime] = None
    sheet_length_cut: Optional[float] = None
    coil_length_run: Optional[float] = None
    relay_output: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ProductionLogListResponse(BaseModel):
    total: int
    items: List[ProductionLogResponse]


# ============= Generic Response Schemas =============

class MessageResponse(BaseModel):
    message: str

class ErrorResponse(BaseModel):
    detail: str

