import csv
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from functools import wraps

from flask import (
    Flask, jsonify, redirect, render_template, request,
    session, url_for, flash, abort, send_from_directory,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import health_assistant as ha

# ============================================================
# APP
# ============================================================
app = Flask(__name__)
app.secret_key = "change-this-to-a-strong-secret-key"

# ============================================================
# PATHS
# ============================================================
BASE_DIR = app.root_path

USERS_CSV_FILE = os.path.join(BASE_DIR, "users.csv")
PATIENTS_CSV_FILE = os.path.join(BASE_DIR, "patients.csv")
SEARCH_HISTORY_FILE = os.path.join(BASE_DIR, "search_history.csv")
DOCUMENT_REQUESTS_FILE = os.path.join(BASE_DIR, "document_requests.csv")

UPLOAD_PENDING_DIR = os.path.join(BASE_DIR, "uploads", "pending")
UPLOAD_APPROVED_DIR = os.path.join(BASE_DIR, "uploads", "approved")
os.makedirs(UPLOAD_PENDING_DIR, exist_ok=True)
os.makedirs(UPLOAD_APPROVED_DIR, exist_ok=True)

# ============================================================
# CSV FIELDS
# ============================================================
USERS_CSV_FIELDS = [
    "username", "name", "role", "linked_patient_id",
    "medical_emergency", "password_hash", "last_login",
]

PATIENT_CSV_FIELDS = [
    "patient_id", "name", "age", "gender", "blood_group",
    "diagnosis", "medical_history", "medications", "allergies",
    "medical_emergency", "aadhaar_no", "last_updated",
]

SEARCH_HISTORY_FIELDS = [
    "timestamp", "searched_by", "role", "query_id", "result_found",
]

DOCUMENT_REQUEST_FIELDS = [
    "request_id", "timestamp", "username", "patient_id",
    "original_filename", "stored_path", "note", "status",
    "reviewed_by", "reviewed_role", "review_note",
]

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}

# ============================================================
# DEMO USERS
# ============================================================
DEMO_USERS = {
    "admin": {
        "password": "123",
        "name": "Admin User",
        "role": "admin",
        "linked_patient_id": "",
        "medical_emergency": "Emergency Contact: ABC, Phone: 9876543210",
    },
    "dr_sharma": {
        "password": "pass_sharma_123",
        "name": "Dr. Rajesh Sharma",
        "role": "doctor",
        "linked_patient_id": "",
        "medical_emergency": "Blood Group: O+, Contact: 9811223344",
    },
    "dr_neha": {
        "password": "pass_neha_123",
        "name": "Dr. Neha Gupta",
        "role": "doctor",
        "linked_patient_id": "",
        "medical_emergency": "Emergency Contact: Vikas, Phone: 9844556677",
    },

}

