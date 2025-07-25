import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from utils import get_gemini_model, parse_excel_file, extract_employee_data_from_text, validate_phone_number, format_salary
from graph_flow import create_onboarding_workflow

# --- Page Configuration ---
st.set_page_config(
    page_title="Intelligent Onboarding Assistant",
    page_icon="🤖",
    layout="wide"
)

# --- Load Environment Variables ---
load_dotenv()

# --- Initialization ---
def initialize_app():
    """Initialize session state variables for the application."""
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "chatbot"  # "chatbot" or "onboarding"
    
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Hi! I'm your assistant. Type 'Onboard' to start the employee onboarding process."}]
        
    if "onboarding_workflow" not in st.session_state:
        st.session_state.onboarding_workflow = create_onboarding_workflow()

    if "onboarding_state" not in st.session_state:
        st.session_state.onboarding_state = None
    
    # Initialize Gemini model if API key is present
    try:
        st.session_state.gemini_model = get_gemini_model()
    except ValueError as e:
        st.error(str(e))
        st.stop()

# --- UI Rendering Functions ---
def display_chat_history():
    """Displays the chat history, handling special UI elements from the graph."""
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            # Handle special UI elements defined in the graph state
            if msg.get("type") == "choice":
                cols = st.columns(len(msg["options"]))
                for i, option in enumerate(msg["options"]):
                    if cols[i].button(option, key=f"choice_{option}_{i}"):
                        handle_user_input(option)
            
            if msg.get("type") == "dataframe":
                df = pd.DataFrame(msg["data"])
                edited_df = st.data_editor(df, num_rows="dynamic", key="data_editor")
                st.session_state.onboarding_state['onboarding_data'] = edited_df.to_dict('records')

# --- Main Application Logic ---
def handle_user_input(prompt: str):
    """Main function to process user input based on the current app mode."""
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Mode Switching
    if prompt.strip().lower() == "onboard" and st.session_state.app_mode == "chatbot":
        st.session_state.app_mode = "onboarding"
        # Initialize and invoke the onboarding workflow
        initial_state = {
            "history": [{"role": "user", "content": "Start Onboarding"}],
            "onboarding_data": [],
            "current_manual_entry": {},
            "manual_entry_field": "",
            "error_message": ""
        }
        st.session_state.onboarding_state = st.session_state.onboarding_workflow.invoke(initial_state)
        st.session_state.messages.extend(st.session_state.onboarding_state['history'][1:]) # Add bot responses
        st.rerun()

    # Onboarding Flow Logic
    elif st.session_state.app_mode == "onboarding":
        st.session_state.onboarding_state['history'].append({"role": "user", "content": prompt})
        
        # Invoke the graph with the updated state
        response_state = st.session_state.onboarding_workflow.invoke(st.session_state.onboarding_state)
        
        # Check if the flow has ended
        if response_state is None:
            # The END node was reached
            final_bot_message = st.session_state.onboarding_state['history'][-1]
            st.session_state.messages.append(final_bot_message)
            # Reset to chatbot mode
            st.session_state.app_mode = "chatbot"
            st.session_state.onboarding_state = None
        else:
            st.session_state.onboarding_state = response_state
            # Append only new messages from the bot
            new_messages = st.session_state.onboarding_state['history'][len(st.session_state.messages):]
            st.session_state.messages.extend(new_messages)
        st.rerun()

    # Standard Chatbot Logic
    else:
        with st.spinner("Thinking..."):
            response = st.session_state.gemini_model.invoke(prompt)
            st.session_state.messages.append({"role": "assistant", "content": response.content})
        st.rerun()

# --- Main App Execution ---
st.title("✨ Intelligent Employee Onboarding Chatbot")
st.markdown("A Streamlit app using **LangGraph** for stateful conversations and **Gemini** for intelligence.")
st.markdown("---")

# Set GOOGLE_API_KEY from .env or sidebar
api_key = os.getenv("GOOGLE_API_KEY") or st.sidebar.text_input("Enter your Google API Key:", type="password")
if not api_key:
    st.info("Please provide your Google API Key in the sidebar or a .env file to proceed.")
    st.stop()
os.environ["GOOGLE_API_KEY"] = api_key

initialize_app()

# --- File Uploader Logic ---
# This widget is placed outside the main chat flow to be accessible when needed.
last_bot_message = st.session_state.messages[-1]["content"] if st.session_state.messages else ""
if st.session_state.app_mode == "onboarding" and "upload excel file" in last_bot_message.lower():
    uploaded_file = st.file_uploader("Upload an Excel file with employee data", type=["xlsx", "xls"])
    if uploaded_file is not None:
        with st.spinner("Processing your file... This may take a moment."):
            raw_data = parse_excel_file(uploaded_file)
            if raw_data:
                extracted_data = []
                # Use a progress bar for large files
                progress_bar = st.progress(0, text="Extracting employee data...")
                for i, row in enumerate(raw_data):
                    text_chunk = ", ".join([f"{k}: {v}" for k, v in row.items()])
                    extracted_row = extract_employee_data_from_text(text_chunk, st.session_state.gemini_model)
                    
                    # Validate and format data
                    extracted_row['phone'] = extracted_row.get('phone', 'N/A')
                    if not validate_phone_number(extracted_row['phone']):
                       extracted_row['phone'] = f"INVALID - {extracted_row['phone']}"
                    extracted_row['salary'] = format_salary(extracted_row.get('salary', 0))

                    extracted_data.append(extracted_row)
                    progress_bar.progress((i + 1) / len(raw_data), text=f"Extracting employee data... ({i+1}/{len(raw_data)})")
                
                # Update the graph state and re-invoke
                st.session_state.onboarding_state['onboarding_data'] = extracted_data
                handle_user_input("File Uploaded and Processed")
            else:
                st.error("Could not parse the Excel file. Please check the format and try again.")

# Display chat messages and UI elements
display_chat_history()

# Chat input is the primary way to interact, except for button clicks
if prompt := st.chat_input("Your message..."):
    handle_user_input(prompt)