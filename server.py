from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta
import json

from database import get_db_connection, execute_query, execute_insert, execute_update
from auth import (
    hash_password, verify_password, create_access_token, 
    create_refresh_token, decode_token, ACCESS_TOKEN_EXPIRE_MINUTES
)
from models import (
    LoginRequest, TokenResponse, RefreshTokenRequest,
    TeamMemberResponse, TeamMemberCreate, TeamMemberUpdate,
    CompanyResponse, CompanyCreate,
    ContactResponse, ContactCreate, ContactUpdate,
    QuoteResponse, QuoteCreate, QuoteUpdate,
    CurrentUser, UserRole, QuoteStatus, GHLSyncRequest
)
try:
    from ghl_integration import (
        fetch_all_ghl_contacts, transform_ghl_contact_to_local, test_ghl_connection
    )
except ImportError:
    # GHL integration not available
    fetch_all_ghl_contacts = None
    transform_ghl_contact_to_local = None
    test_ghl_connection = None
try:
    from ghl_integration import (
        fetch_all_ghl_contacts, transform_ghl_contact_to_local, test_ghl_connection
    )
    GHL_AVAILABLE = True
except ImportError:
    # GHL integration not available
    GHL_AVAILABLE = False
    def fetch_all_ghl_contacts():
        raise HTTPException(status_code=500, detail="GHL integration not configured")
    def transform_ghl_contact_to_local(*args):
        raise HTTPException(status_code=500, detail="GHL integration not configured")
    def test_ghl_connection():
        return {"success": False, "message": "GHL integration not configured"}

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create the main app
app = FastAPI(title="WinDoorPro API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()


# Dependency to get current user
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> CurrentUser:
    """Extract and validate current user from JWT token"""
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Get user from database
    query = """
        SELECT tm.id, tm.email, tm.first_name, tm.last_name, tm.role, tm.company_id, c.name as company_name
        FROM team_members tm
        JOIN companies c ON tm.company_id = c.id
        WHERE tm.id = %s AND tm.is_active = TRUE
    """
    results = execute_query(query, (int(user_id),))
    
    if not results:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    user_data = results[0]
    return CurrentUser(
        id=user_data['id'],
        email=user_data['email'],
        first_name=user_data['first_name'],
        last_name=user_data['last_name'],
        role=UserRole(user_data['role']),
        company_id=user_data['company_id'],
        company_name=user_data['company_name']
    )


# Authentication Routes
@api_router.post("/auth/login", response_model=TokenResponse)
def login(login_data: LoginRequest):
    """Login endpoint"""
    # Get user from database
    query = """
        SELECT tm.id, tm.email, tm.password_hash, tm.first_name, tm.last_name, 
               tm.role, tm.company_id, tm.is_active, c.name as company_name
        FROM team_members tm
        JOIN companies c ON tm.company_id = c.id
        WHERE tm.email = %s
    """
    results = execute_query(query, (login_data.email,))
    
    if not results:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    user = results[0]
    
    if not user['is_active']:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive"
        )
    
    # Verify password
    if not verify_password(login_data.password, user['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Update last login
    update_query = "UPDATE team_members SET last_login = %s WHERE id = %s"
    execute_update(update_query, (datetime.now(), user['id']))
    
    # Create tokens
    token_data = {
        "sub": str(user['id']),
        "email": user['email'],
        "role": user['role'],
        "company_id": user['company_id']
    }
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    # Store refresh token in database
    expires_at = datetime.now() + timedelta(days=30)
    insert_query = """
        INSERT INTO refresh_tokens (team_member_id, token, expires_at)
        VALUES (%s, %s, %s)
    """
    execute_insert(insert_query, (user['id'], refresh_token, expires_at))
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@api_router.post("/auth/refresh", response_model=TokenResponse)
def refresh_token(refresh_data: RefreshTokenRequest):
    """Refresh access token"""
    payload = decode_token(refresh_data.refresh_token)
    
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Verify refresh token exists in database
    query = "SELECT team_member_id FROM refresh_tokens WHERE token = %s AND expires_at > %s"
    results = execute_query(query, (refresh_data.refresh_token, datetime.now()))
    
    if not results:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or expired"
        )
    
    user_id = payload.get("sub")
    
    # Get user data
    user_query = """
        SELECT tm.id, tm.email, tm.role, tm.company_id
        FROM team_members tm
        WHERE tm.id = %s AND tm.is_active = TRUE
    """
    user_results = execute_query(user_query, (int(user_id),))
    
    if not user_results:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    user = user_results[0]
    
    # Create new tokens
    token_data = {
        "sub": str(user['id']),
        "email": user['email'],
        "role": user['role'],
        "company_id": user['company_id']
    }
    
    access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)
    
    # Update refresh token in database
    expires_at = datetime.now() + timedelta(days=30)
    update_query = """
        UPDATE refresh_tokens 
        SET token = %s, expires_at = %s 
        WHERE token = %s
    """
    execute_update(update_query, (new_refresh_token, expires_at, refresh_data.refresh_token))
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@api_router.post("/auth/logout")
def logout(current_user: CurrentUser = Depends(get_current_user)):
    """Logout endpoint - invalidate refresh tokens"""
    query = "DELETE FROM refresh_tokens WHERE team_member_id = %s"
    execute_update(query, (current_user.id,))
    return {"message": "Logged out successfully"}


