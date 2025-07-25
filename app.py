# Directory: employee_onboarding_app/
# File: app.py
import pandas as pd
import streamlit as st
import os
from dotenv import load_dotenv
from datetime import datetime
from database import EmployeeDatabase
from utils import (
    process_uploaded_file,
    sanitize_input,
    format_employee_data,
)
from workflow import build_workflow
import logging

# Load env vars
load_dotenv()
DB_PATH = os.getenv("DATABASE_PATH", "employees.db")
db = EmployeeDatabase(DB_PATH)
db.create_table()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlit App Config
st.set_page_config(page_title="Employee Onboarding App", layout="wide")
st.title("🌟 Employee Onboarding Assistant")

# Session State Initialization
if "messages" not in st.session_state:
    st.session_state.messages = []

if "workflow" not in st.session_state:
    st.session_state.workflow = build_workflow()

# Sidebar Navigation
mode = st.sidebar.radio("Choose Mode", ["Chat", "Upload", "Employees"])

if mode == "Chat":
    st.subheader("Conversational Onboarding")
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).markdown(msg["content"])

    if prompt := st.chat_input("Ask anything or start onboarding..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.spinner("Thinking..."):
            try:
                result = st.session_state.workflow.invoke({"input": prompt})
                reply = result.get("response", "Sorry, something went wrong.")
                st.session_state.messages.append({"role": "assistant", "content": reply})
                st.chat_message("assistant").markdown(reply)
            except Exception as e:
                logger.error(f"Workflow Error: {e}")
                st.error("An error occurred while processing your message.")

elif mode == "Upload":
    st.subheader("Upload Employee Data")
    uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xls", "xlsx"])
    if uploaded_file:
        with st.spinner("Processing file..."):
            valid, df, errors = process_uploaded_file(uploaded_file)
            if valid:
                st.success("File processed successfully!")
                st.dataframe(df)
                if st.button("Add to Database"):
                    success_count = 0
                    for _, row in df.iterrows():
                        data = row.to_dict()
                        ok = db.add_employee(data)
                        success_count += int(ok)
                    st.success(f"{success_count} employees added to database!")
            else:
                st.error("File processing failed:")
                for e in errors:
                    st.warning(e)

elif mode == "Employees":
    st.subheader("Employee Directory")
    employees = db.get_all_employees()
    if employees:
        df = pd.DataFrame(employees)
        st.dataframe(df)
    else:
        st.info("No employees found in the database.")

# Footer
st.markdown("---")
st.markdown("Made with ♥ by HR Tech Team")
