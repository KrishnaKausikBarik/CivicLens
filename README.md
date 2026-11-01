# CivicLens

CivicLens is a Flask-backed citizen complaint application with a vanilla JavaScript frontend. The backend connects to Supabase PostgreSQL through SQLAlchemy and psycopg; database credentials stay in the backend environment.

## Local setup

1. Install Python 3.9 or newer and dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Edit the project-root `.env` file. In Supabase, open **Connect → Transaction pooler** and copy its connection string. This shared pooler endpoint is IPv4-compatible and works from Vercel. Enter it as `DATABASE_URL`, changing the URL scheme to `postgresql+psycopg://` if the copied value starts with `postgresql://`.

   Example format (replace with the exact host, username, and database from your Supabase Connect panel):

   ```dotenv
   DATABASE_URL=postgresql+psycopg://postgres.YOUR_PROJECT_REF:YOUR_DB_PASSWORD@YOUR_POOLER_HOST:6543/postgres?sslmode=require
   ```

   Replace the pooler host, project-specific username, and password with the exact values from Supabase. Keep the generated `SECRET_KEY` line already present in `.env`. Set this same URL as Vercel's `DATABASE_URL` and redeploy.

   Do not send your password in chat or commit `.env`. Percent-encode reserved URL characters in the password. If your local network cannot reach Supabase’s direct IPv6 endpoint, use the exact session-pooler URL from **Connect**. For Vercel later, select the Supabase pooler connection mode suitable for serverless and retain SSL.

3. Start the local Flask server:

   ```powershell
   python app.py
   ```

   Startup initializes the Flask app without opening a database connection. `GET /api/health/database` runs `SELECT 1` and reports the connection state.

## Supabase data safety

The application does not call `create_all`, run migrations, seed demo reports, disable RLS, or modify table contents during startup. The models are aligned to the existing `users` and `reports` Supabase schema. The database does not have `reports.admin_notes` or `reports.updated_at`; API output keeps those response keys with null/created-time compatibility values. Existing legacy complaints with a null `user_id` continue to display as `Legacy/Unknown` in the admin dashboard.

## Authentication and complaint flow

- Register and log in as a citizen from the home page. Passwords are stored as Werkzeug hashes.
- Citizen sessions can submit complaints and retrieve their own complaints. The backend assigns the current user ID; the browser never sends a trusted user ID.
- The Admin Portal retains the login modal and one administrator account configured through `ADMIN_USERNAME` and `ADMIN_PASSWORD_HASH`. The admin reports endpoint includes submitter name and email, and status changes are restricted to the admin session.
- State-changing API requests require the session CSRF token. API database operations use SQLAlchemy ORM query parameters.

## Vercel deployment

Deploy the repository root as one Vercel project. The root `app.py` exports the Flask WSGI app, `Backend/` and `Frontend/templates/` are bundled with the Python Function, and static assets are published from `public/static/` at the existing `/static/...` URLs. Flask detection itself is automatic; `vercel.json` explicitly includes the dynamically located templates in the function bundle.

Configure these Vercel environment variables for Production (and Preview if desired): `DATABASE_URL` using the Supabase **Transaction pooler** (port `6543`), `SECRET_KEY`, `FLASK_ENV=production`, `COOKIE_SECURE=true`, `ADMIN_USERNAME`, and `ADMIN_PASSWORD_HASH`. The direct database hostname resolves to IPv6, which Vercel cannot reach in this deployment. Generate a Werkzeug-compatible password hash locally with:

```powershell
python -c "from getpass import getpass; from werkzeug.security import generate_password_hash; print(generate_password_hash(getpass('Admin password: '), method='scrypt'))"
```

Set the printed hash directly as `ADMIN_PASSWORD_HASH` in Vercel Project Settings. Keep real values out of source control; `.env.example` contains placeholders only. Production startup fails closed when the PostgreSQL URL, signing key, or admin credentials are missing. SQLite remains a local-development fallback only.

## Local checks after entering `DATABASE_URL`

1. Run `python app.py`; confirm startup completes.
2. Open `http://127.0.0.1:5000/api/health/database`; expect `{"success":true,"database":"connected"}`.
3. Register a citizen, log in, submit a complaint, and confirm it appears in `/citizen`.
4. Log in through **Admin Portal** and confirm the complaint shows the citizen’s full name and email. Change its status and refresh to verify it persisted.
5. Confirm citizen requests to `/api/admin/reports` and admin requests to `/api/reports` are rejected.
