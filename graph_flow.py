from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from db import save_to_db

# --- State Definition ---
class OnboardingState(TypedDict):
    """
    Represents the state of our onboarding workflow.
    """
    history: List[Dict[str, Any]]
    onboarding_data: List[Dict[str, Any]]
    current_manual_entry: Dict[str, Any]
    manual_entry_field: str

# --- Graph Node Functions (No changes needed here) ---

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
    state['history'].append({
        "role": "assistant",
        "content": "File processed. Here is the extracted data. Please review it carefully."
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
    current_field = state['manual_entry_field']
    user_input = state['history'][-1]['content']
    
    state['current_manual_entry'][current_field] = user_input
    
    current_index = fields_order.index(current_field)
    if current_index + 1 < len(fields_order):
        next_field = fields_order[current_index + 1]
        state['manual_entry_field'] = next_field
        state['history'].append({
            "role": "assistant",
            "content": f"Great. Now, what is their {next_field.replace('_', ' ')}?"
        })
    else:
        state['onboarding_data'].append(state['current_manual_entry'])
        state['manual_entry_field'] = None # Signal completion
        state['current_manual_entry'] = {}
        state['history'].append({
            "role": "assistant",
            "content": "All details for one employee have been collected."
        })
    return state

def validate_data(state: OnboardingState):
    """Node to show collected data and ask for user validation."""
    state['history'].append({
        "role": "assistant",
        "content": "Please review the collected data. Do you want to proceed with saving, modify the data, or add another employee manually?",
        "type": "dataframe",
        "data": state['onboarding_data']
    })
    state['history'].append({
        "role": "assistant",
        "content": "",
        "type": "choice",
        "options": ["Proceed to Save", "Modify Data", "Add Another Manually"]
    })
    return state
    
def save_data(state: OnboardingState):
    """Node to save the final data to the database."""
    result_message = save_to_db(state['onboarding_data'])
    state['history'].append({
        "role": "assistant",
        "content": f"{result_message}\nThe onboarding process is complete. You are now back in standard chat mode."
    })
    return state

# --- NEW: Conditional Entry Point Router ---
def route_entry_point(state: OnboardingState):
    """
    Routes the workflow based on the last user message to the correct starting node.
    This is the main dispatcher for the graph.
    """
    last_message = state['history'][-1]['content'].lower()

    if "start onboarding" in last_message:
        return "start_onboarding"
    if "upload" in last_message:
        return "process_upload"
    if "enter manually" in last_message:
        # If we are just starting manual entry
        if not state.get('manual_entry_field'):
            return "start_manual_entry"
    if "add another manually" in last_message:
        return "start_manual_entry"
    if "proceed" in last_message or "modify" in last_message:
        return "validate_data"
    
    # If none of the above, it's likely data for a manual field
    if state.get('manual_entry_field'):
        return "process_manual_entry"
    
    # Fallback to the beginning
    return "start_onboarding"

# --- REFACTORED: Workflow Definition ---
def create_onboarding_workflow():
    """Creates and compiles the LangGraph workflow with a robust, event-driven structure."""
    workflow = StateGraph(OnboardingState)

    # Add all nodes
    workflow.add_node("start_onboarding", start_onboarding)
    workflow.add_node("process_upload", process_upload)
    workflow.add_node("start_manual_entry", start_manual_entry)
    workflow.add_node("process_manual_entry", process_manual_entry)
    workflow.add_node("validate_data", validate_data)
    workflow.add_node("save_data", save_data)

    # Set the conditional entry point
    workflow.set_conditional_entry_point(
        route_entry_point,
        {
            "start_onboarding": "start_onboarding",
            "process_upload": "process_upload",
            "start_manual_entry": "start_manual_entry",
            "process_manual_entry": "process_manual_entry",
            "validate_data": "validate_data",
        }
    )

    # Define the explicit flow of the graph
    # KEY FIX: Nodes that require user input now go to END, pausing the graph.
    workflow.add_edge("start_onboarding", END)
    workflow.add_edge("start_manual_entry", END)
    workflow.add_edge("validate_data", END)
    workflow.add_edge("save_data", END)

    # After processing a file, always go to validation
    workflow.add_edge("process_upload", "validate_data")

    # After processing a manual field, decide whether to ask for the next field or validate
    workflow.add_conditional_edges(
        "process_manual_entry",
        lambda s: "validate_data" if s.get('manual_entry_field') is None else "process_manual_entry",
        {
            "process_manual_entry": END, # Ask the next question and wait
            "validate_data": "validate_data" # All fields collected, go to validation
        }
    )

    # Compile and return the graph
    return workflow.compile()