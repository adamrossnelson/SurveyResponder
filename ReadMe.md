# SurveyResponder

### Developer Setup
1. Clone: `git clone https://github.com/adamrossnelson/SurveyResponder.git`
2. Environment: `python -m venv venv`
3. Activate: `.\venv\Scripts\activate` (Windows)
4. Install: `pip install -r requirements.txt`

**Survey responses using LLMs** For researchers, developers, and psychometricians testing, scoring, and metrics evaluation.

## 🚀 What Is SurveyResponder?

**SurveyResponder** is a Python package and CLI tool that uses Large Language Models (LLMs), such as those accessed through [Ollama - ollama.com](https://ollama.com), to generate synthetic survey instrument responses.

Useful for:

- Testing and validating **Likert-scale** or **multiple-choice** instruments.
- Simulating responses across different **personas**.
- Exploring **LLM behavior** when prompted with surveys.
- Creating synthetic datasets for development and analysis.

A small collection of previous responses are available via [Google Drive](https://drive.google.com/drive/folders/11nAmH9aUoeg9vzKYqT1hXYd_GJxay_lA?usp=sharing).

## 🔧 Features

- ✅ Named response scales (e.g., 5-point agreement, 5-point frequency) defined once and referenced per question.
- ✅ Per-question response options with numeric codes and prompt prefaces (via `questions.json`).
- ✅ Persona-driven simulation (via a JSON file with structured traits and descriptions).
- ✅ Questions specified in JSON with stable ids (used as output column headings) and reverse-coding flags.
- ✅ Generates N responses per session.
- ✅ Outputs a tidy CSV file and a cell-by-cell response log CSV.
- ✅ Optional response validation against per-scale `valid_responses`.
- ✅ Optional LLM-based recoding of invalid responses (research-assistant prompt).
- ✅ Optional numeric reverse coding for questions flagged `reverse_coded`.
- ✅ Temperature setting for controlling LLM creativity.
- ✅ Parameter logging for reproducibility.
- ✅ Configurable LLM base URL for using remote instances.

---

## 📥 Installation

SurveyResponder requires Python 3.7+ and [Ollama](https://ollama.com) for local LLM execution.

### Prerequisites

1) Install Python, Pandas, 
  a) The Anaconda distribution is recommended.
  b) Otherwise the lastest of Python can work.
2) Install [Ollama](https://ollama.com/download) and/or [Annything LLM](https://anythingllm.com/).
3) Pull an LLM model with Ollama (Ex: `ollama pull llava-llama3:latest`)

### Installing SurveyResponder

SurveyResponder is currently a single Python file (beta), installation is simple:

#### Windows

```powershell
# Download the Python file
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/adamrossnelson/SurveyResponder/main/SurveyResponder.py" -OutFile "SurveyResponder.py"

# Download example files (optional)
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/adamrossnelson/SurveyResponder/main/questions.json" -OutFile "questions.json"
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/adamrossnelson/SurveyResponder/main/persona.json" -OutFile "persona.json"
```

#### macOS/Linux

```bash
# Download the Python file
curl -O https://raw.githubusercontent.com/adamrossnelson/SurveyResponder/main/SurveyResponder.py

# Download example files (optional)
curl -O https://raw.githubusercontent.com/adamrossnelson/SurveyResponder/main/questions.json
curl -O https://raw.githubusercontent.com/adamrossnelson/SurveyResponder/main/persona.json
```

### Verifying Installation

To use SurveyResponder, import it in your Python code:

```python
# Import the SurveyResponder class
from SurveyResponder import SurveyResponder

# Create a responder with example data
responder = SurveyResponder()

# Make sure Ollama is running before executing
df = responder.run_write('responses.csv')
print(f"Generated {len(df)} responses successfully!")
```

---

## 🧪 Quickstart

### As a Python module

```python
from SurveyResponder import SurveyResponder

# Basic usage with defaults
responder = SurveyResponder()
df = responder.run()
df.to_csv("results.csv", index=False)

# Advanced usage with all parameters
responder = SurveyResponder(
    questions_path="questions.json",
    persona_path="persona.json",
    model_name="llava-llama3:latest",
    num_responses=100,
    temperature=1.0,
    base_url="http://localhost:11434/api/generate"
)

# Option 1: Get DataFrame only
df = responder.run()

# Option 2: Get DataFrame and write to CSV file (records save as they're generated)
#           Also creates results_params.json with configuration parameters and
#           results_response_log.csv with one row per (respondent, question).
df = responder.run_write("results.csv")

# Option 3: Validate responses against each scale's `valid_responses` list and,
#           when the model returns an invalid answer, ask an LLM "research
#           assistant" to recode it to the most likely valid response. Also
#           apply numeric reverse coding to questions flagged `reverse_coded`.
df = responder.run_write(
    "results.csv",
    validate=True,          # check response is in scale["valid_responses"]
    on_invalid="recode",    # "none" | "retry" | "recode"
    max_retries=2,          # only used when on_invalid="retry"
    reverse_code=True       # apply max+min-value to reverse_coded questions
)

# The cell-by-cell log is also available as `responder.response_log`
```
### As a Google Colab / Jupyter Notebook
#### [Open SurveyResponder in Colab](https://colab.research.google.com/drive/1LyVCeYnH33CTQzyo-F0kKvjYv-8jGjDB?usp=sharing)

