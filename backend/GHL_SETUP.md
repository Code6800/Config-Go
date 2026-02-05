# GoHighLevel (GHL) Integration Setup

This guide explains how to set up the GoHighLevel API integration to sync contacts from your GHL account.

## Prerequisites

1. A GoHighLevel account with API access
2. An API key from your GHL account
3. Your GHL Location ID

## Getting Your GHL API Credentials

### Step 1: Get Your API Key (Bearer Token)

1. Log in to your GoHighLevel account
2. Navigate to **Settings** → **Integrations** → **API**
3. Click on **"Create API Key"** or use an existing key
4. Copy the API key (Bearer Token) - it will look like: `pit-529ada05-dcf8-4414-aa08-ae7a6cafd1ed`
5. **Important**: This is your Bearer Token, not a JWT token. Use it directly as the API key.

### Step 2: Get Your Location ID

1. In GoHighLevel, go to **Settings** → **Locations**
2. Select your location
3. The Location ID is in the URL or can be found in the location settings
4. It's typically a string like: `abc123def456`

## Configuration

### Step 1: Update .env File

Add the following variables to your `jopp/backend/.env` file:

```env
# GoHighLevel API Configuration
GHL_API_URL=https://services.leadconnectorhq.com
GHL_API_KEY=your_api_key_here
GHL_LOCATION_ID=your_location_id_here
```

**Important:** Replace `your_api_key_here` and `your_location_id_here` with your actual credentials.

### Step 2: Install Dependencies

The `requests` library is already included in `requirements.txt`. If you need to install it:

```bash
cd jopp/backend
pip install requests
```

### Step 3: Restart Backend Server

After updating the `.env` file, restart your backend server:

```bash
python -m uvicorn server:app --reload --port 8000
```

## Using the Integration

### Testing the Connection

1. Log in to the Dashboard as an admin
2. Go to the **Contacts** tab
3. Click **"Sync from GHL"** button
4. The system will test the connection and sync contacts

### API Endpoints

#### Test Connection
```
GET /api/ghl/test-connection
```
Tests the GHL API connection (admin only)

#### Sync Contacts
```
POST /api/ghl/sync-contacts?overwrite=false
```
Syncs all contacts from GHL to your local database (admin only)

**Parameters:**
- `overwrite` (boolean, default: false): If true, updates existing contacts. If false, skips duplicates.

### How It Works

1. **Fetching Contacts**: The system fetches all contacts from your GHL account
2. **Transformation**: GHL contact data is transformed to match your local database schema
3. **Deduplication**: Contacts are matched by email address
4. **Sync Options**:
   - **Skip Duplicates** (default): Existing contacts are not updated
   - **Overwrite**: Existing contacts are updated with GHL data

### Contact Mapping

The integration maps GHL contact fields to your local database:

| GHL Field | Local Field |
|-----------|-------------|
| firstName | first_name |
| lastName | last_name |
| email | email |
| phone / phoneNumber | phone |
| address.address1 | address |
| address.city | city |
| address.postalCode | postal_code |
| address.country | country |
| tags | notes |

## Troubleshooting

### Error: "GHL_API_KEY is not set in .env file"

**Solution:** Make sure you've added `GHL_API_KEY` to your `.env` file and restarted the backend server.

### Error: "GHL_LOCATION_ID is not set in .env file"

**Solution:** Make sure you've added `GHL_LOCATION_ID` to your `.env` file and restarted the backend server.

### Error: "Failed to fetch contacts from GHL: 401 Unauthorized"

**Solution:** 
- Verify your API key is correct
- Make sure the API key hasn't expired
- Check that the API key has the necessary permissions

### Error: "Failed to fetch contacts from GHL: 404 Not Found"

**Solution:**
- Verify your Location ID is correct
- Make sure the location exists in your GHL account

### Contacts Not Syncing

**Check:**
1. API credentials are correct in `.env`
2. Backend server has been restarted after updating `.env`
3. You're logged in as an admin user
4. GHL account has contacts available

## Security Notes

- **Never commit your `.env` file** to version control
- Keep your API key secure and rotate it periodically
- The API key should only be accessible to authorized administrators

## API Documentation

For more information about the GoHighLevel API, visit:
- [GoHighLevel API Documentation](https://highlevel.stoplight.io/docs/integrations)

