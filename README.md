# AI Call Center Agent

An intelligent call center agent system that automates customer service interactions using AI, speech recognition, and natural language processing.

## Overview

This project implements an automated call center system that uses artificial intelligence to handle customer service calls. It provides a scalable, 24/7 solution for customer support by understanding customer queries and providing appropriate responses in real-time.

## Features

- 🤖 AI-Powered Conversation Handling
- 🎤 Real-time Speech Recognition
- 🔊 Text-to-Speech Response Generation
- 📝 Session Management for Multiple Calls
- 🔄 Real-time Call Processing
- 📊 Call Logging and Analytics
- 🔌 LiveKit Integration for Real-time Communication

## Technical Stack

- **Backend Framework**: FastAPI (Python)
- **Database**: SQLite
- **Containerization**: Docker & Docker Compose
- **Speech Processing**: 
  - Speech Recognition Engine
  - Text-to-Speech Engine
- **Real-time Communication**: LiveKit
- **Testing**: pytest for unit and integration tests

## API Endpoints

### Call Management

- **POST** `/api/call/start`
  - Initiates a new customer service call
  - Returns a session ID for the call

- **POST** `/api/call/process`
  - Processes ongoing call interactions
  - Handles speech-to-text conversion
  - Generates AI responses
  - Converts responses to speech

- **POST** `/api/call/end`
  - Terminates the call session
  - Logs call details

## Project Structure

```
├── main.py                 # FastAPI application entry point
├── pytest.ini             # pytest configuration
├── requirements.txt       # Python dependencies
├── src/
│   ├── agent/            # AI agent implementation
│   │   ├── call_handler.py
│   │   ├── speech_recognition.py
│   │   └── tts_engine.py
│   ├── api/              # API implementation
│   │   ├── models.py
│   │   └── routes.py
│   ├── database/         # Database models and operations
│   │   └── models.py
│   └── utils/            # Utility functions
│       └── helpers.py
├── tests/                # Test suite
│   ├── test_api.py
│   ├── test_call_handler.py
│   ├── test_database.py
│   ├── test_helpers.py
│   ├── test_speech_recognition.py
│   └── test_tts_engine.py
└── livekit-agent/       # LiveKit integration
```

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose
- LiveKit server (for production)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/deadhulk/AiAgentcallcenter.git
cd AiAgentcallcenter
```

2. Build and start the containers:
```bash
docker-compose up --build
```

3. Access the API documentation:
   - Open http://localhost:8000/docs in your browser
   - Interactive API documentation will be available

### Configuration

Create a `.env` file with the following variables:
```
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
AI_MODEL_API_KEY=your_ai_model_key
```

## Testing

Run the test suite:
```bash
python -m pytest
```

The project includes:
- Unit tests for individual components
- Integration tests for API endpoints
- End-to-end test scenarios
- Mock data for testing

## Development

1. Set up a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate   # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the development server:
```bash
uvicorn main:app --reload
```

## Features Status

✅ Database seeding with dummy data
✅ Mock AI responses for testing
✅ Sample audio/text for tests
✅ Integration tests
✅ External service mocking
✅ Simple UI/CLI for testing
🚧 End-to-end testing (In Progress)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request
