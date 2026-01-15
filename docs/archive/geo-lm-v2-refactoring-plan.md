# geo-lm v2 Refactoring Plan

**Date**: 2026-01-11
**Status**: Planning Complete - Awaiting Approval

## Overview

Refactor geo-lm from a primitive prototype into a full-stack application with:
- **FastAPI REST API** backend
- **React + Vite** frontend with simple web UI
- **SQLite** database for persistence
- **LangGraph** workflows for document processing
- **Proper DSL parser** with validation

All development stays **LOCAL** - no pushing to remote.

---

## Phase 1: Foundation & Security Fixes

### 1.1 Create New Package Structure
```
geo_lm/
├── __init__.py
├── config.py                    # Pydantic settings, env vars
├── exceptions.py                # Custom exceptions
├── domain/                      # Domain models
│   ├── base.py                  # ObjectModel base (adapted from open-notebook)
│   ├── document.py              # Document, DocumentChunk
│   ├── geological_model.py      # GeologicalModel, SurfacePoint, Orientation
│   └── dsl.py                   # DSL AST nodes
├── database/
│   ├── repository.py            # SQLite repository pattern
│   ├── connection.py            # Connection management
│   └── migrations/              # Schema migrations
├── ai/
│   ├── models.py                # ModelManager
│   ├── providers/
│   │   ├── base.py              # BaseLLMProvider ABC
│   │   ├── anthropic.py         # Claude provider
│   │   └── openai.py            # OpenAI provider
│   └── prompts/                 # Prompt templates
├── parsers/
│   ├── pdf.py                   # PDF extraction (refactored)
│   └── dsl/                     # DSL parser module
│       ├── grammar.lark         # Lark grammar
│       ├── parser.py            # Parser implementation
│       ├── validator.py         # Semantic validation
│       └── ast.py               # AST classes
├── graphs/                      # LangGraph workflows
│   ├── document.py              # PDF → DSL pipeline
│   └── gempy.py                 # DSL → GemPy pipeline
├── services/                    # Business logic
│   ├── document_service.py
│   ├── dsl_service.py
│   └── gempy_service.py
└── utils/
    └── text.py
```

### 1.2 CRITICAL: Remove Hardcoded Credentials
**File**: `hutton_lm/llm_interface.py` lines 398-399, 493-494

Replace hardcoded API keys with environment variables:
```python
# BEFORE (INSECURE)
api_key="LLM|1092127122939929|swnut7Dzo4N-CdXCmXFLKxWJC9s"

# AFTER
api_key=os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
```

### 1.3 Configuration Management
Create `geo_lm/config.py`:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_path: str = "./data/geo_lm.db"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    default_model: str = "claude-sonnet-4-20250514"
    uploads_dir: str = "./uploads"

    class Config:
        env_prefix = "GEO_LM_"
        env_file = ".env"
```

---

## Phase 2: Database & Domain Models

### 2.1 SQLite Schema
```sql
-- Core tables
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    source_path TEXT,
    raw_text TEXT,
    consolidated_text TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dsl_documents (
    id INTEGER PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    raw_dsl TEXT NOT NULL,
    is_valid BOOLEAN DEFAULT FALSE,
    validation_errors TEXT
);

CREATE TABLE geological_models (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    dsl_document_id INTEGER REFERENCES dsl_documents(id),
    status TEXT DEFAULT 'pending'
);

CREATE TABLE surface_points (
    id INTEGER PRIMARY KEY,
    model_id INTEGER REFERENCES geological_models(id),
    x REAL, y REAL, z REAL,
    surface TEXT NOT NULL
);

