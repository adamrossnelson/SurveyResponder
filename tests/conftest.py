import pytest
import os
import json
import tempfile
import requests
import warnings

@pytest.fixture
def sample_questions_file():
    """Create a temporary questions file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Question 1: How often do you exercise?\n")
        f.write("Question 2: Do you enjoy reading?\n")
        f.write("Question 3: How well do you handle stress?\n")
    yield f.name
    os.unlink(f.name)

@pytest.fixture
def sample_persona_file():
    """Create a temporary persona file for testing."""
    persona_data = {
        "age": [[25, "is 25 years old"], [35, "is 35 years old"]],
        "education": [
            ["bachelor", "has a bachelor's degree"],
            ["master", "has a master's degree"]
        ],
        "occupation": [
            ["engineer", "works as an engineer"],
            ["teacher", "works as a teacher"]
        ]
    }
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(persona_data, f)
    yield f.name
    os.unlink(f.name)

@pytest.fixture
def custom_response_options():
    """Return custom response options for testing."""
    return ["Never", "Rarely", "Sometimes", "Often", "Always"]

@pytest.fixture(scope="session")
def ollama_available():
    """Check if Ollama is available at http://localhost:11434."""
    try:
        response = requests.get("http://localhost:11434/api/version")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        warnings.warn("\nOllama is not running at http://localhost:11434. Some tests will use mock responses.\n"
                     "To use actual Ollama responses:\n"
                     "1. Install Ollama from https://ollama.com\n"
                     "2. Start the Ollama service\n"
                     "3. Pull a model using: ollama pull llama2")
        return False

@pytest.fixture
def mock_ollama_response(monkeypatch):
    """Mock the Ollama API response."""
    class MockResponse:
        def __init__(self, *args, **kwargs):
            pass
        
        def json(self):
            return {"response": "agree"}
        
        def raise_for_status(self):
            pass
    
    def mock_post(*args, **kwargs):
        return MockResponse()
    
    import requests
    monkeypatch.setattr(requests, "post", mock_post)
