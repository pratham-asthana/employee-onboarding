import os
import re
import json
import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI

def get_gemini_model():
    """Initializes and returns the Gemini Pro model."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set.")
    return ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2)

def parse_excel_file(uploaded_file):
    """Parses an uploaded Excel file and returns a list of dictionaries."""
    try:
        df = pd.read_excel(uploaded_file)
        # Convert all data to string to handle various data types smoothly
        df = df.astype(str)
        return df.to_dict('records')
    except Exception as e:
        print(f"Error parsing Excel file: {e}")
        return None

def extract_employee_data_from_text(text_chunk, model):
    """
    Uses Gemini to extract structured employee data from a text chunk.
    It includes retry logic for JSON parsing.
    """
    prompt = f"""
    From the following text, extract the employee's information.
    The text might contain data like name, phone number, designation, and salary.
    Please extract these four fields. The phone number should be a valid number. Salary should be a number.
    
    Respond ONLY with a single, valid JSON object with the keys: "name", "phone", "designation", "salary".
    If a value is not found, use an empty string "" for that key.

    Text: "{text_chunk}"
    
    JSON Response:
    """
    for _ in range(3): # Retry up to 3 times
        try:
            response = model.invoke(prompt)
            # Clean the response to get only the JSON part
            json_str = response.content.strip().replace("```json", "").replace("```", "")
            data = json.loads(json_str)
            
            # Basic validation
            if all(k in data for k in ["name", "phone", "designation", "salary"]):
                return data
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Attempt failed to parse JSON: {e}. Retrying...")
            continue # Retry the loop
            
    # Return a default error structure if all retries fail
    return {
        "name": "Extraction Error",
        "phone": "N/A",
        "designation": "N/A",
        "salary": 0
    }


def validate_phone_number(phone):
    """A simple regex to validate a phone number."""
    if not isinstance(phone, str):
        return False
    # This regex is lenient: allows digits, spaces, dashes, parentheses, and an optional '+'
    pattern = re.compile(r'^\+?[\d\s\-\(\)]{7,15}$')
    return bool(pattern.match(phone))

def format_salary(salary):
    """Ensures salary is a float, returns 0.0 on failure."""
    try:
        return float(salary)
    except (ValueError, TypeError):
        return 0.0