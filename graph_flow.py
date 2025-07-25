from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from db import save_to_db

# Define the state structure for our graph
class OnboardingState(TypedDict):
    """
    Represents the state of our onboarding workflow.
    
    Attributes:
        history: The conversation history.
        onboarding_data: A list of dictionaries, each holding one employee's data.
        current_manual_entry: A dictionary to build up a single employee's data manually.
        manual_entry_field: The current field we are asking for in manual entry mode.
        error_message: Any error message to be displayed to the user.
    """
    history: List[Dict[str, Any]]
    onboarding_data: List[Dict[str, Any]]
    current_manual_entry: Dict[str, Any]
    manual_entry_field: str
    error_message: str

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
    # The actual file processing and extraction happens in the Streamlit UI.
    # This node just confirms the data received and moves to validation.
    state['history'].append({
        "role": "assistant",
        "content": "File processed. Here is the extracted data. Please review it carefully."
    })
    return state # Go directly to validation after processing

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
        # All fields collected
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

# --- Conditional Edge Logic ---

def route_initial_choice(state: OnboardingState):
    """Router to decide the path after the initial user choice."""
    last_message = state['history'][-1]['content'].lower()
    if "upload" in last_message:
        return "process_upload"
    elif "manually" in last_message:
        return "start_manual_entry"
    else:
        # If input is unclear, perhaps ask again or handle error
        state['error_message'] = "Invalid choice. Please choose 'Upload' or 'Manually'."
        return "start_onboarding" # Loop back

def route_after_manual_entry(state: OnboardingState):
    """Router to decide if manual entry continues or moves to validation."""
    if state['manual_entry_field'] is None:
        return "validate_data"
    else:
        return "process_manual_entry"

def route_after_validation(state: OnboardingState):
    """Router to handle user's choice after reviewing the data."""
    last_message = state['history'][-1]['content'].lower()
    if "proceed" in last_message:
        return "save_data"
    elif "modify" in last_message:
        # The Streamlit UI will handle the modification logic.
        # We just need to signal a loop back to validation.
        return "validate_data"
    elif "add another" in last_message:
        return "start_manual_entry"
    else:
        return "validate_data" # Loop back on invalid input


# --- Workflow Definition ---

def create_onboarding_workflow():
    """Creates and compiles the LangGraph workflow."""
    workflow = StateGraph(OnboardingState)

    # Add nodes
    workflow.add_node("start_onboarding", start_onboarding)
    workflow.add_node("process_upload", process_upload)
    workflow.add_node("start_manual_entry", start_manual_entry)
    workflow.add_node("process_manual_entry", process_manual_entry)
    workflow.add_node("validate_data", validate_data)
    workflow.add_node("save_data", save_data)

    # Set entry point
    workflow.set_entry_point("start_onboarding")

    # Add conditional edges
    workflow.add_conditional_edges(
        "start_onboarding",
        route_initial_choice,
        {"process_upload": "validate_data", "start_manual_entry": "process_manual_entry"}
    )
    workflow.add_conditional_edges(
        "process_manual_entry",
        route_after_manual_entry,
        {"validate_data": "validate_data", "process_manual_entry": "process_manual_entry"}
    )
    workflow.add_conditional_edges(
        "validate_data",
        route_after_validation,
        {
            "save_data": "save_data",
            "validate_data": "validate_data",
            "start_manual_entry": "start_manual_entry"
        }
    )

    # End flow after saving
    workflow.add_edge("save_data", END)

    # Compile and return the graph
    return workflow.compile()