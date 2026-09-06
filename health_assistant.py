import os, re, json
from collections import Counter

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge")
CHUNKS = []
DISEASES = []

STOPWORDS = set("a an and are as at be by can could did do does for from had has have how i if in into is it its of on or our should so than that the their them then there these they this to was were what when where which who will with would you your yours".split())

EMERGENCY_TERMS = [
    "chest pain","heart attack","stroke","face drooping","arm weakness","slurred speech",
    "severe breathing difficulty","cannot breathe","cant breathe","can't breathe","blue lips",
    "unconscious","fainting","severe bleeding","vomiting blood","black stool",
    "severe allergic reaction","swelling of face","throat swelling",
    "high fever with stiff neck","seizure","suicidal","self harm",
    "sudden weakness","sudden numbness","sudden confusion",
]

# ============================================================
# KNOWLEDGE BASE LOADING
# ============================================================
def refresh_chunks():
    global CHUNKS, DISEASES
    CHUNKS = []
    DISEASES = []
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

    # Load structured disease database
    disease_file = os.path.join(KNOWLEDGE_DIR, "diseases.json")
    if os.path.exists(disease_file):
        try:
            with open(disease_file, "r", encoding="utf-8") as f:
                DISEASES = json.load(f)
        except Exception as e:
            print(f"Could not load diseases.json: {e}")

    # Load PDF/TXT chunks
    for root, _, files in os.walk(KNOWLEDGE_DIR):
        for filename in files:
            path = os.path.join(root, filename)
            text = ""
            try:
                if filename.lower().endswith(".pdf"):
                    if PdfReader is None:
                        continue
                    text = "\n".join((p.extract_text() or "") for p in PdfReader(path).pages)
                elif filename.lower().endswith((".txt", ".md")):
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                else:
                    continue
                CHUNKS.extend(_chunk_text(text, filename))
            except Exception as e:
                print(f"Could not read {path}: {e}")


def _chunk_text(text, source, chunk_size=900, overlap=120):
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        part = text[start:end]
        chunks.append({"text": part, "source": source, "tokens": set(_tokens(part))})
        if end == len(text):
            break
        start = end - overlap
    return chunks


def _tokens(text):
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t not in STOPWORDS and len(t) > 2]


def _search_chunks(query, top_k=4):
    if not CHUNKS:
        return []
    q = set(_tokens(query))
    if not q:
        return []
    scored = []
    for chunk in CHUNKS:
        overlap = q.intersection(chunk["tokens"])
        if not overlap:
            continue
        score = len(overlap) + sum(0.1 for t in overlap if t in chunk["text"].lower())
        scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]


def _search_diseases(query):
    if not DISEASES:
        return None
    q = query.lower()
    best, best_score = None, 0
    for d in DISEASES:
        score = 0
        name = (d.get("name") or "").lower()
        aliases = [a.lower() for a in d.get("aliases", [])]
        if name in q:
            score += 10
        for a in aliases:
            if a in q:
                score += 8
        for word in _tokens(q):
            if word in name:
                score += 3
            if any(word in a for a in aliases):
                score += 2
            summary = (d.get("summary") or "").lower()
            if word in summary:
                score += 1
        if score > best_score:
            best_score = score
            best = d
    return best if best_score >= 5 else None


def _disease_response(d, language="en"):
    lines = [f"{d.get('name','')}", f"Category: {d.get('category','')}", "", d.get("summary","")]
    sections = [
        ("Symptoms", "symptoms"),
        ("Red Flags / Seek urgent care if", "red_flags"),
        ("Prevention", "prevention"),
        ("Lifestyle Advice", "lifestyle"),
        ("Treatment Overview", "treatment_overview"),
        ("When To See A Doctor", "when_to_see_doctor"),
    ]
    for label, key in sections:
        val = d.get(key)
        if val:
            lines.append(f"\n{label}:")
            if isinstance(val, list):
                for item in val:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"  {val}")
    lines.append("\nThis is general health information only and not a substitute for professional medical care.")
    return "\n".join(lines)


