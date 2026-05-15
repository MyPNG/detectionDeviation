# REG Pipeline Code Demo Script

This script is for explaining the code first. The actual demo run can come at the end later.

## 1. Start With The REG Runner

Open: `pipeline/run_reg_pipeline.py`

Show lines 3-15.

Say:

> This file is the beginner-friendly entry script for the REG preparation pipeline. It describes the whole flow: load regulation input, extract requirements, run deontic slot extraction, filter main slots, build the graph, and visualize it.

Show lines 23-37.

Say:

> This is the code-first configuration. We define the project root, choose the regulation input folder, decide whether PDF-to-JSON conversion is needed, and choose the main articles plus context articles.

Show lines 39-45.

Say:

> Here the script creates the pipeline object. `RegPrepPipeline` receives all user-level settings, so the rest of the code can run the steps consistently.

Show lines 47-56.

Say:

> This is the actual demo run call. Each step can be enabled or disabled. For the explanation part, I will not run it yet; I first show how the code works.

## 2. Show The Main Orchestrator

Open: `pipeline/Orchestrate_RegPrepPipeline.py`

Show lines 10-19.

Say:

> This is the main REG preparation pipeline class. The runner script delegates to this class. The docstring shows the same flow as the runner: optional PDF-to-JSON conversion, requirement extraction, deontic slot extraction, main-slot filtering, graph building, and graph visualization.

Show lines 21-33.

Say:

> The constructor takes the user parameters: project root, input name or path, whether the input is a PDF, which articles are the main articles, which articles are context articles, and the local LLM settings for deontic processing.

Show lines 39-51.

Say:

> The orchestrator imports the worker classes here. This is useful for the demo because it shows that the pipeline itself does not do every task directly. It coordinates specialized classes: `RequirementsExtractor`, `DeonticSlotExtractor`, `MainRequirementsSlotFilter`, `RequirementsGraphBuilder`, `GraphVisualizer`, and `DoclingProcessor`.

Show lines 56-60.

Say:

> Here the selected articles are configured. `main_articles` are the legal constraints we want to compare against REA later. `depth_one_articles` are additional context articles. The extended article list is main plus context, with duplicates removed.

Show lines 71-80.

Say:

> These lines define all generated output files. The pipeline produces main requirements, extended requirements, deontic slots, filtered main slots, graph JSON/GraphML, and an HTML visualization.

## 3. Explain Input Handling

Open: `pipeline/Orchestrate_RegPrepPipeline.py`

Show lines 94-130.

Say:

> These helper methods validate the input. If the user set `pdf_to_json=True`, the pipeline expects a PDF. Otherwise it expects a JSON file. This prevents silent wrong input usage.

Show lines 132-162.

Say:

> This optional step converts a PDF into markdown and then into Docling JSON. The important thing is that the rest of the pipeline always works with structured JSON, regardless of whether the original input was PDF or JSON.

## 4. Explain Requirement Extraction

Open: `pipeline/Orchestrate_RegPrepPipeline.py`

Show lines 164-215.

Say:

> This method runs `RequirementsExtractor`. It creates two files: one for main articles and one for extended articles. If no context articles are selected, the pipeline writes the same content to both files so main and extended are identical.

Open: `pipeline/01_preprocessing/reg_prep/01_extracting/RequirementsExtractor.py`

Show lines 140-146.

Say:

> `RequirementsExtractor` starts by loading the Docling JSON. It keeps two important structures: `texts`, which contain the actual text blocks, and `groups`, which say which blocks belong together.

Show lines 148-162.

Say:

> spaCy is loaded if available. It is not an LLM, so it does not hallucinate. It is used only as a parser for sentence and subject hints. If it is missing, the extractor continues with rule-based fallback.

Show lines 188-226.

Say:

> The extractor first detects article boundaries. It scans section headers like `Article 13`, records their text indices, and knows which later text blocks belong to which article.

Show lines 228-252.

Say:

> These two methods decide whether a list item is a normal paragraph or a bullet point like `(a)`, `(b)`. That matters because bullet points are kept as separate requirements but can inherit context from the paragraph intro.

Show lines 261-277.

Say:

> Docling groups contain references to text indices. This method resolves those references so the extractor can move from group metadata to the actual legal text.

Show lines 284-309.

Say:

> The extractor detects modal signals such as `shall`, `must`, `may`, and `shall not`. It keeps the exact modal verb in parentheses, for example `Mandatory(shall)`.

Show lines 342-401.

Say:

> This part detects legal references such as `Article 14(3)(a)` or `point (d) of paragraph 2`. These references later become graph edges.

Show lines 449-533.

Say:

> This is the modality splitter. If a paragraph contains multiple deontic clauses, it splits them into requirement units around modal verbs, semicolons, and connectors. It also stores whether the relation is `SEQUENCE`, `AND`, `OR`, or another logical relation.

Show lines 593-660.

Say:

> This is lightweight anaphora handling. It tries to resolve sentence-initial pronouns such as `It` or `This` using the previous subject. spaCy can help find the subject, but there is also a regex fallback.

Show lines 749-838.

Say:

