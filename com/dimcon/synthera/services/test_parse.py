from com.dimcon.synthera.services.json_service import JsonService

# Define your test JSON payload
sample_event = {
    "meeting_id": "CHIME12345",
    "answers": {
        "Q1": "What is the timeline?",
        "A1": "6 months",
        "Q3": "What is the budget?",
        "A3": "$500,000"
    }
}

# Run the function and print the result
try:
    result = JsonService.parse_event(sample_event)
    print("✅ Parsed Result:")
    print(result)
except Exception as e:
    print("❌ Error occurred:")
    print(e)
