"""
SurveyResponder
Processes survey questions using a local Ollama LLM and returns Likert-scale responses.
"""
import os
from typing import List, Tuple, Dict, Optional, Union
import requests
from random import choice
import uuid
import json
import pandas as pd
import warnings
from tqdm import tqdm
import argparse
import sys

def load_persona_file(file_path: str) -> Dict:
    """Load persona definitions from a JSON file.
    
    Args:
        file_path (str): Path to the persona JSON file
        
    Returns:
        Dict: Dictionary containing persona traits
    """
    with open(file_path, 'r') as f:
        return json.load(f)

def generate_persona_from_file(persona_dict: Dict) -> Tuple[Dict, List[str]]:
    """Generate a random persona from a dictionary loaded from JSON.
    
    Args:
        persona_dict (Dict): Dictionary containing persona traits
        
    Returns:
        Tuple[Dict, List[str]]: 
            - Dictionary mapping trait categories to selected trait values
            - List of persona trait descriptions for prompting
    """
    persona_traits = {}
    persona_descriptions = []

    for category, options in persona_dict.items():
        selected = choice(options)
        persona_traits[category] = selected[0]
        persona_descriptions.append(selected[1])

    return persona_traits, persona_descriptions

def load_questions(file_path: str) -> Tuple[Dict, List[Dict]]:
    """Load named response scales and questions from a JSON survey file.

    The file must contain a JSON object with two top-level keys:
    - 'scales': a dictionary mapping scale names to scale definitions. Each
      scale definition has a 'preface' (str) and 'options' (dict mapping
      response labels to numeric codes).
    - 'questions': a list of question objects. Each question has an 'id'
      (used as the output column heading), 'text', a 'scale' name reference,
      and an optional 'reverse_coded' flag (defaults to False).

    Args:
        file_path (str): Path to the questions JSON file

    Returns:
        Tuple[Dict, List[Dict]]: The scales dictionary and the list of questions

    Raises:
        ValueError: If the file is not valid JSON or does not match the
            expected structure.
    """
    with open(file_path, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Could not parse '{file_path}' as JSON ({e}). Questions are now "
                "specified as a JSON file with a 'scales' library and a 'questions' "
                "list (see questions.json for an example). Plain-text questions "
                "files are no longer supported."
            )

    if isinstance(data, list):
        raise ValueError(
            f"'{file_path}' contains a JSON list. The questions file must be a JSON "
            "object with 'scales' and 'questions' keys (see questions.json for an example)."
        )
    if not isinstance(data, dict) or "scales" not in data or "questions" not in data:
        raise ValueError(
            f"'{file_path}' must be a JSON object with 'scales' and 'questions' keys "
            "(see questions.json for an example)."
        )

    scales = data["scales"]
    questions = data["questions"]

    for name, scale in scales.items():
        if "preface" not in scale or "options" not in scale or not scale["options"]:
            raise ValueError(
                f"Scale '{name}' must define a 'preface' and a non-empty 'options' "
                "dictionary mapping response labels to numeric codes."
            )

    seen_ids = set()
    for question in questions:
        for key in ("id", "text", "scale"):
            if key not in question:
                raise ValueError(f"Question {question} is missing required key '{key}'.")
        if question["id"] in seen_ids:
            raise ValueError(f"Duplicate question id '{question['id']}'. Question ids must be unique.")
        seen_ids.add(question["id"])
        if question["scale"] not in scales:
            raise ValueError(
                f"Question '{question['id']}' references undefined scale '{question['scale']}'. "
                f"Defined scales: {list(scales.keys())}"
            )
        question.setdefault("reverse_coded", False)

    return scales, questions

