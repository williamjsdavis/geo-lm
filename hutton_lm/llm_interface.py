import os
import re
from datetime import datetime
from openai import OpenAI

# Use relative import for data constants within the package
from .data_loader import (
    DEFAULT_POINTS_DATA,
    DEFAULT_ORIENTATIONS_DATA,
    DEFAULT_STRUCTURE_DATA,
    _WORKSPACE_ROOT,
)

# Attempt to import the Llama API client, handle import error gracefully
try:
    from llama_api_client import LlamaAPIClient, APIError
except ImportError:
    print("Warning: llama_api_client not installed. LLM mode will not be available.")
    LlamaAPIClient = None
    APIError = None

# --- LLM Helper Functions ---


def get_llm_prompt(
    prompt_type: str,
    dsl_text_path: str | None = "extracted-data/bingham-canyon/geo-dsl-rev1.txt",
) -> str:
    """Builds and returns the appropriate LLM prompt string based on the type."""

    # --- Read DSL Text (if provided) ---
    dsl_text = None
    if dsl_text_path:
        try:
            # Construct absolute path if relative
            full_dsl_path = dsl_text_path
            if not os.path.isabs(dsl_text_path):
                full_dsl_path = os.path.join(_WORKSPACE_ROOT, dsl_text_path)

            with open(full_dsl_path, "r") as f:
                dsl_text = f.read()
            print(f"Successfully read DSL text from: {full_dsl_path}")
            # NOTE: dsl_text is read but not yet used in the prompt generation below.
        except FileNotFoundError:
            print(
                f"Warning: DSL file not found at '{dsl_text_path}'. Proceeding without DSL text."
            )
        except Exception as e:
            print(
                f"Warning: Error reading DSL file '{dsl_text_path}': {e}. Proceeding without DSL text."
            )
    # ------------------------------------

    prompt_intro = "You are a helpful assistant for geological modeling. Please generate three completely new CSV datasets suitable for GemPy: surface points, orientations, and structural group definitions."
    prompt_format_suffix = """Ensure the output format is exactly CSV, with the correct columns as shown in the reference/examples.
Clearly separate the three datasets using '=== POINTS DATA ===', '=== ORIENTATIONS DATA ===', and '=== STRUCTURE DATA ===' markers.
Include the CSV data within markdown code blocks (```csv ... ```).
For the structure data, use only the following relations: ERODE, ONLAP, BASEMENT.

Now, generate the data, keeping the structure and headers consistent. Start with '=== POINTS DATA ==='."""

    prompt_task = ""
    prompt_examples = ""

    if prompt_type == "default":
        prompt_task = "Please generate three CSV datasets for GemPy: surface points, orientations, and structural definitions.\nUse the following examples as a base, but introduce some small modifications like changing some dip/azimuth values, adding or removing a rock type/surface (and updating structure accordingly), or adjusting point coordinates slightly."
        prompt_examples = f"""Example Points Data:
```csv
{DEFAULT_POINTS_DATA.strip()}
```

Example Orientations Data:
```csv
{DEFAULT_ORIENTATIONS_DATA.strip()}
```

Example Structure Data:
```csv
{DEFAULT_STRUCTURE_DATA.strip()}
```"""

    elif prompt_type == "random":
        prompt_task = "Please generate three completely new CSV datasets suitable for GemPy: surface points, orientations, and structural group definitions.\nInvent a plausible but random geological structure (e.g., folded layers, a simple fault, an intrusion). Do NOT use the example data provided below as a base, only use it for format reference.\nDefine at least 3-5 distinct surfaces/rock types.\nGenerate a reasonable number of points (15-30) and orientations (10-20) to define the structure.\nEnsure the structural definitions reference only the surfaces/rock types defined in the points data and use only ERODE, ONLAP, or BASEMENT relations."
        prompt_examples = f"""Points Data Format Reference (DO NOT COPY VALUES):
```csv
{DEFAULT_POINTS_DATA.strip()}
```

Orientations Data Format Reference (DO NOT COPY VALUES):
```csv
{DEFAULT_ORIENTATIONS_DATA.strip()}
```

Structure Data Format Reference (DO NOT COPY VALUES):
```csv
{DEFAULT_STRUCTURE_DATA.strip()}
```"""

    elif prompt_type == "DSL":
        if dsl_text:
            dsl_explanation = """
The provided DSL describes geological entities and events:
- ROCK: Defines rock units with type and optional age.
- DEPOSITION: Represents sedimentary or volcanic rock formation, potentially ordered (`after`).
- EROSION: Represents an erosional event, potentially ordered (`after`).
- INTRUSION: Represents magma emplacement (dike, sill, etc.), potentially ordered (`after`).
`after:` clauses define relative timing constraints. Ages provide absolute timing where available."""

            prompt_task = f"""Please generate three CSV datasets for GemPy (surface points, orientations, structural definitions) that are consistent with the geological history described in the following DSL:

```dsl
{dsl_text.strip()}
```

{dsl_explanation}

Your task is to translate this DSL description into plausible GemPy input data:
1.  **Points:** Create X, Y, Z coordinates for surfaces representing the boundaries between the defined ROCK units. Ensure the spatial arrangement reflects the depositional, erosional, and intrusive relationships and timing (`after:` clauses, `age`/`time`).
2.  **Orientations:** Define dip and azimuth values for relevant surfaces. These should be consistent with the geological structure implied by the DSL (e.g., layers deposited flat initially, tilted/folded later, cut by intrusions).
3.  **Structure:** Define the stratigraphic relationships (series/groups) using the GemPy relations (ERODE, ONLAP, BASEMENT) consistent with the DSL's DEPOSITION, EROSION, and INTRUSION events and their `after:` constraints. The surface names in the structure data must match the `surface` column in the points data, which should correspond to the ROCK units defined in the DSL.

Use the format reference below, but generate *new* data based *only* on the provided DSL."""
            prompt_examples = f"""Points Data Format Reference (DO NOT COPY VALUES):
```csv
{DEFAULT_POINTS_DATA.strip()}
```

Orientations Data Format Reference (DO NOT COPY VALUES):
```csv
{DEFAULT_ORIENTATIONS_DATA.strip()}
```

Structure Data Format Reference (DO NOT COPY VALUES):
```csv
{DEFAULT_STRUCTURE_DATA.strip()}
```"""
        else:
            print(
                "Warning: 'DSL' prompt type selected, but no DSL text was successfully read. Falling back to 'default' prompt type."
            )
            # Fallback to default if DSL text isn't available
            return get_llm_prompt(
                "default", dsl_text_path=None
            )  # Pass None to avoid re-reading attempt

    else:
        print(
            f"Warning: Unknown prompt type '{prompt_type}'. Falling back to default prompt."
        )
        return get_llm_prompt("default", dsl_text_path=None)  # Pass None here too

    # Combine the sections
    full_prompt = f"""{prompt_intro}

{prompt_task}

{prompt_examples}

{prompt_format_suffix}"""

    return full_prompt


