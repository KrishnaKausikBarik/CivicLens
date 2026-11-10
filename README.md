
### Cloud-Based Citizen Complaint Reporting and Tracking Platform

**See the Problem. Report the Issue. Improve the Community.**

CivicLens is a cloud-hosted citizen complaint management application that helps communities report, monitor, and track public infrastructure problems through a centralized digital platform.

Citizens can register, log in, submit complaints, and track their reports. Administrators can review complaints, view submitter information, and update complaint statuses.

The application is built with **Python Flask**, **HTML**, **CSS**, **vanilla JavaScript**, and **Supabase PostgreSQL**. The current production deployment is on **Vercel**, where the Flask backend runs through Vercel's Python Functions runtime. **Google Cloud Platform (GCP)** is documented as a proposed extension: Google Cloud Storage can be integrated for complaint photographs and uploaded files. This GCP integration is a roadmap item and must not be described as active until it has been configured, connected to the backend, and tested.

---

## Table of Contents

- [Features](#features)
- [Technology Stack](#technology-stack)
- [System Architecture](#system-architecture)
  - [Current Deployment Architecture](#current-deployment-architecture)
  - [Proposed GCP Extension Architecture](#proposed-gcp-extension-architecture)
- [Cloud Platforms and Services](#cloud-platforms-and-services)
- [Database Design](#database-design)
- [Authentication and Security](#authentication-and-security)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Local Installation and Setup](#local-installation-and-setup)
- [Environment Variables](#environment-variables)
- [Database Setup](#database-setup)
- [Run the Application](#run-the-application)
- [API and Health Check](#api-and-health-check)
- [Production Deployment](#production-deployment)
- [Automated Testing](#automated-testing)
- [Cloud Computing Concepts](#cloud-computing-concepts)
- [GCP Integration Roadmap](#gcp-integration-roadmap)
- [Limitations](#limitations)
- [Future Enhancements](#future-enhancements)
- [Contributors](#contributors)
- [Useful Documentation](#useful-documentation)
- [Repository and Live Demo](#repository-and-live-demo)

---

## Features

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
- Visibility into legacy complaints whose user associations are unavailable.

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

---

## Technology Stack

| Layer / Component | Technology | Purpose |
|---|---|---|
| Frontend | HTML, CSS, JavaScript | User interface |
| Backend | Python Flask | Application logic and REST APIs |
| Database | Supabase PostgreSQL | Persistent application data |
| ORM | SQLAlchemy | Database operations |
| Database Driver | Psycopg | PostgreSQL connectivity |
| Primary Cloud Hosting | Vercel | Application deployment and hosting |
| Backend Runtime | Vercel Python Functions | Serverless backend execution |
| Proposed GCP Storage Extension | Google Cloud Storage | Planned storage for complaint photographs; not yet integrated |
| Database Connection Pooling | Supavisor | Managed PostgreSQL connection pooling |
| Authentication | Flask session-based authentication | Citizen and administrator authentication |
| Password Security | Werkzeug | Password hashing |
| Email Service | Gmail SMTP | Password recovery emails |
| Testing | Python unittest | Automated application testing |
| Version Control | Git and GitHub | Source code management |

> **GCP implementation status:** Vercel and Supabase are the services used by the current deployment. GCP is included as an additional platform for future integration. Do not consider a GCP service active until it has been configured and connected in the application.

---

## System Architecture

CivicLens follows a cloud-hosted, three-tier application architecture.

### 1. Presentation Layer

The presentation layer consists of HTML, CSS, and vanilla JavaScript. It provides separate interfaces for citizens and administrators. Frontend templates and static resources are served through the Vercel deployment.

### 2. Application Layer

The application layer is implemented using Python Flask. It handles:

- User registration and authentication.
- Citizen complaint submission.
- Complaint retrieval and management.
- Administrative authorization.
- Complaint status updates.
- Password recovery.
- Database communication.

The Flask application is deployed as a Python Function on Vercel.

### 3. Data Layer

The data layer uses Supabase PostgreSQL, a managed cloud relational database. SQLAlchemy and Psycopg are used to interact with PostgreSQL. Supavisor provides managed database connection pooling.

Database credentials are maintained in the backend environment and are not exposed to the browser.

### Current Deployment Architecture

The following diagram describes the application that is currently deployed. Vercel hosts the frontend assets and executes the Flask application through its Python Functions runtime. Supabase provides the managed PostgreSQL database. Gmail SMTP is used for password-recovery email delivery.

```mermaid
flowchart TD
    U[Citizens and Administrators] --> B[Web Browser]
    B -->|HTTPS| V[Vercel Cloud Platform]

    subgraph VERCEL[Current Application Hosting - Vercel]
        V --> FE[HTML / CSS / Vanilla JavaScript Frontend]
        V --> FN[Vercel Python Function]
        FN --> FL[Flask Application]
        FL --> AUTH[Authentication and Authorization]
        FL --> API[Complaint Management APIs]
        FL --> PW[Password Recovery]
    end

    AUTH --> ORM[SQLAlchemy ORM]
    API --> ORM
    PW --> ORM
    ORM --> PSY[Psycopg PostgreSQL Driver]
    PSY --> POOL[Supavisor Session Pooler]
    POOL --> DB[(Supabase PostgreSQL)]

    PW --> SMTP[Gmail SMTP]
    SMTP --> MAIL[Password Recovery Email]

    classDef current fill:#e8f1ff,stroke:#2864b4,color:#12345a;
    classDef database fill:#e9f7ef,stroke:#24834b,color:#154c2d;
    class V,FE,FN,FL,AUTH,API,PW,ORM,PSY,POOL current;
    class DB database;
```

### Proposed GCP Extension Architecture

The proposed GCP integration is to use **Google Cloud Storage (GCS)** as object storage for complaint photographs and other uploaded files. The existing Vercel-hosted Flask backend and Supabase PostgreSQL database would remain in place. The backend—not browser JavaScript—would authenticate to GCS, validate uploads, store files in a private bucket, and save an object reference in the relevant complaint record.

```mermaid
flowchart TD
    C[Citizen] -->|Complaint and Photograph| UI[Existing CivicLens Frontend on Vercel]
    UI -->|Authenticated HTTPS Request| FL[Existing Flask Backend on Vercel]

    FL --> VAL[Validate Session, File Type and File Size]
    VAL -->|Complaint Fields| ORM[SQLAlchemy / Psycopg]
    ORM --> POOL[Supavisor]
    POOL --> DB[(Supabase PostgreSQL)]

    VAL -. Planned server-side upload .-> GCSAPI[Google Cloud Storage Client]
    subgraph GCP[Google Cloud Platform - Proposed Extension]
        GCSAPI --> IAM[Service Identity / IAM Permissions]
        IAM --> BUCKET[(Private Cloud Storage Bucket)]
    end

    BUCKET -. Object name or storage reference .-> META[Complaint Image Reference]
    META -. Persist reference after integration .-> DB
    FL -->|Authorized image access or short-lived signed URL| UI

    classDef existing fill:#e8f1ff,stroke:#2864b4,color:#12345a;
    classDef planned fill:#fff3dc,stroke:#bd8420,color:#66450b,stroke-dasharray: 5 5;
    classDef database fill:#e9f7ef,stroke:#24834b,color:#154c2d;
    class FL,UI,VAL,ORM,POOL existing;
    class GCSAPI,IAM,BUCKET,META planned;
    class DB database;
```

**Status of the second diagram:** it is a proposed design, not a record of a completed integration. The GCS bucket, IAM/service identity, backend upload code, storage reference field, and controlled image-access flow must all be implemented and tested before this diagram can be presented as the deployed architecture. If the existing `reports` table does not contain an image-reference field, a reviewed database migration will be needed before persisting object references.

---

## Cloud Platforms and Services

### 1. Vercel

Vercel is the primary cloud application hosting and deployment platform.

The project is deployed from the repository root as a single Vercel application. It provides:

- Hosting for the public-facing application.
- Execution of the Python Flask application through Vercel Functions.
- Delivery of static frontend resources.
- HTTPS-enabled application access.
- Environment variable configuration.
- Deployment management and application logs.

The root `app.py` exports the Flask application, which is detected by Vercel's Python runtime. The deployment configuration includes the required Flask templates and static assets.

### 2. Supabase PostgreSQL

Supabase provides the managed PostgreSQL database used by CivicLens.

The database maintains persistent information about:

- Registered citizens.
- Complaint records.
- Password recovery records.
- Authentication-related rate limiting.

The application communicates with the database through SQLAlchemy and Psycopg.

The application does not automatically recreate the database schema or modify existing complaint records during startup.

### 3. Supavisor Connection Pooler

Supavisor is used for managed PostgreSQL connection pooling.

The production deployment currently uses the shared Session Pooler on port `5432`. This allows the application to connect through Supabase's shared pooler rather than depending on a direct database connection.

The application also supports the Transaction Pooler configuration, with prepared statements disabled for compatibility.

### 4. Gmail SMTP

Gmail SMTP is used to deliver citizen password recovery emails.

When a citizen requests password recovery:

1. The backend generates a reset token.
2. A SHA-256 hash of the token is stored in PostgreSQL.
3. The reset token is sent to the registered email address.
4. The citizen uses the reset link to establish a new password.
5. The token is invalidated after successful use.

SMTP credentials are configured through environment variables. For local development, add these values to the ignored project-root `.env` file. In Vercel, set them in Project Settings for each environment that should send email.

```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-address@gmail.com
SMTP_PASSWORD=your-16-character-gmail-app-password
SMTP_SENDER_EMAIL=your-address@gmail.com
SMTP_SENDER_NAME=CivicLens
```

Enable 2-Step Verification on the Google account, then create an App Password in Google Account security settings. Use that 16-character value as `SMTP_PASSWORD`; do not use the normal Gmail password. Port `587` uses STARTTLS, while port `465` uses implicit TLS. Keep real credentials out of Git.

SMTP delivery runs synchronously with a 10-second connection timeout. The Vercel function allows up to 30 seconds for password recovery email processing.

> Gmail SMTP is an external email integration, not the application's primary cloud hosting service.

### 5. Google Cloud Platform (GCP) - Proposed Integration

Google Cloud Platform is included in the CivicLens technology roadmap as a proposed extension. The specific service selected for the first GCP integration is **Google Cloud Storage**, which is designed for storing object data such as complaint photographs and uploaded files.

The current application deployment described in this README uses Vercel for application hosting and Supabase PostgreSQL for persistent relational data. No GCP service is currently part of the application's request-processing path in this version.

The proposed integration would add the following capabilities:

- Store complaint photographs in a private Google Cloud Storage bucket.
- Keep file bytes outside the relational database.
- Store only an object name or storage reference in the corresponding PostgreSQL complaint record.
- Let the Flask backend validate uploads and mediate authorized image access.
- Use a dedicated service identity with least-privilege IAM permissions.
- Avoid exposing service-account credentials or unrestricted bucket access in browser JavaScript.

This is a planned GCP integration. It must not be listed as an implemented cloud service until the bucket, IAM permissions, backend upload/download logic, database reference, and end-to-end tests have been completed.

---

## Database Design

The application uses the existing Supabase PostgreSQL schema.

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

---

## Authentication and Security

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

- State-changing API requests require a valid CSRF token.
- SQLAlchemy ORM query operations are used to reduce the risk of SQL injection.
- Citizen and administrator login failures are rate limited using PostgreSQL-backed records.

### Password Recovery Security

Password reset tokens:

- Are stored as SHA-256 hashes.
- Expire after 15 minutes.
- Can be used only once.
- Are protected by rate limiting.

Password changes increment the user's password version, invalidating existing citizen sessions.

Reset links use the configured `FRONTEND_URL` rather than trusting an incoming request's Host header.

---

## Project Structure

The repository uses the following important paths. Adjust this example if your actual repository has a different layout.

```text
CivicLens/
├── app.py
├── vercel.json
├── requirements.txt
├── .env.example
├── .gitignore
├── Backend/
│   └── migrations/
│       ├── 20261101_password_reset.sql
│       └── 20261102_password_reset_security.sql
├── Frontend/
│   └── templates/
├── public/
│   └── static/
└── tests/
```

---

## Prerequisites

Install the following before running CivicLens locally:

- Python 3.9 or newer.
- pip package manager.
- Git.
- Access to a Supabase PostgreSQL database for cloud database testing.

---

## Local Installation and Setup

### Step 1: Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd CivicLens
```

### Step 2: Create a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure environment variables

Create a `.env` file in the project root and add the required configuration. Refer to the [Environment Variables](#environment-variables) section.

### Step 5: Start the application

```bash
python app.py
```

Open the application at:

```text
http://127.0.0.1:5000
```

---

## Environment Variables

Create a `.env` file in the project root. The following is a template; replace every placeholder with your own configuration.

```dotenv
FLASK_ENV=development

SECRET_KEY=replace_with_a_secure_random_secret

DATABASE_URL=postgresql+psycopg://postgres.PROJECT_REF:ENCODED_PASSWORD@POOLER_HOST:5432/postgres?sslmode=require

FRONTEND_URL=http://127.0.0.1:5000

COOKIE_SECURE=false

ADMIN_USERNAME=admin

ADMIN_PASSWORD_HASH=your_werkzeug_password_hash

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
SMTP_SENDER_EMAIL=your_email@gmail.com
SMTP_SENDER_NAME=CivicLens
```

Important:

- Replace placeholder values with the actual configuration.
- Obtain the database URL from **Supabase Dashboard → Connect → Session Pooler**.
- Use the PostgreSQL Psycopg SQLAlchemy scheme: `postgresql+psycopg://`.
- Keep SSL enabled and percent-encode reserved characters in database passwords.
- Never commit `.env` to GitHub.
- Keep `.env.example` limited to placeholders; never put real credentials in it.
- Generate a Werkzeug password hash for the administrator password and store the hash in `ADMIN_PASSWORD_HASH`, not the plain-text password.

For local development, SQLite is supported as a fallback. Production configuration requires the supported Supabase PostgreSQL pooler connection.

---

## Database Setup

The application uses the existing Supabase PostgreSQL schema.

Password recovery requires additional database migrations. For another Supabase database, run the following migration files in the Supabase SQL Editor, in this order:

1. `Backend/migrations/20261101_password_reset.sql`
2. `Backend/migrations/20261102_password_reset_security.sql`

These migrations add the required `users.password_version` field and password-reset database structures, enable the relevant RLS protections, and revoke direct API grants. They do not modify existing users or complaints.

The migrations must be executed manually. The application does not execute database migrations automatically during startup.

The migrations have already been applied to the Supabase database used for the current development environment.

---

## API and Health Check

The application includes a database health-check endpoint.

Start the application and open:

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

---

## Production Deployment

### Deploying on Vercel

The application is deployed on Vercel using the repository root as the project directory.

#### Step 1: Import the repository

1. Open the Vercel Dashboard.
2. Import the CivicLens GitHub repository.
3. Select the repository root as the project directory.

#### Step 2: Configure environment variables

Configure the following variables under **Vercel Project Settings → Environment Variables**.

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

Use the shared Supabase Session Pooler URL from **Connect** (port `5432`) with SSL. The production app also accepts the Transaction Pooler on port `6543`; prepared statements are disabled for compatibility. Direct database hosts and SQLite URLs are rejected in production.

Set the production values:

```dotenv
FLASK_ENV=production
COOKIE_SECURE=true
FRONTEND_URL=https://civiclens-lake.vercel.app
```

Replace the frontend URL if the production deployment uses another domain.

For password recovery, set `FRONTEND_URL` to the exact application origin. Reset links use `${FRONTEND_URL}/reset-password#token=...`. The token is placed in the URL fragment, read by the reset page, and removed from browser history; fragments are not sent in HTTP requests or Vercel request logs.

#### Step 3: Configure the administrator password hash

Generate a Werkzeug-compatible hash locally:

```powershell
python -c "from getpass import getpass; from werkzeug.security import generate_password_hash; print(generate_password_hash(getpass('Admin password: '), method='scrypt'))"
```

Add the generated hash to the Vercel `ADMIN_PASSWORD_HASH` setting.

In Vercel, open **Project Settings → Environment Variables**, set `ADMIN_USERNAME` to `admin`, and set `ADMIN_PASSWORD_HASH` to the generated hash. Select **Production** (and **Preview** if needed), save the variables, then redeploy the latest deployment so the environment changes take effect.

Do not store the administrator's actual password in the repository.

#### Step 4: Deploy and verify

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

### Proposed GCP integration alongside Vercel

The current production deployment remains on Vercel. The proposed GCP extension does not migrate the Flask application to Cloud Run and does not replace Supabase PostgreSQL. Instead, it adds Google Cloud Storage as a separate object-storage service for complaint photographs.

When implemented, the Flask backend will communicate with the GCS bucket using a server-side service identity with least-privilege IAM permissions. The backend should validate file type and size, upload to a private bucket, and store the object reference in the complaint record. Image retrieval should be authorized by the backend, for example by generating short-lived signed URLs when appropriate.

The existing production application does not require GCP to run. Do not add GCP environment variables or claim GCP usage until the storage bucket, permissions, backend integration, database reference, and end-to-end behavior have actually been configured and tested.

---

## Automated Testing

The application includes automated tests using Python's `unittest` framework.

Run the test suite:

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

| Test | Expected Result |
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

---

## Cloud Computing Concepts Demonstrated

CivicLens demonstrates the practical application of several cloud computing concepts.

1. **Platform as a Service (PaaS):** Vercel provides a managed platform for application deployment and execution without manually configuring and maintaining an application server.
2. **Serverless Computing:** The Python Flask application is executed through Vercel Functions. Application requests are handled through the managed cloud runtime rather than a continuously managed server maintained by the project team.
3. **Database as a Service (DBaaS):** Supabase provides a managed PostgreSQL database, eliminating the requirement to maintain a separate database server manually.
4. **Database Connection Pooling:** Supavisor manages database connections and provides an intermediary between application requests and PostgreSQL.
5. **Cloud-Based Deployment:** The application is publicly accessible through its Vercel production deployment.
6. **Cloud Environment Configuration:** Sensitive deployment settings are maintained outside the source code through environment variables.
7. **Cloud Monitoring and Diagnostics:** Vercel deployment and function logs, along with the application database health endpoint, help identify application and connectivity problems.
8. **Secure Cloud Communication:** HTTPS is used for application access, while SSL is required for production PostgreSQL communication.
9. **Planned GCP Object Storage Extension:** Google Cloud Storage is a proposed future service for complaint photographs. It is not part of the current running application until the bucket, IAM configuration, backend integration, and tests have been completed.

---

## GCP Integration Roadmap

The following design is a proposed extension, not a description of functionality already deployed.

### Proposed Google Cloud Storage Integration

Google Cloud Storage can be integrated as object storage for complaint photographs and other uploaded files. The current Vercel-hosted Flask application and Supabase PostgreSQL database can remain in place.

**Proposed request flow:**

1. A citizen submits a complaint with a photograph through the existing frontend.
2. The Flask backend authenticates the user and validates the file type, file size, and request.
3. The backend uses a dedicated GCP service identity to upload the file to a private Google Cloud Storage bucket.
4. Cloud Storage returns an object name or storage reference.
5. The backend stores that reference in the corresponding PostgreSQL complaint record. A database migration may be required if the existing schema does not have an image-reference field.
6. When an authorized user views the complaint, the backend checks access and provides the image through a controlled mechanism, such as a short-lived signed URL.

**Implementation checklist:**

- Create or select a GCP project and enable the Cloud Storage API.
- Create a bucket in an appropriate region and keep public access prevention enabled unless there is a justified requirement otherwise.
- Create a dedicated service identity and grant only the bucket permissions required by the application.
- Store runtime credentials securely; never place service-account keys in frontend code or commit them to GitHub. Prefer an attached service identity where the hosting environment supports it; otherwise use an approved secure credential-delivery mechanism.
- Implement server-side upload and authorized retrieval in Flask.
- Add and review a database field for the storage object name/reference if needed.
- Test successful uploads, invalid file types, oversized files, unauthorized access, missing objects, and image retrieval.

Only after these steps are complete should Google Cloud Storage be moved from the roadmap into the implemented technology stack and current architecture diagram.

---

## Limitations

The current implementation has some limitations:

- Administrator access uses one centrally configured administrator account.
- Email delivery is synchronous with the password recovery request.
- The application depends on external hosting, database, and email service availability.
- Application-level authorization is primarily enforced through Flask sessions and backend ownership checks.
- The current database connection uses privileged backend credentials, so RLS should not be assumed to provide per-citizen authorization for those direct SQL connections.
- The current implementation does not establish a dedicated, independently managed object-storage architecture for complaint photographs.
- Google Cloud Storage is a proposed extension and is not yet part of the current application request flow.

---

## Future Enhancements

CivicLens can be extended through several additional capabilities:

- Integration with Google Cloud Storage or Supabase Storage for persistent complaint photographs.
- Geographical visualization of public complaints.
- Duplicate complaint detection.
- Complaint prioritization based on severity and frequency.
- AI-powered classification of complaint photographs.
- Automated email and application notifications.
- Analytics for identifying areas with recurring infrastructure problems.
- Integration with municipal authorities and public-service departments.
- Support for multiple administrative users and geographical regions.
- Asynchronous notification processing.
- Integration of additional GCP services where they provide a clear benefit.

---

## Conclusion

CivicLens presents a cloud-based approach to improving the management of public infrastructure complaints.

By combining Python Flask, Supabase PostgreSQL, and Vercel, the current implementation provides an accessible platform for submitting, managing, and tracking citizen complaints.

The implementation demonstrates serverless application execution, managed relational database services, connection pooling, cloud deployment, environment-based configuration, and secure application communication. Google Cloud Storage is documented as a proposed extension for complaint photographs; it should be described as implemented only after the integration has been configured and tested.

CivicLens provides a foundation for a more transparent, organized, and community-oriented public issue management system.

---

## Contributors

**Developed by:**

1. [Student Name – Roll Number]
2. [Student Name – Roll Number]
3. [Student Name – Roll Number]

**Department:** Computer Science and Engineering  
**Institution:** [Institute Name]  
**Academic Project:** Cloud Computing

---

## Useful Documentation

- [Vercel Documentation](https://vercel.com/docs)
- [Vercel Python Runtime](https://vercel.com/docs/functions/runtimes/python)
- [Supabase Documentation](https://supabase.com/docs)
- [Supabase PostgreSQL Connection Guide](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Supabase Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Google Cloud Documentation](https://cloud.google.com/docs)
- [Google Cloud Storage Documentation](https://cloud.google.com/storage/docs)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Psycopg Documentation](https://www.psycopg.org/)

---

## Repository and Live Demo

**Repository:** [Add your GitHub repository URL]  
**Live Application (current Vercel deployment):** https://civiclens-lake.vercel.app

**GCP status:** Google Cloud Storage is a proposed extension and is not represented as an active service in the current deployment.
"""

output_path = "/mnt/data/README_CivicLens.md"
pypandoc.convert_text(readme, "md", format="md", outputfile=output_path, extra_args=["--standalone"])
print(f"Created: {output_path}")
