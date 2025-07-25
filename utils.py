# Directory: employee_onboarding_app/
# File: utils.py

import re
import pandas as pd
from typing import Dict, Any, Tuple, List
import logging
import os
import requests
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/text-bison-001:generateText"

def validate_phone_number(phone: str) -> bool:
    phone = re.sub(r"\D", "", phone)
    return bool(re.fullmatch(r"\d{10,15}", phone))

def validate_salary(salary: Any) -> Tuple[bool, float]:
    try:
        value = float(str(salary).replace(",", "").strip())
        return True, value
    except Exception as e:
        logger.warning(f"Salary validation failed: {e}")
        return False, 0.0

def format_employee_data(data: Dict) -> str:
    return f"""
**Name**: {data.get('name', '-')}
**Phone**: {data.get('phone', '-')}
**Designation**: {data.get('designation', '-')}
**Salary**: ₹{data.get('salary', '-')}
    """

def call_google_llm(prompt: str) -> str:
    headers = {"Content-Type": "application/json"}
    payload = {
        "prompt": {"text": prompt},
        "temperature": 0.2,
        "topK": 40,
        "topP": 0.95,
        "candidateCount": 1
    }
    response = requests.post(
        f"{GOOGLE_API_URL}?key={GOOGLE_API_KEY}",
        headers=headers,
        data=json.dumps(payload)
    )
    response.raise_for_status()
    candidates = response.json().get("candidates", [])
    return candidates[0]["output"] if candidates else ""

def extract_entities_from_text(text: str) -> List[Dict[str, Any]]:
    prompt = (
        "Extract structured employee data as a list of JSON objects with the following keys: "
        "name, phone, designation, salary. Only include valid, complete entries.\n\n"
        f"Input Text:\n{text}\n"
        "Output (JSON List):"
    )
    llm_output = call_google_llm(prompt)
    try:
        data = json.loads(llm_output)
        if isinstance(data, list):
            return data
    except Exception as e:
        logger.warning(f"LLM output parsing failed: {e}")
    return []

def process_uploaded_file(file) -> Tuple[bool, pd.DataFrame, List[str]]:
    try:
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)

        text_blob = df.astype(str).apply(lambda row: ", ".join(row.values), axis=1).str.cat(sep="\n")
        extracted = extract_entities_from_text(text_blob)
        if not extracted:
            return False, pd.DataFrame(), ["LLM extraction failed or returned no valid entries."]

        clean_data = []
        errors = []
        for i, entry in enumerate(extracted):
            name = sanitize_input(entry.get("name", ""))
            phone = str(entry.get("phone", "")).strip()
            designation = sanitize_input(entry.get("designation", ""))
            salary = entry.get("salary", "")

            if not name or not designation:
                errors.append(f"Entry {i+1}: Missing name/designation")
                continue

            if not validate_phone_number(phone):
                errors.append(f"Entry {i+1}: Invalid phone number")

            valid_salary, salary_value = validate_salary(salary)
            if not valid_salary:
                errors.append(f"Entry {i+1}: Invalid salary")

            clean_data.append({
                "name": name,
                "phone": phone,
                "designation": designation,
                "salary": salary_value
            })

        df_clean = pd.DataFrame(clean_data)
        return (len(errors) == 0, df_clean, errors)

    except Exception as e:
        logger.error(f"File processing failed: {e}")
        return False, pd.DataFrame(), [str(e)]

def sanitize_input(text: str) -> str:
    return re.sub(r"[^\w\s\-]", "", text).strip()