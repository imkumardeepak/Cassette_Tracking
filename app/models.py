from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database import Base

class CassetteMaster(Base):
    __tablename__ = "cassette_master"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cassette_code = Column(String(100), unique=True, nullable=False, index=True)
    desc = Column(String(200), nullable=False)
    rfid_number = Column(String(100), nullable=True, index=True)  # Nullable, can be updated later
    gpio_output = Column(String(10), nullable=True)  # GPIO output: DO0, DO1, DO2, DO3
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CassetteMaster(id={self.id}, cassette_code='{self.cassette_code}', rfid_number='{self.rfid_number}', gpio='{self.gpio_output}')>"


class RFIDTransaction(Base):
    __tablename__ = "rfid_transactions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rfid_number = Column(String(100), nullable=False, index=True)
    cassette_id = Column(Integer, nullable=True, index=True)  # Null if not assigned
    cassette_code = Column(String(100), nullable=True)
    event_type = Column(String(50), nullable=False)  # 'scan', 'assign', 'unassign'
    status = Column(String(50), nullable=False)  # 'success', 'error', 'pending'
    message = Column(String(500), nullable=True)
    extra_data = Column(String(1000), nullable=True)  # JSON string for additional data
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<RFIDTransaction(id={self.id}, rfid='{self.rfid_number}', type='{self.event_type}', status='{self.status}')>"
