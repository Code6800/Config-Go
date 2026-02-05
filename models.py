"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    SALES = "sales"
    MANAGER = "manager"


class QuoteStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


# Authentication Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# User Models
class TeamMemberBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole = UserRole.SALES
    phone: Optional[str] = None


class TeamMemberCreate(TeamMemberBase):
    password: str
    company_id: int


class TeamMemberResponse(TeamMemberBase):
    id: int
    company_id: int
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TeamMemberUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


# Company Models
class CompanyBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "Netherlands"


class CompanyCreate(CompanyBase):
    pass


class CompanyResponse(CompanyBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Contact Models
class ContactBase(BaseModel):
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "Netherlands"
    notes: Optional[str] = None


class ContactCreate(ContactBase):
    company_id: int


class ContactResponse(ContactBase):
    id: int
    company_id: int
    created_by: Optional[int] = None
    ghl_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ContactUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    notes: Optional[str] = None


# Quote Models
class QuoteBase(BaseModel):
    quote_number: str
    quote_data: Dict[str, Any]
    status: QuoteStatus = QuoteStatus.DRAFT
    total_amount: Optional[float] = None
    currency: str = "EUR"
    valid_until: Optional[datetime] = None
    contact_id: Optional[int] = None


class QuoteCreate(QuoteBase):
    company_id: int


class QuoteResponse(QuoteBase):
    id: int
    company_id: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    creator_first_name: Optional[str] = None
    creator_last_name: Optional[str] = None
    creator_email: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class QuoteUpdate(BaseModel):
    quote_data: Optional[Dict[str, Any]] = None
    status: Optional[QuoteStatus] = None
    total_amount: Optional[float] = None
    valid_until: Optional[datetime] = None
    contact_id: Optional[int] = None


# GHL Integration Models
class GHLSyncRequest(BaseModel):
    overwrite: bool = False


# Current User Model
class CurrentUser(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    role: UserRole
    company_id: int
    company_name: str