def initialize_llm():
    """Initializes and returns the Llama API client."""
    if LlamaAPIClient is None:
        print(
            "Error: LlamaAPIClient is not available. Please install llama_api_client."
        )
        return None
    api_key = os.environ.get("LLAMA_API_KEY")
    if not api_key:
        print("Error: LLAMA_API_KEY environment variable not set.")
        return None
    try:
        client = LlamaAPIClient(api_key=api_key)
        return client
    except Exception as e:
        print(f"Error initializing Llama API client: {e}")
        return None


def generate_data_with_llm(client, prompt, temperature):
    """Calls the LLM API to generate data based on the prompt."""
    if not client or not APIError:
        print("Error: LLM Client or APIError not available.")
        return None
    try:
        print(f"Sending prompt to LLM (Temperature: {temperature})...")
        response = client.chat.completions.create(
            model="Llama-4-Maverick-17B-128E-Instruct-FP8",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        print("LLM response received.")
        print(response)  # Keep full response print for debugging
        return response
    except APIError as e:
        print(f"LLM API Error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during LLM generation: {e}")
        return None


def parse_llm_response(llm_response_object):
    """Parses the LLM response object to extract points, orientations, and structure CSV data."""
    response_text = None
    try:
        # Extract the text content from the response object structure
        if (
            llm_response_object
            and hasattr(llm_response_object, "completion_message")
            and hasattr(llm_response_object.completion_message, "content")
            and hasattr(llm_response_object.completion_message.content, "text")
        ):
            response_text = llm_response_object.completion_message.content.text
        else:
            print("Error: Unexpected LLM response object structure.")
            return None, None, None

    except AttributeError as e:
        print(f"Error accessing attributes in LLM response object: {e}")
        return None, None, None

    if not response_text:
        print("Error: No text content found in LLM response.")
        return None, None, None

    # Use regex to find the data blocks, allowing for potential markdown code fences
    points_match = re.search(
        r"(?s)=== POINTS DATA ===.*?```csv\n(.*?)\n```", response_text
    )
    if not points_match:  # Fallback without code fences
        points_match = re.search(
            r"(?s)=== POINTS DATA ===\n(.*?)\n=== ORIENTATIONS DATA ===", response_text
        )

    orientations_match = re.search(
        r"(?s)=== ORIENTATIONS DATA ===.*?```csv\n(.*?)\n```", response_text
    )
    if not orientations_match:  # Fallback without code fences
        orientations_match = re.search(
            r"(?s)=== ORIENTATIONS DATA ===\n(.*?)\n=== STRUCTURE DATA ===",
            response_text,
        )

    structure_match = re.search(
        r"(?s)=== STRUCTURE DATA ===.*?```csv\n(.*?)\n```", response_text
    )
    if not structure_match:  # Fallback without code fences
        structure_match = re.search(
            r"(?s)=== STRUCTURE DATA ===\n(.*?)\Z", response_text
        )

    points_csv = points_match.group(1).strip() if points_match else None
    orientations_csv = (
        orientations_match.group(1).strip() if orientations_match else None
    )
    structure_csv = structure_match.group(1).strip() if structure_match else None

    if not points_csv or not orientations_csv or not structure_csv:
        print(
            "Error: Could not parse points, orientations, and/or structure data from LLM response text."
        )
        print(
            "Expected format markers: === POINTS DATA ===, === ORIENTATIONS DATA ===, === STRUCTURE DATA ==="
        )
        return None, None, None

    return points_csv, orientations_csv, structure_csv


def save_generated_data(points_csv, orientations_csv, structure_csv, output_dir):
    """Saves the generated points, orientations, and structure data to timestamped files."""
    try:
        # Ensure output directory is absolute or relative to workspace root (from data_loader)
        # This assumes output_dir might be relative
        # If output_dir needs to be relative to where script is run, adjust accordingly
        if not os.path.isabs(output_dir):
            from .data_loader import (
                _WORKSPACE_ROOT,
            )  # Use the root defined in data_loader

            output_dir = os.path.join(_WORKSPACE_ROOT, output_dir)

        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        points_filename = os.path.join(output_dir, f"points_{timestamp}.csv")
        orientations_filename = os.path.join(
            output_dir, f"orientations_{timestamp}.csv"
        )
        structure_filename = os.path.join(output_dir, f"structure_{timestamp}.csv")

        with open(points_filename, "w") as f:
            f.write(points_csv)
        print(f"Saved generated points data to: {points_filename}")

        with open(orientations_filename, "w") as f:
            f.write(orientations_csv)
        print(f"Saved generated orientations data to: {orientations_filename}")

        with open(structure_filename, "w") as f:
            f.write(structure_csv)
        print(f"Saved generated structure data to: {structure_filename}")

        return points_filename, orientations_filename, structure_filename
    except OSError as e:
        print(f"Error creating directory or writing files: {e}")
        return None, None, None
    except Exception as e:
        print(f"An unexpected error occurred during saving: {e}")
        return None, None, None


# --- End LLM Helper Functions ---


# --- Deprecated LLM Functions --- #
def generate_input_orientations_llm():
    """Deprecated: Generate input orientations using Llama 4 API."""
    pass


def generate_input_points_llm():
    """Deprecated: Generate input points using Llama 4 API."""
    pass


# -------------------------------- #

# --- LLM Orchestration Function ---


def run_llm_generation(prompt_type: str, temperature: float, output_dir: str):
    """Orchestrates LLM data generation (points, orientations, structure)."""
    client = initialize_llm()
    if not client:
        print("Exiting due to LLM initialization failure.")
        return None, None, None

    prompt = get_llm_prompt(prompt_type)

    llm_response = generate_data_with_llm(client, prompt, temperature)
    if not llm_response:
        print("Failed to get response from LLM. Exiting.")
        return None, None, None

    points_csv, orientations_csv, structure_csv = parse_llm_response(llm_response)
    if not points_csv or not orientations_csv or not structure_csv:
        print("Failed to parse LLM response. Exiting.")
        return None, None, None

    # --- Print generated data --- #
    print("\n--- Generated Points Data ---")
    print(points_csv)
    print("\n--- Generated Orientations Data ---")
    print(orientations_csv)
    print("\n--- Generated Structure Data ---")
    print(structure_csv)
    print("\n-----------------------------\n")
    # ---------------------------- #

    generated_files = save_generated_data(
        points_csv, orientations_csv, structure_csv, output_dir
    )

    if not all(generated_files):
        print("Failed to save one or more generated data files. Exiting.")
        return None, None, None

    return generated_files  # Returns (points_filename, orientations_filename, structure_filename)


# --- Text Consolidation --- #


def llm_consolidate_parsed_text(pdf_text: str) -> str:
    """
    Consolidate the parsed text using the LLM
    """

    # Define the prompt text
    prompt = f"""
    You are a senior geologist with many years of experience.
    You are given a geological description of a region from a report.
    Your job is to consolidate the description into a single, coherent geological description.
    Focus on: rock types present, the orientation of large-scale structures, stratigraphic relationships, erosion, and igneous intrusions.
    Ignore: Chemical analysis, mineralogy, and other non-geological information.
    Condense the description into one or two paragraphs without line breaks, avoid using headings and bullet points.
    Here is the geological description:
    {pdf_text}
    """

    # Initialize the LLM client using environment variable
    api_key = os.environ.get("LLAMA_API_KEY")
    if not api_key:
        print("Error: LLAMA_API_KEY environment variable not set.")
        return "Error: LLAMA_API_KEY not configured."

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.llama.com/compat/v1/",
    )
    try:
        completion = client.chat.completions.create(
            model="Llama-4-Maverick-17B-128E-Instruct-FP8",
            messages=[{"role": "user", "content": prompt}],
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Error during LLM text consolidation: {e}")
        return "Error: Failed to consolidate text."


# --- DSL Generation --- #

prompt_dsl_template = """
You are an expert geological interpreter and DSL compiler.  Your goal is to read a free-text description of an area's stratigraphy, structures, and events, then emit a concise, declarative DSL encoding of that description.

── INPUT ──

1) Geological description (condensed, one or two paragraphs):
{}

2) DSL specification and usage example:
```

# DSL Grammar

ROCK  <ID> [
name:    <string>;
type:    <sedimentary|volcanic|intrusive|metamorphic>;
age?:    <number><Ma|ka>|"?";
]

DEPOSITION <ID> [
rock:  <ID>;
time?: <number><Ma|ka>|"?";
after?: <ID>[, <ID>…];
]

EROSION <ID> [
time?: <number><Ma|ka>|"?";
after?: <ID>[, <ID>…];
]

INTRUSION <ID> [
rock:    <ID>;
style?:  <dike|sill|stock|batholith>;
time?:   <number><Ma|ka>|"?";
after?:  <ID>[, <ID>…];
]

# Example: Copper Porphyry System

ROCK   R1 [ name: Andesitic host;      type: volcanic;     age: 40Ma ]
ROCK   R2 [ name: Sedimentary cover;    type: sedimentary;  age: 38Ma ]
ROCK   R3 [ name: Quartz diorite porphyry; type: intrusive;  age: 35Ma ]
ROCK   R4 [ name: Copper-gold mineralization; type: intrusive;  age: 34Ma ]

DEPOSITION  D1 [ rock: R1;   time: 40Ma ]
DEPOSITION  D2 [ rock: R2;   time: 38Ma;   after: D1 ]

EROSION     E1 [ time: 37Ma; after: D2 ]

INTRUSION   I1 [ rock: R3;   style: stock;  time: 35Ma; after: D2, E1 ]
INTRUSION   I2 [ rock: R4;   style: dike;   time: 34Ma; after: I1 ]

```

── INSTRUCTIONS ──

• Parse the geological description.  
• Identify all distinct rock units, depositional events, erosional events, and intrusive events.  
• Assign a unique short ID to each (e.g. R1, D1, E1, I1…).  
• Fill in all known fields (`name`, `type`, `age`, `rock`, `time`, `style`, `after`).  
• Use absolute ages when given; otherwise use `after:` relationships to order events.  
• **Output ONLY** the DSL statements (one per line), in the order:  
  1. All `ROCK` definitions  
  2. All `DEPOSITION` statements  
  3. All `EROSION` statements  
  4. All `INTRUSION` statements  

Do **not** include any explanatory text—only the DSL code.
"""


def llm_generate_dsl_summary(consolidated_text: str) -> str:
    """
    Generates a DSL summary from consolidated text using the LLM.
    """
    prompt_dsl = prompt_dsl_template.format(consolidated_text)

    # Initialize the LLM client using environment variable
    api_key = os.environ.get("LLAMA_API_KEY")
    if not api_key:
        print("Error: LLAMA_API_KEY environment variable not set.")
        return "Error: LLAMA_API_KEY not configured."

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.llama.com/compat/v1/",
    )
    try:
        completion = client.chat.completions.create(
            model="Llama-4-Maverick-17B-128E-Instruct-FP8",  # Consider if a different model/params are needed
            messages=[{"role": "user", "content": prompt_dsl}],
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Error during LLM DSL generation: {e}")
        return "Error: Failed to generate DSL."


# -----------------------------------
