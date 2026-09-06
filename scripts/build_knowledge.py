import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
DISEASE_JSON = KNOWLEDGE_DIR / "diseases.json"
DISEASE_TXT_DIR = KNOWLEDGE_DIR / "diseases"
TRAINING_DIR = BASE_DIR / "training_data"
TRAINING_FILE = TRAINING_DIR / "disease_qa.jsonl"

DISCLAIMER = (
    " This is general health information only and not a substitute for professional medical care."
)


def ensure_dirs():
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    DISEASE_TXT_DIR.mkdir(parents=True, exist_ok=True)
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)


def clean_items(items):
    return [item.strip() for item in items if item and item.strip()]


def build_text_for_disease(disease):
    lines = []

    lines.append(f"Disease: {disease.get('name', '')}")
    lines.append(f"Category: {disease.get('category', '')}")
    lines.append(f"Summary: {disease.get('summary', '')}")

    sections = [
        ("Symptoms", "symptoms"),
        ("Red Flags / Emergency Warning Signs", "red_flags"),
        ("Causes", "causes"),
        ("Risk Factors", "risk_factors"),
        ("Prevention", "prevention"),
        ("Lifestyle Advice", "lifestyle"),
        ("Treatment Overview", "treatment_overview"),
        ("When To See A Doctor", "when_to_see_doctor"),
    ]

    for label, key in sections:
        value = disease.get(key)

        if not value:
            continue

        if isinstance(value, list):
            items = clean_items(value)
            if items:
                lines.append(f"{label}:")
                for item in items:
                    lines.append(f"- {item}")
        else:
            lines.append(f"{label}: {str(value).strip()}")

    return "\n".join(lines)


def build_training_pairs(disease):
    name = disease.get("name", "")
    pairs = []

    def add(question, answer):
        if answer and str(answer).strip():
            pairs.append(
                {
                    "prompt": question,
                    "completion": str(answer).strip() + DISCLAIMER
                }
            )

    add(
        f"What is {name}?",
        disease.get("summary", "")
    )

    symptoms = disease.get("symptoms")
    if symptoms:
        add(
            f"What are the symptoms of {name}?",
            "Common symptoms include: " + ", ".join(clean_items(symptoms)) + "."
        )

    red_flags = disease.get("red_flags")
    if red_flags:
        add(
            f"What are the danger signs or red flags in {name}?",
            "Seek urgent medical care if these occur: " + ", ".join(clean_items(red_flags)) + "."
        )

    causes = disease.get("causes")
    if causes:
        add(
            f"What causes {name}?",
            "Common causes include: " + ", ".join(clean_items(causes)) + "."
        )

    risk_factors = disease.get("risk_factors")
    if risk_factors:
        add(
            f"What are the risk factors for {name}?",
            "Risk factors include: " + ", ".join(clean_items(risk_factors)) + "."
        )

    prevention = disease.get("prevention")
    if prevention:
        add(
            f"How can {name} be prevented?",
            "Prevention measures include: " + ", ".join(clean_items(prevention)) + "."
        )

    lifestyle = disease.get("lifestyle")
    if lifestyle:
        add(
            f"What lifestyle advice is useful for {name}?",
            "Helpful lifestyle measures include: " + ", ".join(clean_items(lifestyle)) + "."
        )

    treatment = disease.get("treatment_overview")
    if treatment:
        add(
            f"What is the general treatment approach for {name}?",
            treatment
        )

    when_to_see_doctor = disease.get("when_to_see_doctor")
    if when_to_see_doctor:
        add(
            f"When should a person with {name} see a doctor?",
            when_to_see_doctor
        )

    return pairs


def main():
    ensure_dirs()

    diseases = json.loads(DISEASE_JSON.read_text(encoding="utf-8"))

    all_training_pairs = []

    for disease in diseases:
        disease_id = disease.get("id", "unknown")
        text = build_text_for_disease(disease)

        txt_path = DISEASE_TXT_DIR / f"{disease_id}.txt"
        txt_path.write_text(text, encoding="utf-8")

        all_training_pairs.extend(build_training_pairs(disease))

    with TRAINING_FILE.open("w", encoding="utf-8") as f:
        for pair in all_training_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    print(f"Generated {len(diseases)} disease knowledge files.")
    print(f"Generated {len(all_training_pairs)} training pairs.")
    print(f"Disease TXT folder: {DISEASE_TXT_DIR}")
    print(f"Training JSONL file: {TRAINING_FILE}")


if __name__ == "__main__":
    main()