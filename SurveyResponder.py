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

def cli() -> None:
    """Creates a CLI (command line interface) to provide an alternate, more customizable way of running the Responder

    Returns: None

    """
    # Instantiate a parser with arguments for questions, persona, questions, num responses, temperature, scale
    parser = argparse.ArgumentParser(description="SurveyResponder CLI")

    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run survey responder")

    run_parser.add_argument("--questions", default="questions.txt",
                            help="Path to questions text file (default: questions.txt)")
    run_parser.add_argument("--persona", default="persona.json",
                            help="Path to persona JSON file (default: persona.json)")
    run_parser.add_argument("--model", default="llama3.1:latest",
                            help="Ollama model to use. Model must be pulled locally. (default: llama3.1:latest)")
    run_parser.add_argument("--num-responses", type=int, default=10,
                            help="Number of responses to generate (default: 10)")
    run_parser.add_argument("--temperature", type=float, default=1.0,
                            help="LLM temperature (default: 1.0)")
    run_parser.add_argument("--response-options", default=None,
                            help="Comma-separated custom response options (default: 5-point Likert scale)")
    run_parser.add_argument("--output", default="results.csv",
                            help="CSV filepath to save results (default: results.csv)")

    # CLI commands for listing and modifying a file of questions
    q_parser = subparsers.add_parser("questions", help="List or update questions file (default: questions.txt)")

    # Ensures questions commands can only be run one at a time
    group = q_parser.add_mutually_exclusive_group(required=True)

    q_parser.add_argument("--file", default="questions.txt", help="Specify which questions file to manage (default: questions.txt)")
    group.add_argument("--list", action="store_true", help="List all questions")
    group.add_argument("--add", type=str, help="Add a new question")
    group.add_argument("--delete", type=int, help="Delete question by line number")

    args = parser.parse_args()

    # Run question CLI commands
    if args.command == "questions":
        file_path = args.file
        # Ensure file exists
        if not os.path.exists(file_path):
            # If adding, create the file
            if args.add:
                open(file_path, "a").close()
            else:
                print(f"Questions file not found: {file_path}", file=sys.stderr)
                sys.exit(1)

        if args.list:
            questions = load_questions(file_path)
            for i, question in enumerate(questions, 1):
                print(f"{i}. {question}")

        elif args.add:
            with open(file_path, "a") as f:
                f.write(args.add.strip() + "\n")
            print(f"Added question: {args.add.strip()}")

        elif args.delete:
            questions = load_questions(file_path)
            index = args.delete - 1
            if index < 0 or index >= len(questions):
                print(f"Invalid line number: {args.delete}", file=sys.stderr)
                sys.exit(1)
            removed = questions.pop(index)
            with open(file_path, "w") as f:
                for q in questions:
                    f.write(q + "\n")
            print(f"Deleted question: {removed}")

        else:
            print("No action specified. Use --list, --add, or --delete.", file=sys.stderr)
            sys.exit(1)
        return

    # Run main program commands
    elif args.command == "run":
        # Convert response options to default array (in form of ["Never", "Sometimes", "Always"])
        response_options = None
        if args.response_options:
            response_options = []
            split_options = args.response_options.split(",")
            for option in split_options:
                stripped = option.strip()
                if stripped:
                    response_options.append(stripped)
        # Validate args and instantiate a SurveyResponder
        try:
            # Check for the existence of starting files
            if not os.path.exists(args.questions):
                raise FileNotFoundError(f"Questions file not found: {args.questions}")

            if not os.path.exists(args.persona):
                raise FileNotFoundError(f"Persona file not found: {args.persona}")

            # Ensure the directory for the output file exists.
            output_dir = os.path.dirname(args.output)
            # If the path is just a filename in the current working directory, this is skipped.
            if output_dir and not os.path.exists(output_dir):
                raise FileNotFoundError(f"Output directory does not exist: {output_dir}")

            # Responses and Temperature validation
            if response_options is not None and len(response_options) <= 2:
                raise ValueError("You must provide at least 2 response options.")
            if not (0.0 <= args.temperature <= 2.0):
                raise ValueError("Temperature must be between 0.0 and 2.0")

            # Create SurveyResponder
            responder = SurveyResponder(
                questions_path=args.questions,
                persona_path=args.persona,
                model_name=args.model,
                response_options=response_options,
                num_responses=args.num_responses,
                temperature=args.temperature,
            )

        except FileNotFoundError as e:
            print(f"File Error: {e}", file=sys.stderr)
            sys.exit(1)
        except ValueError as e:
            print(f"Input Error: {e}", file=sys.stderr)
            sys.exit(1)
        except ConnectionError as e:
            print(f"Connection Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected Error: {e}", file=sys.stderr)
            sys.exit(1)

        responder.run_write(args.output)

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

