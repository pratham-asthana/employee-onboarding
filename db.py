import os
import pandas as pd

DB_FILE = os.path.join(os.path.dirname(__file__), "onboarding_database.csv")

def save_to_db(employee_data_list):
    """
    Saves a list of employee data dictionaries to a CSV file.
    Appends data if the file already exists.
    """
    if not employee_data_list:
        return "No data to save."

    df = pd.DataFrame(employee_data_list)
    try:
        # Check if file exists to determine if we need to write headers
        file_exists = os.path.exists(DB_FILE)
        # Append to the CSV file without writing the index
        df.to_csv(DB_FILE, mode='a', header=not file_exists, index=False)
        return f"Successfully saved {len(employee_data_list)} employee(s) to {DB_FILE}."
    except Exception as e:
        return f"Error saving to database: {e}"

def read_from_db():
    """
    Reads all employee data from the CSV file.
    Returns a list of dictionaries.
    """
    if not os.path.exists(DB_FILE):
        return []
    try:
        df = pd.read_csv(DB_FILE)
        return df.to_dict(orient="records")
    except Exception as e:
        return f"Error reading from database: {e}"