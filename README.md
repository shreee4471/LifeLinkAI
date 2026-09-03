# LifeLink AI

LifeLink AI is a blood-donation coordination web app. It connects people who need blood with medically compatible, available donors and ranks candidates using an explainable probability model.

> Coordination software is not a substitute for hospital verification, clinical compatibility testing, donor consent, or emergency services.

## Run on Windows

```powershell
cd C:\abhyas\LifeLinkAI
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python database\create_db.py
python database\migrate_matches.py
python database\migrate_trust.py
python wsgi.py
```

Open http://127.0.0.1:5000 (or run `python database\bootstrap.py` to create and migrate the database in one step).

Set a production secret before sharing the app:

```powershell
$env:SECRET_KEY = "replace-with-a-long-random-secret"
```

## Build a Windows executable

The executable is fully self-contained. Double-clicking it:

1. Creates its own database in a `database` folder next to the exe (first run only).
2. Starts the server (port 5000, or the next free port if busy).
3. Opens the landing page in your default browser automatically.

Keep the console window open while using the app; closing it stops the server. All data (accounts, donors, requests, matches) persists in the `database` folder next to the exe across restarts — back up that folder to keep your data.

1. Install Python 3.11+.
2. Double-click `build_windows.bat`, or run it from PowerShell:

```powershell
.\build_windows.bat
```

3. Run the generated file:

```powershell
.\dist\LifeLinkAI.exe
```

4. Your browser opens at http://127.0.0.1:5000 automatically.

The build bundles templates, static files, and schema SQL — never your local dev database. For a public service, deploy to a cloud host instead.

## Deploy publicly with Render

The repository includes `Dockerfile` and `render.yaml`.

1. Put this project in a GitHub repository. Do not commit secrets or private database data.
2. Create a Render account and choose **New → Blueprint**.
3. Select the repository and deploy the included `render.yaml`.
4. Render builds the Docker image and assigns an HTTPS URL such as `https://lifelink-ai.onrender.com`.
5. The generated `SECRET_KEY` and persistent `/data` disk are configured by `render.yaml`.
6. Share the HTTPS URL with users.

The persistent disk is important because the app currently uses SQLite. SQLite is suitable for a demo or low-volume deployment. For many concurrent users, move persistence to PostgreSQL and add production controls such as CSRF protection, rate limiting, verified donor identity, consent records, audit logs, backups, and clinical review.

Manual Render settings, if you do not use Blueprint:

- Environment: Docker
- Build: handled by Dockerfile
- Start: handled by Dockerfile
- Health check path: `/`
- Environment variable: `SECRET_KEY` with a long random value
- Persistent disk mounted at `/data`
- `LIFELINK_DATABASE=/data/login_auth.db`

## Alternative cloud hosts

Any Docker-compatible host can run the app:

```powershell
docker build -t lifelink-ai .
docker run -p 5000:5000 -e SECRET_KEY="change-me" -v lifelink-data:/data lifelink-ai
```

For Railway, Fly.io, Azure Container Apps, or Google Cloud Run, deploy the image and ensure the platform forwards its `PORT` environment variable. Use persistent storage or PostgreSQL if data must survive restarts.

## Matching model

Candidates are first filtered through the deterministic `BLOOD_COMPATIBILITY` matrix, an 18–65 donor-age window, and the 56-day whole-blood donation cooldown (tracked via donor-logged donations). Eligible candidates receive a logistic probability based on same-city proximity, availability, urgency, donor age eligibility, and recent donation status. Each result stores an explanation and its feature vector.

The service includes gradient-descent fitting for labeled match outcomes. Requesters label each match as "Responded" or "No response" after contacting donors; an admin triggers retraining from the admin dashboard. A fresh installation uses a transparent domain-informed prior until at least ten real labeled outcomes exist. Trained weights are versioned and persisted in the `model_state` table.

The probability is a ranking signal, not a medical guarantee. Production use requires validated clinical policies and real consented outcome data.

## Operating workflow

1. A requester creates a blood request. It starts in `PendingHospitalReview`.
2. An admin or hospital reviewer approves the request from `/admin` (only then can matching run).
3. Donors register, and a reviewer verifies their identity and blood group from `/admin` before they can appear in matches.
4. The requester generates matches; compatible, verified, available donors are ranked with explanations.
5. The requester labels each match outcome ("Responded" / "No response").
6. Donors log donations; this enforces the 56-day cooldown and pauses their availability.
7. An admin retrains the ranking model from labeled outcomes on the admin dashboard.

The first admin must be promoted by setting `role = 'admin'` on a user row in the database (for example with the `sqlite3` CLI). Roles can then be managed from `/admin`.

## Verification

```powershell
python -m compileall -q app.py wsgi.py routes models services utils database
pytest -q
```
