from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from typing import Optional, List
from app import models, schemas

# ============= Cassette Master CRUD =============

def get_cassette(db: Session, cassette_id: int):
    """Get cassette by ID"""
    cassette = db.query(models.CassetteMaster).filter(models.CassetteMaster.id == cassette_id).first()
    if not cassette:
        raise HTTPException(status_code=404, detail=f"Cassette with id {cassette_id} not found")
    return cassette

def get_cassettes(db: Session, skip: int = 0, limit: int = 10):
    """Get all cassettes with pagination"""
    total = db.query(models.CassetteMaster).count()
    items = db.query(models.CassetteMaster).offset(skip).limit(limit).all()
    return {"total": total, "items": items}

def get_cassette_by_code(db: Session, cassette_code: str):
    """Get cassette by code"""
    return db.query(models.CassetteMaster).filter(models.CassetteMaster.cassette_code == cassette_code).first()

def create_cassette(db: Session, cassette: schemas.CassetteCreate):
    """Create new cassette"""
    # Check if cassette code already exists
    existing = get_cassette_by_code(db, cassette.cassette_code)
    if existing:
        raise HTTPException(status_code=400, detail=f"Cassette with code '{cassette.cassette_code}' already exists")
    
    # Check if RFID is already assigned to another cassette
    if cassette.rfid_number:
        existing_rfid = get_cassette_by_rfid(db, cassette.rfid_number)
        if existing_rfid:
            raise HTTPException(
                status_code=409, 
                detail=f"RFID '{cassette.rfid_number}' is already assigned to cassette '{existing_rfid.cassette_code}'"
            )
    
    try:
        db_cassette = models.CassetteMaster(**cassette.model_dump())
        db.add(db_cassette)
        db.commit()
        db.refresh(db_cassette)
        return db_cassette
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {str(e)}")


def update_cassette(db: Session, cassette_id: int, cassette: schemas.CassetteUpdate):
    """Update cassette"""
    db_cassette = get_cassette(db, cassette_id)
    
    # Check if new code conflicts with existing cassette
    if cassette.cassette_code and cassette.cassette_code != db_cassette.cassette_code:
        existing = get_cassette_by_code(db, cassette.cassette_code)
        if existing:
            raise HTTPException(status_code=400, detail=f"Cassette with code '{cassette.cassette_code}' already exists")
    
    # Check if RFID is already assigned to another cassette
    if cassette.rfid_number and cassette.rfid_number != db_cassette.rfid_number:
        existing_rfid = get_cassette_by_rfid(db, cassette.rfid_number)
        if existing_rfid and existing_rfid.id != cassette_id:
            raise HTTPException(
                status_code=409, 
                detail=f"RFID '{cassette.rfid_number}' is already assigned to cassette '{existing_rfid.cassette_code}'"
            )
    
    try:
        # Only update fields that are provided (not None)
        update_data = cassette.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_cassette, key, value)
        
        db.commit()
        db.refresh(db_cassette)
        return db_cassette
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {str(e)}")


def delete_cassette(db: Session, cassette_id: int):
    """Delete cassette"""
    db_cassette = get_cassette(db, cassette_id)
    try:
        db.delete(db_cassette)
        db.commit()
        return {"message": "Cassette deleted successfully"}
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Cannot delete cassette: {str(e)}")

def search_cassettes(db: Session, query: str):
    """Search cassettes by code or description"""
    cassettes = db.query(models.CassetteMaster).filter(
        (models.CassetteMaster.cassette_code.contains(query)) |
        (models.CassetteMaster.desc.contains(query)) |
        (models.CassetteMaster.rfid_number.contains(query) if query else False)
    ).all()
    return cassettes

def get_cassette_by_rfid(db: Session, rfid_number: str):
    """Get cassette by RFID number"""
    return db.query(models.CassetteMaster).filter(models.CassetteMaster.rfid_number == rfid_number).first()


# ============= RFID Transaction CRUD =============

def create_rfid_transaction(db: Session, transaction: schemas.RFIDTransactionCreate):
    """Create a new RFID transaction record"""
    try:
        db_transaction = models.RFIDTransaction(**transaction.dict())
        db.add(db_transaction)
        db.commit()
        db.refresh(db_transaction)
        return db_transaction
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating transaction: {str(e)}")

