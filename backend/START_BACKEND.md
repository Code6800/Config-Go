# How to Start the Backend Server

## Step 1: Navigate to Backend Directory

Open Git Bash or Command Prompt and run:
```bash
cd /c/xampp/htdocs/jopp/backend
```

## Step 2: Verify .env File Exists

Make sure you have a `.env` file with:
```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=
DB_NAME=windoorpro
JWT_SECRET_KEY=windoorpro-secret-key-change-in-production-2024
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

If it doesn't exist, create it.

## Step 3: Install Dependencies (if not done already)

```bash
pip install -r requirements.txt
```

Or if you need to use python3:
```bash
python3 -m pip install -r requirements.txt
```

## Step 4: Start the Server

```bash
python -m uvicorn server:app --reload --port 8000
```

You should see output like:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## Step 5: Keep This Terminal Open

The backend server must stay running. Keep this terminal window open.

## Step 6: Test the Backend

Open a new browser tab and go to:
```
http://localhost:8000
```

You should see: `{"message":"WinDoorPro API","version":"1.0.0"}`

## Troubleshooting

### "uvicorn: command not found"
Use `python -m uvicorn` instead:
```bash
python -m uvicorn server:app --reload --port 8000
```

Or install uvicorn globally:
```bash
pip install uvicorn
```

### "ModuleNotFoundError"
Install all dependencies:
```bash
pip install -r requirements.txt
```

### "Can't connect to MySQL"
- Make sure MySQL is running in XAMPP
- Check your `.env` file has correct database credentials
- Verify database `windoorpro` exists

### Port 8000 already in use
Use a different port:
```bash
python -m uvicorn server:app --reload --port 8001
```
Then update frontend `.env` or `AuthContext.jsx` to use port 8001.