# ============================================================
# DEMO PATIENTS  (11 patients)
# ============================================================
DEMO_PATIENTS = [
    {"patient_id":"1001","name":"Sunita Rao","age":"54","gender":"Female","blood_group":"O+","diagnosis":"Type 2 Diabetes / Routine Checkup","medical_history":"Type 2 diabetes since 2018. HbA1c 7.8. Mild hypertension.","medications":"Metformin 500mg twice daily, Amlodipine 5mg once daily","allergies":"No known drug allergies","medical_emergency":"Contact: Suresh (Son), Phone: 9871122334","aadhaar_no":"[Aadhaar Redacted]"},
    {"patient_id":"1002","name":"Vikram Malhotra","age":"46","gender":"Male","blood_group":"AB+","diagnosis":"Hypertension & Lipid Profile Review","medical_history":"Hypertension since 2020. Borderline high LDL. Ex-smoker.","medications":"Telmisartan 40mg once daily, Atorvastatin 10mg nightly","allergies":"None reported","medical_emergency":"Contact: Meena (Wife), Phone: 9819988776","aadhaar_no":"[Aadhaar Redacted]"},
    {"patient_id":"1003","name":"Kavita Joshi","age":"32","gender":"Female","blood_group":"A-","diagnosis":"Severe Drug Reaction (Sulfa Group)","medical_history":"Severe sulfa drug reaction in 2023. Avoid sulfa antibiotics.","medications":"Levocetirizine 5mg SOS","allergies":"Sulfa group drugs","medical_emergency":"Contact: Rakesh (Spouse), Phone: 9765432109","aadhaar_no":"[Aadhaar Redacted]"},
    {"patient_id":"1004","name":"Arjun Nair","age":"28","gender":"Male","blood_group":"B+","diagnosis":"Acute Asthma Exacerbation","medical_history":"Childhood asthma. Recent exacerbation after dust exposure.","medications":"Salbutamol inhaler PRN, Budesonide 200mcg daily","allergies":"Dust allergy","medical_emergency":"Contact: Dr. Iyer, Phone: 9823019283","aadhaar_no":"[Aadhaar Redacted]"},
    {"patient_id":"1005","name":"Fatima Sheikh","age":"61","gender":"Female","blood_group":"O-","diagnosis":"Post-Operative Orthopedic Rehabilitation","medical_history":"Total knee replacement surgery 6 weeks ago. Osteoarthritis.","medications":"Calcium + Vitamin D, Paracetamol 500mg SOS","allergies":"Penicillin rash","medical_emergency":"Contact: Tariq (Brother), Phone: 9890123456","aadhaar_no":"[Aadhaar Redacted]"},
    {"patient_id":"1006","name":"Rahul Verma","age":"37","gender":"Male","blood_group":"B+","diagnosis":"Anxiety Disorder / Panic Episodes","medical_history":"Generalized anxiety disorder with panic episodes since 2022.","medications":"Escitalopram 10mg once daily","allergies":"None reported","medical_emergency":"Contact: Anjali (Spouse), Phone: 9812345670","aadhaar_no":"[Aadhaar Redacted]"},
    {"patient_id":"1007","name":"Meena Iyer","age":"45","gender":"Female","blood_group":"A+","diagnosis":"Hypothyroidism","medical_history":"Primary hypothyroidism diagnosed in 2019. TSH previously 8.2.","medications":"Levothyroxine 75mcg empty stomach daily","allergies":"No known drug allergies","medical_emergency":"Contact: Ravi (Husband), Phone: 9822334455","aadhaar_no":"[Aadhaar Redacted]"},
    {"patient_id":"1008","name":"Sameer Khan","age":"58","gender":"Male","blood_group":"O+","diagnosis":"Chronic Kidney Disease Stage 2 with Hypertension","medical_history":"CKD stage 2, hypertension, mild proteinuria. Avoid NSAIDs.","medications":"Telmisartan 40mg daily, Calcium carbonate with meals","allergies":"NSAID sensitivity","medical_emergency":"Contact: Farah (Daughter), Phone: 9890011223","aadhaar_no":"[Aadhaar Redacted]"},
    {"patient_id":"1009","name":"Priya Patel","age":"24","gender":"Female","blood_group":"O-","diagnosis":"Iron Deficiency Anemia","medical_history":"Iron deficiency anemia with fatigue and low ferritin.","medications":"Oral iron supplement once daily, Vitamin C with iron","allergies":"Latex allergy","medical_emergency":"Contact: Kiran (Mother), Phone: 9765001122","aadhaar_no":"[Aadhaar Redacted]"},
    {"patient_id":"1010","name":"Ramesh Kulkarni","age":"67","gender":"Male","blood_group":"AB-","diagnosis":"Coronary Artery Disease Post Stent","medical_history":"Coronary artery disease. Angioplasty with stent in 2023.","medications":"Aspirin 75mg daily, Atorvastatin 40mg nightly, Metoprolol 25mg twice daily","allergies":"No known drug allergies","medical_emergency":"Contact: Sunita (Wife), Phone: 9823456781","aadhaar_no":"[Aadhaar Redacted]"},
    {"patient_id":"1011","name":"Neha Bhatt","age":"31","gender":"Female","blood_group":"B-","diagnosis":"PCOS with Insulin Resistance","medical_history":"Polycystic ovarian syndrome with irregular cycles and insulin resistance.","medications":"Metformin 500mg twice daily ","allergies":"Sulfa drugs rash ","medical_emergency":"Contact: Devang (Brother), Phone: 9900887766 ","aadhaar_no":"[Aadhaar Redacted] "}
]

