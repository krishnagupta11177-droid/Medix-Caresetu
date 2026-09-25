# ClearID (Medix Caresetu)

A Flask-based patient case-taking and record management platform built for **Smart India Hackathon 2026 — Problem Statement 26047 (AYUSH/OPD patient case-taking kiosk)**.

ClearID digitizes the OPD patient journey — from intake and record lookup to an AI-assisted health chat and a staff-side document review queue — so hospitals and clinics can move away from paper-based case sheets.

## Features

- 🔐 **Role-based login** for admins, doctors, and patients
- 🔎 **Patient record search** with searchable case history and logging of every lookup
- 🩺 **Patient record management** — add new patients, view full medical history, medications, allergies, and emergency contact details
- 💬 **AI health assistant** for conversational symptom capture and quick patient lookup via chat
- 📄 **Document upload & approval workflow** — patients/staff upload documents (PDF/image), and admins/doctors review and approve or reject them
- 👩‍⚕️ **Doctor management** panel for admins
- 📊 **Admin dashboard** with data overview and knowledge-base refresh

## Tech Stack

- **Backend:** Python, Flask
- **Auth:** Werkzeug password hashing, session-based login
- **Data storage:** CSV-based storage for users, patients, search history, and document requests
- **Frontend:** Flask templates (Jinja2)

## Project Structure

```
Medix-Caresetu/
├── app.py                 # Main Flask app: routes, auth, patient & document workflows
├── health_assistant.py    # AI health assistant / chatbot logic
├── templates/              # HTML templates
├── static/                 # CSS/JS/static assets
├── knowledge/               # Knowledge base used by the health assistant
├── training_data/           # Data used for the assistant
├── uploads/                # Pending & approved patient document uploads
├── users.csv                # User records
├── patients.csv              # Patient records
├── search_history.csv        # Logged patient searches
└── document_requests.csv      # Document upload/approval requests
```

## Getting Started

1. Clone the repository
   ```bash
   git clone https://github.com/krishnagupta11177-droid/Medix-Caresetu.git
   cd Medix-Caresetu
   ```
2. Install dependencies
   ```bash
   pip install flask werkzeug
   ```
3. Run the app
   ```bash
   python app.py
   ```
4. Open `http://localhost:5000` in your browser

## About

Built as part of a Smart India Hackathon 2026 internal round submission for Problem Statement 26047, focused on digitizing AYUSH/OPD patient case-taking through an accessible kiosk-style platform.

## License

No license specified yet — add one if you plan to open this up for contributions.