### As a CLI tool 

1. **Run a survey:** `python cli.py run --questions questions.json --num-responses 10`
2. **Manage your questions:**
   `python cli.py questions --list`
   `python cli.py questions --add "I enjoy this research project." --scale likert5`

**Full example with advanced options:**
```bash
python cli.py run \
  --questions questions.json \
  --persona persona.json \
  --model llama3.1:latest \
  --num-responses 100 \
  --output results.csv \
  --temperature 1.0

---

## 🛠️ Customization Options
Below are a few examples of ways to customize and tailor the Survey Responder for specific use cases:

### Changing LLM Models

To test how responses differ among LLM models, you can change the LLM by pulling it from Ollama

A full list of available LLM's are found here: https://ollama.com/library

```python
# Example: pull mistral and use it in the responder
ollama pull mistral:latest

from SurveyResponder import SurveyResponder
responder = SurveyResponder(
    questions_path="questions.json",
    persona_path="persona.json",
    model_name="mistral:latest", # Changed to mistral
    num_responses=100,
    temperature=1.0,
    base_url="http://localhost:11434/api/generate"
)
```
### Editing Questions and Personas
SurveyResponder uses two input files:

`questions.json` — JSON with a `scales` library and a `questions` list. Each question has an `id` (used as the output column heading), `text`, a `scale` reference, and a `reverse_coded` flag.

`persona.json` — a dictionary of traits where each key becomes a column and each value is a list of [value, description] pairs.

You can edit these files manually in a file browser, text editor, or like this:
```python
# Add a new question to questions.json
import json

with open("questions.json", "r") as f:
    survey = json.load(f)

survey["questions"].append({
    "id": "confident_programming",
    "text": "I feel confident solving programming problems.",
    "scale": "likert5",
    "reverse_coded": False
})

with open("questions.json", "w") as f:
    json.dump(survey, f, indent=2)

# Add a new trait to persona.json
import json

with open("persona.json", "r") as f:
    personas = json.load(f)

# Add a new student status trait
personas["student_status"] = personas.get("student_status", [])
personas["student_status"].append(["full-time", "who is a full-time student"])

# Save the changes
with open("persona.json", "w") as f:
    json.dump(personas, f, indent=2)
```
### Changing Response Options
Response options are defined as named scales in `questions.json`. Each scale pairs a prompt `preface` with an `options` map of response labels to numeric codes. Add or edit scales in the `scales` section, then reference them from individual questions:
```json
{
  "scales": {
    "freq4": {
      "preface": "How often is the following true for you:",
      "options": {"never": 1, "rarely": 2, "often": 3, "always": 4}
    }
  },
  "questions": [
    {"id": "calm_pressure", "text": "I stay calm under pressure", "scale": "freq4", "reverse_coded": false}
  ]
}
```

Note: The `response_options` parameter has been removed from `SurveyResponder`. Passing it raises an error directing you to the questions JSON file.

### Preview Personas and Prompts

SurveyResponder includes methods to preview the personas and prompts that will be used (can be useful in verifying proper `persona.json` specifications):

```python
# Create a SurveyResponder
responder = SurveyResponder()

# Generate a random persona description
persona = responder.example_persona()
print(persona)
# Output: "You are a someone who is multiracial, who is from a family whose members go to and do well in college..." 

# Generate multiple personas
personas = responder.example_persona(npersonas=3)
for i, p in enumerate(personas):
    print(f"Persona {i+1}: {p}")

# Generate an example prompt using the first question in questions.txt
prompt = responder.example_prompt()
print(prompt)

