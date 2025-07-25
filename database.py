# Directory: employee_onboarding_app/
# File: database.py

import sqlite3
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmployeeDatabase:
    def __init__(self, db_path: str = "employees.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.create_table()

    def create_table(self):
        try:
            query = """
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                designation TEXT NOT NULL,
                salary REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            self.conn.execute(query)
            self.conn.commit()
            logger.info("Employee table ensured.")
        except Exception as e:
            logger.error(f"Failed to create table: {e}")

    def add_employee(self, employee_data: Dict) -> bool:
        try:
            query = """
                INSERT INTO employees (name, phone, designation, salary)
                VALUES (?, ?, ?, ?)
            """
            self.conn.execute(
                query,
                (
                    employee_data["name"],
                    employee_data["phone"],
                    employee_data["designation"],
                    employee_data["salary"],
                ),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to insert employee: {e}")
            return False

    def get_all_employees(self) -> List[Dict]:
        try:
            cursor = self.conn.execute("SELECT * FROM employees")
            columns = [description[0] for description in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return results
        except Exception as e:
            logger.error(f"Failed to fetch employees: {e}")
            return []

    def validate_employee_data(self, data: Dict) -> Tuple[bool, List[str]]:
        errors = []
        if not data.get("name"):
            errors.append("Missing name")
        if not data.get("phone") or len(data["phone"]) < 10:
            errors.append("Invalid or missing phone")
        if not data.get("designation"):
            errors.append("Missing designation")
        if "salary" not in data or not isinstance(data["salary"], (int, float)):
            errors.append("Invalid salary")
        return (len(errors) == 0, errors)

    def close(self):
        self.conn.close()
