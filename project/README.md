# Smart Reminder and Personal Protection System

A small Flask + SQLite web app with reminders, in-app/browser notifications, emergency contacts,
a 5-second SOS flow, on-demand location sharing, an append-only activity history and a
privacy-respecting admin console. Frontend is plain HTML, CSS and vanilla JavaScript.

## Setup and run

Requires Python 3.9+.

```bash
# 1. (recommended) create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 2. install dependencies
pip install -r requirements.txt

# 3. start the app (creates the SQLite DB and seeds demo data on first run)
python app.py
```

Open **http://127.0.0.1:5000** (also reachable as http://localhost:5000).

> Browser geolocation and notifications only work on `localhost` or HTTPS, so use the URL above.

## Demo accounts (seeded automatically)

| Role  | Login                | Password     | Where                       |
|-------|----------------------|--------------|-----------------------------|
| User  | `demo@example.com`   | `Demo@1234`  | http://localhost:5000/login |
| Admin | `admin`              | `Admin@1234` | http://localhost:5000/admin/login |

The demo user comes with a few reminders (one due in 5 minutes, so you can watch a notification
arrive) and one emergency contact. **Change these passwords before any real use.**

## Project structure

```
app.py          Flask app and all routes (commented, grouped by feature)
db.py           SQLite helpers, schema creation, seed data, history logger
schema.sql      Table definitions (8 tables + append-only triggers)
PROJECT_DOCUMENTATION.md  College project documentation & viva defense guide
templates/      Jinja pages: login, register, dashboard, reminders, contacts,
                sos, location, history, admin (+ layouts and partials)
static/css/     style.css (CSS variables, flexbox/grid, responsive)
static/js/      app.js (helpers + notification polling), reminders.js,
                sos.js (countdown + steps), location.js (share + copy link)
instance/       created at runtime: app.db and secret.key (do not commit)
```

## How the main features work

- **Auth** - passwords hashed with Werkzeug; Flask sessions (HttpOnly, SameSite=Lax cookie);
  one generic "Invalid email or password" message for every failed login; `@login_required`
  protects pages and APIs; deactivated users are logged out on their next request.
- **Reminders** - create / edit / delete (with confirm) / complete / snooze / cancel; filters
  Today, Upcoming, Completed, All. Completing a *recurring* reminder moves it to its next
  occurrence (daily, weekly, monthly) instead of closing it.
- **Notifications** - `app.js` polls `GET /api/notifications` every 30 s. The server creates one
  notification per reminder and time slot (a UNIQUE index prevents duplicates). The page shows an
  in-app list, a toast and a browser `Notification` (click **Enable alerts** to grant permission).
- **Emergency contacts** - phone must have 7-15 digits, email is validated; lower priority
  number = contacted first.
- **SOS** - the red button is on every page. Press -> 5-second countdown with CANCEL (records a
  `cancelled` event). Otherwise: confirm -> one-time `navigator.geolocation` lookup (SOS still
  works if denied) -> `POST /api/sos` creates the event + location, loads contacts, builds the
  message with a Google Maps link and calls `dispatch_alert()`. Each step is shown on screen.
- **Going beyond the demo** - `dispatch_alert(contact, message)` in `app.py` only logs the message
  (stored in `emergency_events.message`, shown on screen). Replace its body with an SMS provider
  (e.g. Twilio) or `smtplib` email to send for real - nothing else needs to change.
- **Location sharing** - the **Share My Location** button calls `getCurrentPosition` once; the
  server validates the coordinates and returns a map link. Nothing is tracked in the background
  and these coordinates are not stored (only a history line is written). SOS stores its location
  for that SOS event only.
- **History** - append-only (enforced by SQLite triggers); newest first; filter by type and date.
- **Admin** - separate login; lists users, activates/deactivates them, shows activity **counts**
  only. The admin queries never select reminder content or locations.

## Security notes

- All SQL is parameterized (`?` placeholders); user input is never concatenated into SQL.
- Every user-owned query includes `AND user_id = ?`, so users can only access their own data.
- Server-side validation for all forms and APIs; Jinja auto-escapes output and JS uses `textContent`.
- CSRF token required on every POST (forms and `fetch`).
- The secret key comes from the `SECRET_KEY` env var, or is generated into `instance/secret.key`.
- For production: set `debug=False`, serve over HTTPS, set `SESSION_COOKIE_SECURE=True`, change
  the seeded passwords, and add rate limiting on login.

## Resetting the demo data

Stop the server and delete the `instance/app.db` file; it is recreated and re-seeded on next start.
