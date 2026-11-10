# CivicLens
### Cloud-Based Citizen Complaint Reporting and Tracking Platform

**See the Problem. Report the Issue. Improve the Community.**

CivicLens is a cloud-hosted citizen complaint management application designed to help communities report, monitor, and track public infrastructure problems through a centralized digital platform.

The application provides separate interfaces for citizens and administrators. Citizens can register, log in, submit complaints, and monitor their submitted reports. Administrators can review complaints, identify their submitters, and update complaint statuses.

CivicLens is built using Python Flask, vanilla JavaScript, and Supabase PostgreSQL. The application is deployed on Vercel, where the Flask backend runs through Vercel's Python Functions runtime.

---

## 1. Problem Statement

Public infrastructure problems such as damaged roads, potholes, garbage accumulation, blocked drainage systems, and malfunctioning streetlights affect the daily lives of citizens.

However, reporting and monitoring these problems can be difficult when information is scattered across different communication channels.

CivicLens aims to address this issue by providing a centralized platform where citizens can submit complaints and administrators can manage and monitor them.

The application promotes transparency, accessibility, and organized complaint management through cloud-based infrastructure.

## 2. Objectives

The main objectives of CivicLens are:

- To provide a centralized platform for reporting public infrastructure problems.
- To enable citizens to register and authenticate securely.
- To maintain complaint records in a cloud-hosted relational database.
- To provide administrators with complaint management capabilities.
- To allow citizens to track their submitted complaints.
- To implement secure authentication and authorization mechanisms.
- To provide a cloud-deployed application accessible through the internet.
- To demonstrate the practical use of serverless cloud computing and Database as a Service (DBaaS).

## 3. Key Features

### Citizen Module

- Citizen registration and login.
- Secure password storage using password hashing.
- Complaint submission and management.
- Access to individually submitted complaints.
- Password recovery through email.
- Secure citizen sessions.
- Protection against unauthorized access.

### Administrator Module

- Dedicated administrator login.
- Centralized complaint management.
- Access to complaint submitter information.
- Complaint status management.
- Restricted administrative operations.
- Visibility into legacy complaints with unavailable user associations.

### Security Features

- Werkzeug password hashing.
- Server-side session authentication.
- CSRF protection for state-changing API requests.
- Database-backed login rate limiting.
- Password reset tokens stored as SHA-256 hashes.
- Single-use password reset tokens with a 15-minute expiry.
- Password-reset rate limiting.
- Environment-based credential management.
- SQLAlchemy ORM-based database operations.
- HTTPS and SSL-secured database connections in production.

## 4. Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| Frontend | HTML, CSS, JavaScript | User interface |
| Backend | Python Flask | Application logic and REST APIs |
| Database | Supabase PostgreSQL | Persistent application data |
| ORM | SQLAlchemy | Database operations |
| Database Driver | Psycopg | PostgreSQL connectivity |
| Cloud Application Hosting | Vercel | Application deployment |
| Backend Runtime | Vercel Python Functions | Serverless backend execution |
| Database Connection Pooling | Supavisor | Managed PostgreSQL connection pooling |
| Authentication | Flask session-based authentication | Citizen and administrator authentication |
| Password Security | Werkzeug | Password hashing |
| Email Service | Gmail SMTP | Password recovery emails |
| Testing | Python unittest | Automated application testing |
| Version Control | Git and GitHub | Source code management |

## 5. Cloud Architecture

CivicLens follows a cloud-hosted, three-tier application architecture.

### Presentation Layer

The presentation layer consists of HTML, CSS, and vanilla JavaScript. It provides the citizen and administrator interfaces.

The frontend templates and static resources are served through the Vercel deployment.

### Application Layer

The application layer is implemented using Python Flask.

The Flask application handles:

- User registration and authentication.
- Citizen complaint submission.
- Complaint retrieval and management.
- Administrative authorization.
- Complaint status updates.
- Password recovery.
- Database communication.

The Flask application is deployed as a Python Function on Vercel.

### Data Layer

The data layer uses Supabase PostgreSQL, a managed cloud relational database.

SQLAlchemy and Psycopg are used to interact with PostgreSQL. Supavisor provides managed database connection pooling.

Database credentials are maintained in the backend environment rather than exposed to the browser.

### Architecture Diagram

```mermaid
flowchart TD
    A[Citizens and Administrators] --> B[Web Browser]
    B --> C[Vercel Cloud Platform]

    C --> D[Static Frontend]
    C --> E[Python Runtime / Flask Function]

    E --> F[Authentication and Authorization]
    E --> G[Complaint Management APIs]
    E --> H[Password Recovery]

    G --> I[SQLAlchemy ORM]
    F --> I
    H --> I

    I --> J[Supavisor Connection Pooler]
    J --> K[Supabase PostgreSQL]

    H --> L[Gmail SMTP]
    L --> M[Password Recovery Email]

    K --> I
    I --> E
    E --> B
```