# ============================================================
# CSV HELPERS
# ============================================================
def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_csv(path):
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            rows.append({
                (k or "").strip(): ("" if v is None else str(v).strip())
                for k, v in raw.items() if k is not None
            })
    return rows


def _write_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({
                k: ("" if row.get(k) is None else str(row.get(k)).strip())
                for k in fieldnames
            })


def read_users():
    return _read_csv(USERS_CSV_FILE)

def write_users(rows):
    _write_csv(USERS_CSV_FILE, USERS_CSV_FIELDS, rows)

def read_patients():
    return _read_csv(PATIENTS_CSV_FILE)

def write_patients(rows):
    _write_csv(PATIENTS_CSV_FILE, PATIENT_CSV_FIELDS, rows)

def read_document_requests():
    return _read_csv(DOCUMENT_REQUESTS_FILE)

def write_document_requests(rows):
    _write_csv(DOCUMENT_REQUESTS_FILE, DOCUMENT_REQUEST_FIELDS, rows)


def dedupe_by_key(rows, key_field):
    seen = {}
    for row in rows:
        key = (row.get(key_field) or "").strip().upper()
        if key:
            seen[key] = row
    return list(seen.values())

# ============================================================
# USER / PATIENT HELPERS
# ============================================================
def get_user_by_username(username):
    username = (username or "").strip().upper()
    if not username:
        return None
    for row in read_users():
        if (row.get("username") or "").strip().upper() == username:
            return row
    return None


def update_last_login(username):
    users = read_users()
    for user in users:
        if (user.get("username") or "").strip().upper() == (username or "").strip().upper():
            user["last_login"] = now_iso()
            break
    write_users(dedupe_by_key(users, "username"))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_patient_id():
    max_number = 1000
    for patient in read_patients():
        match = re.search(r"(\d+)", patient.get("patient_id", ""))
        if match:
            max_number = max(max_number, int(match.group(1)))
    return f"PAT-{max_number + 1}"


def log_patient_search(searched_by, role, query_id, found):
    with open(SEARCH_HISTORY_FILE, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=SEARCH_HISTORY_FIELDS).writerow({
            "timestamp": now_iso(),
            "searched_by": searched_by,
            "role": role,
            "query_id": query_id,
            "result_found": "Yes" if found else "No",
        })


def find_patient_by_id(patient_id):
    patient_id = (patient_id or "").strip().upper()
    if not patient_id:
        return None
    for row in read_patients():
        if (row.get("patient_id") or "").strip().upper() == patient_id:
            return row
    return None


def extract_patient_from_message(message):
    message = (message or "").strip()
    if not message:
        return None
    m = re.search(r"PAT-\d+", message, re.IGNORECASE)
    if m:
        patient = find_patient_by_id(m.group(0))
        if patient:
            return patient
    message_upper = message.upper()
    for row in read_patients():
        name = (row.get("name") or "").strip().upper()
        if name and name in message_upper:
            return row
    return None

# ============================================================
# DATA INITIALIZATION
# ============================================================
def ensure_patient_logins():
    users = read_users()
    users_by_username = {(u.get("username") or "").strip().upper(): u for u in users}
    for patient in read_patients():
        patient_id = (patient.get("patient_id") or "").strip().upper()
        if not patient_id:
            continue
        user = users_by_username.get(patient_id)
        if not user:
            user = {"last_login": ""}
            users.append(user)
        user.update({
            "username": patient_id,
            "name": patient.get("name", ""),
            "role": "patient",
            "linked_patient_id": patient_id,
            "medical_emergency": patient.get("medical_emergency", ""),
            "password_hash": generate_password_hash("patient123"),
        })
    write_users(dedupe_by_key(users, "username"))


