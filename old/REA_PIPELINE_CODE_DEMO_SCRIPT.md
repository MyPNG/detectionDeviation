# REA Pipeline Code Demo Script

This script explains how the REA pipeline works before doing a live demo run. The demo run itself can come at the end later.

## 1. Start With The REA Runner

Open: `pipeline/run_rea_pipeline.py`

Show lines 3-14.

Say:

> This file is the beginner-friendly entry script for the REA pipeline. The docstring shows the four main blocks: REA preprocessing, retrieval, graph context traversal, and reasoning preparation. The important safety point is that `send_prompts=False` by default, so no GPT API call is made unless we explicitly enable it.

Show lines 26-38.

Say:

> This is the code-first configuration. We choose the REA input folder, the prepared REG input, article settings, retrieval sizes, the prompt model name, and whether prompt sending is enabled.

Show lines 40-42.

Say:

> These two files are expected from the REG pipeline: the main REG slots file for retrieval, and the REG graph JSON for graph context.

Show lines 44-60.

Say:

> The REA pipeline is run in blocks. Block 1 prepares REA texts. Block 2 performs stage 4 slot extraction, vector search, and reranking. Block 3 adds graph context. Block 4 generates prompts, and optionally sends them to the LLM.

## 2. Show The Main REA Orchestrator

Open: `pipeline/Orchestrate_ReaPipelines.py`

Show lines 13-19.

Say:

> `InjectionAutoPipeline` is the main REA orchestrator. It connects a realization document, called REA here, to an already prepared regulatory document, called REG.

Show lines 21-35.

Say:

> The constructor exposes the key user parameters: REA input name, REG input name, main/context articles, dense retrieval size, reranking size, prompt top-k, and whether LLM prompts should be sent.

Show lines 52-70.

Say:

> These are the worker classes used by the REA pipeline. The orchestrator does not do every task itself. It coordinates extraction, REA deontic stages, vector retrieval, reranking, graph traversal, prompt preparation, prompt sending, and readable response formatting.

Show lines 74-91.

Say:

> These lines define all input and output folders. The folder names combine the REA input name and REG input name, so the outputs are traceable to the exact experiment.

Show lines 105-111.

Say:

> Before writing outputs, the pipeline clears old output folders by default. That means rerunning a block gives fresh output instead of mixing old and new files.

## 3. Explain REA Requirement Extraction

Open: `pipeline/Orchestrate_ReaPipelines.py`

Show lines 161-172.

Say:

> This method runs the REA requirements extractor over every chunk text file. The output is one JSON file per chunk under `intermediate_results/01_preprocessing/reaPrep/01_extracting/rearequirementsextractor/<rea_input_name>/`.

Open: `pipeline/01_preprocessing/reaPrep/01_extracting/ReaRequirementsExtractor.py`

Show lines 14-17.

Say:

> `ReaRequirementsExtractor` is much simpler than the REG extractor because REA input is already chunked text. It stores the input `.txt` path.

Show lines 35-98.

Say:

> The extractor reads the text line by line. If it sees explicit markers like `REA-01:`, it creates one row per marker. If the file has no REA marker, it falls back to one row for the whole chunk.

Show lines 100-124.

Say:

> `save_json` writes one chunk's extracted REA rows. `process_folder` applies this to all text chunks and creates the folder structure used by the later stages.

## 4. Explain REA Stage 1-4

Open: `pipeline/Orchestrate_ReaPipelines.py`

Show lines 174-200.

Say:

> There are three methods for REA deontic stages. One can run stage 1-4 all at once, but the pipeline usually separates stage 1-3 from stage 4. This lets us manually inspect or edit stage 3 output before slot extraction.

Show lines 404-427.

Say:

> These block methods make the notebook workflow clear. Block 1 runs extraction plus stage 1-3. Block 2 later runs stage 4, vector retrieval, and reranking. This is where manual review fits between block 1 and block 2.

Open: `pipeline/01_preprocessing/reaPrep/01_extracting/ReaDeonticStagePipeline.py`

Show lines 14-21.

Say:

> `ReaDeonticStagePipeline` adapts the shared deontic extractor for REA text. It runs the same conceptual stages: missing actor/anaphora handling, normalization, passive-active recovery, and slot extraction.

Show lines 31-37.

Say:

> The REA stage pipeline reuses `DeonticSlotExtractor`, so REG and REA slot extraction are aligned instead of using two unrelated implementations.

Show lines 63-76.

Say:

> This converts extracted REA rows into stage nodes with `ID` and `Text`. The downstream deontic extractor expects this simple shape.

Show lines 78-89.

Say:

> Before stage 1 processing, each REA text is split into smaller action units. This matters because one REA sentence can contain multiple obligations or actions.

Show lines 185-268.

Say:

> This is the REA-specific action splitter. It keeps coordinated verbs together when they belong to the same modal, for example `shall establish, implement, document and maintain`. It only splits when there is a new main action or a separate modal/action unit.

Show lines 286-335.

Say:

> This method turns one REA text into `REA-xx#n` sub-units. For example, one realization chunk can become `REA-02#1` and `REA-02#2`. These sub-IDs are important because retrieval and deviation detection happen per action unit.

Show lines 337-360.

Say:

> After splitting, missing actor and anaphora handling runs again. This is important because splitting can create smaller fragments that need local repair.

## 5. Explain Vector Search

Open: `pipeline/Orchestrate_ReaPipelines.py`

Show lines 256-305.

Say:

> This method embeds REG constraints and searches for the most relevant REG candidates for each REA sub-unit. It uses the main REG slots as the search corpus.

