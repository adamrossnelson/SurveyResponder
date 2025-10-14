import argparse
import os
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

if __name__ == "__main__":
    cli()