def init_db():
    # Users
    users = read_users()
    users_by_username = {(u.get("username") or "").strip().upper(): u for u in users}
    for username, profile in DEMO_USERS.items():
        user = users_by_username.get(username.upper())
        if not user:
            user = {"last_login": ""}
            users.append(user)
        user.update({
            "username": username,
            "name": profile["name"],
            "role": profile["role"],
            "linked_patient_id": profile.get("linked_patient_id", ""),
            "medical_emergency": profile.get("medical_emergency", ""),
            "password_hash": generate_password_hash(profile["password"]),
        })
    write_users(dedupe_by_key(users, "username"))

    # Patients
    patients = read_patients()
    patients_by_id = {(p.get("patient_id") or "").strip().upper(): p for p in patients}
    for demo in DEMO_PATIENTS:
        pid = demo["patient_id"].strip().upper()
        patient = patients_by_id.get(pid)
        if not patient:
            patient = {"last_updated": now_iso()}
            patients.append(patient)
        for field in PATIENT_CSV_FIELDS:
            if field != "last_updated":
                patient[field] = demo.get(field, "")
        if not patient.get("last_updated"):
            patient["last_updated"] = now_iso()
    write_patients(dedupe_by_key(patients, "patient_id"))

    ensure_patient_logins()

    if not os.path.exists(SEARCH_HISTORY_FILE):
        _write_csv(SEARCH_HISTORY_FILE, SEARCH_HISTORY_FIELDS, [])
    if not os.path.exists(DOCUMENT_REQUESTS_FILE):
        _write_csv(DOCUMENT_REQUESTS_FILE, DOCUMENT_REQUEST_FIELDS, [])


init_db()
ha.refresh_chunks()

# ============================================================
# AUTH DECORATOR
# ============================================================
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

# ============================================================
# CONTEXT PROCESSOR — pending badge in sidebar
# ============================================================
@app.context_processor
def inject_globals():
    pending = 0
    if session.get("role") in ("admin", "doctor"):
        pending = len([
            r for r in read_document_requests()
            if r.get("status") == "Pending"
        ])
    return {"nav_pending": pending}

# ============================================================
# AUTH ROUTES
# ============================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = get_user_by_username(username)
        if user and check_password_hash(user.get("password_hash", ""), password):
            session.clear()
            session["username"] = user.get("username")
            session["role"] = user.get("role", "staff")
            session["linked_patient_id"] = user.get("linked_patient_id", "")
            update_last_login(username)
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Invalid username or password")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ============================================================
# DASHBOARD
# ============================================================
@app.route("/")
@login_required
def dashboard():
    role = session.get("role")
    patients = read_patients()
    users = read_users()
    docs = read_document_requests()
    stats, recent = [], []

    if role == "admin":
        stats = [
            {"icon":"users","tone":"brand","label":"Total Patients","value":len(patients)},
            {"icon":"steth","tone":"sky","label":"Doctors","value":len([u for u in users if u.get("role")=="doctor"])},
            {"icon":"file","tone":"warn","label":"Pending Approvals","value":len([d for d in docs if d.get("status")=="Pending"])},
            {"icon":"shield","tone":"success","label":"Total Users","value":len(users)},
        ]
        recent = patients[:5]

    elif role == "doctor":
        stats = [
            {"icon":"users","tone":"brand","label":"Patients On Record","value":len(patients)},
            {"icon":"file","tone":"warn","label":"Pending Approvals","value":len([d for d in docs if d.get("status")=="Pending"])},
            {"icon":"book","tone":"sky","label":"Knowledge Sources","value":len({c["source"] for c in ha.CHUNKS})},
            {"icon":"activity","tone":"success","label":"Knowledge Chunks","value":len(ha.CHUNKS)},
        ]
        recent = patients[:5]

    elif role == "patient":
        mine = [d for d in docs if (d.get("username") or "").upper() == (session.get("username") or "").upper()]
        me = find_patient_by_id(session.get("linked_patient_id"))
        stats = [
            {"icon":"file","tone":"brand","label":"My Documents","value":len(mine)},
            {"icon":"clock","tone":"warn","label":"Pending Review","value":len([d for d in mine if d.get("status")=="Pending"])},
            {"icon":"check","tone":"success","label":"Approved","value":len([d for d in mine if d.get("status")=="Approved"])},
            {"icon":"heart","tone":"sky","label":"Blood Group","value":(me.get("blood_group") if me else "-") or "-"},
        ]

    return render_template("index.html", stats=stats, recent=recent, role=role)

