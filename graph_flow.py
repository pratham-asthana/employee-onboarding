from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from db import save_to_db, read_from_db

# --- State Definition ---
class OnboardingState(TypedDict):
    """
    Represents the state of our onboarding workflow.
    """
    history: List[Dict[str, Any]]
    onboarding_data: List[Dict[str, Any]]
    current_manual_entry: Dict[str, Any]
    manual_entry_field: str

# --- Graph Node Functions ---

def start_onboarding(state: OnboardingState):
    """Node to begin the onboarding flow."""
    state['history'].append({
        "role": "assistant",
        "content": "Welcome to the employee onboarding flow! How would you like to provide employee details?",
        "type": "choice",
        "options": ["Upload Excel File", "Enter Manually"]
    })
    return state

def process_upload(state: OnboardingState):
    """Node to confirm file upload and show extracted data."""
    if state.get('onboarding_data'):
        state['history'].append({
            "role": "assistant",
            "content": "File processed successfully! Here is the extracted data. Please review it carefully.",
            "type": "dataframe",
            "data": state['onboarding_data']
        })
    else:
        state['history'].append({
            "role": "assistant",
            "content": "Please upload an Excel file with employee data to continue."
        })
    return state

def start_manual_entry(state: OnboardingState):
    """Node to start the manual data entry process."""
    state['manual_entry_field'] = "name"
    state['current_manual_entry'] = {}
    state['history'].append({
        "role": "assistant",
        "content": "Let's add an employee manually. What is the employee's full name?"
    })
    return state

def process_manual_entry(state: OnboardingState):
    """Node to handle each step of the manual entry process."""
    fields_order = ["name", "phone", "designation", "salary"]
    current_field = state.get('manual_entry_field', "name")
    user_input = state['history'][-1]['content'] if state['history'] else ""
    
    # Store the current field value
    state['current_manual_entry'][current_field] = user_input
    
    # Move to next field
    try:
        current_index = fields_order.index(current_field)
        if current_index + 1 < len(fields_order):
            next_field = fields_order[current_index + 1]
            state['manual_entry_field'] = next_field
            
            # Create appropriate prompt for next field
            field_prompts = {
                "phone": "Great! Now, what is their phone number?",
                "designation": "Perfect! What is their job designation/title?",
                "salary": "Excellent! What is their salary (annual amount)?"
            }
            
            state['history'].append({
                "role": "assistant",
                "content": field_prompts.get(next_field, f"Now, what is their {next_field}?")
            })
        else:
            # All fields collected, add to onboarding data
            state['onboarding_data'].append(state['current_manual_entry'].copy())
            state['manual_entry_field'] = ""  # Signal completion
            state['current_manual_entry'] = {}
            state['history'].append({
                "role": "assistant",
                "content": "All details collected! You can review the data below and choose your next action.",
                "type": "dataframe",
                "data": state['onboarding_data']
            })
            state['history'].append({
                "role": "assistant",
                "content": "What would you like to do next?",
                "type": "choice",
                "options": ["Save Data", "Add Another Employee", "Modify Data"]
            })
    except ValueError:
        # Field not found in order, restart
        state['manual_entry_field'] = "name"
        state['current_manual_entry'] = {}
        state['history'].append({
            "role": "assistant",
            "content": "Let's start over. What is the employee's full name?"
        })
    
    return state

def validate_data(state: OnboardingState):
    """Node to show collected data and ask for user validation."""
    if state.get('onboarding_data'):
        state['history'].append({
            "role": "assistant",
            "content": "Please review the collected employee data below:",
            "type": "dataframe",
            "data": state['onboarding_data']
        })
        state['history'].append({
            "role": "assistant",
            "content": "What would you like to do?",
            "type": "choice",
            "options": ["Save Data", "Add Another Employee", "Modify Data", "Clear All Data"]
        })
    else:
        state['history'].append({
            "role": "assistant",
            "content": "No employee data found. Would you like to add an employee?",
            "type": "choice",
            "options": ["Enter Manually", "Upload Excel File"]
        })
    return state
    
def save_data(state: OnboardingState):
    """Node to save the final data to the database."""
    if state.get('onboarding_data'):
        result_message = save_to_db(state['onboarding_data'])
        state['history'].append({
            "role": "assistant",
            "content": f"{result_message}\n\nThe onboarding process is complete! You are now back in standard chat mode."
        })
        # Clear the onboarding data after saving
        state['onboarding_data'] = []
    else:
        state['history'].append({
            "role": "assistant",
            "content": "No data to save. The onboarding process is complete."
        })
    return state

def clear_data(state: OnboardingState):
    """Node to clear all collected data."""
    state['onboarding_data'] = []
    state['current_manual_entry'] = {}
    state['manual_entry_field'] = ""
    state['history'].append({
        "role": "assistant",
        "content": "All data cleared. What would you like to do next?",
        "type": "choice",
        "options": ["Enter Manually", "Upload Excel File"]
    })
    return state

# --- Routing Functions ---
def route_entry_point(state: OnboardingState):
    """
    Routes the workflow based on the last user message to the correct starting node.
    """
    if not state.get('history'):
        return "start_onboarding"
    
    last_message = state['history'][-1]['content'].lower()

    # Handle specific user choices
    if "start onboarding" in last_message:
        return "start_onboarding"
    elif "upload excel file" in last_message:
        return "process_upload"
    elif "enter manually" in last_message:
        return "start_manual_entry"
    elif "add another employee" in last_message:
        return "start_manual_entry"
    elif "save data" in last_message:
        return "save_data"
    elif "modify data" in last_message or "review" in last_message:
        return "validate_data"
    elif "clear all data" in last_message:
        return "clear_data"
    elif "file uploaded and processed" in last_message:
        return "validate_data"
    
    # If we're in the middle of manual entry
    if state.get('manual_entry_field') and state['manual_entry_field'] != "":
        return "process_manual_entry"
    
    # Default fallback
    return "start_onboarding"

def route_after_manual_entry(state: OnboardingState):
    """Routes after manual entry is complete."""
    if state.get('manual_entry_field') == "":
        return "validate_data"
    else:
        return END

# --- Workflow Definition ---
def create_onboarding_workflow():
    """Creates and compiles the LangGraph workflow."""
    workflow = StateGraph(OnboardingState)

    # Add all nodes
    workflow.add_node("start_onboarding", start_onboarding)
    workflow.add_node("process_upload", process_upload)
    workflow.add_node("start_manual_entry", start_manual_entry)
    workflow.add_node("process_manual_entry", process_manual_entry)
    workflow.add_node("validate_data", validate_data)
    workflow.add_node("save_data", save_data)
    workflow.add_node("clear_data", clear_data)

    # Set the conditional entry point
    workflow.set_conditional_entry_point(
        route_entry_point,
        {
            "start_onboarding": "start_onboarding",
            "process_upload": "process_upload",
            "start_manual_entry": "start_manual_entry",
            "process_manual_entry": "process_manual_entry",
            "validate_data": "validate_data",
            "save_data": "save_data",
            "clear_data": "clear_data",
        }
    )

    # Define the flow edges
    workflow.add_edge("start_onboarding", END)
    workflow.add_edge("start_manual_entry", END)
    workflow.add_edge("validate_data", END)
    workflow.add_edge("save_data", END)
    workflow.add_edge("clear_data", END)
    workflow.add_edge("process_upload", "validate_data")

    # Conditional edge for manual entry
    workflow.add_conditional_edges(
        "process_manual_entry",
        route_after_manual_entry,
        {
            "validate_data": "validate_data",
            END: END
        }
    )

    # Compile and return the graph
    return workflow.compile()
