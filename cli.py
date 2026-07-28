import argparse
import json
import os
import re
import sys
from SurveyResponder import SurveyResponder, load_questions

def cli() -> None:
    """Creates a CLI (command line interface) to provide an alternate, more customizable way of running the Responder

    Returns: None

    """
    # Instantiate a parser with arguments for questions, persona, questions, num responses, temperature, scale
    parser = argparse.ArgumentParser(description="SurveyResponder CLI")

    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run survey responder")

    run_parser.add_argument("--questions", default="questions.json",
                            help="Path to questions JSON file with scales and questions (default: questions.json)")
    run_parser.add_argument("--persona", default="persona.json",
                            help="Path to persona JSON file (default: persona.json)")
    run_parser.add_argument("--model", default="llama3.1:latest",
                            help="Ollama model to use. Model must be pulled locally. (default: llama3.1:latest)")
    run_parser.add_argument("--num-responses", type=int, default=10,
                            help="Number of responses to generate (default: 10)")
    run_parser.add_argument("--temperature", type=float, default=1.0,
                            help="LLM temperature (default: 1.0)")
    run_parser.add_argument("--response-options", default=None,
                            help="REMOVED: response options are now defined as named scales in the questions JSON file")
    run_parser.add_argument("--output", default="results.csv",
                            help="CSV filepath to save results (default: results.csv)")

    # CLI commands for listing and modifying a file of questions
    q_parser = subparsers.add_parser("questions", help="List or update questions JSON file (default: questions.json)")

    # Ensures questions commands can only be run one at a time
    group = q_parser.add_mutually_exclusive_group(required=True)

    q_parser.add_argument("--file", default="questions.json", help="Specify which questions JSON file to manage (default: questions.json)")
    q_parser.add_argument("--id", default=None, help="Question id for --add; used as the output column heading (default: generated from the question text)")
    q_parser.add_argument("--scale", default=None, help="Scale name for --add; must be defined in the file (default: first scale in the file)")
    group.add_argument("--list", action="store_true", help="List all questions")
    group.add_argument("--add", type=str, help="Add a new question (question text)")
    group.add_argument("--delete", type=int, help="Delete question by list position (see --list)")

    args = parser.parse_args()

    # Run question CLI commands
    if args.command == "questions":
        file_path = args.file
        # Ensure file exists
        if not os.path.exists(file_path):
            # If adding, create a new survey file with a default scale
            if args.add:
                default_doc = {
                    "scales": {
                        "likert5": {
                            "preface": "How strongly do you agree or disagree with the following statement:",
                            "options": {
                                "strongly disagree": 1,
                                "disagree": 2,
                                "neutral": 3,
                                "agree": 4,
                                "strongly agree": 5
                            }
                        }
                    },
                    "questions": []
                }
                with open(file_path, "w") as f:
                    json.dump(default_doc, f, indent=2)
            else:
                print(f"Questions file not found: {file_path}", file=sys.stderr)
                sys.exit(1)

        try:
            scales, questions = load_questions(file_path)
        except ValueError as e:
            print(f"File Error: {e}", file=sys.stderr)
            sys.exit(1)

        if args.list:
            for i, question in enumerate(questions, 1):
                print(f"{i}. [{question['id']}] ({question['scale']}) {question['text']}")

        elif args.add:
            text = args.add.strip()

            # Resolve the scale for the new question
            scale_name = args.scale if args.scale else next(iter(scales))
            if scale_name not in scales:
                print(f"Scale '{scale_name}' is not defined in {file_path}. "
                      f"Defined scales: {list(scales.keys())}", file=sys.stderr)
                sys.exit(1)

            # Resolve the id for the new question
            existing_ids = {q["id"] for q in questions}
            if args.id:
                qid = args.id
                if qid in existing_ids:
                    print(f"Question id '{qid}' already exists in {file_path}.", file=sys.stderr)
                    sys.exit(1)
            else:
                base_id = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40] or "question"
                qid = base_id
                counter = 2
                while qid in existing_ids:
                    qid = f"{base_id}_{counter}"
                    counter += 1

            questions.append({"id": qid, "text": text, "scale": scale_name, "reverse_coded": False})
            with open(file_path, "w") as f:
                json.dump({"scales": scales, "questions": questions}, f, indent=2)
            print(f"Added question [{qid}] ({scale_name}): {text}")

        elif args.delete:
            index = args.delete - 1
            if index < 0 or index >= len(questions):
                print(f"Invalid question number: {args.delete}", file=sys.stderr)
                sys.exit(1)
            removed = questions.pop(index)
            with open(file_path, "w") as f:
                json.dump({"scales": scales, "questions": questions}, f, indent=2)
            print(f"Deleted question [{removed['id']}]: {removed['text']}")

        else:
            print("No action specified. Use --list, --add, or --delete.", file=sys.stderr)
            sys.exit(1)
        return

    # Run main program commands
    elif args.command == "run":
        # The --response-options flag has been removed in favor of scales in the questions JSON file
        if args.response_options:
            print("Input Error: --response-options has been removed. Response options are now "
                  "defined as named scales in the questions JSON file passed to --questions "
                  "(see questions.json for an example).", file=sys.stderr)
            sys.exit(1)
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

            # Temperature validation
            if not (0.0 <= args.temperature <= 2.0):
                raise ValueError("Temperature must be between 0.0 and 2.0")

            # Create SurveyResponder
            responder = SurveyResponder(
                questions_path=args.questions,
                persona_path=args.persona,
                model_name=args.model,
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

if __name__ == "__main__":
    cli()