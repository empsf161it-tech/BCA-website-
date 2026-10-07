# Smart Reminder and Personal Protection System
## College Final-Year Project Documentation & Viva Examination Guide
**Degree:** Bachelor of Computer Applications (BCA)  
**Academic Project Specification & Defense Manual**

---

## 1. Project Title
**Smart Reminder and Personal Protection System**

---

## 2. Project Overview
The **Smart Reminder and Personal Protection System** is an integrated web-based productivity and personal safety platform designed to provide both structured daily task organization and instant emergency response capabilities.

* **The Problem It Solves:** In everyday life, individuals frequently struggle with managing routine tasks, medication schedules, and important deadlines while simultaneously lacking an immediate, dependable personal safety tool in threatening situations. Furthermore, most commercial safety applications continuously track user GPS coordinates in the background, consuming substantial battery life and creating severe personal privacy concerns.
* **The Solution:** This project bridges both needs into a unified, privacy-respecting web application:
  1. A structured **Smart Reminder System** that handles daily tasks, events, and recurring habits with advance alerts and audible browser alarms.
  2. A privacy-focused **Personal Protection & SOS System** featuring a 5-second countdown panic button, on-demand GPS coordinate capture, prioritized emergency contact notification dispatch, and one-click location sharing.
  3. Continuous security and transparency through an **append-only audit history** that cannot be altered or deleted, and a **privacy-respecting administration console**.

---

## 3. Technologies Used