@api_router.get("/auth/me", response_model=CurrentUser)
def get_current_user_info(current_user: CurrentUser = Depends(get_current_user)):
    """Get current user information"""
    return current_user


# Team Members Routes
@api_router.get("/team", response_model=List[TeamMemberResponse])
def get_team_members(current_user: CurrentUser = Depends(get_current_user)):
    """Get all team members for the current user's company"""
    query = """
        SELECT id, company_id, email, first_name, last_name, role, phone, 
               is_active, last_login, created_at, updated_at
        FROM team_members
        WHERE company_id = %s
        ORDER BY created_at DESC
    """
    results = execute_query(query, (current_user.company_id,))
    return [TeamMemberResponse(**row) for row in results]


@api_router.post("/team", response_model=TeamMemberResponse)
def create_team_member(
    member_data: TeamMemberCreate,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Create a new team member (admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create team members"
        )
    
    if member_data.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create team member for different company"
        )
    
    # Check if email already exists
    check_query = "SELECT id FROM team_members WHERE email = %s"
    existing = execute_query(check_query, (member_data.email,))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    # Hash password
    password_hash = hash_password(member_data.password)
    
    # Insert team member
    insert_query = """
        INSERT INTO team_members (company_id, email, password_hash, first_name, last_name, role, phone)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    member_id = execute_insert(insert_query, (
        member_data.company_id,
        member_data.email,
        password_hash,
        member_data.first_name,
        member_data.last_name,
        member_data.role.value,
        member_data.phone
    ))
    
    # Get created member
    get_query = """
        SELECT id, company_id, email, first_name, last_name, role, phone, 
               is_active, last_login, created_at, updated_at
        FROM team_members
        WHERE id = %s
    """
    result = execute_query(get_query, (member_id,))[0]
    return TeamMemberResponse(**result)


@api_router.delete("/team/{member_id}")
def delete_team_member(
    member_id: int,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Delete a team member (admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete team members"
        )
    
    # Prevent admin from deleting themselves
    if member_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Check if member exists and belongs to the same company
    check_query = """
        SELECT id, company_id FROM team_members WHERE id = %s
    """
    member = execute_query(check_query, (member_id,))
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found"
        )
    
    if member[0]['company_id'] != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete team member from different company"
        )
    
    # Delete refresh tokens first (foreign key constraint)
    delete_tokens_query = "DELETE FROM refresh_tokens WHERE team_member_id = %s"
    execute_update(delete_tokens_query, (member_id,))
    
    # Delete the team member
    delete_query = "DELETE FROM team_members WHERE id = %s"
    execute_update(delete_query, (member_id,))
    
    return {"message": "Team member deleted successfully"}


# Contacts Routes
@api_router.get("/contacts", response_model=List[ContactResponse])
def get_contacts(current_user: CurrentUser = Depends(get_current_user)):
    """Get all contacts for the current user's company"""
    query = """
        SELECT id, company_id, first_name, last_name, email, phone, address, 
               city, postal_code, country, notes, ghl_data, created_by, created_at, updated_at
        FROM contacts
        WHERE company_id = %s
        ORDER BY created_at DESC
    """
    results = execute_query(query, (current_user.company_id,))
    # Parse JSON ghl_data if present
    for result in results:
        if result.get('ghl_data') and isinstance(result['ghl_data'], str):
            try:
                result['ghl_data'] = json.loads(result['ghl_data'])
            except:
                result['ghl_data'] = None
    return [ContactResponse(**row) for row in results]


