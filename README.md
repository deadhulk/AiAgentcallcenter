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

## System Flow Overview

The AI Call Center Agent system automates customer service calls using a modular, event-driven architecture. Here’s the end-to-end flow:

1. **Call Initiation**
   - A customer call is received (via SIP/LiveKit or API).
   - `/api/call/start` endpoint is called, creating a new session and returning a session ID.
   - The system initializes metrics and registers the call in the active session store.

2. **Speech Recognition & Processing**
   - Audio from the customer is streamed or uploaded to `/api/call/process`.
   - The system uses the configured Speech-to-Text (STT) adapter (e.g., Google, AWS, Whisper, or mock) to transcribe the audio.
   - Transcribed text is logged and added to the conversation history.

3. **AI Response Generation**
   - The transcribed text is sent to the selected LLM (OpenAI, AWS, or mock) for intent detection and response generation.
   - The AI-generated response is logged and appended to the conversation history.

4. **Text-to-Speech (TTS) Synthesis**
   - The AI response is converted to speech using the configured TTS adapter (gTTS, OpenAI, AWS Polly, or mock).
   - The resulting audio is returned to the caller or sent to the SIP/LiveKit bridge for playback.

5. **Event Emission & Webhooks**
   - All major call events (created, answered, ended, etc.) are mapped to internal event schemas.
   - Events are dispatched to registered workflow endpoints (e.g., n8n, Zapier) via webhooks for further automation.
   - CRM integration is triggered for call logging and analytics.

6. **Call Termination**
   - `/api/call/end` endpoint is called to end the session.
   - Final call data (duration, transcript, etc.) is logged to the CRM.
   - Metrics are updated and the session is cleaned up.

7. **Monitoring & Observability**
   - Prometheus metrics are tracked for all major operations (active calls, queue size, errors, durations).
   - OpenTelemetry spans are created for distributed tracing.
   - Logs are structured and can be shipped to observability platforms.

---

**Key Components:**
- `src/ops/orchestration.py`: Orchestrates event flow, webhook dispatch, and CRM integration.
- `src/agent/call_handler.py`: Manages the main call loop and conversation state.
- `src/agent/speech_recognition.py` & `src/agent/tts_engine.py`: Handle STT and TTS operations.
- `src/api/routes.py`: Exposes FastAPI endpoints for call control and processing.
- `src/ops/monitoring.py`: Handles metrics, tracing, and logging.

**Extensibility:**
- Easily add new adapters for STT, TTS, or LLM by implementing the adapter interface and updating the factory methods.
- Register new workflow endpoints for automation via the orchestration API.

---

For a detailed code-level flow, see the docstrings in `src/ops/orchestration.py` and the test suite in `tests/`.
