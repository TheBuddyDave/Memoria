# Cloudflare Pages Functions Setup Guide

This guide explains how to set up the waitlist functionality using Cloudflare Pages Functions and D1 Database.

## Free Tier Compatibility ✅

**This implementation works perfectly on Cloudflare's free tier!** No payment required.

### Free Tier Limits:
- **Pages Functions**: 100,000 requests per day
- **D1 Database**: 
  - 5 GB total storage (across all databases)
  - 5 million rows read per day
  - 100,000 rows written per day
  - Up to 10 databases

For a waitlist, these limits are more than sufficient. Even with thousands of signups, you'll stay well within the free tier.

## Prerequisites

1. A Cloudflare account (free account works perfectly)
2. Wrangler CLI installed (`npm install -g wrangler`)
3. Cloudflare Pages project connected to your repository

## Setup Steps

### 1. Create a D1 Database

Run the following command to create a new D1 database:

```bash
wrangler d1 create mindmarque-db
```

This will output something like:
```
✅ Successfully created DB 'mindmarque-db' in region WEUR

[[d1_databases]]
binding = "DB"
database_name = "mindmarque-db"
database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

### 2. Update wrangler.toml

Copy the `database_id` from the output above and update `frontend/wrangler.toml`:

```toml
[[d1_databases]]
binding = "DB"
database_name = "mindmarque-db"
database_id = "your-database-id-here"  # Replace with your actual database ID
```

### 3. Run Database Migration

Execute the schema migration to create the waitlist table:

```bash
cd frontend
wrangler d1 execute mindmarque-db --file=./schema.sql --remote
```

### 4. Configure Cloudflare Pages

In your Cloudflare Pages dashboard:

1. Go to your project settings
2. Navigate to **Functions** → **D1 Database bindings**
3. Add a binding:
   - **Variable name**: `DB`
   - **D1 Database**: Select `mindmarque-db`

### 5. Deploy

The Cloudflare Pages Function will be automatically deployed when you push to your repository. The function is located at:
- `frontend/functions/api/waitlist.js` (or `.ts`)

## Local Development

When running locally, Wrangler uses a **local SQLite database** that mimics D1. This database is stored in `.wrangler/state/v3/d1/` directory (relative to where you run wrangler commands).

### Setting Up Local Development

1. **Create the local database schema:**
   ```bash
   cd frontend
   wrangler d1 execute mindmarque-db --local --file=./schema.sql
   ```
   
   This creates a local SQLite file at `.wrangler/state/v3/d1/miniflare-D1DatabaseObject/<database-id>/db.sqlite`

2. **Start the local development server:**
   ```bash
   # First, build your frontend
   npm run build
   
   # Then start Wrangler Pages dev server
   wrangler pages dev dist --d1=DB=mindmarque-db
   ```

3. **Access the API:**
   - Frontend: `http://localhost:8788` (or the port Wrangler assigns)
   - API endpoint: `http://localhost:8788/api/waitlist`

### Important Notes About Local Development

- **Separate databases**: The local SQLite database is completely separate from your production D1 database
- **Database location**: The local database file is stored in `.wrangler/state/v3/d1/` (this directory is gitignored)
- **Data persistence**: Local database data persists between runs (until you delete `.wrangler/` directory)
- **Migrations**: You need to run migrations separately for local (`--local` flag) and production (no flag)

### Querying Local Database

To view entries in your local database:

```bash
wrangler d1 execute mindmarque-db --local --command="SELECT * FROM waitlist ORDER BY created_at DESC LIMIT 10"
```

### Resetting Local Database

To start fresh locally, delete the `.wrangler` directory:

```bash
rm -rf .wrangler
wrangler d1 execute mindmarque-db --local --file=./schema.sql
```

## API Endpoint

Once deployed, the waitlist endpoint will be available at:
- Production: `https://your-domain.com/api/waitlist`
- Local: `http://localhost:8788/api/waitlist`

### Request Format

```json
POST /api/waitlist
Content-Type: application/json

{
  "email": "user@example.com"
}
```

### Response Format

**Success:**
```json
{
  "success": true,
  "message": "Successfully added to waitlist!"
}
```

**Already exists:**
```json
{
  "success": true,
  "message": "You're already on the waitlist!",
  "alreadyExists": true
}
```

**Error:**
```json
{
  "error": "Invalid email format"
}
```

## Database Schema

The waitlist table has the following structure:

```sql
CREATE TABLE waitlist (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE NOT NULL,
  created_at TEXT NOT NULL
);
```

## Querying the Database

To view waitlist entries:

```bash
wrangler d1 execute mindmarque-db --command="SELECT * FROM waitlist ORDER BY created_at DESC LIMIT 10"
```

## Troubleshooting

### Function not found
- Make sure `functions/api/waitlist.js` is in your repository
- Check that the file is in the correct location relative to your Pages project root

### Database binding error
- Verify the D1 database binding is configured in Cloudflare Pages dashboard
- Check that `wrangler.toml` has the correct database_id

### CORS issues
- The function includes CORS headers for OPTIONS requests
- Make sure your frontend is making requests to the correct domain

## Notes

- The function uses JavaScript (`.js`) for maximum compatibility. If you prefer TypeScript, you can use `.ts` but may need additional build configuration.
- Email addresses are normalized (lowercased and trimmed) before storage
- Duplicate emails are detected and return a friendly message
- All timestamps are stored in ISO 8601 format