# Generate an example prompt with a custom question
prompt = responder.example_prompt("I enjoy Python programming.")
print(prompt)
```
---

## 📁 File Formats

### Input: `questions.json`

JSON file with named response scales and a list of questions. Each question's `id` becomes its column heading in the output CSV. Each question references a scale by name, and each scale defines the prompt `preface` and the `options` (response labels mapped to numeric codes):

```json
{
  "scales": {
    "likert5": {
      "preface": "How strongly do you agree or disagree with the following statement:",
      "options": {
        "strongly disagree": 1,
        "disagree": 2,
        "neutral": 3,
        "agree": 4,
        "strongly agree": 5
      },
      "valid_responses": ["1", "2", "3", "4", "5"]
    }
  },
  "questions": [
    {"id": "enjoy_teams", "text": "I enjoy working in teams.", "scale": "likert5", "reverse_coded": false},
    {"id": "prefer_structure", "text": "I prefer a structured schedule.", "scale": "likert5", "reverse_coded": false},
    {"id": "confident_abilities", "text": "I feel confident in my abilities.", "scale": "likert5", "reverse_coded": false}
  ]
}
```

Each scale may include an optional `valid_responses` list. When `run()` or `run_write()` is called with `validate=True`, raw model responses are checked (case-insensitive, stripped) against this list. If a scale omits `valid_responses`, the full set of option labels is used as the valid set.

### Input: `persona.json`

Each key becomes a column in the output CSV. Each value is a list of tuples. The first element is recorded in the CSV. The second element is included in the LLM prompt.

```json
{
  "age": [[16, "is 16 years old"], [18, "is 18 years old"], [20, "is 20 years old"]],
  "gender": [["male", "is male"], ["female", "is female"]],
  "hobbies": [["art", "who enjoys making art"], ["music", "who enjoys music"]]
}
```

### Output: `results.csv`

Example format:

| resid    | age | gender | hobbies | enjoy_teams | prefer_structure | confident_abilities |
| -------- | --- | ------ | ------- | ----------- | ---------------- | ------------------- |
| 1        | 18  | male   | music   | agree       | neutral          | strongly agree      |
| 2        | 20  | female | art     | disagree    | agree            | agree               |

### Output: `results_response_log.csv`

When `run_write()` is called, a cell-by-cell log is written alongside the results file with one row per (respondent, question). The same log is also available in memory as `responder.response_log`.

| Column              | Description                                                                                              |
| ------------------- | -------------------------------------------------------------------------------------------------------- |
| `resid`             | Respondent id (matches the `resid` column in `results.csv`).                                             |
| `question_id`       | Question id from `questions.json`.                                                                       |
| `scale`             | Name of the scale that question references.                                                              |
| `original_response` | Raw response returned by the LLM before any recoding or reverse coding.                                  |
| `final_response`    | Response after validation/recoding/reverse-coding (this is what appears in `results.csv`).               |
| `validated`         | `True`/`False`/`None`. `None` means validation was not enabled.                                          |
| `action_taken`      | `not_checked`, `validated`, `retry`, `recode`, `invalid`, or `error`.                                    |
| `reverse_coded`     | `1` if reverse coding was applied to this cell, else `0`.                                                |

### Output: `results_params.json`

Configuration parameters file for reproducibility:

```json
{
  "questions_path": "questions.json",
  "persona_path": "persona.json",
  "model_name": "llava-llama3:latest",
  "base_url": "http://localhost:11434/api/generate",
  "num_responses": 100,
  "temperature": 1.0,
  "run_date": "2025-04-03 21:04:23.123456",
  "num_questions": 3,
  "questions_json": {
    "scales": {
      "likert5": {
        "preface": "How strongly do you agree or disagree with the following statement:",
        "options": {"strongly disagree": 1, "disagree": 2, "neutral": 3, "agree": 4, "strongly agree": 5}
      }
    },
    "questions": [
      {"id": "enjoy_teams", "text": "I enjoy working in teams.", "scale": "likert5", "reverse_coded": false}
    ]
  },
  "example_prompts": {
    "enjoy_teams": "You are a someone who is 18 years old, ... \n\nHow strongly do you agree or disagree with the following statement:\n\"I enjoy working in teams.\"\n\nstrongly disagree, disagree, neutral, agree, strongly agree\n\n..."
  }
}
```

The `questions_json` key preserves the complete contents of the questions file (scales and questions) as used for the run. The `example_prompts` key records one fully rendered prompt per question (each with a randomly generated persona) so the exact prompt wording sent to the LLM is documented.

---

## 👨‍🔬 Intended Use Cases

- Simulating data for **scoring algorithm validation**
- Explore how LLMs might (or might not) reflect or **replicate human biases**
- Generating **mock data** for dashboards or demonstrations

---

## 💬 Contributing

Pull requests welcome (especially if consistent with the rooadmap below)! Please open an issue first to discuss major changes. Or work to address an existing issue.

### Aspirational Project Structure

```
SurveyResponder/
├── src/
│   └── surveyresponder/
│       ├── __init__.py          ← re-exports SurveyResponder class, __version__
│       ├── core.py              ← SurveyResponder class + helper functions
│       ├── cli.py               ← CLI entry point
│       └── data/
│           ├── questions.txt    ← default example questions
│           └── persona.json     ← default example persona
├── tests/
│   ├── conftest.py
│   └── test_core.py
├── examples/
│   └── PRCA_LLM_Original_FrequencyScale.csv
├── .github/
│   └── workflows/
│       └── test.yml
├── pyproject.toml               ← build metadata, dependencies, CLI entry point
├── README.md                    ← renamed from ReadMe.md
├── LICENSE
└── .gitignore                   ← simplified
```

### High Level Look at Existing Issues

| Priority | Change |
|----------|--------|
| 🔴 High | Add `pyproject.toml` — makes the project installable [Issue](https://github.com/adamrossnelson/SurveyResponder/issues/8) |
| 🔴 High | Move source into `src/surveyresponder/` package directory [Issue](https://github.com/adamrossnelson/SurveyResponder/issues/9) |
| 🔴 High | Rename [SurveyResponder.py](cci:7://file:///Users/adamrossnelson/Documents/gits/SurveyResponder/SurveyResponder.py:0:0-0:0) → `core.py` (PEP 8) |
| 🟡 Medium | Rename [ReadMe.md](cci:7://file:///Users/adamrossnelson/Documents/gits/SurveyResponder/ReadMe.md:0:0-0:0) → `README.md` |
| 🟡 Medium | Refactor [run()](cci:1://file:///Users/adamrossnelson/Documents/gits/SurveyResponder/SurveyResponder.py:287:4-368:17)/[run_write()](cci:1://file:///Users/adamrossnelson/Documents/gits/SurveyResponder/SurveyResponder.py:370:4-517:17) to eliminate duplication [Issue](https://github.com/adamrossnelson/SurveyResponder/issues/12) |
| 🟡 Medium | Clean up imports (remove unused, move inline imports to top)[Issue](https://github.com/adamrossnelson/SurveyResponder/issues/10) |
| 🟡 Medium | Add `psutil` to dependencies; trim [requirements.txt](cci:7://file:///Users/adamrossnelson/Documents/gits/SurveyResponder/requirements.txt:0:0-0:0) to direct deps only [Issue](https://github.com/adamrossnelson/SurveyResponder/issues/1) |
| 🟡 Medium | Register CLI entry point; update README to reflect CLI is implemented |
| 🟢 Low | Add CI workflow (GitHub Actions) [Issue](https://github.com/adamrossnelson/SurveyResponder/issues/13) |
| 🟢 Low | Move example data into `data/` or `examples/` subdirectories [Issue](https://github.com/adamrossnelson/SurveyResponder/issues/11) |
| 🟢 Low | Simplify [.gitignore](cci:7://file:///Users/adamrossnelson/Documents/gits/SurveyResponder/.gitignore:0:0-0:0) strategy |
| 🟢 Low | Add `__version__` |

### 🔍 Roadmap

The following features are under consideration for future releases:

- **Support for open-ended responses**: Allow questions that require textual responses in addition to multiple-choice options.
- **Persona templates**: Provide predefined personas for ease of use.
- **Expanded persona logic**: Include sampling strategies, weights, and dependencies between persona traits.
- **Question metadata support**: Allow users to include additional metadata about questions (e.g., topic, valence) to inform response generation.
- **Batch processing of surveys**: Enable running multiple different surveys or question sets in one go.
- **Psychometric summaries**:
  - Perform exploratory factor analysis (EFA) and provide outputs.
  - Estimate internal consistency metrics (e.g., Cronbach’s alpha).
  - Visualize response patterns.
- **Evaluation module**: Compare LLM-generated responses with real human response distributions.
- **Cloud deployment support**: Make the tool available as a web service or via API.

---

## 📚 Citation

If you use SurveyResponder in your research, please cite it using the following formats:

### BibTeX

```bibtex
@software{nelson2025surveyresponder,
  author       = {Nelson, Adam Ross},
  title        = {SurveyResponder: Generate synthetic survey responses using LLMs},
  year         = 2025,
  publisher    = {Up Level Data, LLC},
  version      = {1.0},
  url          = {https://github.com/adamrossnelson/SurveyResponder}
}
```

### APA Format

Nelson, A. R. (2025). *SurveyResponder: Generate synthetic survey responses using LLMs* (Version 1.0) [Computer software]. Up Level Data, LLC. https://github.com/adamrossnelson/SurveyResponder

---

## 📄 License

MIT License. See `LICENSE` file for details.
