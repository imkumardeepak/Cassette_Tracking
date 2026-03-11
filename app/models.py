from sqlalchemy import Column, Integer, String, DateTime, Float
from datetime import datetime
from app.database import Base


class CassetteMaster(Base):
    __tablename__ = "cassette_master"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cassette_code = Column(String(100), unique=True, index=True, nullable=False)
    desc = Column(String(200), nullable=True)
    rfid_number = Column(String(100), unique=True, nullable=True)
    gpio_output = Column(String(10), nullable=True)  # RELAY1-RELAY8
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class RFIDTransaction(Base):
    __tablename__ = "rfid_transactions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rfid1 = Column(String(100), index=True)
    rfid2 = Column(String(100), index=True, nullable=True)
    cassette1_id = Column(Integer, index=True, nullable=True)
    cassette1_code = Column(String(100), nullable=True)
    cassette2_id = Column(Integer, index=True, nullable=True)
    cassette2_code = Column(String(100), nullable=True)
    event_type = Column(String(50))       # scan / assign / unassign
    status = Column(String(50))           # success / error / pending
    message = Column(String(500), nullable=True)
    extra_data = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class ProductionLog(Base):
    __tablename__ = "production_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cassette1_id = Column(Integer, index=True, nullable=True)
    cassette1_code = Column(String(100), nullable=True)
    rfid1 = Column(String(100), index=True, nullable=True)
    cassette2_id = Column(Integer, index=True, nullable=True)
    cassette2_code = Column(String(100), nullable=True)
    rfid2 = Column(String(100), index=True, nullable=True)
    from_date = Column(DateTime, nullable=True)
    to_date = Column(DateTime, nullable=True)
    sheet_length_cut = Column(Float, nullable=True)
    coil_length_run = Column(Float, nullable=True)
    relay1_output = Column(String(10), nullable=True)
    relay2_output = Column(String(10), nullable=True)
    status = Column(String(20), default="open")  # open / closed
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