# ============================================================
# SEARCH / RECORDS
# ============================================================
@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    role = session.get("role")
    if role == "patient":
        return redirect(url_for("my_record"))
    if request.method == "POST":
        query = (request.form.get("patient_query") or "").strip().upper()
        patient = None
        for row in read_patients():
            if (row.get("patient_id") or "").strip().upper() == query or (row.get("name") or "").strip().upper() == query:
                patient = row
                break
        log_patient_search(session.get("username"), role, query, bool(patient))
        if patient:
            return redirect(url_for("patient_record", patient_id=patient["patient_id"]))
        return render_template("search.html", role=role, error="Patient record not found.")
    return render_template("search.html", role=role)


@app.route("/patient-record/<patient_id>")
@login_required
def patient_record(patient_id):
    role = session.get("role")
    patient = find_patient_by_id(patient_id)
    if not patient:
        flash("Patient record not found.")
        return redirect(url_for("dashboard"))

    if role == "patient":
        linked = (session.get("linked_patient_id") or "").strip().upper()
        if linked != patient["patient_id"].strip().upper():
            abort(403)
    elif role not in {"doctor", "admin"}:
        abort(403)

    docs = [
        d for d in read_document_requests()
        if (d.get("patient_id") or "").strip().upper() == patient["patient_id"].strip().upper()
    ]
    if role == "patient":
        docs = [d for d in docs if (d.get("username") or "").strip().upper() == (session.get("username") or "").strip().upper()]
    docs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return render_template("patient_record.html", patient=patient, role=role, docs=docs)


@app.route("/my-record")
@login_required
def my_record():
    if session.get("role") != "patient":
        return redirect(url_for("search"))
    patient_id = session.get("linked_patient_id")
    if not patient_id:
        flash("No patient profile is linked to this login.")
        return redirect(url_for("dashboard"))
    return redirect(url_for("patient_record", patient_id=patient_id))

# ============================================================
# ADMIN: ADD PATIENT
# ============================================================
@app.route("/patients/add", methods=["GET", "POST"])
@login_required
def add_patient():
    if session.get("role") != "admin":
        abort(403)
    if request.method == "POST":
        patient_id = (request.form.get("patient_id") or "").strip().upper() or generate_patient_id()
        if find_patient_by_id(patient_id):
            flash("Patient ID already exists.")
            return render_template("add_patient.html")
        fields = ["name","age","gender","blood_group","diagnosis","medical_history","medications","allergies","medical_emergency","aadhaar_no"]
        row = {f: (request.form.get(f) or "").strip() for f in fields}
        row["patient_id"] = patient_id
        row["last_updated"] = now_iso()
        if not row["name"]:
            flash("Patient name is required.")
            return render_template("add_patient.html")
        patients = read_patients()
        patients.append(row)
        write_patients(dedupe_by_key(patients, "patient_id"))

        if request.form.get("create_login") == "on":
            username = (request.form.get("username") or patient_id).strip()
            password = (request.form.get("password") or "patient123").strip()
            existing = get_user_by_username(username)
            if existing and existing.get("role") != "patient":
                flash("Patient saved, but username belongs to a non-patient user.")
            elif not existing:
                users = read_users()
                users.append({
                    "username": username, "name": row["name"], "role": "patient",
                    "linked_patient_id": patient_id,
                    "medical_emergency": row.get("medical_emergency", ""),
                    "password_hash": generate_password_hash(password),
                    "last_login": "",
                })
                write_users(dedupe_by_key(users, "username"))
                flash("Patient record and patient login created.")
        return redirect(url_for("patient_record", patient_id=patient_id))
    return render_template("add_patient.html")