class SurveyResponder:
    def __init__(self,
                 questions_path: str = "questions.json",
                 persona_path: str = "persona.json",
                 model_name: str = "llama3.1:latest",
                 response_options: Optional[List[str]] = None,
                 num_responses: int = 10,
                 temperature: float = 1.0,
                 base_url: str = "http://localhost:11434/api/generate",
                 max_try: int = 2):
        """Initialize the SurveyResponder with specified paths and parameters.
        
        Args:
            questions_path (str): Path to the questions JSON file containing
                'scales' and 'questions'. Defaults to "questions.json".
            persona_path (str): Path to the persona JSON file. Defaults to "persona.json".
            model_name (str): Name of the Ollama model to use. Defaults to "llama3.1:latest".
            response_options: Removed; must be None. Response options are now
                defined as named scales in the questions JSON file.
                If specified a deprecation message and ValueError will raise.
            num_responses (int): Number of responses to generate. Defaults to 10.
            temperature (float): Temperature setting for LLM response generation. Defaults to 1.0.
            base_url (str): URL for the Ollama API. Defaults to "http://localhost:11434/api/generate".
            max_try (int): Maximum number of consecutive errors before early termination.
        """
        if response_options is not None:
            raise ValueError(
                "The response_options parameter has been removed. Response options "
                "are now defined as named scales in the questions JSON file passed "
                f"to questions_path ('{questions_path}'). Each question references "
                "a scale by name (see questions.json for an example)."
            )

        self.questions_path = questions_path
        self.persona_path = persona_path
        self.model_name = model_name
        self.base_url = base_url
        self.num_responses = num_responses
        self.temperature = temperature
        self.max_try = max_try

        # Load scales, questions, and persona dictionary
        self.scales, self.questions = load_questions(questions_path)
        self.persona_dict = load_persona_file(persona_path)

        # Guard against output column collisions
        reserved = {"resid", "model"} | set(self.persona_dict.keys())
        clashes = [q["id"] for q in self.questions if q["id"] in reserved]
        if clashes:
            raise ValueError(
                f"Question ids collide with reserved or persona column names: {clashes}. "
                "Rename these ids in the questions JSON file."
            )

    def __str__(self) -> str:
        """Return a user-friendly string representation of the SurveyResponder."""
        return f"""SurveyResponder(model={self.model_name}, 
        {len(self.questions)} questions from {self.questions_path}, 
        personas at {self.persona_path}"""

    def __repr__(self) -> str:
        """Return a developer-friendly string representation of the SurveyResponder."""
        return (f"SurveyResponder(questions_path='{self.questions_path}', "
                f"persona_path='{self.persona_path}', model_name='{self.model_name}', "
                f"num_responses={self.num_responses}, temperature={self.temperature})")

    def __len__(self) -> int:
        """Return the number of questions in this SurveyResponder."""
        return len(self.questions)

    def __getitem__(self, index):
        """Allow indexing to access question dictionaries directly."""
        return self.questions[index]

    def __iter__(self):
        """Make SurveyResponder iterable over its question dictionaries."""
        return iter(self.questions)

    def _generate_prompt(self, question: Dict, persona_descriptions: List[str]) -> str:
        """Generate a prompt for the LLM that includes the question and available responses.
        
        The prompt preface and response options come from the scale the
        question references in the questions JSON file.
        
        Args:
            question (Dict): The survey question object with 'text' and 'scale' keys.
            persona_descriptions (List[str]): List of descriptions defining the responding persona.
            
        Returns:
            str: Formatted prompt for the LLM.
        """
        persona_description = "You are a someone " + ", ".join(persona_descriptions) + "."
        scale = self.scales[question["scale"]]
        option_labels = list(scale["options"].keys())
        return f"""{persona_description}

{scale["preface"]}
"{question["text"]}"

{', '.join(option_labels)}

Be sure to consider the full range of options including: 
'{option_labels[0]}' and '{option_labels[-1]}' and all items in between."""

    def example_prompt(self, question: Optional[Union[str, Dict]] = None) -> str:
        """Generate and return an example prompt using a random persona.
        
        This method is useful for previewing what prompts will be sent to the LLM.
        It generates a random persona and constructs a prompt using either the
        provided question or the first question from the loaded questions file.
        
        Args:
            question (Optional[Union[str, Dict]]): Custom question to use in the prompt.
                If None, uses the first question from the loaded file. If a string is
                provided, it is paired with the first scale defined in the questions
                file. If a dictionary is provided, it must include 'text' and 'scale' keys.
                                      
        Returns:
            str: The constructed prompt that would be sent to the LLM.
        """
        # Generate a random persona
        _, persona_descriptions = generate_persona_from_file(self.persona_dict)

        # Use the provided question or the first question from the loaded questions
        default_scale = next(iter(self.scales))
        if question is None:
            if len(self.questions) > 0:
                question = self.questions[0]
            else:
                question = {"text": "This is a placeholder question since no questions were loaded.",
                            "scale": default_scale}
        elif isinstance(question, str):
            question = {"text": question, "scale": default_scale}

        # Generate and return the prompt
        return self._generate_prompt(question, persona_descriptions)

    def example_persona(self, npersonas: int = 1) -> Union[str, List[str]]:
        """Generate and return example personas from the persona.json file as human-readable strings.
        
        This method is useful for previewing what kinds of personas will be used
        when generating survey responses.
        
        Args:
            npersonas (int): Number of personas to generate. Defaults to 1.
            
        Returns:
            Union[str, List[str]]: For a single persona, returns a string description.
                                    For multiple personas, returns a list of string descriptions.
        """
        results = []

        for _ in range(npersonas):
            # Generate a persona
            _, descriptions = generate_persona_from_file(self.persona_dict)

            # Format the description as a human-readable string
            description_text = "You are a someone " + ", ".join(descriptions) + "."

            # Add to results
            results.append(description_text)

        # If only one persona was requested, return just that persona instead of a list
        if npersonas == 1:
            return results[0]

        return results

    def get_response(self, question: Dict, persona_descriptions: List[str]) -> str:
        """Get a response for a single question.
        
        Args:
            question (Dict): The survey question object with 'text' and 'scale' keys.
            persona_descriptions (List[str]): List of descriptions defining the responding persona.
            
        Returns:
            str: The selected response.
        """
        prompt = self._generate_prompt(question, persona_descriptions)

        try:
            response = requests.post(
                self.base_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": self.temperature
                }
            )
            response.raise_for_status()
            result = response.json()
            return result['response'].strip()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise ConnectionError(
                    f"404 Error: Common reason is model ('{self.model_name}') not found. "
                    "This may mean the model name is not available. Try 'ollama pull <model_name>'"
                    "or 'ollama list' to check available models with 'ollama list'")
            raise ConnectionError(f"HTTP Error: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to connect to Ollama: {str(e)}")

    def _is_valid_response(self, response: str, question: Dict) -> bool:
        """Return True if the raw response is one of the scale's valid_responses.

        If the scale does not define `valid_responses`, this falls back to the
        set of option labels defined for the scale.
        """
        scale = self.scales[question["scale"]]
        valid = scale.get("valid_responses", list(scale["options"].keys()))
        cleaned = str(response).strip().lower()
        return cleaned in [str(v).strip().lower() for v in valid]

    def _recode_invalid_response(self, question: Dict, invalid_response: str) -> str:
        """Ask the LLM (acting as a research assistant) to recode an invalid response.

        Uses a low temperature and the same base_url as the primary responder to
        request a single valid numeric response.
        """
        scale = self.scales[question["scale"]]
        valid_responses = scale.get("valid_responses", list(scale["options"].keys()))
        valid_str = ", ".join(str(v) for v in valid_responses)
        option_labels = list(scale["options"].keys())
        prompt = (
            "You are a research assistant who specializes in manually recoding "
            "incorrectly entered survey responses.\n\n"
            f"A respondent was asked a survey question with the following valid responses:\n"
            f"{valid_str}.\n\n"
            f"The full option labels are: {', '.join(option_labels)}.\n\n"
            f"The respondent incorrectly entered:\n\"{invalid_response}\"\n\n"
            "Return the single most likely correctly valid response.\n"
            f"Respond with ONLY one of: {valid_str}."
        )
        try:
            response = requests.post(
                self.base_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.2
                }
            )
            response.raise_for_status()
            return response.json()["response"].strip()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to recode invalid response: {str(e)}")

    def _apply_reverse_code(self, response: str, question: Dict) -> Tuple[str, bool]:
        """Reverse-code a numeric response using the scale's option codes.

        Returns (new_response, applied). If the question is not reverse_coded or
        the response cannot be parsed as one of the scale's numeric codes, the
        response is returned unchanged with applied=False.
        """
        if not question.get("reverse_coded"):
            return response, False
        scale = self.scales[question["scale"]]
        codes = list(scale["options"].values())
        try:
            value = int(str(response).strip())
        except (ValueError, TypeError):
            return response, False
        if value not in codes:
            return response, False
        new_value = max(codes) + min(codes) - value
        return str(new_value), True

    def process_question(self,
                         question: Dict,
                         persona_traits: Dict,
                         persona_descriptions: List[str],
                         validate: bool = False,
                         on_invalid: str = "none",
                         max_retries: int = 2,
                         reverse_code: bool = False) -> Dict:
        """Process a single question and get a response.

        Args:
            question (Dict): The survey question object with 'text' and 'scale' keys.
            persona_traits (Dict): Dictionary of trait categories to selected values.
            persona_descriptions (List[str]): List of descriptions defining the persona.
            validate (bool): If True, validate the response against the scale's
                'valid_responses'. Defaults to False.
            on_invalid (str): Action when an invalid response is detected.
                One of 'none' (accept as-is), 'retry' (re-ask the original prompt
                up to max_retries times), or 'recode' (ask an LLM research
                assistant to recode the invalid response). Defaults to 'none'.
            max_retries (int): Maximum retry attempts when on_invalid='retry'.
                Defaults to 2.
            reverse_code (bool): If True, apply numeric reverse coding to
                questions whose 'reverse_coded' flag is True. Defaults to False.

        Returns:
            Dict: Dictionary containing question, prompt, response (final),
                original_response, validated, action_taken, reverse_coded_applied,
                and persona metadata.

        Raises:
            Exception: If there is an error processing the question or getting a response.
        """
        prompt = self._generate_prompt(question, persona_descriptions)
        response = self.get_response(question, persona_descriptions)
        original_response = response

        validated = None
        action_taken = "not_checked"

        if validate:
            validated = self._is_valid_response(response, question)
            if validated:
                action_taken = "validated"
            else:
                if on_invalid == "retry":
                    action_taken = "invalid"
                    for _ in range(max_retries):
                        retry_response = self.get_response(question, persona_descriptions)
                        if self._is_valid_response(retry_response, question):
                            response = retry_response
                            validated = True
                            action_taken = "retry"
                            break
                elif on_invalid == "recode":
                    try:
                        recoded = self._recode_invalid_response(question, response)
                    except ConnectionError:
                        recoded = None
                    if recoded is not None and self._is_valid_response(recoded, question):
                        response = recoded
                        validated = True
                        action_taken = "recode"
                    else:
                        action_taken = "invalid"
                else:
                    action_taken = "invalid"

        reverse_applied = False
        if reverse_code:
            response, reverse_applied = self._apply_reverse_code(response, question)

        return {
            'question': question,
            'response': response,
            'original_response': original_response,
            'validated': validated,
            'action_taken': action_taken,
            'reverse_coded_applied': 1 if reverse_applied else 0,
            'prompt': prompt,
            'persona_traits': persona_traits,
            'persona_descriptions': persona_descriptions
        }

    def get_settings(self) -> Dict:
        """Get the current settings of the SurveyResponder instance.
        
        Returns:
            Dict: Dictionary containing all current settings and their values
        """
        return {
            "questions_path": self.questions_path,
            "persona_path": self.persona_path,
            "model_name": self.model_name,
            "base_url": self.base_url,
            "num_responses": self.num_responses,
            "temperature": self.temperature,
            "scales": self.scales,
            "num_questions": len(self.questions),
            "persona_traits": list(self.persona_dict.keys())
        }

    def _print_survey_overview(self) -> None:
        """Print each question with its preface and response options for previewing runs."""
        print(f"Survey: {len(self.questions)} questions from {self.questions_path}")
        print(f"Scales: {', '.join(self.scales.keys())}")
        for i, question in enumerate(self.questions, 1):
            scale = self.scales[question["scale"]]
            options = ", ".join(scale["options"].keys())
            reverse_note = "  (reverse-coded)" if question.get("reverse_coded") else ""
            print(f"\n{i}. [{question['id']}] ({question['scale']}){reverse_note}")
            print(f"   {scale['preface']}")
            print(f"   \"{question['text']}\"")
            print(f"   Options: {options}")
        print()

    def run(self,
            verbosity: int = 1,
            validate: bool = False,
            on_invalid: str = "none",
            max_retries: int = 2,
            reverse_code: bool = False) -> pd.DataFrame:
        """Generate synthetic survey responses and return as a DataFrame.
        
        If any errors occur during generation, warnings will be issued. Processing will stop
        if max_try consecutive errors are encountered. The DataFrame will include all
        successfully generated responses up to that point.

        A cell-by-cell response log is collected on `self.response_log` (one entry
        per respondent-question pair). Use `run_write()` to also persist this log
        to a `{output_file_base}_response_log.csv` file.

        Args:
            verbosity (int): 1 (default) prints each question with its preface and
                response options before generation begins. 0 suppresses that output.
            validate (bool): If True, validate each response against the scale's
                'valid_responses'. Defaults to False.
            on_invalid (str): Action when an invalid response is detected. One of
                'none' (accept as-is), 'retry' (re-ask the original prompt up to
                max_retries times), or 'recode' (ask an LLM research assistant to
                recode the invalid response). Defaults to 'none'.
            max_retries (int): Maximum retry attempts when on_invalid='retry'.
                Defaults to 2.
            reverse_code (bool): If True, apply numeric reverse coding to
                questions whose 'reverse_coded' flag is True. Defaults to False.

        Returns:
            pd.DataFrame: DataFrame containing all generated responses
            
        Raises:
            RuntimeError: If no valid responses could be generated
        """
        if verbosity >= 1:
            self._print_survey_overview()

        # Create header for the dataframe
        columns = ["resid", "model"] + list(self.persona_dict.keys()) + [q["id"] for q in self.questions]

        # Initialize empty lists to store the data
        data = []

        # Cell-by-cell response log
        self.response_log = []

        # Initialize error counter
        error_count = 0

        # Generate responses
        for n in tqdm(range(self.num_responses), desc="Generating responses", unit="response"):
            try:
                # Create a respondent ID
                resid = str(uuid.uuid4())

                # Create a persona for this respondent
                persona_traits, persona_descriptions = generate_persona_from_file(self.persona_dict)

                # Prepare the row with resid and persona traits
                row_data = [resid, self.model_name] + [str(persona_traits.get(key, "")) for key in self.persona_dict.keys()]

                # Process each question
                for question in self.questions:
                    try:
                        result = self.process_question(
                            question, persona_traits, persona_descriptions,
                            validate=validate,
                            on_invalid=on_invalid,
                            max_retries=max_retries,
                            reverse_code=reverse_code
                        )
                        row_data.append(result.get('response', 'ERROR'))
                        self.response_log.append({
                            "resid": resid,
                            "question_id": question["id"],
                            "scale": question["scale"],
                            "original_response": result.get("original_response"),
                            "final_response": result.get("response"),
                            "validated": result.get("validated"),
                            "action_taken": result.get("action_taken"),
                            "reverse_coded": result.get("reverse_coded_applied", 0),
                        })
                        error_count = 0
                    except Exception as e:
                        error_count += 1
                        warnings.warn(f"Error processing question '{question['text']}': {str(e)}")
                        row_data.append("ERROR")
                        self.response_log.append({
                            "resid": resid,
                            "question_id": question["id"],
                            "scale": question["scale"],
                            "original_response": "ERROR",
                            "final_response": "ERROR",
                            "validated": False,
                            "action_taken": "error",
                            "reverse_coded": 0,
                        })

                        if error_count >= self.max_try:
                            warnings.warn(
                                f"Stopping after {error_count} consecutive errors. "
                                f"Returning {len(data)} successful responses."
                            )
                            # Pad row_data with 'INCOMPLETE' if it's shorter than expected
                            if len(row_data) < len(columns):
                                row_data.extend(['INCOMPLETE'] * (len(columns) - len(row_data)))
                            # Add partial response if we have any answers
                            if any(x != "ERROR" for x in row_data):
                                data.append(row_data)
                            break

                if error_count < self.max_try:
                    data.append(row_data)
                else:
                    break

            except Exception as e:
                error_count += 1
                warnings.warn(f"Error generating response {n+1}: {str(e)}")
                if error_count >= self.max_try:
                    warnings.warn(
                        f"Stopping after {error_count} consecutive errors. "
                        f"Returning {len(data)} successful responses."
                    )
                    break

        if not data:
            raise RuntimeError(
                f"Failed to generate any valid responses after {error_count} consecutive errors. "
                "Check if Ollama is running and the model is available."
            )

        # Create DataFrame
        df = pd.DataFrame(data, columns=columns)
        return df

    def run_write(self,
                  output_file: str,
                  verbosity: int = 1,
                  validate: bool = False,
                  on_invalid: str = "none",
                  max_retries: int = 2,
                  reverse_code: bool = False) -> pd.DataFrame:
        """Generate synthetic survey responses, write to file as they're generated, and return as DataFrame.
        
        This method writes each response to the output file as soon as it's generated, ensuring
        that partial results are saved even if an error occurs during generation.
        Also writes a JSON file with the parameters used for this run for reproducibility
        and a cell-by-cell CSV response log named `{output_file_base}_response_log.csv`.
        If the output file already exists, an enumerated suffix will be added to prevent overwriting.
        Progress is displayed using a progress bar.
        
        Args:
            output_file (str): Path to the output CSV file
            verbosity (int): 1 (default) prints each question with its preface and
                response options before generation begins. 0 suppresses that output.
            validate (bool): If True, validate each response against the scale's
                'valid_responses'. Defaults to False.
            on_invalid (str): Action when an invalid response is detected. One of
                'none' (accept as-is), 'retry' (re-ask the original prompt up to
                max_retries times), or 'recode' (ask an LLM research assistant to
                recode the invalid response). Defaults to 'none'.
            max_retries (int): Maximum retry attempts when on_invalid='retry'.
                Defaults to 2.
            reverse_code (bool): If True, apply numeric reverse coding to
                questions whose 'reverse_coded' flag is True. Defaults to False.
            
        Returns:
            pd.DataFrame: DataFrame containing all generated responses
        """
        if verbosity >= 1:
            self._print_survey_overview()

        # Check if file exists and update filename with enumeration if needed
        import os
        import psutil
        import platform
        import sys
        import csv
        base_name, extension = os.path.splitext(output_file) if '.' in output_file else (output_file, '')
        counter = 1
        final_output_file = output_file

        while os.path.exists(final_output_file):
            final_output_file = f"{base_name}_{counter}{extension}"
            counter += 1

        output_file = final_output_file

        # Create header for the output file and dataframe
        columns = ["resid", "model"] + list(self.persona_dict.keys()) + [q["id"] for q in self.questions]

        # Initialize empty list to store the data for the returned DataFrame
        data = []

        # Cell-by-cell response log
        self.response_log = []

        # Write header to the output file
        with open(output_file, 'w') as f:
            f.write(",".join(columns) + "\n")

        # Prepare response log file
        base_output = output_file.rsplit('.', 1)[0] if '.' in output_file else output_file
        response_log_file = base_output + "_response_log.csv"
        log_columns = [
            "resid", "question_id", "scale",
            "original_response", "final_response",
            "validated", "action_taken", "reverse_coded"
        ]
        log_fh = open(response_log_file, 'w', newline='')
        log_writer = csv.DictWriter(log_fh, fieldnames=log_columns)
        log_writer.writeheader()

        # Save parameters to JSON file for reproducibility
        params_file = output_file.rsplit('.', 1)[0] + "_params.json" if '.' in output_file else output_file + "_params.json"

        # Computer stats (GB Ram)
        try:
            computer_memory = psutil.virtual_memory().total / 1024  / 1024 / 1024
        except:
            computer_memory = "ERROR"
        # Computer OS + Version
        try:
            computer_os = f'Operating System: {platform.system()} Version {platform.version()}'
        except:
            computer_os = "ERROR"
        # Computer Python Version
        try:
            computer_python = sys.version
        except:
            computer_python = "ERROR"

        # Build an example prompt (with a random persona) for each question
        example_prompts = {}
        for question in self.questions:
            _, persona_descriptions = generate_persona_from_file(self.persona_dict)
            example_prompts[question["id"]] = self._generate_prompt(question, persona_descriptions)

        # Collect parameters
        params = {
            "questions_path": self.questions_path,
            "persona_path": self.persona_path,
            "model_name": self.model_name,
            "base_url": self.base_url,
            "num_responses": self.num_responses,
            "temperature": self.temperature,
            "run_date": str(pd.Timestamp.now()),
            "num_questions": len(self.questions),
            "questions_json": {"scales": self.scales, "questions": self.questions},
            "persona_dictionary": self.persona_dict,
            "example_prompts": example_prompts,
            "validate": validate,
            "on_invalid": on_invalid,
            "max_retries": max_retries,
            "reverse_code": reverse_code,
            "response_log_file": response_log_file,
            "computer_memory":computer_memory,
            "computer_os":computer_os,
            "computer_python":computer_python
        }

        # Write parameters to JSON file
        with open(params_file, 'w') as f:
            json.dump(params, f, indent=2)

        # Initialize error counter
        error_count = 0

        # Generate responses
        for n in tqdm(range(self.num_responses), desc="Generating responses", unit="response"):
            try:
                # Create a respondent ID
                resid = str(uuid.uuid4())

                # Create a persona for this respondent
                persona_traits, persona_descriptions = generate_persona_from_file(self.persona_dict)

                # Prepare the row with resid and persona traits
                row_data = [resid, self.model_name] + [str(persona_traits.get(key, "")) for key in self.persona_dict.keys()]

                # Process each question
                for question in self.questions:
                    try:
                        result = self.process_question(
                            question, persona_traits, persona_descriptions,
                            validate=validate,
                            on_invalid=on_invalid,
                            max_retries=max_retries,
                            reverse_code=reverse_code
                        )
                        row_data.append(result.get('response', 'ERROR'))
                        log_row = {
                            "resid": resid,
                            "question_id": question["id"],
                            "scale": question["scale"],
                            "original_response": result.get("original_response"),
                            "final_response": result.get("response"),
                            "validated": result.get("validated"),
                            "action_taken": result.get("action_taken"),
                            "reverse_coded": result.get("reverse_coded_applied", 0),
                        }
                        self.response_log.append(log_row)
                        log_writer.writerow(log_row)
                        log_fh.flush()
                        error_count = 0
                    except Exception as e:
                        error_count += 1
                        warnings.warn(f"Error processing question '{question['text']}': {str(e)}")
                        row_data.append("ERROR")
                        log_row = {
                            "resid": resid,
                            "question_id": question["id"],
                            "scale": question["scale"],
                            "original_response": "ERROR",
                            "final_response": "ERROR",
                            "validated": False,
                            "action_taken": "error",
                            "reverse_coded": 0,
                        }
                        self.response_log.append(log_row)
                        log_writer.writerow(log_row)
                        log_fh.flush()

                        if error_count >= self.max_try:
                            warnings.warn(
                                f"Stopping after {error_count} consecutive errors. "
                                f"Returning {len(data)} successful responses."
                            )
                            # Pad row_data with 'INCOMPLETE' if it's shorter than expected
                            if len(row_data) < len(columns):
                                row_data.extend(['INCOMPLETE'] * (len(columns) - len(row_data)))
                            # Add partial response if we have any answers
                            if any(x != "ERROR" for x in row_data):
                                data.append(row_data)
                                with open(output_file, 'a') as f:
                                    f.write(",".join([str(x) for x in row_data]) + "\n")
                            break

                if error_count < self.max_try:
                    data.append(row_data)
                    with open(output_file, 'a') as f:
                        f.write(",".join([str(x) for x in row_data]) + "\n")
                else:
                    break

            except Exception as e:
                error_count += 1
                warnings.warn(f"Error generating response {n+1}: {str(e)}")
                if error_count >= self.max_try:
                    warnings.warn(
                        f"Stopping after {error_count} consecutive errors. "
                        f"Returning {len(data)} successful responses."
                    )
                    break

        log_fh.close()

        if not data:
            raise RuntimeError(
                f"Failed to generate any valid responses after {error_count} consecutive errors. "
                "Check if Ollama is running and the model is available."
            )

        # Create and return DataFrame from all successfully collected data
        df = pd.DataFrame(data, columns=columns)
        return df

if __name__ == "__main__":
    print("""
    SurveyResponder
    Survey responses using LLMs For researchers, developers, and 
    psychometricians testing, scoring, and metrics evaluation.

    🚀 What Is SurveyResponder?
    SurveyResponder is a Python package and CLI tool that uses 
    Large Language Models (LLMs), such as those accessed through 
    Ollama - ollama.com, to generate synthetic survey instrument
    responses. Use 'python cli.py --help' for a list of available 
    commands to run.

    More information here:
    https://github.com/adamrossnelson/SurveyResponder
     """)