Open: `pipeline/02_processing/01_retrieval/VectorSearch.py`

Show lines 36-49.

Say:

> `VectorSearch` loads a sentence embedding model. The default is `BAAI/bge-large-en-v1.5`.

Show lines 136-161.

Say:

> The embedding text combines structured slots and raw text. This gives retrieval both semantic nuance from the original clause and structure from actor, action, object, modal, temporal, condition, and manner.

Show lines 196-258.

Say:

> `embed_and_store` encodes all REG objects and stores them in a persistent ChromaDB collection using cosine similarity.

Show lines 265-302.

Say:

> REA stage 4 rows are converted into query text. The code removes `[missing_subject]` placeholders before embedding so placeholder text does not distort retrieval.

Show lines 304-347.

Say:

> This method embeds one REA query and retrieves top REG matches from ChromaDB. It returns REG ID, article location, original REG text, embedding text, and similarity score.

Show lines 425-460.

Say:

> Folder mode applies vector search to every REA deontic-stage file and writes one retrieval JSON per REA sub-unit.

## 6. Explain Reranking

Open: `pipeline/Orchestrate_ReaPipelines.py`

Show lines 307-324.

Say:

> After dense vector search, the pipeline reranks the candidates. Dense retrieval gives broad recall, and reranking improves precision.

Open: `pipeline/02_processing/01_retrieval/Reranker.py`

Show lines 10-22.

Say:

> The reranker expects one REA query and a list of REG candidates. It rewrites the candidate order using a reranking model.

Show lines 65-82.

Say:

> For reranking, the query is the natural REA search query, and each candidate is the original REG text when available. That keeps reranking closer to the actual legal wording.

Show lines 102-149.

Say:

> This method calls the reranking API and returns candidates sorted by rerank relevance. Each result gets a rerank score and rank.

Show lines 223-255.

Say:

> This folder-level method reranks every retrieval file under the artifact output folder.

## 7. Explain Graph Context

Open: `pipeline/Orchestrate_ReaPipelines.py`

Show lines 326-338.

Say:

> After reranking, the pipeline expands each top REG match with graph neighbors. This gives the later LLM more legal context, such as related sequence nodes, parent/child clauses, and references.

Open: `pipeline/02_processing/02_graph_traversal/GraphTraversal.py`

Show lines 16-37.

Say:

> `GraphTraversal` defines the graph context policy. It uses `AND`, `REFERENCES`, `SEQUENCE`, and `PARENT_CHILD`. `OR` and `BELONGS_TO` are excluded from prompt graph context.

Show lines 129-155.

Say:

> This method takes the top reranked REG candidates, deduplicates them by REG ID, and treats them as the main constraints for prompt context.

Show lines 157-222.

Say:

> This expands one-hop neighbors. `REFERENCES` are followed outgoing. `AND`, `SEQUENCE`, and `PARENT_CHILD` can also bring in incoming or outgoing context depending on relation type.

Show lines 224-264.

Say:

> This is the parent-child sibling exception. If a main REG is a child, the pipeline also includes sibling clauses through the parent. This is useful when a legal list is split across multiple REG IDs.

Show lines 266-334.

Say:

> This method builds the final graph context object for one reranked REA file: main constraints, graph context neighbors, visited IDs, and allowed relation types.

## 8. Explain Prompt Preparation

Open: `pipeline/Orchestrate_ReaPipelines.py`

Show lines 340-364.

Say:

> Prompt generation uses reranked matches and graph context. If graph context artifacts already exist from Block 3, prompt generation uses exactly those artifacts instead of rebuilding the graph context.

Open: `pipeline/02_processing/03_reasoning/ReaPromptPreparation.py`

Show lines 20-28.

Say:

> `ReaPromptPreparation` prepares one final deviation-detection prompt for each REA sub-unit. It extracts top REG matches, collects graph context, and creates the LLM prompt payload.

Show lines 84-87.

Say:

> The prompt top-k is capped at three main REG entries per prompt. This keeps each prompt focused and reduces cost.

Show lines 94-116.

Say:

> Step 2 extracts the selected main REG matches from one reranked REA artifact.

Show lines 118-129.

Say:

> Step 3 collects graph context around those main REG entries.

Show lines 131-148.

Say:

> Step 4 builds the final prompt payload using REA text, REG text, slots, and graph context.

Show lines 250-330.

Say:

> In the normal orchestrated flow, prompts are generated from precomputed graph context files. This preserves the exact graph context selected in Block 3.

## 9. Explain Optional Prompt Sending

Open: `pipeline/Orchestrate_ReaPipelines.py`

Show lines 366-390.

Say:

> This sends prompts only if `send_prompts=True`. The default is false, which protects us from accidental API cost. When enabled, it uses the configured model and optional system-prompt caching.

Show lines 392-402.

Say:

> After responses are received, this step formats raw LLM responses into readable outputs.

Show lines 461-473.

Say:

> This method controls Block 4. If prompt sending is disabled, Block 4 only generates prompts. If sending is enabled, it also sends prompts and formats the responses.

## 10. End With The Full Run Method

Open: `pipeline/Orchestrate_ReaPipelines.py`

Show lines 475-560.

Say:

> This is the full pipeline runner. REG preparation can be run or skipped. Then the REA pipeline runs with configurable steps. The return value records inputs, runtime settings, output folders, and step summaries.

## Demo Run Placeholder

Say:

> After explaining the code, I would run the notebook blocks or `run_rea_pipeline.py`. For the first live demo, I would keep `send_prompts=False`, show the REA stage outputs, retrieval files, graph context files, and generated prompt payloads. The actual GPT call can be a separate final step.
