# CivicLens

CivicLens is a Flask-backed citizen complaint application with a vanilla JavaScript frontend. The backend connects to Supabase PostgreSQL through SQLAlchemy and psycopg; database credentials stay in the backend environment.

## Local setup

1. Install Python 3.9 or newer and dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Edit the project-root `.env` file. In Supabase, open **Connect → Session pooler** and copy its shared pooler connection string. It is IPv4-compatible. Enter it as `DATABASE_URL`, changing the URL scheme to `postgresql+psycopg://` if the copied value starts with `postgresql://`.

   Example format (replace with the exact host, username, and database from your Supabase Connect panel):

   ```dotenv
   DATABASE_URL=postgresql+psycopg://postgres.YOUR_PROJECT_REF:YOUR_DB_PASSWORD@YOUR_POOLER_HOST:5432/postgres?sslmode=require
   ```

   Replace the pooler host, project-specific username, and password with the exact values from Supabase. Keep the generated `SECRET_KEY` line already present in `.env`. Set this same URL as Vercel's `DATABASE_URL` and redeploy.

   Do not send your password in chat or commit `.env`. Percent-encode reserved URL characters in the password. Local development may use a direct URL or a pooler URL. Production configuration accepts the Supabase shared Session pooler (port `5432`) and Transaction pooler (port `6543`), and requires SSL. Psycopg prepared statements are disabled for Transaction pooler compatibility.

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
- Citizens can request a password reset by email. Reset tokens are stored as SHA-256 hashes, expire after 15 minutes, work once, and are rate limited in PostgreSQL. Password changes increment a version so existing citizen sessions expire. Citizen and admin login failures are also rate limited in PostgreSQL.
- State-changing API requests require the session CSRF token. API database operations use SQLAlchemy ORM query parameters.

## Citizen password recovery

Before enabling password recovery on another Supabase database, run [`Backend/migrations/20261101_password_reset.sql`](Backend/migrations/20261101_password_reset.sql) followed by [`Backend/migrations/20261102_password_reset_security.sql`](Backend/migrations/20261102_password_reset_security.sql) in the Supabase SQL Editor. They add `users.password_version` and reset tables, enable RLS, and revoke direct API grants; they do not modify existing users or complaints. The application does not run migrations automatically. Both migrations have been applied to the Supabase database currently configured for local development.

Set `FRONTEND_URL` to the exact CivicLens application origin. Use `http://127.0.0.1:5000` for local development and the HTTPS deployment URL in Vercel. Reset links are built from this variable, never from the incoming Host header. The token is placed in the URL fragment, read by the reset page, and removed from browser history immediately; fragments are not sent in HTTP requests or Vercel request logs.

Configure SMTP in the root `.env` locally or in Vercel Project Settings:

```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-address@gmail.com
SMTP_PASSWORD=your-16-character-gmail-app-password
SMTP_SENDER_EMAIL=your-address@gmail.com
SMTP_SENDER_NAME=CivicLens
```

For Gmail, enable 2-Step Verification on the sender's Google account, create an **App Password** in Google Account security settings, and use that 16-character app password as `SMTP_PASSWORD`. Do not use the normal Gmail password. Port `587` uses STARTTLS; port `465` uses implicit TLS. The sender address should be the authenticated Gmail account. Keep real values in the ignored `.env` or Vercel environment settings, never in Git.

In Vercel, set `FRONTEND_URL`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_SENDER_EMAIL`, and `SMTP_SENDER_NAME` for each environment that should send email, alongside the existing database and Flask settings. Redeploy after changing environment variables. The SMTP send is synchronous with a 10-second connection timeout; the Vercel function has a 30-second maximum duration to allow time for SMTP delivery without background workers or local storage.

## Password recovery checks

Run the automated tests with `python -m unittest discover -s tests -v`. They use a temporary SQLite database and mock SMTP; they do not send real emails. To confirm Gmail delivery, configure the SMTP variables and request a reset for a registered citizen account in the local app.

### Local end-to-end run

1. In PowerShell, from the project root, activate the environment and install dependencies:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. In the ignored root `.env`, set `FLASK_ENV=development`, `FRONTEND_URL=http://127.0.0.1:5000`, and `COOKIE_SECURE=false`. Add the Gmail SMTP values above, using a Gmail App Password. Ensure `DATABASE_URL` points to Supabase PostgreSQL. Local development may use direct access; the Vercel production app requires a Supabase shared pooler URL.
3. Start the app with `python app.py`, then open <http://127.0.0.1:5000>.
4. Open the citizen login form, click **Forgot password?**, and submit an email for a registered citizen. Check that inbox and junk folder for **Reset Your CivicLens Password**.
5. Open the message’s reset link. Enter and confirm a new password, then return to the login form and sign in with that password. The previous password should fail.
6. Verify expired, reused, invalid-token, unregistered-email, login rate-limit, and admin restrictions with `python -m unittest discover -s tests -v`; these automated tests use SQLite and mocked SMTP.

## Vercel deployment

Deploy the repository root as one Vercel project. The root `app.py` exports the Flask WSGI app, `Backend/` and `Frontend/templates/` are bundled with the Python Function, and static assets are published from `public/static/` at the existing `/static/...` URLs. Flask detection itself is automatic; `vercel.json` explicitly includes the dynamically located templates in the function bundle.

Configure these Vercel environment variables for Production (and Preview if desired): `DATABASE_URL` using the Supabase shared **Session pooler** from **Connect** (port `5432`), `SECRET_KEY`, `FLASK_ENV=production`, `COOKIE_SECURE=true`, `ADMIN_USERNAME`, `ADMIN_PASSWORD_HASH`, `FRONTEND_URL=https://civiclens-lake.vercel.app`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_SENDER_EMAIL`, and `SMTP_SENDER_NAME`. The production app rejects a direct Supabase database host and SQLite URL. The pooler connection must retain SSL. Reset emails link to `${FRONTEND_URL}/reset-password#token=...`; set `FRONTEND_URL=http://127.0.0.1:5000` in local development. Generate a Werkzeug-compatible password hash locally with:

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