CREATE TABLE orientations (
    id INTEGER PRIMARY KEY,
    model_id INTEGER REFERENCES geological_models(id),
    x REAL, y REAL, z REAL,
    azimuth REAL, dip REAL, polarity REAL,
    surface TEXT NOT NULL
);
```

### 2.2 ObjectModel Base Class
Adapt from `open-notebook/open_notebook/domain/base.py`:
- Pydantic BaseModel with SQLite CRUD
- `save()`, `get()`, `delete()` methods
- Async-first design

---

## Phase 3: LLM Abstraction Layer

### 3.1 Provider Abstraction
```python
class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str: ...

class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)

class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = openai.OpenAI(api_key=api_key)
```

### 3.2 ModelManager
```python
class ModelManager:
    async def get_model(self, model_id: str = None) -> BaseLLMProvider:
        # Returns configured provider based on settings
```

---

## Phase 4: DSL Parser & Validator

### 4.1 Lark Grammar (`geo_lm/parsers/dsl/grammar.lark`)
Preserve current DSL syntax:
```lark
start: statement*
statement: rock_stmt | deposition_stmt | erosion_stmt | intrusion_stmt

rock_stmt: "ROCK" ID "[" rock_body "]"
deposition_stmt: "DEPOSITION" ID "[" event_body "]"
erosion_stmt: "EROSION" ID "[" erosion_body "]"
intrusion_stmt: "INTRUSION" ID "[" intrusion_body "]"
```

### 4.2 AST Classes
```python
@dataclass
class RockDefinition:
    id: str
    name: str
    rock_type: RockType  # sedimentary, volcanic, intrusive, metamorphic
    age: TimeValue | None

@dataclass
class DepositionEvent:
    id: str
    rock_id: str
    time: TimeValue | None
    after: list[str]
```

### 4.3 Validation
- Check all ID references are defined
- Detect circular dependencies in `after:` chains
- Verify temporal consistency (absolute ages vs ordering)

---

## Phase 5: LangGraph Workflows

### 5.1 Document Processing Workflow
Pattern from `open-notebook/open_notebook/graphs/source.py`:

```python
class DocumentState(TypedDict):
    document_id: int
    raw_text: str | None
    consolidated_text: str | None
    dsl_text: str | None
    errors: list[str]

workflow = StateGraph(DocumentState)
workflow.add_node("extract_text", extract_text)
workflow.add_node("consolidate", consolidate_text)
workflow.add_node("generate_dsl", generate_dsl)
workflow.add_node("validate_dsl", validate_dsl)

workflow.add_edge(START, "extract_text")
workflow.add_edge("extract_text", "consolidate")
workflow.add_edge("consolidate", "generate_dsl")
workflow.add_conditional_edges("validate_dsl", should_retry, ["generate_dsl", END])
```

---

## Phase 6: REST API

### 6.1 FastAPI Structure
```
api/
├── __init__.py
├── main.py              # FastAPI app
├── models.py            # Pydantic schemas
└── routers/
    ├── documents.py     # POST /documents, GET /documents/{id}
    ├── dsl.py           # POST /dsl/parse, POST /dsl/validate
    ├── models.py        # POST /models, GET /models/{id}
    └── workflows.py     # POST /workflows/process
```

### 6.2 Key Endpoints
```
POST   /api/documents              Upload PDF
GET    /api/documents/{id}         Get document
POST   /api/documents/{id}/process Run full pipeline
GET    /api/dsl/{id}               Get DSL
POST   /api/dsl/validate           Validate DSL text
POST   /api/models/{id}/compute    Run GemPy
```

---

## Phase 7: Frontend

### 7.1 Technology Stack
- **React 18 + Vite** (simpler than Next.js for prototype)
- **TypeScript**
- **Zustand** for state
- **TanStack Query** for data fetching
- **Tailwind + Shadcn/ui** for styling
- **CodeMirror 6** for DSL syntax highlighting

### 7.2 Structure
```
web/
├── package.json
├── vite.config.ts
├── src/
│   ├── App.tsx
│   ├── api/
│   │   └── client.ts
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── ProjectView.tsx
│   │   └── ModelViewer.tsx
│   └── components/
│       ├── DocumentUpload.tsx
│       ├── DSLEditor.tsx
│       └── ProcessingPanel.tsx
```

### 7.3 Development
```bash
# Backend
poetry run uvicorn api.main:app --reload --port 8000