def load_questions(file_path: str) -> List[str]:
    """Load questions from a text file.
    
    Args:
        file_path (str): Path to the questions text file
        
    Returns:
        List[str]: List of questions
    """
    with open(file_path, 'r') as f:
        return [line.strip() for line in f if line.strip()]

class SurveyResponder:
    def __init__(self,
                 questions_path: str = "questions.txt",
                 persona_path: str = "persona.json",
                 model_name: str = "llama3.1:latest",
                 response_options: Optional[List[str]] = None,
                 num_responses: int = 10,
                 temperature: float = 1.0,
                 base_url: str = "http://localhost:11434/api/generate",
                 max_try: int = 2):
        """Initialize the SurveyResponder with specified paths and parameters.
        
        Args:
            questions_path (str): Path to the questions text file. Defaults to "questions.txt".
            persona_path (str): Path to the persona JSON file. Defaults to "persona.json".
            model_name (str): Name of the Ollama model to use. Defaults to "llama3.1:latest".
            response_options (Optional[List[str]]): Custom response options. If None, uses default Likert scale.
            num_responses (int): Number of responses to generate. Defaults to 10.
            temperature (float): Temperature setting for LLM response generation. Defaults to 1.0.
            base_url (str): URL for the Ollama API. Defaults to "http://localhost:11434/api/generate".
            max_try (int): Maximum number of consecutive errors before early termination.
        """
        self.questions_path = questions_path
        self.persona_path = persona_path
        self.model_name = model_name
        self.base_url = base_url
        self.num_responses = num_responses
        self.temperature = temperature
        self.max_try = max_try

        # Load questions and persona dictionary
        self.questions = load_questions(questions_path)
        self.persona_dict = load_persona_file(persona_path)

        # Default 5-point Likert scale if no custom options provided
        self.response_options = response_options if response_options else [
            "strongly disagree",
            "disagree",
            "neutral",
            "agree",
            "strongly agree"
        ]

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
        """Allow indexing to access questions directly."""
        return self.questions[index]

    def __iter__(self):
        """Make SurveyResponder iterable over its questions."""
        return iter(self.questions)

    def _generate_prompt(self, question: str, persona_descriptions: List[str]) -> str:
        """Generate a prompt for the LLM that includes the question and available responses.
        
        Args:
            question (str): The survey question to be answered.
            persona_descriptions (List[str]): List of descriptions defining the responding persona.
            
        Returns:
            str: Formatted prompt for the LLM.
        """
        persona_description = "You are a someone " + ", ".join(persona_descriptions) + "."
        return f"""{persona_description}

Question: {question}
        
Please select ONE of the following responses that best matches your opinion:
{', '.join(self.response_options)}

Respond with ONLY one of the above options, nothing else.

Be sure to consider the  full range of options including: 
'{self.response_options[0]}' and '{self.response_options[-1]}' and all items in between."""

    def example_prompt(self, question: Optional[str] = None) -> str:
        """Generate and return an example prompt using a random persona.
        
        This method is useful for previewing what prompts will be sent to the LLM.
        It generates a random persona and constructs a prompt using either the
        provided question or the first question from the loaded questions file.
        
        Args:
            question (Optional[str]): Custom question to use in the prompt.
                                      If None, uses the first question from the loaded file.
                                      
        Returns:
            str: The constructed prompt that would be sent to the LLM.
        """
        # Generate a random persona
        _, persona_descriptions = generate_persona_from_file(self.persona_dict)

        # Use the provided question or the first question from the loaded questions
        if question is None:
            if len(self.questions) > 0:
                question = self.questions[0]
            else:
                question = "This is a placeholder question since no questions were loaded."

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

    def get_response(self, question: str, persona_descriptions: List[str]) -> str:
        """Get a response for a single question.
        
        Args:
            question (str): The survey question to be answered.
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

    def process_question(self, question: str, persona_traits: Dict, persona_descriptions: List[str]) -> Dict:
        """Process a single question and get a response.
        
        Args:
            question (str): The survey question to be answered.
            persona_traits (Dict): Dictionary of trait categories to selected values.
            persona_descriptions (List[str]): List of descriptions defining the persona.
            
        Returns:
            Dict: Dictionary containing 'question', 'response', and other metadata
            
        Raises:
            Exception: If there is an error processing the question or getting a response
        """
        prompt = self._generate_prompt(question, persona_descriptions)
        response = self.get_response(question, persona_descriptions)

        return {
            'question': question,
            'response': response,
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
            "response_options": self.response_options,
            "num_questions": len(self.questions),
            "persona_traits": list(self.persona_dict.keys())
        }

    def run(self) -> pd.DataFrame:
        """Generate synthetic survey responses and return as a DataFrame.
        
        If any errors occur during generation, warnings will be issued. Processing will stop
        if max_try consecutive errors are encountered. The DataFrame will include all
        successfully generated responses up to that point.
        
        Returns:
            pd.DataFrame: DataFrame containing all generated responses
            
        Raises:
            RuntimeError: If no valid responses could be generated
        """
        # Create header for the dataframe
        columns = ["resid", "model"] + list(self.persona_dict.keys()) + [f"Q{i+1}" for i in range(len(self.questions))]

        # Initialize empty lists to store the data
        data = []

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
                        result = self.process_question(question, persona_traits, persona_descriptions)
                        row_data.append(result.get('response', 'ERROR'))
                        error_count = 0
                    except Exception as e:
                        error_count += 1
                        warnings.warn(f"Error processing question '{question}': {str(e)}")
                        row_data.append("ERROR")

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

    def run_write(self, output_file: str) -> pd.DataFrame:
        """Generate synthetic survey responses, write to file as they're generated, and return as DataFrame.
        
        This method writes each response to the output file as soon as it's generated, ensuring
        that partial results are saved even if an error occurs during generation.
        Also writes a JSON file with the parameters used for this run for reproducibility.
        If the output file already exists, an enumerated suffix will be added to prevent overwriting.
        Progress is displayed using a progress bar.
        
        Args:
            output_file (str): Path to the output CSV file
            
        Returns:
            pd.DataFrame: DataFrame containing all generated responses
        """
        # Check if file exists and update filename with enumeration if needed
        import os
        import psutil
        import platform
        import sys
        base_name, extension = os.path.splitext(output_file) if '.' in output_file else (output_file, '')
        counter = 1
        final_output_file = output_file

        while os.path.exists(final_output_file):
            final_output_file = f"{base_name}_{counter}{extension}"
            counter += 1

        output_file = final_output_file

        # Create header for the output file and dataframe
        columns = ["resid", "model"] + list(self.persona_dict.keys()) + [f"Q{i+1}" for i in range(len(self.questions))]

        # Initialize empty list to store the data for the returned DataFrame
        data = []

        # Write header to the output file
        with open(output_file, 'w') as f:
            f.write(",".join(columns) + "\n")

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

        # Collect parameters
        params = {
            "questions_path": self.questions_path,
            "persona_path": self.persona_path,
            "model_name": self.model_name,
            "base_url": self.base_url,
            "num_responses": self.num_responses,
            "temperature": self.temperature,
            "response_options": self.response_options,
            "run_date": str(pd.Timestamp.now()),
            "num_questions": len(self.questions),
            "questions": self.questions,
            "persona_dictionary": self.persona_dict,
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
                        result = self.process_question(question, persona_traits, persona_descriptions)
                        row_data.append(result.get('response', 'ERROR'))
                        error_count = 0
                    except Exception as e:
                        error_count += 1
                        warnings.warn(f"Error processing question '{question}': {str(e)}")
                        row_data.append("ERROR")

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

        if not data:
            raise RuntimeError(
                f"Failed to generate any valid responses after {error_count} consecutive errors. "
                "Check if Ollama is running and the model is available."
            )

        # Create and return DataFrame from all successfully collected data
        df = pd.DataFrame(data, columns=columns)
        return df

if __name__ == "__main__":
    # Run the command line
    cli()