def get_rfid_transactions(db: Session, skip: int = 0, limit: int = 50):
    """Get all RFID transactions with pagination"""
    total = db.query(models.RFIDTransaction).count()
    items = db.query(models.RFIDTransaction).order_by(models.RFIDTransaction.created_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": items}

def get_rfid_transactions_by_rfid(db: Session, rfid_number: str):
    """Get all transactions for a specific RFID"""
    return db.query(models.RFIDTransaction).filter(
        models.RFIDTransaction.rfid_number == rfid_number
    ).order_by(models.RFIDTransaction.created_at.desc()).all()

def get_recent_rfid_transactions(db: Session, limit: int = 10):
    """Get recent RFID transactions"""
    return db.query(models.RFIDTransaction).order_by(
        models.RFIDTransaction.created_at.desc()
    ).limit(limit).all()


# ============= Production Log CRUD =============

def create_production_log(db: Session, log_data: schemas.ProductionLogCreate):
    """Create a new production log entry (auto-created when new RFID detected)"""
    try:
        from datetime import datetime
        db_log = models.ProductionLog(
            cassette_id=log_data.cassette_id,
            cassette_code=log_data.cassette_code,
            rfid_number=log_data.rfid_number,
            relay_output=log_data.relay_output,
            from_date=log_data.from_date or datetime.now(),
            status="open"
        )
        db.add(db_log)
        db.commit()
        db.refresh(db_log)
        return db_log
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating production log: {str(e)}")


def close_open_production_logs(db: Session):
    """Close all currently open production logs (set to_date = now, status = closed)"""
    from datetime import datetime
    open_logs = db.query(models.ProductionLog).filter(
        models.ProductionLog.status == "open"
    ).all()
    
    for log in open_logs:
        log.to_date = datetime.now()
        log.status = "closed"
    
    db.commit()
    return len(open_logs)


def update_production_log(db: Session, log_id: int, log_data: schemas.ProductionLogUpdate):
    """Update production log with user-entered data (sheet_length_cut, coil_length_run)"""
    db_log = db.query(models.ProductionLog).filter(models.ProductionLog.id == log_id).first()
    if not db_log:
        raise HTTPException(status_code=404, detail=f"Production log with id {log_id} not found")
        
    if db_log.status == "open":
        raise HTTPException(
            status_code=400, 
            detail="Cannot update data for an active cassette session. Wait until the cassette is changed."
        )    
    try:
        update_data = log_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_log, key, value)
        
        db.commit()
        db.refresh(db_log)
        return db_log
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating production log: {str(e)}")


def get_production_logs(db: Session, skip: int = 0, limit: int = 50):
    """Get all production logs, open ones first, then by from_date descending"""
    total = db.query(models.ProductionLog).count()
    items = db.query(models.ProductionLog).order_by(
        models.ProductionLog.status.asc(),  # 'open' before 'closed'
        models.ProductionLog.from_date.desc()
    ).offset(skip).limit(limit).all()
    return {"total": total, "items": items}


def get_production_log(db: Session, log_id: int):
    """Get a single production log by ID"""
    log = db.query(models.ProductionLog).filter(models.ProductionLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail=f"Production log with id {log_id} not found")
    return log


def get_open_production_log(db: Session):
    """Get the currently open production log (if any)"""
    return db.query(models.ProductionLog).filter(
        models.ProductionLog.status == "open"
    ).first()


def delete_production_log(db: Session, log_id: int):
    """Delete a production log"""
    db_log = db.query(models.ProductionLog).filter(models.ProductionLog.id == log_id).first()
    if not db_log:
        raise HTTPException(status_code=404, detail=f"Production log with id {log_id} not found")
    try:
        db.delete(db_log)
        db.commit()
        return {"message": "Production log deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting production log: {str(e)}")


# ============= Cleanup CRUD =============
def truncate_logs_and_transactions(db: Session):
    """Truncate production logs and transactions tables"""
    try:
        db.query(models.ProductionLog).delete()
        db.query(models.RFIDTransaction).delete()
        db.commit()
        return {"message": "Successfully cleared production logs and transactions"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error clearing data: {str(e)}")
