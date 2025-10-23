import sys

def main():
    print("Welcome to the AI Agent Call Center CLI Demo!")
    print("1. Start a call")
    print("2. Process a call (simulate audio)")
    print("3. End a call")
    print("4. Exit")
    session_id = None
    while True:
        choice = input("Select an option: ")
        if choice == "1":
            session_id = "session_001"
            print(f"Call started. Session ID: {session_id}")
        elif choice == "2":
            if not session_id:
                print("Start a call first!")
                continue
            text = input("Simulate audio (type text): ")
            if "order" in text:
                print("AI: Sure, I can help you with your order. Can you provide your order ID?")
            elif "working hours" in text:
                print("AI: Our working hours are 9am to 5pm, Monday to Friday.")
            elif "hello" in text:
                print("AI: Hello! How can I assist you today?")
            else:
                print("AI: I'm sorry, I didn't understand that. Could you please rephrase?")
        elif choice == "3":
            if session_id:
                print(f"Call ended for session {session_id}.")
                session_id = None
            else:
                print("No active call.")
        elif choice == "4":
            print("Exiting.")
            sys.exit(0)
        else:
            print("Invalid option.")

if __name__ == "__main__":
    main()
