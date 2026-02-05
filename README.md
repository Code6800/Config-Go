# WinDoorPro Backend API

This is the backend API server for WinDoorPro, built with FastAPI and MySQL.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in this directory:

```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=
DB_NAME=windoorpro
JWT_SECRET_KEY=windoorpro-secret-key-change-in-production-2024
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### 3. Start the Server

```bash
python -m uvicorn server:app --reload --port 8000
```

Or in Git Bash:
```bash
cd /c/xampp/htdocs/jopp/backend
python -m uvicorn server:app --reload --port 8000
```

## Database Setup

The database schema is in `../landing/database/schema.sql`. Run it to create the database:

```bash
mysql -u root -p < ../landing/database/schema.sql
```

## Create Admin User

```bash
python create_admin.py admin@vmkkozijnen.nl yourpassword
```

## API Endpoints

- `POST /api/auth/login` - Login
- `POST /api/auth/refresh` - Refresh token
- `POST /api/auth/logout` - Logout
- `GET /api/auth/me` - Get current user
- `GET /api/contacts` - List contacts
- `POST /api/contacts` - Create contact
- `GET /api/team` - List team members
- `POST /api/team` - Create team member (admin only)
- `GET /api/quotes` - List quotes
- `POST /api/quotes` - Create quote

## Notes

- The backend uses MySQL (not MongoDB)
- All database connections are configured via `.env` file
- JWT tokens are used for authentication
- CORS is enabled for frontend access


