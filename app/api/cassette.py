from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app import crud, schemas
from app.database import get_db
from app.rfid_reader import read_rfid_tag

router = APIRouter(prefix="/api/cassettes", tags=["Cassette Master"])

@router.get("", response_model=schemas.CassetteListResponse)
def get_all_cassettes(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    db: Session = Depends(get_db)
):
    """Get all cassettes with pagination"""
    return crud.get_cassettes(db, skip=skip, limit=limit)

@router.get("/{cassette_id}", response_model=schemas.CassetteResponse)
def get_cassette_by_id(cassette_id: int, db: Session = Depends(get_db)):
    """Get cassette by ID"""
    return crud.get_cassette(db, cassette_id)

@router.post("", response_model=schemas.CassetteResponse, status_code=201)
def create_new_cassette(cassette: schemas.CassetteCreate, db: Session = Depends(get_db)):
    """Create new cassette"""
    return crud.create_cassette(db, cassette)

@router.put("/{cassette_id}", response_model=schemas.CassetteResponse)
def update_cassette_by_id(
    cassette_id: int, 
    cassette: schemas.CassetteUpdate, 
    db: Session = Depends(get_db)
):
    """Update cassette by ID (including RFID number)"""
    return crud.update_cassette(db, cassette_id, cassette)

@router.delete("/{cassette_id}", response_model=schemas.MessageResponse)
def delete_cassette_by_id(cassette_id: int, db: Session = Depends(get_db)):
    """Delete cassette by ID"""
    return crud.delete_cassette(db, cassette_id)

@router.get("/search/", response_model=List[schemas.CassetteResponse])
def search_cassettes(
    query: str = Query(..., min_length=1, description="Search by cassette code, description, or RFID number"),
    db: Session = Depends(get_db)
):
    """Search cassettes by code, description, or RFID number"""
    return crud.search_cassettes(db, query)

@router.post("/read-rfid")
def read_rfid_from_device(db: Session = Depends(get_db)):
    """
    Read RFID tag from RFID device
    Sends READ command to RFID device and returns the first tag detected
    Also checks if the RFID is already assigned to another cassette
    """
    result = read_rfid_tag()
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])
    
    rfid_number = result['rfid_number']
    
    # Check if this RFID is already assigned to a cassette
    existing_cassette = crud.get_cassette_by_rfid(db, rfid_number)
    
    response = {
        "success": True,
        "rfid_number": rfid_number,
        "message": result['message'],
        "already_assigned": existing_cassette is not None
    }
    
    if existing_cassette:
        response["assigned_to"] = {
            "id": existing_cassette.id,
            "cassette_code": existing_cassette.cassette_code,
            "description": existing_cassette.desc
        }
        response["message"] = f"RFID already assigned to cassette '{existing_cassette.cassette_code}'"
    
    return response


@router.post("/{cassette_id}/assign-rfid", response_model=schemas.CassetteResponse)
def assign_rfid_to_cassette(
    cassette_id: int,
    db: Session = Depends(get_db)
):
    """
    Read RFID from device and assign it to the specified cassette
    Validates that the RFID number is not already assigned to another cassette
    """
    # Read RFID from device
    rfid_result = read_rfid_tag()
    
    if not rfid_result['success']:
        raise HTTPException(status_code=400, detail=rfid_result['message'])
    
    rfid_number = rfid_result['rfid_number']
    
    # Check if RFID is already assigned to another cassette
    existing_cassette = crud.get_cassette_by_rfid(db, rfid_number)
    if existing_cassette and existing_cassette.id != cassette_id:
        raise HTTPException(
            status_code=409, 
            detail=f"RFID number '{rfid_number}' is already assigned to cassette '{existing_cassette.cassette_code}'"
        )
    
    # Assign RFID to cassette
    update_data = schemas.CassetteUpdate(rfid_number=rfid_number)
    updated_cassette = crud.update_cassette(db, cassette_id, update_data)
    
    return updated_cassette