@api_router.post("/contacts", response_model=ContactResponse)
def create_contact(
    contact_data: ContactCreate,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Create a new contact"""
    if contact_data.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create contact for different company"
        )
    
    insert_query = """
        INSERT INTO contacts (company_id, first_name, last_name, email, phone, 
                             address, city, postal_code, country, notes, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    contact_id = execute_insert(insert_query, (
        contact_data.company_id,
        contact_data.first_name,
        contact_data.last_name,
        contact_data.email,
        contact_data.phone,
        contact_data.address,
        contact_data.city,
        contact_data.postal_code,
        contact_data.country,
        contact_data.notes,
        current_user.id
    ))
    
    get_query = """
        SELECT id, company_id, first_name, last_name, email, phone, address, 
               city, postal_code, country, notes, ghl_data, created_by, created_at, updated_at
        FROM contacts
        WHERE id = %s
    """
    result = execute_query(get_query, (contact_id,))[0]
    # Parse JSON ghl_data if present
    if result.get('ghl_data') and isinstance(result['ghl_data'], str):
        try:
            result['ghl_data'] = json.loads(result['ghl_data'])
        except:
            result['ghl_data'] = None
    return ContactResponse(**result)


@api_router.get("/contacts/{contact_id}", response_model=ContactResponse)
def get_contact(contact_id: int, current_user: CurrentUser = Depends(get_current_user)):
    """Get a specific contact"""
    query = """
        SELECT id, company_id, first_name, last_name, email, phone, address, 
               city, postal_code, country, notes, ghl_data, created_by, created_at, updated_at
        FROM contacts
        WHERE id = %s AND company_id = %s
    """
    results = execute_query(query, (contact_id, current_user.company_id))
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )
    result = results[0]
    # Parse JSON ghl_data if present
    if result.get('ghl_data') and isinstance(result['ghl_data'], str):
        try:
            result['ghl_data'] = json.loads(result['ghl_data'])
        except:
            result['ghl_data'] = None
    return ContactResponse(**result)


# GHL Integration Routes
@api_router.get("/ghl/test-connection")
def test_ghl_api_connection(current_user: CurrentUser = Depends(get_current_user)):
    """Test GHL API connection (admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can test GHL connection"
        )
    
    if not GHL_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GHL integration module not available"
        )
    
    result = test_ghl_connection()
    return result


@api_router.post("/ghl/sync-contacts")
def sync_ghl_contacts(
    request: GHLSyncRequest,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Sync contacts from GoHighLevel to local database (admin only)
    
    Request body:
        overwrite: If True, update existing contacts. If False, skip duplicates.
    """
    overwrite = request.overwrite
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can sync GHL contacts"
        )
    
    if not GHL_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GHL integration module not available"
        )
    
    try:
        # Fetch all contacts from GHL
        ghl_contacts = fetch_all_ghl_contacts()
        
        synced_count = 0
        skipped_count = 0
        error_count = 0
        
        for ghl_contact in ghl_contacts:
            try:
                # Transform GHL contact to local format
                contact_data = transform_ghl_contact_to_local(ghl_contact)
                
                # Debug logging to verify data before saving
                logging.info(f"Contact data before save: email='{contact_data.get('email')}', phone='{contact_data.get('phone')}', name='{contact_data.get('first_name')} {contact_data.get('last_name')}'")
                
                # Check if contact already exists (by email if available)
                if contact_data.get('email'):
                    check_query = """
                        SELECT id FROM contacts 
                        WHERE company_id = %s AND email = %s
                    """
                    existing = execute_query(check_query, (current_user.company_id, contact_data['email']))
                    
                    if existing and not overwrite:
                        skipped_count += 1
                        continue
                    
                    if existing and overwrite:
                        # Update existing contact
                        update_query = """
                            UPDATE contacts 
                            SET first_name = %s, last_name = %s, phone = %s,
                                address = %s, city = %s, postal_code = %s,
                                country = %s, notes = %s
                            WHERE id = %s AND company_id = %s
                        """
                        execute_update(update_query, (
                            contact_data['first_name'],
                            contact_data['last_name'],
                            contact_data['phone'],
                            contact_data['address'],
                            contact_data['city'],
                            contact_data['postal_code'],
                            contact_data['country'],
                            contact_data['notes'],
                            existing[0]['id'],
                            current_user.company_id
                        ))
                        synced_count += 1
                        continue
                
                # Insert new contact with full GHL data
                insert_query = """
                    INSERT INTO contacts (company_id, first_name, last_name, email, phone, 
                                       address, city, postal_code, country, notes, ghl_data, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                # Store the full GHL contact data as JSON
                ghl_data_json = json.dumps(ghl_contact) if ghl_contact else None
                
                # Log the exact values being inserted
                logging.info(f"Inserting contact - Email: '{contact_data['email']}', Phone: '{contact_data['phone']}', Address: '{contact_data['address']}', City: '{contact_data['city']}', Postal: '{contact_data['postal_code']}', Country: '{contact_data['country']}'")
                
                contact_id = execute_insert(insert_query, (
                    current_user.company_id,
                    contact_data['first_name'],
                    contact_data['last_name'],
                    contact_data['email'],
                    contact_data['phone'],
                    contact_data['address'],
                    contact_data['city'],
                    contact_data['postal_code'],
                    contact_data['country'],
                    contact_data['notes'],
                    ghl_data_json,
                    current_user.id
                ))
                
                # Verify what was actually saved
                verify_query = "SELECT email, phone, address, city, postal_code, country FROM contacts WHERE id = %s"
                saved_data = execute_query(verify_query, (contact_id,))
                if saved_data:
                    logging.info(f"Contact saved with ID {contact_id} - Email: '{saved_data[0].get('email')}', Phone: '{saved_data[0].get('phone')}', Address: '{saved_data[0].get('address')}', City: '{saved_data[0].get('city')}', Postal: '{saved_data[0].get('postal_code')}', Country: '{saved_data[0].get('country')}'")
                
                synced_count += 1
                
            except Exception as e:
                error_count += 1
                logging.error(f"Error syncing contact {ghl_contact.get('id', 'unknown')}: {str(e)}")
                continue
        
        return {
            'success': True,
            'message': f'Synced {synced_count} contacts from GHL',
            'synced': synced_count,
            'skipped': skipped_count,
            'errors': error_count,
            'total_ghl_contacts': len(ghl_contacts)
        }
        
    except Exception as e:
        logging.error(f"Error syncing GHL contacts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync contacts from GHL: {str(e)}"
        )


# Quotes Routes
@api_router.get("/quotes", response_model=List[QuoteResponse])
def get_quotes(current_user: CurrentUser = Depends(get_current_user)):
    """Get quotes for the current user's company
    - Admin: sees all quotes for the company
    - User: sees only quotes they created
    """
    if current_user.role == UserRole.ADMIN:
        # Admin sees all quotes for the company with creator information
        query = """
            SELECT q.id, q.company_id, q.contact_id, q.quote_number, q.quote_data, q.status, 
                   q.total_amount, q.currency, q.valid_until, q.created_by, q.created_at, q.updated_at,
                   tm.first_name as creator_first_name, tm.last_name as creator_last_name, tm.email as creator_email
            FROM quotes q
            LEFT JOIN team_members tm ON q.created_by = tm.id
            WHERE q.company_id = %s
            ORDER BY q.created_at DESC
        """
        results = execute_query(query, (current_user.company_id,))
    else:
        # Regular users see only their own quotes
        query = """
            SELECT id, company_id, contact_id, quote_number, quote_data, status, 
                   total_amount, currency, valid_until, created_by, created_at, updated_at
            FROM quotes
            WHERE company_id = %s AND created_by = %s
            ORDER BY created_at DESC
        """
        results = execute_query(query, (current_user.company_id, current_user.id))
    
    # Convert JSON string to dict if needed
    for result in results:
        if isinstance(result['quote_data'], str):
            result['quote_data'] = json.loads(result['quote_data'])
    return [QuoteResponse(**row) for row in results]


@api_router.post("/quotes", response_model=QuoteResponse)
def create_quote(
    quote_data: QuoteCreate,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Create a new quote"""
    if quote_data.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create quote for different company"
        )
    
    insert_query = """
        INSERT INTO quotes (company_id, contact_id, quote_number, quote_data, status, 
                          total_amount, currency, valid_until, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    quote_id = execute_insert(insert_query, (
        quote_data.company_id,
        quote_data.contact_id,
        quote_data.quote_number,
        json.dumps(quote_data.quote_data),
        quote_data.status.value,
        quote_data.total_amount,
        quote_data.currency,
        quote_data.valid_until,
        current_user.id
    ))
    
    get_query = """
        SELECT id, company_id, contact_id, quote_number, quote_data, status, 
               total_amount, currency, valid_until, created_by, created_at, updated_at
        FROM quotes
        WHERE id = %s
    """
    result = execute_query(get_query, (quote_id,))[0]
    if isinstance(result['quote_data'], str):
        result['quote_data'] = json.loads(result['quote_data'])
    return QuoteResponse(**result)


# Include the router in the main app
app.include_router(api_router)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.get("/")
def root():
    return {"message": "WinDoorPro API", "version": "1.0.0"}