def _summarize(text, max_sentences=4):
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if len(sentences) <= max_sentences:
        return " ".join(sentences)
    freq = Counter(_tokens(" ".join(sentences)))
    scored = []
    for idx, s in enumerate(sentences):
        toks = _tokens(s)
        if toks:
            scored.append((sum(freq.get(t, 0) for t in toks) / len(toks), idx, s))
    if not scored:
        return text[:600]
    top = sorted(sorted(scored, reverse=True)[:max_sentences], key=lambda x: x[1])
    return " ".join([s for _, _, s in top])


def _patient_context(patient):
    parts = []
    for field, label in [
        ("name","Name"),("patient_id","Patient ID"),("age","Age"),("gender","Gender"),
        ("blood_group","Blood Group"),("diagnosis","Diagnosis"),
        ("medical_history","Medical History"),("medications","Medications"),
        ("allergies","Allergies"),("medical_emergency","Emergency Contact"),
    ]:
        v = (patient.get(field) or "").strip()
        if v:
            parts.append(f"{label}: {v}")
    return "; ".join(parts)


def _patient_summary(patient, language="en"):
    lines = [f"Medical record summary - {patient.get('name','')} ({patient.get('patient_id','')})"]
    for label, value in [
        ("Age/Gender", f"{patient.get('age','')} / {patient.get('gender','')}"),
        ("Blood Group", patient.get("blood_group","")),
        ("Diagnosis", patient.get("diagnosis","")),
        ("Medical History", patient.get("medical_history","")),
        ("Medications", patient.get("medications","")),
        ("Allergies", patient.get("allergies","")),
        ("Emergency Contact", patient.get("medical_emergency","")),
        ("Last Updated", patient.get("last_updated","")),
    ]:
        if (value or "").strip():
            lines.append(f"- {label}: {value}")
    lines.append("")
    lines.append("Please verify with the treating clinician before action.")
    return "\n".join(lines)


def _emergency_detected(m):
    low = (m or "").lower()
    return any(t in low for t in EMERGENCY_TERMS)


def _symptom_advice(message):
    low = (message or "").lower()
    if any(w in low for w in ["common cold","cold","runny nose","sore throat","sneezing","flu"]):
        return "Common cold / flu-like symptoms:\n- Rest well\n- Drink plenty of fluids\n- Saline gargles or steam if needed\n- Monitor for fever or breathing difficulty\n\nConsult a doctor if symptoms worsen or persist."
    if any(w in low for w in ["fever","temperature"]):
        return "For fever:\n- Rest and drink fluids\n- Wear light clothing\n- Monitor temperature regularly\n\nSeek urgent care for very high/persistent fever, rash, confusion, breathing difficulty, or stiff neck."
    if "cough" in low:
        return "For cough:\n- Stay hydrated\n- Avoid smoke, dust, pollution\n- Warm saline gargles\n\nConsult a doctor if cough persists, blood appears, or breathing difficulty develops."
    if any(w in low for w in ["headache","migraine"]):
        return "For headache:\n- Rest in a quiet, dim room\n- Stay hydrated\n- Avoid screen strain\n\nSeek urgent care for sudden severe headache, weakness, speech difficulty, or vision changes."
    if any(w in low for w in ["diarrhea","loose motion","vomiting","stomach pain","food poisoning"]):
        return "For stomach upset:\n- Small frequent sips of fluids / ORS\n- Avoid heavy, oily food\n\nSeek care for blood in stool, severe pain, persistent vomiting, or dizziness."
    if any(w in low for w in ["diabetes","blood sugar","sugar level"]):
        return "General diabetes guidance:\n- Take medicines as prescribed\n- Balanced meals, controlled carbs\n- Stay active if safe\n- Monitor sugar if advised\n\nContact your doctor for repeatedly high/low readings."
    if any(w in low for w in ["blood pressure","bp","hypertension"]):
        return "General BP guidance:\n- Take medication regularly\n- Reduce salt\n- Manage stress and sleep\n- Avoid smoking/alcohol\n\nSeek urgent care for chest pain, severe headache, or breathlessness."
    if any(w in low for w in ["asthma","wheezing","breathlessness","shortness of breath"]):
        return "General asthma guidance:\n- Avoid dust/smoke/triggers\n- Use reliever inhaler as directed\n- Continue controller medicines\n\nSeek emergency care if breathing difficulty is severe."
    return None


