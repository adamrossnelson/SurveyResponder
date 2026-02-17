# SurveyResponder

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

- ✅ Default Likert scale (`Strongly Disagree` to `Strongly Agree`, with neutral midpoint).
- ✅ Custom response options (passed as a list).
- ✅ Persona-driven simulation (via a JSON file with structured traits and descriptions).
- ✅ Supports simple text files (one question per line).
- ✅ Generates N responses per session.
- ✅ Outputs a tidy CSV file.
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
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/adamrossnelson/SurveyResponder/main/questions.txt" -OutFile "questions.txt"
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/adamrossnelson/SurveyResponder/main/persona.json" -OutFile "persona.json"
```

#### macOS/Linux

```bash
# Download the Python file
curl -O https://raw.githubusercontent.com/adamrossnelson/SurveyResponder/main/SurveyResponder.py

# Download example files (optional)
curl -O https://raw.githubusercontent.com/adamrossnelson/SurveyResponder/main/questions.txt
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
from surveyresponder import SurveyResponder

# Basic usage with defaults
responder = SurveyResponder()
df = responder.run()
df.to_csv("results.csv", index=False)

# Advanced usage with all parameters
responder = SurveyResponder(
    questions_path="questions.txt",
    persona_path="persona.json",
    model_name="llava-llama3:latest",
    response_options=["Never", "Rarely", "Sometimes", "Often", "Always"],
    num_responses=100,
    temperature=1.0,
    base_url="http://localhost:11434/api/generate"
)

# Option 1: Get DataFrame only
df = responder.run()

# Option 2: Get DataFrame and write to CSV file (records save as they're generated)
#           Also creates results_params.json with configuration parameters
df = responder.run_write("results.csv")
```
### As a Google Colab / Jupyter Notebook
#### [Open SurveyResponder in Colab](https://colab.research.google.com/drive/1LyVCeYnH33CTQzyo-F0kKvjYv-8jGjDB?usp=sharing)

### As a CLI tool (To Be Implemented)

*Anticipated CLI syntax here:*

```bash
surveyresponder run \
  --questions questions.txt \
  --persona persona.json \
  --model llava-llama3:latest \
  --num-responses 100 \
  --output results.csv \
  --temperature 1.0 \
  --response-options "Never,Rarely,Sometimes,Often,Always"
```

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
    questions_path="questions.txt",
    persona_path="persona.json",
    model_name="mistral:latest", # Changed to mistral
    response_options=["Disagree", "Slightly Disagree", "Neutral", "Slightly Agree", "Agree"],
    num_responses=100,
    temperature=1.0,
    base_url="http://localhost:11434/api/generate"
)
```
### Editing Questions and Personas
SurveyResponder uses two input files:

`questions.txt` — plain text, one survey question per line.

`persona.json` — a dictionary of traits where each key becomes a column and each value is a list of [value, description] pairs.

You can edit these files manually in a file browser, text editor, or like this:
```python
# Add a new question to questions.txt
with open("questions.txt", "a") as f:
    f.write("\nI feel confident solving programming problems.")

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
The default likert scale can be changed to more accurately fit specific questions and personas, and it can be done via the following:
```python
responder = SurveyResponder(
    questions_path="questions.txt",
    persona_path="persona.json",
    model_name="mistral:latest",
    response_options=["Never", "Rarely", "Often", "Always"], # Changed to 4 point likert scale
    num_responses=100,
    temperature=1.0,
    base_url="http://localhost:11434/api/generate"
)
```

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

### Input: `questions.txt`

Plain text file, one survey question per line:

```
I enjoy working in teams.
I prefer a structured schedule.
I feel confident in my abilities.
```

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

| resid    | age | gender | hobbies | Q1       | Q2      | Q3             |
| -------- | --- | ------ | ------- | -------- | ------- | -------------- |
| 1        | 18  | male   | music   | Agree    | Neutral | Strongly Agree |
| 2        | 20  | female | art     | Disagree | Agree   | Agree          |

### Output: `results_params.json`

Configuration parameters file for reproducibility:

```json
{
  "questions_path": "questions.txt",
  "persona_path": "persona.json",
  "model_name": "llava-llama3:latest",
  "base_url": "http://localhost:11434/api/generate",
  "num_responses": 100,
  "temperature": 1.0,
  "response_options": ["Never", "Rarely", "Sometimes", "Often", "Always"],
  "run_date": "2025-04-03 21:04:23.123456",
  "num_questions": 3
}
```

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
