import pytest
import os
import pandas as pd
from .. import SurveyResponder, load_questions, load_persona_file, generate_persona_from_file
from unittest.mock import patch

def test_surveyresponder_initialization(sample_questions_file, sample_persona_file):
    """Test SurveyResponder initialization with default parameters."""
    responder = SurveyResponder(
        questions_path=sample_questions_file,
        persona_path=sample_persona_file
    )
    assert isinstance(responder, SurveyResponder)     # Verify object instantiation
    assert len(responder.questions) == 3              # Verify expected question count from fixture
    assert isinstance(responder.persona_dict, dict)   # Verify dictionary structure from fixture
    assert len(responder.scales) == 2                 # Verify scales loaded from fixture

def test_response_options_removed(sample_questions_file, sample_persona_file, custom_response_options):
    """Test that passing response_options raises an informative migration error."""
    with pytest.raises(ValueError, match="scales"):   # Verify error directs users to scales
        SurveyResponder(
            questions_path=sample_questions_file,
            persona_path=sample_persona_file,
            response_options=custom_response_options
        )

def test_load_questions(sample_questions_file):
    """Test loading scales and questions from a JSON survey file."""
    scales, questions = load_questions(sample_questions_file)
    assert len(questions) == 3                         # Verify expected question count
    assert all(isinstance(q, dict) for q in questions)
    assert questions[0]["id"] == "exercise_often"      # Verify question id from fixture
    assert questions[0]["scale"] in scales             # Verify scale reference resolves
    assert questions[2]["reverse_coded"] is True       # Verify reverse coding flag from fixture

def test_load_persona_file(sample_persona_file):
    """Test loading persona file."""
    persona_dict = load_persona_file(sample_persona_file)
    assert isinstance(persona_dict, dict)              # Verify dictionary structure from fixture
    assert "age" in persona_dict                       # Verify presence of 'age' attribute
    assert "education" in persona_dict                 # Verify presence of 'education' attribute
    assert "occupation" in persona_dict                # Verify presence of 'occupation' attribute
    assert len(persona_dict["age"]) == 2               # Verify 'age' attribute value length

def test_generate_persona(sample_persona_file):
    """Test persona generation."""
    persona_dict = load_persona_file(sample_persona_file)
    traits, descriptions = generate_persona_from_file(persona_dict)
    
    assert isinstance(traits, dict)                   # Verify persona trait structure
    assert isinstance(descriptions, list)             # Verify persona description format
    assert len(traits) == len(persona_dict)           # Verify all traits were processed
    assert all(isinstance(d, str) for d in descriptions)  # Verify description string format

def test_example_prompt(sample_questions_file, sample_persona_file):
    """Test example prompt generation."""
    responder = SurveyResponder(
        questions_path=sample_questions_file,
        persona_path=sample_persona_file
    )
    prompt = responder.example_prompt()
    assert isinstance(prompt, str)                    # Verify prompt is a string
    assert "I exercise regularly." in prompt          # Verify prompt contains question text
    assert "How often" in prompt                      # Verify scale preface included
    assert all(
        opt in prompt.lower()
        for opt in responder.scales["freq5"]["options"])  # Verify response options included

def test_example_persona(sample_questions_file, sample_persona_file):
    """Test example persona generation."""
    responder = SurveyResponder(
        questions_path=sample_questions_file,
        persona_path=sample_persona_file
    )
    # Test single persona
    single_persona = responder.example_persona()
    assert isinstance(single_persona, str)            # Veryfiy persona is string
    
    # Test multiple personas
    multi_personas = responder.example_persona(npersonas=3)
    assert isinstance(multi_personas, list)           # Verify persona is a list
    assert len(multi_personas) == 3                   # Verify leng from fixture
    assert all(
        isinstance(p, str) for p in multi_personas)   # Veryfiy items in list are str

