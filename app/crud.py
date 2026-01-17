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