def _medication_advice(message):
    low = (message or "").lower()
    terms = ["medicine","medication","tablet","dose","dosage","side effect","antibiotic","painkiller","metformin","aspirin","atorvastatin","levothyroxine","inhaler"]
    if any(t in low for t in terms):
        return "Medication safety guidance:\n- Take medicines exactly as prescribed\n- Do not stop/change without doctor advice\n- Inform your doctor about allergies & other medicines\n- Avoid self-prescribing\n\nFor dose or side-effect concerns, contact your doctor or pharmacist."
    return None


def answer(message, language="en", role=None, patient=None, allow_patient_history=False, allow_pdf=True):
    msg = (message or "").strip()
    low = msg.lower()
    if not msg:
        return "Please ask a question."
    if role == "admin":
        return "Admin role cannot use the chatbot."

    if _emergency_detected(msg):
        if language == "hi":
            return "यह संभावित आपातकालीन स्थिति हो सकती है।\नकृपया तुरंत आपातकालीन सेवा से संपर्क करें।\नयह चैटबॉट आपातकालीन चिकित्सा का विकल्प नहीं है।"
        return "This could be an emergency.\nPlease call emergency services immediately or go to the nearest emergency department.\nThis chatbot is not a substitute for emergency medical care."

    if role == "patient":
        blocked = (
            re.search(r"pat-\d+", low)
            or re.search(r"\b(my|mera|meri|mine)\b.*\b(history|summary|record|diagnosis|condition|medication|allergy)\b", low)
            or re.search(r"\b(patient\s+summary|medical\s+record\s+summary)\b", low)
        )
        if blocked:
            return "You cannot retrieve your full medical record summary through the chatbot.\nPlease use the My Medical Record page or contact your doctor."

    record_keywords = ["history","summary","medical record","record","diagnosis","condition","medication","medications","allergy","allergies"]
    record_intent = any(k in low for k in record_keywords)

    if patient and allow_patient_history and record_intent:
        return _patient_summary(patient, language)

    # Try structured disease database first
    disease = _search_diseases(msg)
    if disease:
        return _disease_response(disease, language)

    # Then try PDF/TXT knowledge
    if allow_pdf:
        query = f"{msg} {_patient_context(patient)}" if (patient and allow_patient_history) else msg
        results = _search_chunks(query, top_k=4)
        if results:
            combined = " ".join([c["text"] for c in results])
            summary = _summarize(combined, max_sentences=6 if role == "doctor" else 4)
            sources = ", ".join(sorted({c["source"] for c in results}))
            if role == "doctor" and patient and allow_patient_history:
                return f"Patient context:\n{_patient_context(patient)}\n\nEvidence summary:\n{summary}\n\nSources: {sources}\n\nPlease verify clinically before making decisions."
            if role == "patient":
                return f"Here is a patient-friendly summary from approved knowledge documents:\n\n{summary}\n\nSources: {sources}\n\nThis is general health information and not a substitute for a doctor."
            return f"Summary from knowledge base:\n{summary}\n\nSources: {sources}\n\nThis is general information and not a substitute for medical advice."

    if patient and allow_patient_history:
        return _patient_summary(patient, language)

    if role == "patient" or not patient:
        s = _symptom_advice(msg)
        if s:
            return s
        m = _medication_advice(msg)
        if m:
            return m

    if role == "patient":
        return "I can help with general health questions, symptom guidance, medication safety, and disease information.\n\nTry: fever, headache, common cold, diabetes diet, BP precautions, asthma precautions, medication safety.\n\nFor your personal medical record, use the My Medical Record page."

    return "I could not find a relevant answer from the knowledge base. Please rephrase the question or add relevant PDFs to the knowledge folder."