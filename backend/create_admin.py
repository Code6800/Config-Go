"""
Script to create or update admin user password
Usage: python create_admin.py <email> <password>
"""
import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from auth import hash_password
from database import execute_query, execute_update, execute_insert

def create_or_update_admin(email, password):
    """Create or update admin user password"""
    # Hash the password
    password_hash = hash_password(password)
    
    # Check if user exists
    query = "SELECT id FROM team_members WHERE email = %s"
    existing = execute_query(query, (email,))
    
    if existing:
        # Update existing user
        update_query = "UPDATE team_members SET password_hash = %s WHERE email = %s"
        execute_update(update_query, (password_hash, email))
        print(f"[OK] Password updated for user: {email}")
    else:
        # Get company ID (assuming VMK Kozijnen is company ID 1)
        company_query = "SELECT id FROM companies WHERE name = 'VMK Kozijnen' LIMIT 1"
        company_result = execute_query(company_query)
        
        if not company_result:
            print("[ERROR] VMK Kozijnen company not found. Please run schema.sql first.")
            return
        
        company_id = company_result[0]['id']
        
        # Create new user
        insert_query = """
            INSERT INTO team_members (company_id, email, password_hash, first_name, last_name, role)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        execute_insert(insert_query, (
            company_id,
            email,
            password_hash,
            'Admin',
            'User',
            'admin'
        ))
        print(f"[OK] Admin user created: {email}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python create_admin.py <email> <password>")
        print("Example: python create_admin.py admin@vmkkozijnen.nl mypassword123")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    try:
        create_or_update_admin(email, password)
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