def test_get_settings(sample_questions_file, sample_persona_file):
    """Test getting settings."""
    responder = SurveyResponder(
        questions_path=sample_questions_file,
        persona_path=sample_persona_file
    )
    settings = responder.get_settings()
    assert isinstance(settings, dict)
    assert settings["questions_path"] == sample_questions_file
    assert settings["persona_path"] == sample_persona_file
    assert settings["num_questions"] == 3

def test_run_with_mock_ollama(sample_questions_file, sample_persona_file, mock_ollama_response, ollama_available):
    """Test running the responder with mocked Ollama responses."""
    responder = SurveyResponder(
        questions_path=sample_questions_file,
        persona_path=sample_persona_file,
        num_responses=2
    )
    df = responder.run()
    assert isinstance(df, pd.DataFrame)               # Verify DataFrame is returned
    assert len(df) == 2                               # Verify expected number of responses
    assert "resid" in df.columns                      # Verify response id column exists
    assert "model" in df.columns                      # Verify model name column exists
    assert "exercise_often" in df.columns             # Verify question id columns exist
    assert "enjoy_reading" in df.columns              # Verify question id columns exist
    assert "handle_stress" in df.columns              # Verify question id columns exist

def test_run_write_with_mock_ollama(sample_questions_file, sample_persona_file, mock_ollama_response, ollama_available, tmp_path):
    """Test running the responder and writing results to file."""
    output_file = os.path.join(tmp_path, "test_responses.csv")
    responder = SurveyResponder(
        questions_path=sample_questions_file,
        persona_path=sample_persona_file,
        num_responses=2
    )
    df = responder.run_write(output_file)
    
    assert isinstance(df, pd.DataFrame)              # Verify DataFrame is returned
    assert len(df) == 2                              # Verify expected number of responses
    
    assert os.path.exists(output_file)               # Verify output files were created
    assert os.path.exists(output_file.replace(".csv", "_params.json"))
    
    df_loaded = pd.read_csv(output_file)
    assert len(df_loaded) == 2                       # Verify CSV contains expected rows
    assert all(qid in df_loaded.columns              # Verify all question id columns exist
               for qid in ["exercise_often", "enjoy_reading", "handle_stress"])

def test_error_handling_invalid_files():
    """Test error handling for invalid files."""
    with pytest.raises(FileNotFoundError):            # Verify proper error handling
        SurveyResponder(
            questions_path="nonexistent_questions.json",
            persona_path="nonexistent_persona.json"
        )

def test_legacy_text_questions_rejected(tmp_path, sample_persona_file):
    """Test that legacy plain-text questions files raise an informative error."""
    legacy_file = tmp_path / "questions.txt"
    legacy_file.write_text("I enjoy being a student.\nI enjoy learning new things.\n")
    with pytest.raises(ValueError, match="JSON"):     # Verify error mentions the JSON format
        SurveyResponder(
            questions_path=str(legacy_file),
            persona_path=sample_persona_file
        )

def test_persona_consistency_across_questions(sample_questions_file, sample_persona_file, mock_ollama_response):
    """Test that the same persona is used for all questions within a single response row."""
    from unittest.mock import patch

    responder = SurveyResponder(
        questions_path=sample_questions_file,
        persona_path=sample_persona_file,
        num_responses=1
    )

    # Track persona_descriptions passed to _generate_prompt for each call
    persona_descriptions_per_call = []

    def capture_generate_prompt(question, persona_descriptions):
        persona_descriptions_per_call.append(persona_descriptions)
        # Return a minimal prompt so the test runs
        return f"Persona: {', '.join(persona_descriptions)}\nQuestion: {question['text']}"

    with patch.object(responder, '_generate_prompt', side_effect=capture_generate_prompt):
        df = responder.run(verbosity=0)

    # _generate_prompt is called twice per question (process_question + get_response)
    # Verify that all captured persona_descriptions are identical across all calls
    assert len(persona_descriptions_per_call) > 0
    first_persona = persona_descriptions_per_call[0]
    for persona in persona_descriptions_per_call[1:]:
        assert persona == first_persona, "Persona descriptions should be identical across all questions"
