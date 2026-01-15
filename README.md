# geo-lm

A prototype language model interface for generating geological models!

![Logo|500](static/image4.png)

## Description

Leveraging the power of large language models and [GemPy](https://www.gempy.org/), `geo-lm` is a Python package designed for generative geology. It utilizes the latest advancements in large language models to understand geological information and translate it into 3D geological models.

## Functionality

`geo-lm` employs LLM multi-modal inference capabilities to automate the process of creating geological models from existing documentation. The workflow involves the following key steps:

1.  **Document Understanding:** The package can process geology reports and documents by reading OCRed text and interpreting extracted maps.
2.  **Geological Knowledge Consolidation:** The interpreted information for a specific locality is then consolidated into a structured "geology DSL" (Domain Specific Language). This DSL encodes crucial geological knowledge, including:
      * Lithology data (rock types and their properties)
      * Structural interpretations (faults, folds, unconformities)
      * Cross-cutting relations between geological units
      * Relative and absolute time-ordering of geological events.
3.  **3D Model Generation:** Finally, the geology DSL is parsed and used as input for [GemPy](https://www.gempy.org/), an open-source Python library for implicit geological modeling and 3D visualization. This allows for the automatic generation of 3D representations of subsurface geology.

## Examples

![Image](https://github.com/user-attachments/assets/1ad1886b-43a2-44f6-ab92-3c5c3de271aa)

---

## Installation

### Prerequisites

- Python 3.12+
- [Poetry](https://python-poetry.org/) for Python dependency management
- [Node.js](https://nodejs.org/) 18+ (for the web frontend)

### Backend Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/geo-lm.git
   cd geo-lm
   ```

2. Install Python dependencies with Poetry:
   ```bash
   poetry install
   ```

3. Copy the environment template and configure your API keys:
   ```bash
   cp .env.example .env
   ```

4. Edit `.env` and add your API keys:
   ```bash
   # Required: Set at least one LLM provider API key
   GEO_LM_ANTHROPIC_API_KEY=your-anthropic-api-key
   GEO_LM_OPENAI_API_KEY=your-openai-api-key
   LLAMA_API_KEY=your-llama-api-key
   ```

### Frontend Setup

1. Navigate to the web directory:
   ```bash
   cd web
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

---

## Running the Application

### Option 1: Full Stack (API + Web UI)

**Terminal 1 - Start the API server:**
```bash
poetry run uvicorn api.main:app --reload --port 8000
```

**Terminal 2 - Start the web frontend:**
```bash
cd web
npm run dev
```

Access the application:
- **Web UI:** http://localhost:5173
- **API Documentation:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/api/health

### Option 2: API Only

Run just the FastAPI backend:
```bash
poetry run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Option 3: CLI Mode (Legacy)

The original CLI interface is still available:

```bash
export LLAMA_API_KEY=<your-key-here>

poetry run python run.py \
    --input-mode llm \
    --prompt-type default \
    --llm-output-dir input-data/llm-generated
```

---

## API Endpoints

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/documents` | Create a new document |
| `POST` | `/api/documents/upload` | Upload a PDF document |
| `GET` | `/api/documents` | List all documents |
| `GET` | `/api/documents/{id}` | Get a specific document |
| `DELETE` | `/api/documents/{id}` | Delete a document |
| `POST` | `/api/documents/{id}/extract` | Extract text from PDF |

### DSL (Domain Specific Language)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/dsl/parse` | Parse and validate DSL text |
| `POST` | `/api/dsl/validate` | Validate DSL text |
| `POST` | `/api/dsl` | Create a DSL document |
| `GET` | `/api/dsl/{id}` | Get a DSL document |
| `GET` | `/api/dsl/grammar/spec` | Get DSL grammar specification |

### Workflows
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/workflows/{document_id}/process` | Start document processing pipeline |
| `GET` | `/api/workflows/{document_id}/status` | Get workflow status |

---

## Geology DSL Syntax

The geology DSL encodes geological knowledge in a structured format:

```dsl
# Rock definitions
ROCK R1 [ name: "Sandstone"; type: sedimentary; age: 100Ma ]
ROCK R2 [ name: "Limestone"; type: sedimentary; age: 90Ma ]
ROCK R3 [ name: "Granite"; type: intrusive; age: 50Ma ]

# Depositional events
DEPOSITION D1 [ rock: R1; time: 100Ma ]
DEPOSITION D2 [ rock: R2; time: 90Ma; after: D1 ]

# Erosional events
EROSION E1 [ time: 80Ma; after: D2 ]

# Intrusive events
INTRUSION I1 [ rock: R3; style: stock; time: 50Ma; after: E1 ]
```

### DSL Elements

| Element | Required Fields | Optional Fields |
|---------|-----------------|-----------------|
| `ROCK` | `name`, `type` | `age` |
| `DEPOSITION` | `rock` | `time`, `after` |
| `EROSION` | - | `time`, `after` |
| `INTRUSION` | `rock` | `style`, `time`, `after` |

### Rock Types
- `sedimentary`
- `volcanic`
- `intrusive`
- `metamorphic`

### Intrusion Styles
- `dike`
- `sill`
- `stock`
- `batholith`

### Age/Time Units
- `Ma` - Million years ago
- `ka` - Thousand years ago
- `Ga` - Billion years ago
- `"?"` - Unknown age

---

## Running Tests

```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest tests/test_dsl_parser.py

# Run with coverage
poetry run pytest --cov=geo_lm
```

---

## Project Structure

```
geo-lm/
├── api/                    # FastAPI REST API
│   ├── main.py             # Application entry point
│   ├── models.py           # Pydantic schemas
│   └── routers/            # API route handlers
├── geo_lm/                 # Core package
│   ├── config.py           # Configuration management
│   ├── domain/             # Domain models
│   ├── database/           # SQLite database layer
│   ├── ai/                 # LLM provider abstraction
│   ├── parsers/dsl/        # DSL parser (Lark grammar)
│   └── graphs/             # LangGraph workflows
├── hutton_lm/              # Legacy CLI package
├── web/                    # React + Vite frontend
│   ├── src/
│   │   ├── api/            # API client
│   │   ├── components/     # React components
│   │   └── pages/          # Page components
│   └── package.json
├── tests/                  # Test suite
├── .env.example            # Environment template
└── pyproject.toml          # Python dependencies
```

---

## Configuration

All configuration is managed through environment variables (prefix: `GEO_LM_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `GEO_LM_DATABASE_PATH` | `./data/geo_lm.db` | SQLite database path |
| `GEO_LM_ANTHROPIC_API_KEY` | - | Anthropic API key |
| `GEO_LM_OPENAI_API_KEY` | - | OpenAI API key |
| `LLAMA_API_KEY` | - | Llama API key |
| `GEO_LM_DEFAULT_MODEL` | `claude-sonnet-4-20250514` | Default LLM model |
| `GEO_LM_API_HOST` | `0.0.0.0` | API server host |
| `GEO_LM_API_PORT` | `8000` | API server port |
| `GEO_LM_DEBUG` | `true` | Enable debug mode |
| `GEO_LM_MAX_DSL_RETRIES` | `5` | Max DSL generation retries |
| `GEO_LM_LLM_TEMPERATURE` | `0.7` | LLM sampling temperature |

---

## Development

### Backend Development

```bash
# Run with auto-reload
poetry run uvicorn api.main:app --reload

# Format code
poetry run black .

# Type checking
poetry run mypy geo_lm
```

### Frontend Development

```bash
cd web

# Development server with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint
npm run lint
```

---

## Notes on Testing

This repo was originally tested on the following paper:

Patrick B. Redmond, Marco T. Einaudi; The Bingham Canyon Porphyry Cu-Mo-Au Deposit. I. Sequence of Intrusions, Vein Formation, and Sulfide Deposition. Economic Geology 2010;; 105 (1): 43–68. doi: https://doi.org/10.2113/gsecongeo.105.1.43

---

## Contributing

We welcome contributions to `geo-lm`! If you have ideas for improvements, new features, or bug fixes, please feel free to open an issue or submit a pull request.

---

## Notes

This package was originally called `hutton-lm`, but was renamed to `geo-lm`.
