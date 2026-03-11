from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============= Cassette Schemas =============

class CassetteCreate(BaseModel):
    cassette_code: str = Field(..., min_length=1, max_length=100)
    desc: str = Field("", max_length=200)
    rfid_number: Optional[str] = Field(None, max_length=100)
    gpio_output: Optional[str] = Field(None, max_length=10)

class CassetteUpdate(BaseModel):
    cassette_code: Optional[str] = Field(None, min_length=1, max_length=100)
    desc: Optional[str] = Field(None, max_length=200)
    rfid_number: Optional[str] = Field(None, max_length=100)
    gpio_output: Optional[str] = Field(None, max_length=10)

class CassetteResponse(BaseModel):
    id: int
    cassette_code: str
    desc: str = ""
    rfid_number: Optional[str] = None
    gpio_output: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============= RFID Transaction Schemas (Paired) =============

class RFIDTransactionCreate(BaseModel):
    rfid1: str
    rfid2: Optional[str] = None
    cassette1_id: Optional[int] = None
    cassette1_code: Optional[str] = None
    cassette2_id: Optional[int] = None
    cassette2_code: Optional[str] = None
    event_type: str
    status: str
    message: Optional[str] = None
    extra_data: Optional[str] = None

class RFIDTransactionResponse(BaseModel):
    id: int
    rfid1: Optional[str] = None
    rfid2: Optional[str] = None
    cassette1_id: Optional[int] = None
    cassette1_code: Optional[str] = None
    cassette2_id: Optional[int] = None
    cassette2_code: Optional[str] = None
    event_type: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None
    extra_data: Optional[str] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============= Production Log Schemas (Paired) =============

class ProductionLogCreate(BaseModel):
    cassette1_id: Optional[int] = None
    cassette1_code: Optional[str] = None
    rfid1: Optional[str] = None
    cassette2_id: Optional[int] = None
    cassette2_code: Optional[str] = None
    rfid2: Optional[str] = None
    relay1_output: Optional[str] = None
    relay2_output: Optional[str] = None
    from_date: Optional[datetime] = None

class ProductionLogUpdate(BaseModel):
    sheet_length_cut: Optional[float] = None
    coil_length_run: Optional[float] = None

class ProductionLogResponse(BaseModel):
    id: int
    cassette1_id: Optional[int] = None
    cassette1_code: Optional[str] = None
    rfid1: Optional[str] = None
    cassette2_id: Optional[int] = None
    cassette2_code: Optional[str] = None
    rfid2: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    sheet_length_cut: Optional[float] = None
    coil_length_run: Optional[float] = None
    relay1_output: Optional[str] = None
    relay2_output: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============= List Response Schemas =============

class CassetteListResponse(BaseModel):
    total: int
    items: List[CassetteResponse]

class RFIDTransactionListResponse(BaseModel):
    total: int
    items: List[RFIDTransactionResponse]

class ProductionLogListResponse(BaseModel):
    total: int
    items: List[ProductionLogResponse]

class MessageResponse(BaseModel):
    message: str