## 6. Cloud Services Used

### 6.1 Vercel

Vercel is used as the cloud application hosting and deployment platform.

The project is deployed from the repository root as a single Vercel application.

The platform provides:

- Hosting for the public-facing application.
- Execution of the Python Flask application through Vercel Functions.
- Delivery of static frontend resources.
- HTTPS-enabled application access.
- Environment variable configuration.
- Deployment management and application logs.

The root `app.py` exports the Flask application, which is detected by Vercel's Python runtime.

The deployment configuration includes the required Flask templates and static assets.

### 6.2 Supabase PostgreSQL

Supabase provides the managed PostgreSQL database used by CivicLens.

The database maintains persistent information about:

- Registered citizens.
- Complaint records.
- Password recovery records.
- Authentication-related rate limiting.

The application communicates with the database through SQLAlchemy and Psycopg.

The application does not automatically recreate the database schema or modify existing complaint records during startup.

### 6.3 Supavisor Connection Pooler

Supavisor is used for managed PostgreSQL connection pooling.

The production deployment currently uses the shared Session Pooler on port 5432.

This enables the application to connect through Supabase's shared pooler rather than depending on a direct database connection.

The application also supports the Transaction Pooler configuration, with prepared statements disabled for compatibility.

### 6.4 Gmail SMTP

Gmail SMTP is used to deliver citizen password recovery emails.

When a citizen requests password recovery:

1. The backend generates a reset token.
2. A SHA-256 hash of the token is stored in PostgreSQL.
3. The reset token is sent to the registered email address.
4. The citizen uses the reset link to establish a new password.
5. The token is invalidated after successful use.

SMTP credentials are configured through environment variables.

Gmail App Passwords are used instead of normal account passwords.

**Note:** Gmail SMTP is an external email integration, not the application's primary cloud hosting service.

## 7. Database Design

The application uses the existing Supabase PostgreSQL schema.

The primary application tables include:

### Users

Maintains citizen information and authentication-related data.

Representative fields include:

- User ID.
- Name.
- Email.
- Password hash.
- Password version.

### Reports

Maintains citizen complaint records.

Representative fields include:

- Report ID.
- User ID.
- Complaint information.
- Complaint status.
- Creation timestamp.

### Password Recovery Records

Maintains securely generated password reset information, including hashed tokens and token expiration data.

### Database Compatibility

The application is aligned with the existing `users` and `reports` database schema.

It does not automatically create tables, seed demonstration complaints, disable Row Level Security, or execute schema migrations during application startup.

Legacy complaint records without an associated user ID are displayed as `Legacy/Unknown`.

The API retains compatibility response fields for `admin_notes` and `updated_at`, using appropriate null or creation-time values where the existing database schema does not contain those columns.

## 8. Authentication and Authorization

CivicLens implements application-level authentication using Flask.

### Citizen Authentication

- Citizens can register and log in.
- Passwords are stored as Werkzeug-generated hashes.
- Authenticated sessions are managed on the server side.
- Citizens can retrieve their own complaints.
- The backend assigns the authenticated user's ID rather than trusting a user ID supplied by the browser.

### Administrator Authentication

The administrator account is configured through environment variables:

- `ADMIN_USERNAME`
- `ADMIN_PASSWORD_HASH`

Administrative functionality is restricted to the authenticated administrator session.

The administrator can access complaint information, including submitter names and email addresses, and update complaint statuses.

### Session and Request Security

State-changing API requests require a valid CSRF token.

The application uses SQLAlchemy ORM query operations to reduce the risk of SQL injection.

Citizen and administrator login failures are rate limited using PostgreSQL-backed records.

### Password Recovery Security

Password reset tokens:

- Are stored as SHA-256 hashes.
- Expire after 15 minutes.
- Can be used only once.
- Are protected by rate limiting.

Password changes increment the user's password version, invalidating existing citizen sessions.

Reset links use the configured `FRONTEND_URL` rather than trusting an incoming request's Host header.

## 9. Application Deployment

The application is deployed on Vercel using the repository root as the project directory.

Vercel detects the Flask application through the root `app.py` file.

The `vercel.json` configuration ensures the required application templates are included in the Python Function bundle.

Static frontend files are served from:

```text
public/static/
```

HTML templates are maintained under:

```text
Frontend/templates/
```

### Production Configuration

