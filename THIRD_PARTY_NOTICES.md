# Third-Party Notices

The MIT License in [`LICENSE`](LICENSE) covers the original code in this
repository. This file lists material in the repository that was not written by
the repository author, or that was produced by someone else's tool or model.
That material is under its own terms, as described below.

Last reviewed: 17 November 2026, against the tree at commit `e3907b3`.
Provenance was established from git history (`git log`, `git show`,
`git log -S`) and by comparing files against the upstream sources linked below.

---

## 1. Code

### 1.1 `geo_lm/parsers/pdf.py`: `validate_pdf()` and `extract_text_from_pdf()`

| | |
|---|---|
| Original source | Meta `llama-cookbook`, [`end-to-end-use-cases/NotebookLlama/Step-1 PDF-Pre-Processing-Logic.ipynb`](https://github.com/meta-llama/llama-cookbook/blob/main/end-to-end-use-cases/NotebookLlama/Step-1%20PDF-Pre-Processing-Logic.ipynb) |
| Copyright | Copyright (c) Meta Platforms, Inc. and affiliates |
| Licence | MIT (full text below) |
| Contributed by | Gain (GitHub `gain9999`), commit `fc24b04` (3 May 2025), in the notebook `llama_api_text_image_pdf.ipynb`. The notebook cited the upstream source in a comment. |

How it reached the current file:

1. `fc24b04` (3 May 2025, `gain9999`): the notebook includes both functions, with
   changes to the upstream code. `max_chars` defaults to `-1`, and a
   `max_chars != -1` guard means "no limit". The page loop is wrapped in a
   `tqdm` progress bar. The per-page `print` is commented out.
2. `02e8c8a` (4 May 2025): both functions were copied into
   `hutton_lm/pdf_parser.py`, keeping the source URL comment.
3. `7327eb3` (15 Jan 2026): the file was moved to `geo_lm/parsers/pdf.py`.
   That change added docstrings, removed inline comments and **removed the
   source URL comment**.

The current file still contains the upstream logic, its log messages, and all
three changes `gain9999` made to the upstream code (step 1 above). Note that `fc24b04` predates
the addition of `LICENSE` to this repository (`c8e80a1`, later the same day).

<details>
<summary>MIT License — meta-llama/llama-cookbook</summary>

```
MIT License

Copyright (c) Meta Platforms, Inc. and affiliates

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

</details>

### 1.2 Remainder of the `gain9999` notebook: not present

The notebook was deleted in `8a73e42`. Its other functions were
`get_llm_response()` (itself adapted from llama-cookbook's
`whatsapp_llama_4_bot/ec2_services.py`), `encode_image_to_base64()` and
`extract_images_from_pdf()`. A `git log -S` search on their distinctive lines
shows none of them in the current tree.

`LlamaProvider` in `geo_lm/ai/providers/openai.py` calls the same public Llama
API OpenAI-compatible endpoint (`https://api.llama.com/compat/v1/`) that first
appears in the notebook. It is separately written class-based async code,
though, and shares no code with the notebook beyond the endpoint URL and
standard `openai` SDK calls. The model name it uses was already in the
repository before the notebook (`dece1c3`).

### 1.3 Frontend scaffold (`web/`)

| Files | Source | Licence |
|---|---|---|
| `web/.gitignore` (identical), `web/index.html`, `web/vite.config.ts`, `web/tsconfig.json`, `web/tsconfig.node.json` | `create-vite` `react-ts` template boilerplate, adapted ([vitejs/vite](https://github.com/vitejs/vite/tree/main/packages/create-vite)) | MIT |
| `geo` colour scale in `web/tailwind.config.js` | Tailwind CSS default `sky` palette values | MIT |

### 1.4 Root `.gitignore`

Its Python sections follow GitHub's
[`Python.gitignore`](https://github.com/github/gitignore/blob/main/Python.gitignore)
template (CC0-1.0).

---

## 2. Data

### 2.1 `input-data/default/default_points.csv` and `default_orientations.csv`: GemPy tutorial data

| | |
|---|---|
| Source | GemPy, `examples/data/input_data/tut-ch1-4/tut_ch1-4_points.csv` and `tut_ch1-4_orientations.csv` ([permalink](https://github.com/gempy-project/gempy/tree/eb3b213bf79f5e3fec13bc12e9582a710c572de5/examples/data/input_data/tut-ch1-4)), used by the tutorial [`ch1_4_onlap_relations.py`](https://github.com/gempy-project/gempy/blob/eb3b213bf79f5e3fec13bc12e9582a710c572de5/examples/tutorials/ch1_fundamentals/ch1_4_onlap_relations.py) |
| Match | Byte-identical (same SHA-1) to the upstream files, which were added upstream on 16 Aug 2023 (`e9c7a89`) |
| Copyright | The GemPy developers |
| Licence | [EUPL-1.2](https://interoperable-europe.ec.europa.eu/collection/eupl/eupl-text-eupl-12), the licence of the `gempy-project/gempy` repository |

Identical copies are also published in
[`cgre-aachen/gempy_data`](https://github.com/cgre-aachen/gempy_data) as
`data/gempy_models/Tutorial_ch1-8_Onlap_relations/Tutorial_ch1-8_Onlap_relations_{surface_points,orientations}.csv`.
That repository is licensed **LGPL-3.0**.

### 2.2 `input-data/default/default_structure.csv`: derived from the same tutorial

The repository author wrote this file (`8f70e88`). Its content transcribes the
structural stack defined in the GemPy tutorial in 2.1: `seafloor_series`/ERODE,
`right_series`/ONLAP, `onlap_series`/ERODE and `left_series`/BASEMENT.

### 2.3 `input-data/example_geological_description.txt`: LLM summary of a published article

- A summary of Redmond, P. B. & Einaudi, M. T. (2010), *The Bingham Canyon
  Porphyry Cu-Mo-Au Deposit. I.*, Economic Geology 105(1): 43–68,
  doi:[10.2113/gsecongeo.105.1.43](https://doi.org/10.2113/gsecongeo.105.1.43)
  (published by the Society of Economic Geologists).
- About 43% of its words fall in runs of eight or more words copied verbatim
  from the article's text.
- It was added in `02e8c8a` (4 May 2025), alongside a Llama-4-Maverick
  consolidation prompt. The generating model is **probably**
  `Llama-4-Maverick-17B-128E-Instruct-FP8`, but this is not recorded.

### 2.4 `input-data/default_geological_description.txt`: origin not recorded

Added in `02e8c8a` (4 May 2025). It shares no verbatim 8-word runs with the
article in 2.3 and is not GemPy data. Git history does not record whether the
author wrote it by hand or generated it with an LLM.

### 2.5 `input-data/llm-generated/`: model output

| | |
|---|---|
| Contents | 362 CSVs: 124 `points_*`, 124 `orientations_*` and 114 `structure_*` |
| Generated | 3–5 May 2025 (timestamps in the file names) |
| Model | `Llama-4-Maverick-17B-128E-Instruct-FP8` (Meta Llama 4), via Meta's Llama API |
| Evidence | This is the only model identifier in any LLM-calling code during the generation period. It is hard-coded in `data-to-3d-model-input.py` and `hutton_lm/llm_interface.py` with no override option. |
| Terms | Generated under Meta's terms for the Llama API and Llama 4 models at that time |

The "default" prompt gave the GemPy tutorial data in 2.1 as an example and
asked for small modifications. Most outputs are new values. Four `points_*`
files and two `orientations_*` files reuse 25–75% of the tutorial's
coordinates. The `structure_*` files follow the format of 2.2.

---

## 3. Images (`static/`)

| File | Origin | Notes |
|---|---|---|
| `image.png` | **AI-generated** with GPT-4o in ChatGPT (OpenAI). Embedded C2PA Content Credentials record `c2pa.created` by "GPT-4o"/"ChatGPT", with IPTC source type `trainedAlgorithmicMedia`. | Not used in the README. |
| `image2.png` | Evidently an edited variant of the same AI-generated diagram: same style, 1536 px wide, no C2PA data kept. Origin inferred. | Contains the **Meta logo and "Llama 4" name**, which are Meta Platforms, Inc. trademarks. |
| `image3.png`, `image4.png` | Hand-composited from the image above; paste-up edges are visible. | Contain the **Meta logo and "Llama 4" name**. `image4.png` is the README logo. |
| `examples-gif.gif` | Screen recording of GemPy/PyVista 3D renders of models produced by this project. The first frame shows the GemPy tutorial dataset in 2.1. | Not third-party imagery. |

The README's "Examples" image is hosted on GitHub (`github.com/user-attachments/...`),
is not stored in this repository, and was not reviewed.

---

## 4. Dependencies

These are not included in this repository; they are installed by Poetry and npm.
Licences were taken from PyPI and npm registry metadata for the locked versions
and checked against the upstream repositories.

### 4.1 Python: direct dependencies (`pyproject.toml`)

> **Copyleft:** `gempy` and `gempy-viewer` are licensed under **EUPL-1.2**, a
> copyleft licence.

| Package | Constraint | Locked | Licence |
|---|---|---|---|
| gempy | ^2024.2.0.2 | 2024.2.0.2 | **EUPL-1.2** (copyleft) |
| gempy-viewer | ^2025.1.1 | 2025.1.6 | **EUPL-1.2** (copyleft) |
| plotly | ^6.0.1 | 6.5.1 | MIT |
| pyvista | ^0.45.0 | 0.45.3 | MIT |
| numpy | ^2.2.5 | 2.4.1 | BSD-3-Clause (wheels also bundle 0BSD, MIT, Zlib and CC0-1.0 components) |
| pandas | ^2.2.3 | 2.3.3 | BSD-3-Clause |
| scipy | ^1.15.2 | 1.17.0 | BSD-3-Clause |
| torch | ^2.7.0 | 2.7.1 | BSD-3-Clause |
| openai | ^1.77.0 | 1.109.1 | Apache-2.0 |
| pypdf2 | ^3.0.1 | 3.0.1 | BSD-3-Clause |
| lark | ^1.1.9 | 1.3.1 | MIT |
| fastapi | ^0.115.0 | 0.115.14 | MIT |
| uvicorn | ^0.32.0 | 0.32.1 | BSD-3-Clause |
| pydantic-settings | ^2.6.0 | 2.12.0 | MIT |
| anthropic | ^0.40.0 | 0.40.0 | MIT |
| langgraph | ^0.2.0 | 0.2.76 | MIT |
| aiosqlite | ^0.20.0 | 0.20.0 | MIT |
| python-multipart | ^0.0.12 | 0.0.12 | Apache-2.0 |
| python-dotenv | ^1.0.0 | 1.0.1 | BSD-3-Clause |

Development dependencies:

| Package | Constraint | Locked | Licence |
|---|---|---|---|
| pytest | ^8.3.0 | 8.4.2 | MIT |
| pytest-asyncio | ^0.24.0 | 0.24.0 | Apache-2.0 |
| httpx | ^0.28.0 | 0.28.1 | BSD-3-Clause |

The code also imports two packages directly that `pyproject.toml` does not
declare; they are installed as transitive dependencies:

| Package | Licence |
|---|---|
| tqdm (`geo_lm/parsers/pdf.py`) | MPL-2.0 AND MIT |
| pydantic | MIT |

### 4.2 npm: direct dependencies (`web/package.json`)

| Package | Constraint | Locked | Licence |
|---|---|---|---|
| @react-three/drei | ^9.122.0 | 9.122.0 | MIT |
| @react-three/fiber | ^8.18.0 | 8.18.0 | MIT |
| @tanstack/react-query | ^5.59.0 | 5.90.17 | MIT |
| @uiw/react-codemirror | ^4.23.5 | 4.25.4 | MIT |
| clsx | ^2.1.1 | 2.1.1 | MIT |
| lucide-react | ^0.454.0 | 0.454.0 | ISC |
| react | ^18.3.1 | 18.3.1 | MIT |
| react-dom | ^18.3.1 | 18.3.1 | MIT |
| react-dropzone | ^14.3.5 | 14.3.8 | MIT |
| react-router-dom | ^6.28.0 | 6.30.3 | MIT |
| three | ^0.182.0 | 0.182.0 | MIT |
| zustand | ^5.0.1 | 5.0.10 | MIT |

Development dependencies:

| Package | Constraint | Locked | Licence |
|---|---|---|---|
| @types/react | ^18.3.12 | 18.3.27 | MIT |
| @types/react-dom | ^18.3.1 | 18.3.7 | MIT |
| @types/three | ^0.182.0 | 0.182.0 | MIT |
| @typescript-eslint/eslint-plugin | ^8.13.0 | 8.53.0 | MIT |
| @typescript-eslint/parser | ^8.13.0 | 8.53.0 | MIT |
| @vitejs/plugin-react | ^4.3.3 | 4.7.0 | MIT |
| autoprefixer | ^10.4.20 | 10.4.23 | MIT |
| eslint | ^9.14.0 | 9.39.2 | MIT |
| eslint-plugin-react-hooks | ^5.0.0 | 5.2.0 | MIT |
| eslint-plugin-react-refresh | ^0.4.14 | 0.4.26 | MIT |
| postcss | ^8.4.47 | 8.5.6 | MIT |
| tailwindcss | ^3.4.14 | 3.4.19 | MIT |
| typescript | ^5.6.3 | 5.9.3 | Apache-2.0 |
| vite | ^5.4.10 | 5.4.21 | MIT |
