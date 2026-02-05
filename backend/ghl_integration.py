"""
GoHighLevel (GHL) API Integration
"""
import os
import requests
import logging
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# GHL API Configuration
GHL_API_URL = os.environ.get('GHL_API_URL', 'https://services.leadconnectorhq.com')
GHL_API_KEY = os.environ.get('GHL_API_KEY', '')
GHL_LOCATION_ID = os.environ.get('GHL_LOCATION_ID', '')


def get_ghl_headers() -> Dict[str, str]:
    """Get headers for GHL API requests"""
    return {
        'Accept': 'application/json',
        'Authorization': f'Bearer {GHL_API_KEY}',
        'Version': '2021-07-28'
    }


def fetch_ghl_contacts(limit: int = 100, start_after: Optional[List] = None) -> Tuple[List[Dict], Optional[List]]:
    """
    Fetch contacts from GoHighLevel API
    
    Args:
        limit: Maximum number of contacts to fetch per request (GHL API doesn't support skip)
        start_after: Cursor for pagination (not currently used as GHL API doesn't support it via query params)
    
    Returns:
        Tuple of (list of contact dictionaries, next page cursor or None)
    """
    if not GHL_API_KEY or not GHL_LOCATION_ID:
        raise ValueError("GHL_API_KEY and GHL_LOCATION_ID must be set in .env file")
    
    url = f"{GHL_API_URL}/contacts/"
    headers = get_ghl_headers()
    # GHL API doesn't support 'skip' parameter - only 'limit' and 'locationId'
    params = {
        'locationId': GHL_LOCATION_ID,
        'limit': limit
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        contacts = data.get('contacts', [])
        
        # Get the cursor for next page from the last contact's startAfter field
        # Note: GHL API doesn't support pagination via query params, so we'll fetch what we can
        next_cursor = None
        if contacts:
            last_contact = contacts[-1]
            next_cursor = last_contact.get('startAfter')
        
        return contacts, next_cursor
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch contacts from GHL: {str(e)}")


def fetch_all_ghl_contacts() -> List[Dict]:
    """
    Fetch contacts from GHL
    
    Note: GHL API doesn't support 'skip' parameter for pagination.
    This function fetches up to the limit specified (default 100).
    For larger datasets, you may need to implement cursor-based pagination
    using the startAfter field from the response, but GHL API doesn't
    support it as a query parameter.
    
    Returns:
        List of contact dictionaries (up to the limit per request)
    """
    # GHL API doesn't support skip parameter, so we can only fetch one page
    # Try with a higher limit to get more contacts in one request
    limit = 1000  # Maximum reasonable limit
    
    try:
        contacts, _ = fetch_ghl_contacts(limit=limit)
        return contacts
    except Exception as e:
        # If high limit fails, try with default limit
        try:
            contacts, _ = fetch_ghl_contacts(limit=100)
            return contacts
        except:
            # Re-raise the original error
            raise e


def transform_ghl_contact_to_local(ghl_contact: Dict) -> Dict:
    """
    Transform a GHL contact to match local contact schema
    
    Args:
        ghl_contact: Contact dictionary from GHL API
    
    Returns:
        Transformed contact dictionary matching local schema
    """
    # Extract name
    first_name = ghl_contact.get('firstName', '') or ''
    last_name = ghl_contact.get('lastName', '') or ''
    
    # If name is in a single field, try to split it
    if not first_name and not last_name:
        full_name = ghl_contact.get('name', '') or ''
        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
    
    # Extract email - GHL API returns email directly
    email = ghl_contact.get('email') or ''
    if email is None:
        email = ''
    
    # Extract phone - GHL API returns phone directly
    phone = ghl_contact.get('phone') or ''
    if phone is None:
        phone = ''
    
    # Extract address - GHL API returns address fields directly
    address = ghl_contact.get('address1', '') or ''
    city = ghl_contact.get('city', '') or ''
    postal_code = ghl_contact.get('postalCode', '') or ''
    country = ghl_contact.get('country', 'NL') or 'NL'
    
    # Map country code to full name if needed
    country_map = {
        'NL': 'Netherlands',
        'US': 'United States',
        'GB': 'United Kingdom',
        'DE': 'Germany',
        'BE': 'Belgium',
        'FR': 'France'
    }
    country = country_map.get(country.upper(), country) if country else 'Netherlands'
    
    # Extract notes/tags
    tags = ghl_contact.get('tags', [])
    notes = ', '.join(tags) if tags else ''
    
    # Debug logging to verify data extraction
    logging.info(f"GHL Contact Transform - Name: {first_name} {last_name}, Email: '{email}', Phone: '{phone}', Address: '{address}', City: '{city}', Postal: '{postal_code}', Country: '{country}'")
    
    return {
        'first_name': first_name,
        'last_name': last_name,
        'email': email if email else None,
        'phone': phone if phone else None,
        'address': address.strip() if address and address.strip() else None,
        'city': city.strip() if city and city.strip() else None,
        'postal_code': postal_code.strip() if postal_code and postal_code.strip() else None,
        'country': country,
        'notes': notes.strip() if notes and notes.strip() else None,
        'ghl_contact_id': ghl_contact.get('id'),  # Store GHL ID for future reference
    }


def test_ghl_connection() -> Dict:
    """
    Test the GHL API connection
    
    Returns:
        Dictionary with connection status and message
    """
    if not GHL_API_KEY:
        return {
            'success': False,
            'message': 'GHL_API_KEY is not set in .env file'
        }
    
    if not GHL_LOCATION_ID:
        return {
            'success': False,
            'message': 'GHL_LOCATION_ID is not set in .env file'
        }
    
    try:
        # Try to fetch a small number of contacts to test the connection
        contacts, _ = fetch_ghl_contacts(limit=1)
        return {
            'success': True,
            'message': f'Successfully connected to GHL. Found contacts in your account.',
            'contact_count': len(contacts)
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Failed to connect to GHL: {str(e)}'
        }