| Category | Technology / Library | Purpose & Version |
| :--- | :--- | :--- |
| **Backend Language** | Python 3 | Core application programming language (Python 3.9+) |
| **Backend Framework** | Flask (>=3.0, <4) | Lightweight WSGI web application framework |
| **Security & Utilities** | Werkzeug | Secure password hashing (`generate_password_hash`, `check_password_hash`) |
| **Database** | SQLite3 | Embedded relational database engine (via Python's standard `sqlite3` module) |
| **Frontend Markup** | HTML5 / Jinja2 | Semantic page structures, templating, layout inheritance, and components |
| **Frontend Styling** | Vanilla CSS3 | Custom responsive UI styling, CSS custom properties (variables), Grid & Flexbox |
| **Frontend Scripting** | Vanilla JavaScript (ES6+) | Dynamic DOM manipulation, asynchronous Fetch API, state handling |
| **Browser Web APIs** | Geolocation API | One-time device GPS coordinate retrieval (`navigator.geolocation`) |
| | Notifications API | Desktop/browser push notification banners (`window.Notification`) |
| | Web Audio API | Client-side synthesized digital alarm audio tones (`AudioContext`) |
| | Clipboard API | Copying emergency map links to device clipboard (`navigator.clipboard`) |
| **External Service Integration** | Google Maps URL API | Generating accessible coordinate map links (`maps.google.com/?q=lat,lng`) |
| **Tools & Environment** | Python `venv`, PowerShell / Terminal | Environment isolation and server execution |

---

## 4. Purpose of Each Technology

1. **Python:** Chosen for its readable syntax, robust standard library (`datetime`, `re`, `secrets`, `sqlite3`), and rapid development speed.
2. **Flask:** Acts as the backend controller. It handles HTTP routing, session lifecycle, template rendering, and RESTful JSON API endpoints without the unnecessary bloat of large frameworks like Django.
3. **SQLite3:** Serves as the relational database engine. Because SQLite is serverless and zero-configuration, it stores the entire application state in a single file (`instance/app.db`), making deployment lightweight, self-contained, and portable.
4. **Jinja2:** Flask's templating engine. It dynamically renders HTML templates on the server, injects CSRF security tokens, auto-escapes user input to stop Cross-Site Scripting (XSS), and provides reusable layout components.
5. **Vanilla CSS3:** Eliminates third-party CSS framework dependencies (like Bootstrap or Tailwind). Uses CSS custom variables, modern flexbox, and responsive CSS grids for a clean, fast-loading, mobile-friendly interface.
6. **Vanilla JavaScript:** Powers client-side interactivity without heavy frontend frameworks (such as React or jQuery). It manages modal dialogues, the 5-second SOS countdown, periodic background polling, and real-time toast alerts.
7. **HTML5 Geolocation API:** Enables precise latitude, longitude, and accuracy measurement directly from the user's browser during an SOS trigger or manual location share.
8. **Web Audio API:** Generates real-time sound frequencies (beeps and alarm sequences) in the browser using mathematical oscillator nodes without having to store or download external audio MP3 files.
9. **Google Maps Link Scheme:** Converts raw GPS coordinates into standard clickable links, allowing emergency contacts to open the user's location instantly in any browser or navigation app.

---

## 5. Main Features

* **User Authentication & Session Management:**
  * User registration with validation (email syntax, phone length, 8+ character password).
  * Secure password hashing using PBKDF2/scrypt.
  * Session protection using `HttpOnly`, `SameSite=Lax` cookies, and session rotation to prevent session fixation.
* **Smart Reminders & Scheduling:**
  * Add, edit, delete, complete, and snooze reminders.
  * Supports three reminder types: **Task**, **Event**, and **Recurring**.
  * Recurrence engine automatically advances recurring reminders to the next occurrence (Daily, Weekly, Monthly) rather than terminating them.
  * Configurable advance notification times (e.g., 5 min, 10 min, 1 hour).
  * Quick-time preset buttons (+5m, +10m, +15m, +30m, +1h) for instant task setup.
* **Two-Tier Notification & Digital Alarm System:**
  * Background polling every 5 seconds queries pending reminder alerts.
  * **Advance Alerts:** Plays a gentle chime and displays an in-app toast/browser notification before the task is due.
  * **Due Alarms:** When the scheduled due time is reached, it triggers a modal popup, toast alert, and a classic digital alarm sequence via the Web Audio API until acknowledged.
* **Emergency Contacts Management:**
  * Add, view, edit, and delete trusted emergency contacts with phone numbers, emails, and relationships.
  * Numeric **priority ordering** (1 = contacted first).
* **5-Second SOS Emergency System:**
  * Persistent floating red SOS button accessible on every page.
  * Triggering SOS initiates a visual 5-second countdown timer.
  * **False-Alarm Cancellation:** User can abort the SOS during countdown; cancellation is logged.
  * **Dispatch Sequence:** Once the timer expires, the app captures GPS coordinates, gathers prioritized emergency contacts, generates an alert message with a Google Maps link, and dispatches the alert.
  * Step-by-step visual feedback displays progress: *Confirmed → Location Captured → Contacts Loaded → Dispatched → Recorded*.
* **Privacy-First On-Demand Location Sharing:**
  * Allows users to generate a Google Maps link of their current location with a single click.
  * **No Continuous Tracking:** Location is polled once (`getCurrentPosition`), never continuously tracked (`watchPosition`), protecting user battery and privacy.
* **Append-Only Activity History:**
  * Every major event (reminder created/edited/completed, SOS triggered/cancelled, contact updated, location shared) is recorded in an audit log.
  * Database triggers block any `UPDATE` or `DELETE` queries on the history table.
* **Privacy-Preserving Admin Panel:**
  * Separate administrative authentication (`/admin/login`).
  * Displays user list and allows administrators to activate or deactivate user accounts.
  * **Privacy Guarantee:** Admin dashboard calculates aggregates and statistics only (`COUNT(*)`). Administrators cannot view private reminder titles, notes, contacts, or coordinates.

---

## 6. Project Structure

```text
d:/BCA PROJECT/project/
│
├── app.py                  # Main Flask application (routes, validation, API endpoints, auth, SOS logic)
├── db.py                   # SQLite helper functions, connection handling, seeding, history logging
├── schema.sql              # Database schema (8 relational tables, indexes, append-only triggers)
├── requirements.txt        # Python dependency manifest (Flask>=3.0,<4)
├── README.md               # Setup instructions, architecture overview, demo credentials
├── PROJECT_DOCUMENTATION.md# Complete college project documentation and viva defense manual
│
├── instance/               # Runtime files generated automatically (excluded from VCS)
│   ├── app.db              # SQLite database file holding tables and records
│   └── secret.key          # Persistent cryptographic key used for Flask session signing
│
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Master layout for authenticated pages (sidebar, modals, SOS button)
│   ├── base_public.html    # Master layout for public pages (login, registration)
│   ├── _flash.html         # Partial template for rendering flash alert messages
│   ├── _macros.html        # Reusable UI macros (e.g., reminder list items with snooze menus)
│   ├── login.html          # User login page
│   ├── register.html       # User registration page
│   ├── dashboard.html      # Main user dashboard displaying summary stats and quick actions
│   ├── reminders.html      # Reminders view with creation form, filters, and management
│   ├── contacts.html       # Emergency contacts management with priority ordering
│   ├── sos.html            # Dedicated SOS page showing trigger button and history of events
│   ├── location.html       # On-demand location sharing widget and map link generator
│   ├── history.html        # Read-only audit log with type and date range filters
│   ├── admin_login.html    # Separate login portal for administrators
│   ├── admin.html          # Administrator console for user activation and system stats
│   └── error.html          # Custom error page (e.g., 404 Not Found)
│
└── static/                 # Static assets served to the client
    ├── css/
    │   └── style.css       # Complete stylesheet (responsive design, themes, cards, modals)
    └── js/
        ├── app.js          # Shared client scripts: API fetch wrapper, notification polling, audio engine
        ├── reminders.js    # Reminder form interactivity and quick time preset handlers
        ├── sos.js          # 5-second countdown timer, step tracker, and SOS API calls
        └── location.js     # Single-click geolocation retriever and link copy handler
```

---

## 7. How the Project Works (Workflow)

```text
+-----------------------+
|  User Visits Website  |
+-----------+-----------+
            |
            v
     [ Authenticated? ]
      /             \
    No               Yes
    /                 \
   v                   v
[ Login/Register ]  [ User Dashboard ]
                        |
       +----------------+----------------+----------------+
       |                                 |                                 |
       v                                 v                                 v
[ Reminders Module ]           [ Emergency Contacts ]             [ SOS Panic Button ]
  - Create / Edit Tasks          - Save phone / email / relation    - 5-Second Countdown
  - Snooze / Complete            - Priority ranking (1..99)         - Cancel if accidental
  - Set Recurrence rules         - Stored in SQLite                 - Fetch GPS coordinates
       |                                 |                          - Dispatch alert message
       v                                 |                          - Append-only log saved
[ 5s Background Polling ]                |                                 |
  - Advance Chime (Lead time)            +----------------+----------------+
  - Due Audio Alarm (Web Audio API)                       |
  - On-screen Alarm Modal                                 v
                                              [ SQLite Relational DB ]
                                              - 8 tables, indexes
                                              - Immutable audit triggers
```

### Basic Workflow Step-by-Step:
1. **Request & Authentication:** A user visits the application. If not logged in, they are redirected to `/login`. Upon submitting credentials, Flask validates the password hash from the SQLite database. On success, an encrypted session cookie is issued.
2. **Dashboard Overview:** The user is directed to `/dashboard`, which loads summary statistics (active reminders, contacts saved, SOS triggers) and lists today's urgent tasks.
3. **Setting Reminders:** The user enters a task, due time, recurrence, and lead time. The request is verified against server-side validation rules and stored in the `reminders` table.
4. **Automated Notification Cycle:** Every 5 seconds, client-side JavaScript (`app.js`) polls `/api/notifications`. The server detects any reminder whose advance time or due time has arrived, generates a row in `notifications`, and sends the details to the client. The browser plays an audio tone and renders an on-screen toast and modal.
5. **Emergency Triggering (SOS):** When in danger, the user clicks the red SOS button. A 5-second countdown begins. If not cancelled, `navigator.geolocation` captures coordinates. The data is posted to `/api/sos`, which saves the event, pairs it with emergency contacts ordered by priority, composes a Google Maps rescue message, logs the dispatch, and appends the action to the tamper-proof history.

---

## 8. Database / API / Services Breakdown

### Database Architecture
* **Engine:** SQLite3 with foreign key enforcement enabled (`PRAGMA foreign_keys = ON;`).
* **Schema Breakdown (8 Tables):**
  1. `users`: User profiles (ID, name, unique email, password hash, phone, active status, creation date).
  2. `reminders`: Scheduled tasks (title, description, type, due timestamp, recurrence rule, advance minutes, status). Indexed on `(user_id, due_at)`.
  3. `notifications`: Alerts generated for reminders. Protected by a `UNIQUE INDEX` on `(reminder_id, channel, scheduled_at)` to prevent duplicate alerts.
  4. `emergency_contacts`: User-configured emergency contacts ordered by priority.
  5. `emergency_events`: Log of all SOS triggers (timestamp, status: `triggered`/`cancelled`/`dispatched`/`failed`, generated message, resolved timestamp).
  6. `locations`: Coordinates captured exclusively during SOS incidents (latitude, longitude, accuracy in meters, timestamp).
  7. `history`: Immutable audit log of all system activities. Enforced via database triggers `history_no_update` and `history_no_delete`.
  8. `admins`: Administrative user credentials.

### API Architecture
* **Internal JSON Endpoints:**
  * `GET /api/notifications` → Returns active alerts for the user and flags `is_due_alarm`.
  * `POST /api/notifications/<id>/ack` → Marks delivered alerts as sent.
  * `POST /api/sos` → Processes SOS alerts with coordinates and returns dispatch status.
  * `POST /api/sos/cancel` → Cancels an active countdown and logs the cancellation.
  * `POST /api/location` → Validates latitude/longitude and returns a Google Maps URL.

### Authentication & External Services
* **Authentication:** Handled natively via Flask sessions and Werkzeug password hashing.
* **External Services:**
  * **Google Maps:** Used via direct standard URL scheme (`https://www.google.com/maps?q=lat,lng`).
  * **SMS / Email Gateway:** *Not implemented in the current version.* The codebase includes an extensible abstraction method `dispatch_alert()` that logs the dispatch message and prepares payload structures ready for plug-in SMS APIs (such as Twilio) or Python `smtplib`.

---

## 9. Current Project Status

### Fully Implemented and Operational:
* Complete user registration, login, logout, and session lifecycle.
* Full reminder management (Create, Read, Update, Delete, Snooze, Complete, Cancel).
* Recurrence calculation engine (Daily, Weekly, Monthly) rolling dates forward automatically.
* Dual-level notification engine with client polling every 5 seconds.
* In-browser sound synthesis (chimes and digital alarm beeps) using the Web Audio API.
* Emergency contact management with custom numeric priority ranking.
* 5-second countdown SOS emergency system with false-alarm abort handling.
* Single-click GPS coordinate capture and Google Maps link generation.
* Database-enforced append-only audit log with search and date filters.
* Separate administrative panel for managing user accounts and viewing system metrics.
* Comprehensive input validation, CSRF verification, and SQL parameterization.

### Mocked / Simulated for Demonstration:
* External SMS / Email dispatch: The system builds the emergency text message and logs it in the database and server console via `dispatch_alert()`, rather than sending live SMS through a paid gateway.

---

## 10. Future Enhancements
1. **SMS & Email Gateway Integration:** Connect third-party providers (e.g., Twilio, Fast2SMS, or SendGrid/SMTP) into `dispatch_alert()` to send real SMS text messages and emergency emails.
2. **Push Notifications via Service Workers:** Implement Web Push API and Service Workers so users can receive reminder and SOS alerts even when the browser tab is closed.
3. **Voice-Activated SOS:** Integrate the Web Speech Recognition API to trigger an SOS upon detecting emergency voice commands (e.g., "Help", "Emergency").
4. **Offline PWA Support:** Convert the application into a Progressive Web App (PWA) with local caching so core functions work offline.
5. **Geofencing / Safe Zones:** Add safe zone boundaries on maps that alert emergency contacts if the user departs unexpectedly late at night.

---

## 11. Advantages of the System
* **Dual Utility:** Combines daily task productivity and critical personal protection into one single dashboard.
* **Guaranteed Privacy:** Strictly avoids continuous 24/7 background GPS tracking; locations are fetched only upon explicit user trigger.
* **Lightweight & Fast:** Built entirely with standard Python libraries and vanilla web technologies; zero bulky JavaScript framework overhead.
* **Tamper-Proof Audit Trail:** Database triggers protect the activity history, preventing users or malicious actors from erasing logs.
* **Resilient SOS Process:** If GPS permissions are denied or unavailable, the SOS flow does not crash; it continues and sends the alert with an explanation.
* **Strong Security Standards:** Built-in defenses against SQL injection, Cross-Site Scripting (XSS), Cross-Site Request Forgery (CSRF), and Session Fixation.

---

## 12. Limitations
* **Local SMS/Email Restriction:** Real-world SMS sending is not active out-of-the-box because it requires paid third-party SMS gateway credentials.
* **Browser Tab Dependency:** Because Web Workers or Service Workers are not yet configured, reminder polling requires an active browser session.
* **HTTPS Requirement for Geolocation:** Modern web browsers only grant access to `navigator.geolocation` and `Notification` over `localhost` or secure `HTTPS` connections.
* **Single Server Architecture:** SQLite is designed for single-file, lightweight operations. High-concurrency enterprise deployments would benefit from migrating to PostgreSQL or MySQL.

---
---

# Possible Viva Questions and Answers

### 1. Why did you choose this project?
> **Answer:** "I chose this project because most people use separate apps for daily reminders and emergency safety. Safety apps often track location continuously, which drains battery and compromises privacy. I wanted to build a unified, privacy-respecting platform that helps users manage their daily tasks while providing an instant, one-click SOS system whenever they feel unsafe."

### 2. What specific problem does your project solve?
> **Answer:** "It solves two problems: first, the tendency to forget important tasks and habits; and second, the lack of an immediate, discreet emergency response tool. It provides advance warnings, alarm tones, and a 5-second countdown panic button that captures GPS coordinates and contacts family members in priority order."

### 3. Why did you choose Python and Flask over other technologies?
> **Answer:** "Python provides clean, readable code and rich built-in libraries for security and date manipulation. Flask was chosen because it is lightweight, modular, and does not add unnecessary overhead. For a project combining REST APIs and server-rendered templates, Flask offers full control over routes, sessions, and database queries."

### 4. What is the purpose of each major technology in your project?
> **Answer:** "Python and Flask serve as our backend server and API layer. SQLite handles data storage in a single portable file. Jinja2 renders dynamic HTML templates on the server. Vanilla CSS handles responsive styling, and Vanilla JavaScript manages the UI countdowns, notification polling, and audio synthesis via the Web Audio API."

### 5. How does the project work from start to finish?
> **Answer:** "A user registers, logs in, and accesses the dashboard. They can create reminders or save emergency contacts. In the background, JavaScript checks the server every 5 seconds for pending notifications. If an alarm is due, a sound plays and a modal appears. If the user presses the SOS button, a 5-second countdown begins. Unless cancelled, the browser retrieves the user's GPS coordinates, sends them to the backend, builds an emergency message with a Google Maps link, and records the event."

### 6. Explain the project workflow when a user triggers an SOS.
> **Answer:** "When the SOS button is pressed:
> 1. A 5-second countdown modal appears with a Cancel option.
> 2. If the user cancels, a 'cancelled' event is logged in the database.
> 3. If the countdown finishes, JavaScript requests GPS coordinates using the Geolocation API.
> 4. The coordinates are posted to `/api/sos`.
> 5. The server retrieves saved contacts in priority order, creates an emergency message containing a Google Maps link, logs the dispatch, and records the event in the history table."

### 7. How does the frontend communicate with the backend?
> **Answer:** "The frontend communicates in two ways:
> 1. Standard HTML form submissions (`POST`) for actions like login, saving reminders, and updating contacts.
> 2. Asynchronous JavaScript `fetch()` calls to internal JSON APIs (`/api/notifications`, `/api/sos`, `/api/location`), which include a custom `X-CSRF-Token` header for security."

### 8. Which database is used and why?
> **Answer:** "SQLite3 is used. It is an embedded, zero-configuration relational database included with Python. It requires no separate server setup, stores data reliably in a single file (`instance/app.db`), and supports full SQL features like foreign keys, indexes, and triggers."

### 9. Which APIs are used in the project and why?
> **Answer:** "We use both internal and browser APIs:
> - **Internal REST APIs:** Endpoints like `/api/notifications` and `/api/sos` for asynchronous data exchange.
> - **HTML5 Geolocation API:** To retrieve latitude and longitude on demand.
> - **Web Notifications API:** To display desktop push alerts.
> - **Web Audio API:** To synthesize alarm beeps directly in the browser without external sound files.
> - **Google Maps API (URL scheme):** To generate universal navigation links from coordinates."

### 10. How is user authentication handled?
> **Answer:** "Authentication is handled using Flask sessions and Werkzeug security. When a user registers, their password is encrypted using a cryptographic salt and hash. During login, `check_password_hash` verifies the credentials. On success, the user ID is stored in a secure server-side session cookie marked `HttpOnly` and `SameSite=Lax`. Session fixation is prevented by calling `session.clear()` before setting the new session."

### 11. What are the main modules or features of the system?
> **Answer:** "The application has six main modules:
> 1. User Authentication and Account Management.
> 2. Smart Reminders and Recurrence Engine.
> 3. Background Notification and Audio Alarm Engine.
> 4. Emergency Contacts Manager (with priority ranking).
> 5. 5-Second SOS Panic Trigger and On-Demand Location Sharing.
> 6. Immutable Activity History and Privacy-Preserving Admin Panel."

### 12. Explain an important part of the code you wrote.
> **Answer:** "An important part is the `next_occurrence()` function in `app.py`. When a user completes a recurring reminder (daily, weekly, or monthly), instead of deleting or closing it, the function calculates the next due date in the future using calendar month clamping and updates the reminder back to 'pending' status."

### 13. What challenges did you face during development?
> **Answer:** "One challenge was browser autoplay restrictions, which block audio from playing automatically without prior user interaction. Another challenge was preventing duplicate reminder notifications during periodic background polling."

### 14. How did you solve those challenges?
> **Answer:** "For audio, I added an event listener that unlocks the browser's `AudioContext` on the user's first click anywhere on the page. For duplicate notifications, I created a `UNIQUE INDEX` in the SQLite database on `(reminder_id, channel, scheduled_at)` so the database rejects duplicate alert inserts."

### 15. What are the limitations of the current system?
> **Answer:** "Currently, live SMS transmission is simulated in code via `dispatch_alert()` rather than being sent through a paid SMS gateway. Also, notifications poll every 5 seconds inside an active browser tab, so alerts will not appear if the browser is closed."

### 16. What security measures are implemented in your project?
> **Answer:** "We implemented five key security layers:
> 1. Parameterized SQL queries using `?` placeholders to prevent SQL Injection.
> 2. Password hashing via Werkzeug to protect credentials.
> 3. Custom CSRF tokens on every `POST` request to prevent Cross-Site Request Forgery.
> 4. `user_id` filtering on all queries to enforce data isolation between users.
> 5. Database triggers on the `history` table to make audit logs append-only."

### 17. What happens if an error occurs during an SOS or location request?
> **Answer:** "The system is designed to fail gracefully. If a user denies location permissions or GPS times out, the Geolocation promise returns an error message instead of rejecting. The SOS process continues without coordinates, alerting emergency contacts that the user triggered an emergency but device location was unavailable."

### 18. How can this project be improved in the future?
> **Answer:** "In the future, we can integrate live SMS and WhatsApp gateways like Twilio, configure Service Workers and Web Push for background notifications when the browser is closed, and introduce voice recognition to trigger SOS alerts hands-free."

### 19. How is your project different from similar existing systems?
> **Answer:** "Most commercial systems either focus only on reminders or act exclusively as tracking apps that continuously monitor location in the background. Our system combines both into a single platform and uses on-demand location sharing, protecting user privacy and battery life."

### 20. What would you change if you developed the project again from scratch?
> **Answer:** "If rebuilding the project, I would implement a Service Worker from the start for background push notifications and offline caching, and I would structure the backend using Flask Blueprints for even cleaner modular code separation."

---
---

## Viva Preparation

### 1. 1–2 Minute Project Explanation (Speaking Script)

> *"Good morning, Respected Examiners.*
> 
> *My final-year project is the **Smart Reminder and Personal Protection System**, developed using Python, Flask, SQLite, and modern JavaScript.*
> 
> *The primary objective of this project is to combine everyday personal productivity with immediate personal safety in a privacy-respecting web application.*
> 
> *On the productivity side, the system provides a smart reminder engine supporting tasks, events, and recurring routines. It features a dual-tier notification engine that polls every 5 seconds to provide both advance chimes and audible digital alarms synthesized directly in the browser via the Web Audio API when a task is due.*
> 
> *On the safety side, the application features an emergency SOS system accessible from any page. When pressed, a 5-second countdown begins, allowing users to abort accidental triggers. Once confirmed, the system fetches one-time GPS coordinates using the HTML5 Geolocation API, generates an emergency message with an accurate Google Maps link, and dispatches the alert to pre-saved emergency contacts ordered by priority.*
> 
> *To protect user privacy, our system strictly avoids continuous background GPS tracking—coordinates are captured only when explicitly triggered by the user. Furthermore, the application enforces an append-only audit history via database triggers and provides an admin console that can only view aggregate counts without accessing private reminder notes or locations.*
> 
> *The system is secure, lightweight, and fully functional. Thank you, and I am ready for your questions."*

---

### 2. Important Technologies – Quick Revision

* **Python & Flask:** The backbone of our app. Python handles core application logic, and Flask maps URLs to Python functions (routes), handles sessions, and returns JSON or HTML templates.
* **SQLite3:** Our local database. Serverless, self-contained, and stores all user data, reminders, contacts, and logs inside `instance/app.db`.
* **Jinja2:** The template engine that allows us to write HTML with embedded Python-like syntax (variables, loops, and conditions) while automatically escaping text to prevent XSS attacks.
* **Vanilla JavaScript:** Powers our frontend logic—handles the 5-second countdown, calls APIs using `fetch()`, and updates the DOM without reloading the page.
* **HTML5 Geolocation API:** A browser standard used to retrieve the user's current GPS position (`latitude`, `longitude`, `accuracy`) on demand.
* **Web Audio API:** Generates real-time audio frequencies directly in the browser, allowing alarm sounds to play without downloading external audio files.
* **Werkzeug Security:** A security library used for generating and verifying cryptographic password hashes using salted algorithms.

---

### 3. Top 10 Most Important Viva Questions

1. **What is the tech stack of this project?**
   * *Answer:* Python 3, Flask framework, SQLite3 database, HTML5, Vanilla CSS3, and Vanilla JavaScript with browser Web APIs (Geolocation, Web Audio, Notifications).
2. **Where and how is the database stored?**
   * *Answer:* It is stored locally as a single relational database file at `instance/app.db` and accessed via Python's standard `sqlite3` module.
3. **How do you prevent SQL Injection in your project?**
   * *Answer:* Every SQL query uses parameterized placeholders (`?`). User inputs are passed as separate parameter tuples, never concatenated directly into SQL strings.
4. **How do notifications and alarms work without third-party services?**
   * *Answer:* JavaScript polls the `/api/notifications` endpoint every 5 seconds. When the due time arrives, client-side JavaScript activates the Web Audio API to play digital alarm beeps and opens a modal dialogue.
5. **How does the recurring reminder feature work?**
   * *Answer:* When a recurring reminder is marked as completed, the `next_occurrence()` function calculates its next due date (daily, weekly, or monthly) and updates the record back to 'pending'.
6. **Why is there a 5-second countdown for the SOS button?**
   * *Answer:* To prevent false alarms. It gives the user an opportunity to cancel if the button was clicked accidentally, and any cancellation is logged in history.
7. **Does your application continuously track the user's location?**
   * *Answer:* No. It uses on-demand location sharing via `getCurrentPosition()` only when the user clicks 'Share Location' or triggers an SOS. It never uses continuous tracking (`watchPosition`), protecting privacy and battery life.
8. **How is the activity history made append-only?**
   * *Answer:* We defined SQLite database triggers (`BEFORE UPDATE` and `BEFORE DELETE`) on the `history` table that raise an abort error whenever an update or delete query is attempted.
9. **How do you ensure administrators cannot spy on private user data?**
   * *Answer:* In `app.py`, the admin queries only select account details and statistical totals using `COUNT(*)`. The query never selects reminder titles, descriptions, contacts, or coordinates.
10. **Is the external SMS dispatch working live?**
    * *Answer:* Not in the current version. Live SMS dispatch is simulated via the `dispatch_alert()` function, which formats the message and logs it to the console and database, ready to connect to an SMS gateway like Twilio.

---

### 4. Difficult Technical Questions (To Test In-Depth Knowledge)

#### Q1: "How does your system handle CSRF protection without using the Flask-WTF extension?"
> **Answer:** 
> *"We implemented custom session-level CSRF verification directly in `app.py`. In the `csrf_token()` function, a random 16-byte cryptographic hex token is generated using Python's `secrets` module and stored in `session['_csrf']`. 
> This token is injected into every form as a hidden input and included in JavaScript `fetch()` requests via the `X-CSRF-Token` header. In the `@app.before_request` hook, every incoming `POST` request compares the submitted token against the session token using `secrets.compare_digest()` to prevent timing attacks. If the token is missing or mismatched, the request is rejected with HTTP 400."*

#### Q2: "How did you solve the browser's autoplay policy when playing the alarm sound?"
> **Answer:** 
> *"Modern browsers block the Web Audio API from playing sounds unless the user has interacted with the document. 
> To resolve this, in `app.js`, we registered passive event listeners for `click`, `keydown`, and `touchstart` on the `document` with `{ once: true }`. On the user's very first interaction, the script resumes or initializes the `AudioContext`. If an alarm triggers before user interaction occurs, the sound request is queued in a `soundWaiting` flag and plays immediately as soon as the user interacts."*

#### Q3: "Explain how SQLite triggers enforce an append-only audit trail in `schema.sql`."
> **Answer:** 
> *"In `schema.sql`, we created two triggers: `history_no_update` and `history_no_delete`. 
> Before any `UPDATE` operation on the `history` table, the trigger fires `SELECT RAISE(ABORT, 'history is append-only');`, which cancels the transaction. For `DELETE`, the trigger similarly aborts the operation if the user still exists. This guarantees that history logs remain immutable at the database engine level, even if someone executes raw SQL updates."*

#### Q4: "How does the system prevent race conditions or duplicate notification creation when the frontend polls every 5 seconds?"
> **Answer:** 
> *"We handle this at both the database level and the application level. 
> At the database level, we created a unique compound index: 
> `CREATE UNIQUE INDEX uq_notification_slot ON notifications(reminder_id, channel, scheduled_at)`. 
> In `app.py`, when `/api/notifications` runs, it first queries whether a record exists for that reminder slot. If two requests execute at the same moment, the database unique constraint throws an `IntegrityError`, which our code catches with `except sqlite3.IntegrityError: pass`. On the frontend, a `shown` Set stored in `sessionStorage` tracks delivered IDs so popups are never displayed twice."*

#### Q5: "How does your database handle foreign key cascading when users or reminders are deleted?"
> **Answer:** 
> *"By default, SQLite disables foreign key enforcement for backwards compatibility. In `db.py`, on every database connection, we execute `PRAGMA foreign_keys = ON;`. 
> In our table definitions in `schema.sql`, child tables like `reminders`, `emergency_contacts`, and `emergency_events` reference `users(user_id) ON DELETE CASCADE`. When a user account is deleted, all their associated reminders, contacts, and SOS events are cleaned up automatically by SQLite's relational engine."*

---
*Documentation prepared for Final Year Project Examination & Viva Voce.*
