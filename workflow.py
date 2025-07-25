# Directory: employee_onboarding_app/
# File: workflow.py

from langgraph.graph import StateGraph
from typing import TypedDict, Annotated, Dict, Any
from langgraph.graph.message import add_messages
import google.generativeai as genai
import os
from dotenv import load_dotenv
from utils import (
    validate_phone_number,
    validate_salary,
    sanitize_input,
    format_employee_data,
)
from database import EmployeeDatabase
import logging

# Load environment and configure logging
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
db = EmployeeDatabase(os.getenv("DATABASE_PATH", "employees.db"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# State Definition
class EmployeeOnboardingState(TypedDict):
    input: str
    context: Dict[str, Any]
    response: str

# LangGraph Node Implementations
def general_chat_node(state: EmployeeOnboardingState) -> EmployeeOnboardingState:
    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(state["input"])
        return {**state, "response": response.text, "context": state.get("context", {})}
    except Exception as e:
        logger.error(f"General Chat Error: {e}")
        return {**state, "response": "Error: Unable to process your message."}

def mode_detection_node(state: EmployeeOnboardingState) -> EmployeeOnboardingState:
    msg = state["input"].lower()
    if any(x in msg for x in ["onboard", "add employee", "new joiner"]):
        state["context"]["mode"] = "onboarding"
    else:
        state["context"]["mode"] = "chat"
    return state

def onboarding_entry_node(state: EmployeeOnboardingState) -> EmployeeOnboardingState:
    return {
        **state,
        "response": "Welcome to the Employee Onboarding Assistant! Would you like to upload a file or enter details manually?",
    }

def method_selection_node(state: EmployeeOnboardingState) -> EmployeeOnboardingState:
    input_msg = state["input"].lower()
    if "file" in input_msg:
        state["context"]["method"] = "file"
    elif "manual" in input_msg:
        state["context"]["method"] = "manual"
    else:
        state["response"] = "Please specify 'file upload' or 'manual entry'."
    return state

def file_processing_node(state: EmployeeOnboardingState) -> EmployeeOnboardingState:
    return {**state, "response": "Please upload the employee data file from the Upload tab."}

def manual_collection_node(state: EmployeeOnboardingState) -> EmployeeOnboardingState:
    ctx = state["context"]
    msg = state["input"]

    if "name" not in ctx:
        ctx["name"] = sanitize_input(msg)
        return {**state, "response": "Got it. What's their phone number?"}

    if "phone" not in ctx:
        if validate_phone_number(msg):
            ctx["phone"] = msg
            return {**state, "response": "Great. What is their designation?"}
        else:
            return {**state, "response": "Invalid phone number. Please re-enter."}

    if "designation" not in ctx:
        ctx["designation"] = sanitize_input(msg)
        return {**state, "response": "Noted. What's the salary?"}

    if "salary" not in ctx:
        valid, salary = validate_salary(msg)
        if valid:
            ctx["salary"] = salary
            return {**state, "response": "Review complete. Shall I save this entry? (yes/no)"}
        else:
            return {**state, "response": "Invalid salary. Please provide a numeric value."}

    if "confirm" not in ctx:
        if "yes" in msg.lower():
            ctx["confirm"] = True
        else:
            ctx["confirm"] = False
        return state

    return state

def validation_node(state: EmployeeOnboardingState) -> EmployeeOnboardingState:
    ctx = state["context"]
    if ctx.get("confirm"):
        valid, errors = db.validate_employee_data(ctx)
        if valid:
            return {**state, "response": "All data looks good. Saving to database..."}
        else:
            return {**state, "response": f"Validation failed: {', '.join(errors)}"}
    return {**state, "response": "Entry discarded. Start again if needed."}

def database_storage_node(state: EmployeeOnboardingState) -> EmployeeOnboardingState:
    ctx = state["context"]
    if ctx.get("confirm"):
        ok = db.add_employee(ctx)
        if ok:
            return {**state, "response": "Employee successfully saved!"}
        else:
            return {**state, "response": "Database error: Could not save employee."}
    return state

def completion_node(state: EmployeeOnboardingState) -> EmployeeOnboardingState:
    return {
        **state,
        "response": "Onboarding complete. You can onboard another employee or ask a question."
    }

# Workflow Definition
def build_workflow():
    graph = StateGraph(EmployeeOnboardingState)

    graph.add_node("general_chat", general_chat_node)
    graph.add_node("mode_detect", mode_detection_node)
    graph.add_node("onboarding_entry", onboarding_entry_node)
    graph.add_node("method_select", method_selection_node)
    graph.add_node("file_processing", file_processing_node)
    graph.add_node("manual_collection", manual_collection_node)
    graph.add_node("validation", validation_node)
    graph.add_node("db_store", database_storage_node)
    graph.add_node("completion", completion_node)

    graph.set_entry_point("mode_detect")

    graph.add_edge("mode_detect", "general_chat")
    graph.add_conditional_edges("general_chat", lambda s: {
        "onboarding_entry": s.get("context", {}).get("mode") == "onboarding",
        "general_chat": s.get("context", {}).get("mode") != "onboarding",
    })

    graph.add_edge("onboarding_entry", "method_select")
    graph.add_conditional_edges("method_select", lambda s: {
        "file_processing": s.get("context", {}).get("method") == "file",
        "manual_collection": s.get("context", {}).get("method") == "manual",
    })

    graph.add_edge("file_processing", "completion")
    graph.add_edge("manual_collection", "validation")
    graph.add_edge("validation", "db_store")
    graph.add_edge("db_store", "completion")

    return graph.compile()