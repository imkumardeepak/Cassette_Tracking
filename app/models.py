from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.sql import func
from app.database import Base

class CassetteMaster(Base):
    __tablename__ = "cassette_master"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cassette_code = Column(String(100), unique=True, nullable=False, index=True)
    desc = Column(String(200), nullable=False)
    rfid_number = Column(String(100), nullable=True, index=True)  # Nullable, can be updated later
    gpio_output = Column(String(10), nullable=True)  # Relay output: RELAY1-RELAY8
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


class ProductionLog(Base):
    """
    Production Log - tracks each cassette usage session.
    A new record is auto-created when a NEW RFID/cassette is detected.
    The record is auto-closed (to_date updated) when a DIFFERENT RFID is detected.
    User manually enters sheet_length_cut and coil_length_run.
    """
    __tablename__ = "production_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cassette_id = Column(Integer, nullable=True, index=True)
    cassette_code = Column(String(100), nullable=True)
    rfid_number = Column(String(100), nullable=False, index=True)
    from_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    to_date = Column(DateTime(timezone=True), nullable=True)  # Null = still active/open
    sheet_length_cut = Column(Float, nullable=True)  # User enters: Total sheet length cut
    coil_length_run = Column(Float, nullable=True)   # User enters: Total coil length run
    relay_output = Column(String(10), nullable=True)  # Which relay was triggered
    status = Column(String(20), nullable=False, default="open")  # 'open' or 'closed'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ProductionLog(id={self.id}, cassette='{self.cassette_code}', status='{self.status}')>"