# ============================================================
# ADMIN: MANAGE DOCTORS
# ============================================================
@app.route("/admin/doctors", methods=["GET", "POST"])
@login_required
def admin_doctors():
    if session.get("role") != "admin":
        abort(403)
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        name = (request.form.get("name") or "").strip()
        password = (request.form.get("password") or "").strip()
        medical_emergency = (request.form.get("medical_emergency") or "").strip()
        if not username or not name or not password:
            flash("Username, name, and password are required.")
        elif len(password) < 6:
            flash("Password must be at least 6 characters long.")
        elif get_user_by_username(username):
            flash("Username already exists. Please choose another username.")
        else:
            users = read_users()
            users.append({
                "username": username, "name": name, "role": "doctor",
                "linked_patient_id": "", "medical_emergency": medical_emergency,
                "password_hash": generate_password_hash(password), "last_login": "",
            })
            write_users(dedupe_by_key(users, "username"))
            flash(f"Doctor account '{username}' created successfully.")
            return redirect(url_for("admin_doctors"))
    doctors = sorted(
        [u for u in read_users() if (u.get("role") or "").lower() == "doctor"],
        key=lambda x: (x.get("username") or "").lower()
    )
    return render_template("admin_doctors.html", doctors=doctors)

# ============================================================
# PATIENT: UPLOAD DOCUMENT FOR APPROVAL
# ============================================================
@app.route("/upload-document", methods=["POST"])
@login_required
def upload_document():
    if session.get("role") != "patient":
        abort(403)
    patient_id = (session.get("linked_patient_id") or session.get("username") or "UNKNOWN").strip().upper()
    file = request.files.get("document")
    note = (request.form.get("note") or "").strip()

    if not file or file.filename == "":
        flash("Please select a file to upload.")
        return redirect(request.referrer or url_for("dashboard"))
    if not allowed_file(file.filename):
        flash("Only PDF, PNG, JPG, and JPEG files are allowed.")
        return redirect(request.referrer or url_for("dashboard"))

    original_filename = file.filename
    safe_filename = secure_filename(original_filename) or "document"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    stored_filename = f"{timestamp}_{patient_id}_{unique_id}_{safe_filename}"
    stored_path = os.path.join(UPLOAD_PENDING_DIR, stored_filename)
    file.save(stored_path)

    rows = read_document_requests()
    rows.append({
        "request_id": uuid.uuid4().hex,
        "timestamp": now_iso(),
        "username": session.get("username", ""),
        "patient_id": patient_id,
        "original_filename": original_filename,
        "stored_path": stored_path,
        "note": note,
        "status": "Pending",
        "reviewed_by": "",
        "reviewed_role": "",
        "review_note": "",
    })
    write_document_requests(rows)
    flash("Your document has been sent for approval.")
    return redirect(url_for("patient_record", patient_id=patient_id))

# ============================================================
# ADMIN + DOCTOR: SHARED APPROVAL QUEUE
# ============================================================
@app.route("/approvals")
@login_required
def approvals():
    role = session.get("role")
    if role not in {"admin", "doctor"}:
        abort(403)

    rows = read_document_requests()
    status_filter = request.args.get("status", "all")
    if status_filter in {"Pending", "Approved", "Rejected"}:
        rows = [r for r in rows if r.get("status") == status_filter]

    rows.sort(key=lambda x: (x.get("status") != "Pending", x.get("timestamp", "")))

    return render_template("approvals.html", rows=rows, status_filter=status_filter, role=role)


