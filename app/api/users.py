from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.db import get_db
from app.models import User

router = APIRouter()


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    allergies: List[str] = []
    medications: List[str] = []
    goals: List[str] = []


class UserUpdate(BaseModel):
    name: Optional[str] = None
    allergies: Optional[List[str]] = None
    medications: Optional[List[str]] = None
    goals: Optional[List[str]] = None


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    allergies: List[str]
    medications: List[str]
    goals: List[str]
    has_oura: bool
    has_whoop: bool

    class Config:
        from_attributes = True


@router.post("", response_model=UserResponse)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Create a new user."""
    # Check if email already exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=user_data.name,
        email=user_data.email,
        allergies=user_data.allergies,
        medications=user_data.medications,
        goals=user_data.goals
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return _user_to_response(user)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db)):
    """Get a user by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return _user_to_response(user)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: str, user_data: UserUpdate, db: Session = Depends(get_db)):
    """Update a user's profile."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_data.name is not None:
        user.name = user_data.name
    if user_data.allergies is not None:
        user.allergies = user_data.allergies
    if user_data.medications is not None:
        user.medications = user_data.medications
    if user_data.goals is not None:
        user.goals = user_data.goals

    db.commit()
    db.refresh(user)

    return _user_to_response(user)


@router.delete("/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db)):
    """Delete a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()

    return {"status": "deleted"}


def _user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        allergies=user.allergies or [],
        medications=user.medications or [],
        goals=user.goals or [],
        has_oura=user.oura_token is not None,
        has_whoop=user.whoop_token is not None
    )