# Frontend (with proxy to backend)
cd web && npm run dev  # port 5173
```

---

## Phase 8: Migration & Testing

### 8.1 Preserve Existing CLI
Keep `hutton_lm/cli.py` functional, refactor to use new services.

### 8.2 Testing Infrastructure
- Add `pytest` to dev dependencies
- Test DSL parser with known inputs
- Test validation error cases
- Integration tests for workflows

---

## Critical Files to Modify

| File | Changes |
|------|---------|
| `hutton_lm/llm_interface.py` | Remove hardcoded API keys (SECURITY), extract prompts to templates |
| `hutton_lm/cli.py` | Refactor to use new services |
| `hutton_lm/model_builder.py` | Wrap in service layer |
| `pyproject.toml` | Add new dependencies (lark, fastapi, pydantic-settings, anthropic) |

---

## New Files to Create

1. `geo_lm/config.py` - Configuration management
2. `geo_lm/domain/base.py` - ObjectModel base class
3. `geo_lm/ai/providers/*.py` - LLM provider abstraction
4. `geo_lm/parsers/dsl/*.py` - DSL parser module
5. `geo_lm/graphs/document.py` - LangGraph workflow
6. `api/main.py` - FastAPI application
7. `web/` - Frontend application

---

## Dependencies to Add

```toml
[tool.poetry.dependencies]
# New
lark = "^1.1.9"
fastapi = "^0.115.0"
uvicorn = "^0.32.0"
pydantic-settings = "^2.6.0"
anthropic = "^0.40.0"
langgraph = "^0.2.0"
aiosqlite = "^0.20.0"
```

---

## Future Considerations (Not in This Refactor)

Per Parquer et al. paper on "Checking the consistency of 3D geological models", prepare for:
- **Spatial relations** (meets, contains, overlaps) - from 9-intersection model
- **Temporal relations** (precedes, overlaps, during) - from Allen's interval algebra
- **Polarity relations** (aligned, opposed) - comparing internal and temporal polarity vectors

The DSL parser is designed to be extensible with:
- New statement types (FAULT, FOLD, METAMORPHISM)
- Constraint validation layer using relational logic
- Relational constraint inference for generation (not just validation)

Key insight from the paper: Use the three-dimensional relation space (spatial × temporal × polarity) to **constrain the generation space** rather than post-generate and filter.

---

## Verification Strategy

1. **Unit Tests**: DSL parser, validator, serializer
2. **Integration Tests**: Full workflow (PDF → DSL → GemPy)
3. **Manual Testing**:
   - Upload test PDF (Bingham Canyon paper)
   - Verify text extraction
   - Verify DSL generation
   - Verify GemPy model output
4. **Frontend Testing**: Document upload, DSL editing, model visualization

---

## Implementation Order

1. Create branch `refactor/v2-architecture` (LOCAL ONLY)
2. Remove hardcoded credentials (CRITICAL SECURITY)
3. Create config management
4. Implement DSL parser with Lark
5. Create domain models and database layer
6. Implement LLM abstraction
7. Build LangGraph workflows
8. Create FastAPI endpoints
9. Build React frontend
10. Add tests
11. Migrate CLI to use new backend

---

## Reference Architecture

This plan draws heavily from the `open-notebook` project architecture:
- `/Users/williamdavis/Documents/Prototypes/open-notebook/open_notebook/domain/base.py` - ObjectModel pattern
- `/Users/williamdavis/Documents/Prototypes/open-notebook/open_notebook/graphs/source.py` - LangGraph workflow pattern
- `/Users/williamdavis/Documents/Prototypes/open-notebook/open_notebook/ai/models.py` - ModelManager pattern