@app.route("/approvals/<request_id>/review", methods=["POST"])
@login_required
def review_document_request(request_id):
    role = session.get("role")
    if role not in {"admin", "doctor"}:
        abort(403)

    status = request.form.get("status")
    review_note = (request.form.get("review_note") or "").strip()
    if status not in {"Approved", "Rejected"}:
        abort(400)

    rows = read_document_requests()
    target = None
    for row in rows:
        if row.get("request_id") == request_id:
            target = row
            if row.get("status") != "Pending":
                flash("This document has already been reviewed.")
                return redirect(url_for("approvals"))

            row["status"] = status
            row["reviewed_by"] = session.get("username", "")
            row["reviewed_role"] = role
            row["review_note"] = review_note

            if status == "Approved":
                old_path = row.get("stored_path", "")
                if old_path and os.path.exists(old_path):
                    new_path = os.path.join(UPLOAD_APPROVED_DIR, os.path.basename(old_path))
                    if os.path.exists(new_path):
                        new_path = os.path.join(UPLOAD_APPROVED_DIR, f"{uuid.uuid4().hex[:6]}_{os.path.basename(old_path)}")
                    try:
                        shutil.move(old_path, new_path)
                        row["stored_path"] = new_path
                    except Exception as e:
                        flash(f"Document approved, but file could not be moved: {e}")
            break

    if not target:
        abort(404)

    write_document_requests(rows)
    flash(f"Document {status.lower()} by {role}.")
    return redirect(url_for("approvals"))


@app.route("/documents/<request_id>/view")
@login_required
def view_document(request_id):
    role = session.get("role")
    rows = read_document_requests()
    target = None
    for row in rows:
        if row.get("request_id") == request_id:
            target = row
            break
    if not target:
        abort(404)

    if role in {"admin", "doctor"}:
        pass
    elif role == "patient":
        if target.get("username") != session.get("username"):
            abort(403)
        if target.get("status") != "Approved":
            abort(403)
    else:
        abort(403)

    stored_path = target.get("stored_path", "")
    if not stored_path or not os.path.exists(stored_path):
        abort(404)

    directory = os.path.dirname(stored_path)
    filename = os.path.basename(stored_path)
    return send_from_directory(directory, filename)

# ============================================================
# ADMIN: SYSTEM ACTIVITY
# ============================================================
@app.route("/admin-data")
@login_required
def admin_data():
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))
    rows = [
        {
            "username": r.get("username", ""),
            "name": r.get("name", ""),
            "role": r.get("role", ""),
            "linked_patient_id": r.get("linked_patient_id", ""),
            "last_login": r.get("last_login", "") or "Not logged in",
        }
        for r in read_users()
    ]
    return render_template("admin_data.html", rows=rows)


@app.route("/admin/refresh-knowledge")
@login_required
def refresh_knowledge():
    if session.get("role") != "admin":
        abort(403)
    ha.refresh_chunks()
    flash("Knowledge base refreshed.")
    return redirect(url_for("dashboard"))

# ============================================================
# CHATBOT
# ============================================================
@app.route("/chat", methods=["GET", "POST"])
def chat():
    if request.method == "POST":
        if "username" not in session:
            return jsonify({"reply": "Please log in first.", "requires_login": True}), 401

        role = session.get("role")
        if role not in {"doctor", "patient"}:
            return jsonify({"reply": "Chatbot access is restricted for your role."}), 403

        data = request.get_json(silent=True) or {}
        user_message = (data.get("message") or "").strip()
        language = (data.get("language") or "en").lower()
        if language not in {"en", "hi"}:
            language = "en"
        if not user_message:
            return jsonify({"reply": "Please type a question first."})

        if user_message.lower() in {"update", "अपडेट"}:
            if role == "doctor":
                ha.refresh_chunks()
                return jsonify({"reply": "Knowledge base updated."})
            return jsonify({"reply": "Only doctors can update the knowledge base from chat."})

        patient, allow_patient_history = None, False
        if role == "doctor":
            patient = extract_patient_from_message(user_message)
            if patient:
                allow_patient_history = True
                log_patient_search(session.get("username"), role, patient.get("patient_id", ""), True)

        reply = ha.answer(
            message=user_message, language=language, role=role,
            patient=patient, allow_patient_history=allow_patient_history,
            allow_pdf=True,
        )
        return jsonify({"reply": reply})

    if "username" not in session:
        return redirect(url_for("login"))
    if session.get("role") not in {"doctor", "patient"}:
        flash("Chatbot access is restricted for your role.")
        return redirect(url_for("dashboard"))
    return render_template("chat.html")

# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    print("Starting ClearID Clinical OS...")
    print("Open: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)