The production application uses environment variables to configure:

- PostgreSQL database connection.
- Flask secret key.
- Administrator credentials.
- Production environment.
- Secure cookies.
- Application origin.
- SMTP email configuration.

The production database uses a Supabase shared pooler connection with SSL enabled.

The production application rejects missing or invalid critical configuration, including database connection information, signing keys and administrator credentials.

SQLite is supported only as a local-development fallback.

## 10. Local Installation and Execution

### Prerequisites

- Python 3.9 or newer.
- pip package manager.
- Git.
- Access to a Supabase PostgreSQL database for cloud database testing.

### Step 1: Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd CivicLens
```

### Step 2: Create a virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv

.\.venv\Scripts\Activate.ps1
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure environment variables

Create a `.env` file in the project root.

Configure the following variables:

```dotenv
FLASK_ENV=development

SECRET_KEY=replace_with_a_secure_random_secret

DATABASE_URL=postgresql+psycopg://postgres.PROJECT_REF:ENCODED_PASSWORD@POOLER_HOST:5432/postgres?sslmode=require

FRONTEND_URL=http://127.0.0.1:5000

COOKIE_SECURE=false

ADMIN_USERNAME=your_admin_username

ADMIN_PASSWORD_HASH=your_werkzeug_password_hash

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
SMTP_SENDER_EMAIL=your_email@gmail.com
SMTP_SENDER_NAME=CivicLens
```

Replace placeholder values with the actual configuration.

The database URL should be obtained from Supabase Dashboard → Connect → Session Pooler.

Use the PostgreSQL Psycopg SQLAlchemy scheme:

```text
postgresql+psycopg://
```

Keep SSL enabled and percent-encode reserved characters in database passwords.

Never commit `.env` to GitHub.

### Step 5: Start the application

```bash
python app.py
```

Open the application at:

```text
http://127.0.0.1:5000
```

## 11. Database Health Check

The application initializes without opening a database connection during startup.

To test the database connection, open:

```text
http://127.0.0.1:5000/api/health/database
```

An example successful response is:

```json
{
  "success": true,
  "database": "connected"
}
```

This endpoint verifies database connectivity by executing a simple SQL query.

## 12. Password Recovery Database Setup

Password recovery requires additional database migrations.

For another Supabase database, run the following migration files in the Supabase SQL Editor, in this order:

1. `Backend/migrations/20261101_password_reset.sql`
2. `Backend/migrations/20261102_password_reset_security.sql`

These migrations add the required password version and reset-related database structures, enable the relevant RLS protections, and revoke direct API grants.

The migrations must be executed manually. The application does not execute database migrations automatically during startup.

The migrations have already been applied to the Supabase database used for the current development environment.

## 13. Production Deployment on Vercel

### Step 1: Import the repository

Open the Vercel Dashboard and import the CivicLens GitHub repository.

Select the repository root as the project directory.

### Step 2: Configure environment variables

Configure the following variables under Vercel Project Settings → Environment Variables.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Supabase PostgreSQL connection |
| `SECRET_KEY` | Flask session signing |
| `FLASK_ENV` | Production environment |
| `COOKIE_SECURE` | Secure production cookies |
| `ADMIN_USERNAME` | Administrator username |
| `ADMIN_PASSWORD_HASH` | Administrator password hash |
| `FRONTEND_URL` | Production application origin |
| `SMTP_HOST` | SMTP server |
| `SMTP_PORT` | SMTP port |
| `SMTP_USERNAME` | Sender account |
| `SMTP_PASSWORD` | Gmail App Password |
| `SMTP_SENDER_EMAIL` | Sender email address |
| `SMTP_SENDER_NAME` | Sender display name |

Use the correct Supabase Session Pooler URL with SSL.

Set:

```dotenv
FLASK_ENV=production
COOKIE_SECURE=true
FRONTEND_URL=https://civiclens-lake.vercel.app
```

Replace the frontend URL if the production deployment uses another domain.

### Step 3: Configure administrator password hash

Generate a Werkzeug-compatible hash locally:

```powershell
python -c "from getpass import getpass; from werkzeug.security import generate_password_hash; print(generate_password_hash(getpass('Admin password: '), method='scrypt'))"
```

Add the generated hash to the Vercel `ADMIN_PASSWORD_HASH` setting.

Do not store the administrator's actual password in the repository.

### Step 4: Deploy

Deploy the project through the Vercel Dashboard.

After deployment, verify that:

- The public homepage loads correctly.
- Citizen registration and login work.
- The database health endpoint succeeds.
- Citizens can submit and retrieve complaints.
- The administrator can access complaint management.
- Complaint status changes persist.
- Password recovery works with correctly configured SMTP.

The configured production function permits up to 30 seconds for password recovery email processing.

## 14. Automated Testing

The application includes automated tests using Python's `unittest` framework.

Execute:

```bash
python -m unittest discover -s tests -v
```

The tests use:

- A temporary SQLite database.
- Mocked SMTP services.
- Test credentials and simulated requests.

The automated suite covers password recovery and relevant security conditions without sending real emails.

Production database and real email delivery should additionally be verified through the deployed application.

### Important Test Scenarios

| Test | Expected result |
|---|---|
| Citizen registration | Account created successfully |
| Citizen login | Authorized session established |
| Complaint submission | Complaint stored in PostgreSQL |
| Citizen complaint retrieval | Only the citizen's own complaints returned |
| Administrator login | Admin access granted |
| Unauthorized admin API request | Request rejected |
| Unauthorized citizen API request | Request rejected |
| Valid password reset | Password updated |
| Expired reset token | Request rejected |
| Reused reset token | Request rejected |
| Invalid reset token | Request rejected |
| Login rate limiting | Excessive attempts restricted |
| Database health check | Successful connection reported |

## 15. Cloud Computing Concepts Demonstrated

CivicLens demonstrates the practical application of several cloud computing concepts.

**1. Platform as a Service (PaaS)**

Vercel provides a managed platform for application deployment and execution without manually configuring and maintaining an application server.

**2. Serverless Computing**

The Python Flask application is executed through Vercel Functions. Application requests are handled through the managed cloud runtime rather than a continuously managed server maintained by the project team.

**3. Database as a Service (DBaaS)**

Supabase provides a managed PostgreSQL database, eliminating the requirement to maintain a separate database server manually.

**4. Database Connection Pooling**

Supavisor manages database connections and provides an intermediary between application requests and PostgreSQL.

**5. Cloud-Based Deployment**

The application is publicly accessible through its Vercel production deployment.

**6. Cloud Environment Configuration**

Sensitive deployment settings are maintained outside the source code through environment variables.

**7. Cloud Monitoring and Diagnostics**

Vercel deployment and function logs, along with the application database health endpoint, help identify application and connectivity problems.

**8. Secure Cloud Communication**

HTTPS is used for application access, while SSL is required for production PostgreSQL communication.

## 16. Limitations

The current implementation has some limitations:

- Administrator access uses one centrally configured administrator account.
- Email delivery is synchronous with the password recovery request.
- The application depends on external hosting, database and email service availability.
- Application-level authorization is primarily enforced through Flask sessions and backend ownership checks.
- The current database connection uses privileged backend credentials, so RLS should not be assumed to provide per-citizen authorization for those direct SQL connections.
- The current implementation does not establish a dedicated, independently managed object-storage architecture in the described database configuration.

## 17. Future Scope

CivicLens can be extended through several additional capabilities:

- Integration with Supabase Storage for persistent complaint photographs.
- Geographical visualization of public complaints.
- Duplicate complaint detection.
- Complaint prioritization based on severity and frequency.
- AI-powered classification of complaint photographs.
- Automated email and application notifications.
- Analytics for identifying areas with recurring infrastructure problems.
- Integration with municipal authorities and public-service departments.
- Support for multiple administrative users and geographical regions.
- Asynchronous notification processing.

## 18. Conclusion

CivicLens presents a cloud-based approach to improving the management of public infrastructure complaints.

By combining Python Flask, Supabase PostgreSQL, and Vercel, the application provides an accessible platform for submitting, managing, and tracking citizen complaints.

The implementation demonstrates the practical use of serverless application execution, managed relational database services, connection pooling, cloud deployment, environment-based configuration, and secure application communication.

The project highlights how publicly accessible cloud infrastructure can support applications designed to address everyday community problems.

CivicLens provides a foundation for a more transparent, organized, and community-oriented public issue management system.

---

## 19. Project Contributors

**Developed by:**

1. [Student Name – Roll Number]
2. [Student Name – Roll Number]
3. [Student Name – Roll Number]

**Department:** Computer Science and Engineering

**Institution:** [Institute Name]

**Academic Project:** Cloud Computing

---

## 20. Useful Documentation

- [Vercel Documentation](https://vercel.com/docs)
- [Vercel Python Runtime](https://vercel.com/docs/functions/runtimes/python)
- [Supabase Documentation](https://supabase.com/docs)
- [Supabase PostgreSQL Connection Guide](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Supabase Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Psycopg Documentation](https://www.psycopg.org/)

---

**Repository:** [Add your GitHub repository URL]

**Live Application:** https://civiclens-lake.vercel.app