> This is the main extraction loop. It walks through Docling groups, keeps list items, assigns article and paragraph numbers, resolves text, adds bullet context, splits by modality, and creates temporary requirement rows.

Show lines 842-907.

Say:

> After extraction, the rows receive final IDs like `REG-001`. The extractor also builds parent-child links, logical relations between split clauses, and reference lists.

Show lines 909-930.

Say:

> These save methods write the final requirement JSON files. `save_requirements_dual` is what the orchestrator uses to create main and extended requirement files.

## 5. Explain Deontic Stage 1-4

Open: `pipeline/Orchestrate_RegPrepPipeline.py`

Show lines 217-266.

Say:

> After requirements are extracted, the orchestrator runs `DeonticSlotExtractor` on the extended requirements. First it runs stage 1-3 and saves a passive-active report. Then stage 4 extracts slots.

Open: `pipeline/01_preprocessing/reg_prep/01_extracting/DeonticSlotExtractor.py`

Show lines 18-33.

Say:

> `DeonticSlotExtractor` is the clean public class. It is intentionally thin. It delegates to smaller modules and to the legacy engine so the pipeline stays stable while the code is being simplified.

Show lines 41-63.

Say:

> The constructor creates the internal legacy engine and attaches the modular stage wrappers. These wrappers are the organized interface for IO, text normalization, modal detection, splitting, stage 1-3, stage 4, and LLM calls.

Show lines 72-91.

Say:

> These are the methods the rest of the pipeline uses. `run_passive_active_pipeline_on_file` runs stage 1-3. `run` runs stage 4 slot extraction.

Open: `pipeline/01_preprocessing/reg_prep/01_extracting/DeonticSlotExtractorLegacy.py`

Show lines 120-140.

Say:

> The legacy engine stores the local LLM endpoint, model name, retry settings, modal rules, temporal phrase rules, and optional spaCy parser. The default LLM endpoint is an Ollama-compatible local endpoint.

Show lines 143-154.

Say:

> spaCy is loaded as a best-effort parser. If `en_core_web_sm` is unavailable, the code simply falls back to regex and rule-based behavior.

Show lines 1396-1412.

Say:

> Stage 1 is rule-based. It normalizes modal phrases, injects missing subjects for connector fragments, and resolves simple anaphora. It does not convert passive voice and it does not add new legal meaning.

Show lines 1414-1431.

Say:

> Stage 3 converts passive voice to active voice using the local LLM. The code builds a prompt, calls the Ollama-compatible endpoint, extracts JSON, and post-processes the result with safeguards.

Show lines 1847-1914.

Say:

> Temporal extraction in stage 4 is rule-first. It first checks the temporal phrase rule list, then uses spaCy to inspect temporal prepositional or adverbial attachments, and finally falls back to regex patterns like `within 72 hours`.

Show lines 1933-1968.

Say:

> Action extraction also uses spaCy when available. It looks for verbs near modal words. If spaCy cannot help, it falls back to a regex pattern like `shall provide`.

Show lines 1970-2001.

Say:

> Modal force is detected from configured modal rules. This maps words like `shall`, `may`, and `shall not` to labels like `Mandatory`, `Permissive`, and `Prohibited`.

Show lines 2003-2055.

Say:

> This is the rule-based slot extraction row. For each requirement, it extracts actor, modal, action, action list, object, temporal, manner, and condition. It also assigns confidence values for the extracted slots.

Show lines 2122-2183.

Say:

> Stage 4 is hybrid. It first extracts slots deterministically, then selects low-confidence rows for LLM fallback. Finally, it merges rule output and LLM output and checks for invented words.

Show lines 2185-2236.

Say:

> This method runs stage 4 over the whole input file. It groups requirements by article and paragraph, extracts slots for each group, collects failures and audit information, and writes the final slot JSON.

## 6. Explain Main Slot Filtering

Open: `pipeline/Orchestrate_RegPrepPipeline.py`

Show lines 268-276.

Say:

> The extended slot file includes main articles and context articles. This step keeps only the slots whose REG IDs appear in the main requirement file. That output becomes the REG index used for retrieval later.

## 7. Explain Graph Output

Open: `pipeline/Orchestrate_RegPrepPipeline.py`

Show lines 278-289.

Say:

> The graph builder uses the extended requirement file because graph context needs both main constraints and context constraints. It produces GraphML and JSON.

Show lines 291-300.

Say:

> The visualizer loads the graph and writes an HTML file so we can inspect references, parent-child edges, and logical relations visually.

## 8. End With The Run Method

Open: `pipeline/Orchestrate_RegPrepPipeline.py`

Show lines 302-353.

Say:

> The `run` method is the full pipeline controller. Each step can be enabled or skipped. This is what makes the notebook easy to use: the user can run everything, or rerun only a later step.

## Demo Run Placeholder

Say:

> After explaining the code, I would run the pipeline from the notebook or from `run(...)` and show the generated files in `intermediate_results/01_preprocessing/reg_prep/.../<reg_input_name>/`. For the first live demo, I would keep `send_prompt` or GPT calls out of scope and focus on deterministic preprocessing outputs.
