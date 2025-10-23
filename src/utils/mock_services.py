# Dummy telephony and AI service mocks for functional testing

def mock_telephony_service():
    return "Telephony service called (mocked)"

def mock_ai_service(input_text):
    if "order" in input_text.lower():
        return "Sure, I can help you with your order. Can you provide your order ID?"
    if "working hours" in input_text.lower():
        return "Our working hours are 9am to 5pm, Monday to Friday."
    return "I'm sorry, I didn't understand that. Could you please rephrase?"
