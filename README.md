# Employee Onboarding Assistant

An intelligent employee onboarding chatbot built with Streamlit, LangGraph, and Google Gemini AI.

## Features

- **Conversational Interface**: Chat-based employee onboarding process
- **Multiple Input Methods**: Manual entry or Excel file upload
- **AI-Powered Data Extraction**: Uses Google Gemini to extract employee data from text
- **Data Validation**: Validates phone numbers and salary formats
- **Interactive Data Review**: Edit and review employee data before saving
- **Persistent Storage**: Saves employee data to CSV file
- **Workflow Management**: Stateful conversations using LangGraph

## Requirements

- Python 3.8+
- Streamlit
- LangGraph
- LangChain Google GenAI
- Pandas
- Google Gemini API Key

## Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install streamlit langgraph langchain-google-genai pandas python-dotenv openpyxl
   ```
3. Set up your Google API key in the `.env` file:
   ```
   GOOGLE_API_KEY=your_actual_api_key_here
   ```

## Usage

1. Run the Streamlit app:
   ```bash
   streamlit run main.py
   ```
2. Open your browser to the displayed URL
3. Type "Onboard" to start the employee onboarding process
4. Follow the prompts to either:
   - Upload an Excel file with employee data
   - Manually enter employee details
5. Review and edit the data as needed
6. Save the employee data to the database

## File Structure

- `main.py` - Main Streamlit application
- `graph_flow.py` - LangGraph workflow definition
- `utils.py` - Utility functions for data processing and AI model setup
- `db.py` - Database operations (CSV file handling)
- `.env` - Environment variables (API keys)
- `onboarding_database.csv` - Employee data storage (created automatically)

## Excel File Format

When uploading Excel files, ensure they contain columns with employee information such as:
- Name
- Phone
- Designation/Job Title
- Salary

The AI will automatically extract and structure this data.

## Features in Detail

### Conversational Flow
- Start with general chat capabilities
- Switch to onboarding mode with "Onboard" command
- Guided step-by-step employee data collection
- Contextual prompts and validation

### Data Processing
- Excel file parsing and data extraction
- AI-powered text-to-structured-data conversion
- Phone number validation
- Salary formatting and validation
- Data sanitization

### User Interface
- Clean, modern Streamlit interface
- Interactive data tables for review and editing
- Progress indicators for file processing
- Error handling and user feedback

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open source and available under the MIT License.
