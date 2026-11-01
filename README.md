<<<<<<< HEAD
# CivicLens

CivicLens is a Flask-backed citizen complaint application with a vanilla JavaScript frontend. The backend connects to Supabase PostgreSQL through SQLAlchemy and psycopg; database credentials stay in the backend environment.

## Local setup

1. Install Python 3.9 or newer and dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Edit the project-root `.env` file. In Supabase, open **Connect** and copy the PostgreSQL connection string. Enter it as `DATABASE_URL`, changing the URL scheme to `postgresql+psycopg://` if the copied value starts with `postgresql://`.

   Example format (replace with the exact host, username, and database from your Supabase Connect panel):

   ```dotenv
   DATABASE_URL=postgresql+psycopg://postgres:YOUR_DB_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres?sslmode=require
   ```

   Keep the generated `SECRET_KEY` line already present in `.env`.

   Do not send your password in chat or commit `.env`. Percent-encode reserved URL characters in the password. If your local network cannot reach Supabase’s direct IPv6 endpoint, use the exact session-pooler URL from **Connect**. For Vercel later, select the Supabase pooler connection mode suitable for serverless and retain SSL.

3. Start the local Flask server:

   ```powershell
   python app.py
   ```

   Startup runs `SELECT 1` against PostgreSQL and stops with a configuration or connection error if it cannot connect. After startup, `GET /api/health/database` reports the connection state.

## Supabase data safety

The application does not call `create_all`, run migrations, seed demo reports, disable RLS, or modify table contents during startup. The existing `users` and `reports` tables must have the columns mapped in `Backend/models/`. If `reports.user_id` or a foreign key is missing, review the schema first; no migration is run automatically. Existing legacy complaints with a null `user_id` continue to display as `Legacy/Unknown` in the admin dashboard.

## Authentication and complaint flow

- Register and log in as a citizen from the home page. Passwords are stored as Werkzeug hashes.
- Citizen sessions can submit complaints and retrieve their own complaints. The backend assigns the current user ID; the browser never sends a trusted user ID.
- The Admin Portal retains the login modal. Its only account is `admin` / `admin1234`. The admin reports endpoint includes submitter name and email, and status changes are restricted to the admin session.
- State-changing API requests require the session CSRF token. API database operations use SQLAlchemy ORM query parameters.

## Local checks after entering `DATABASE_URL`

1. Run `python app.py`; confirm startup completes.
2. Open `http://127.0.0.1:5000/api/health/database`; expect `{"success":true,"database":"connected"}`.
3. Register a citizen, log in, submit a complaint, and confirm it appears in `/citizen`.
4. Log in through **Admin Portal** and confirm the complaint shows the citizen’s full name and email. Change its status and refresh to verify it persisted.
5. Confirm citizen requests to `/api/admin/reports` and admin requests to `/api/reports` are rejected.

Vercel deployment is not configured or performed by this project update.
=======
# CivicLens
>>>>>>> bc76e2397cd78400f9820c2bf9026ad24c1b2fee
