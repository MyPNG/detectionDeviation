from __future__ import annotations

import csv
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import dotenv_values


class PromptSender:
    SYSTEM_PROMPT = """You are an expert GDPR Compliance Auditor. Your task is to evaluate a provided chunk of a company's privacy policy against a specific list of GDPR Articles (REG nodes) to detect any deviations, omissions, or contradictions.

Follow these rules strictly:
1. Regulatory-First Evaluation: You will be provided with a `<main_nodes>` and a `<referenced_nodes>` containing specific REG nodes and their 1-hop cross-references. You will also be provided with a list of `<main_entry_nodes>`.
2. The Task: You must evaluate EACH individual main REG node listed in `<main_entry_nodes>` against the ENTIRE policy chunk.
   - A single REG node evaluation can result in:
     a) No deviations (Non-deviation).
     b) A single deviation.
     c) Multiple deviations of the same or different types (e.g., a statement might have both a Data deviation and a Completeness deviation).
   - CRITICAL: For each main node, you MUST identify and include its cross-references in your analysis.
   - CRITICAL: Many main nodes are incomplete without their context. If a main node refers to another Article, you must retrieve the full text of that reference from the <referenced_nodes> section. Your analysis field must explain how the policy aligns with (or deviates from) the combined requirements of the main node and its references.
3. Definition of Deviation: A "deviation" is any difference in constraints, details, or scope between the policy and the GDPR. Note that a deviation does NOT automatically mean non-compliance.
4. Handling Omissions: If a GDPR requirement (including its references) specifies information that is simply missing from the policy chunk, do not categorize this as a deviation. You must treat all omissions as a Non-Deviation.
4.1 Evidence Requirement (CRITICAL): Before stating if there is a deviation, you MUST extract and quote the exact span of text from the provided regulations that proves your point. If you cannot extract a quote, you must classify it as Non-Deviation.
5. Deviation Taxonomy: If a deviation is found, you MUST classify it into exactly one of the following categories. Read the examples carefully:
   - Data deviation: The specific scope, state, or category of data/processing is subtly altered or narrowed.
     *(Example 1: GDPR grants access to data "being processed", but the policy limits it to data "stored" at rest. Example 2: GDPR grants the right to object specifically to "profiling," but the policy only mentions general "processing".)*
   - Severity deviation: The policy is over-compliant (stricter about constraints than the GDPR requires).
     *(Example: The GDPR requires informing a data subject within 72h, while the policy states it will inform them within 24h.)*
   - Execution style deviation: The method or phrasing of how a task is executed differs.
     *(Example: The regulatory document requires "gluing parts together", but the policy states to "weld the parts".)*
   - Negation deviation: The constraints are similar but logically negated.
     *(Example: The regulatory document requires informing the customer via phone call, but the policy states NOT to reach out via phone.)*
   - Responsibility deviation: The entity, resource, or role specified to execute a task differs.
     *(Example: The regulatory document specifies that Resource A must execute the task, but the policy specifies Resource B.)*
   - Time deviation: The timeframe or deadline allowed for a task differs (in a way that is not an over-compliant severity deviation).
     *(Example: The regulatory document states a task must be finished within one day, but the policy allows two days.)*
   - Task execution order deviation: The required sequence of actions differs.
     *(Example: The regulation states the order of events must be A-B-C, but the policy states the order is B-A-C.)*

6. Deliberation: You MUST think step-by-step inside <deliberation> tags BEFORE generating your final output.
7. Output Format: Output your final decision as a strict JSON array of objects inside a ```json block.
CRITICAL INSTRUCTION: You must begin your entire response with <deliberation>. Do not output the JSON block until your deliberation is complete. You must provide one distinct evaluation object for EACH REG ID listed in the <main_entry_nodes>.

Use this exact nested schema:
[
  {
    "reg_id": "REG-XX",
    "clause": "Short name of the GDPR Article (e.g., Art15(1))",
    "considered_references": ["List of any cross-referenced REG IDs used for this analysis"],
    "deviation_found": boolean,
    "deviations": [
      {
        "deviation_type": "String from the taxonomy above",
        "gdpr_quote": "Exact quoted span from provided GDPR context",
        "policy_quote": "Exact quoted span from target policy chunk",
        "mismatch": "One-sentence direct contradiction/narrowing/over-compliance statement",
        "analysis": "Short justification"
      }
	// here more deviation if exists
    ]
  }
]
Note: If deviation_found is false, output an empty array for "deviations": []
"""

    def __init__(self, env_path: str | Path, model_name: str = "gpt-5"):
        self.env_path = Path(env_path).expanduser().resolve()
        self.model_name = model_name
        self.api_key: str | None = None

    def _candidate_env_paths(self) -> list[Path]:
        """
        Build a small ordered list of .env candidates.
        """
        candidates: list[Path] = []
        explicit = self.env_path
        if explicit.is_dir():
            explicit = explicit / ".env"
        candidates.append(explicit)

        # Common fallback locations near this file and current working dir.
        script_dir = Path(__file__).resolve().parent
        cwd_dir = Path.cwd().resolve()
        candidates.append(script_dir / ".env")
        candidates.append(cwd_dir / ".env")

        # Deduplicate while preserving order.
        seen: set[str] = set()
        deduped: list[Path] = []
        for path in candidates:
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(path)
        return deduped

    @staticmethod
    def _normalize_key_value(raw: Any) -> str:
        value = str(raw or "").strip()
        if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
            value = value[1:-1].strip()
        return value

    @staticmethod
    def _normalize_spaces(value: str) -> str:
        return " ".join(str(value).split()).strip()

    def _load_api_key(self) -> str:
        checked_paths: list[str] = []
        for env_file in self._candidate_env_paths():
            checked_paths.append(str(env_file))
            if not env_file.exists():
                continue
            env_values = dotenv_values(env_file)
            for name in ("API_KEY", "OPENAI_API_KEY"):
                key = self._normalize_key_value(env_values.get(name, ""))
                if key:
                    return key

        # Environment variables fallback
        for name in ("API_KEY", "OPENAI_API_KEY"):
            key = self._normalize_key_value(os.getenv(name, ""))
            if key:
                return key

        raise ValueError(
            "No API key found. Checked .env files: "
            + ", ".join(checked_paths)
            + " and env vars: API_KEY, OPENAI_API_KEY."
        )

    @staticmethod
    def _build_ssl_context(use_certifi: bool = False) -> ssl.SSLContext:
        """
        Build an SSL context for HTTPS calls.
        If use_certifi=True, prefer certifi CA bundle when available.
        """
        if use_certifi:
            try:
                import certifi

                return ssl.create_default_context(cafile=certifi.where())
            except Exception:
                # Fall back to default cert resolution if certifi is unavailable.
                return ssl.create_default_context()
        return ssl.create_default_context()

    @staticmethod
    def _is_ssl_cert_error(exc: urllib.error.URLError) -> bool:
        """
        Identify certificate verification issues robustly across Python builds.
        """
        reason_obj = exc.reason
        reason_text = str(reason_obj).lower()
        if isinstance(reason_obj, ssl.SSLCertVerificationError):
            return True
        return "certificate verify failed" in reason_text or "cert" in reason_text and "verify" in reason_text

    @staticmethod
    def _is_retryable_http_status(status_code: int) -> bool:
        """
        Retry temporary server/rate-limit errors.
        """
        return status_code in {429, 500, 502, 503, 504}

    @staticmethod
    def _load_json(path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _build_relationships_block(relationships_payload: dict[str, Any]) -> str:
        lines = ["<relationships>"]
        rel_items = relationships_payload.get("relationships", [])
        grouped: dict[str, list[str]] = {}

        if isinstance(rel_items, list):
            for row in rel_items:
                if not isinstance(row, dict):
                    continue
                source = str(row.get("source", "")).strip()
                if not source:
                    continue
                ref = str(row.get("reference", "")).strip()
                if not ref:
                    ref = str(row.get("target", "")).strip()
                grouped.setdefault(source, [])
                if ref and ref not in grouped[source]:
                    grouped[source].append(ref)

        for node_id in sorted(grouped.keys()):
            lines.append(f"- node: {node_id}")
            lines.append("  references:")
            refs = grouped[node_id]
            if refs:
                for ref in refs:
                    lines.append(f"    - {ref}")
            else:
                lines.append("    - []")
        lines.append("</relationships>")
        return "\n".join(lines)

    @staticmethod
    def _build_nodes_block(nodes_payload: dict[str, Any]) -> str:
        lines = ["<nodes>"]
        nodes = nodes_payload.get("nodes", [])
        if isinstance(nodes, list):
            for row in nodes:
                if not isinstance(row, dict):
                    continue
                node_id = str(row.get("ID", "")).strip()
                article = str(row.get("Article", "")).strip()
                paragraph = str(row.get("Paragraph", "")).strip()
                text = str(row.get("Text", "")).strip()
                if not node_id:
                    continue
                lines.append(f'  <node id="{node_id}">')
                lines.append(f"    ### Article {article} Paragraph {paragraph}")
                lines.append(f"    {text}")
                lines.append("  </node>")
        lines.append("</nodes>")
        return "\n".join(lines)

    @staticmethod
    def _index_nodes_by_id(nodes_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
        nodes_by_id: dict[str, dict[str, Any]] = {}
        nodes = nodes_payload.get("nodes", [])
        if not isinstance(nodes, list):
            return nodes_by_id
        for row in nodes:
            if not isinstance(row, dict):
                continue
            node_id = str(row.get("ID", "")).strip().upper()
            if not node_id:
                continue
            nodes_by_id[node_id] = row
        return nodes_by_id

    @staticmethod
    def _extract_one_hop_referenced_node_ids(
        relationships_payload: dict[str, Any],
        main_node_ids: list[str],
    ) -> list[str]:
        """
        Collect 1-hop referenced node IDs:
        source in main_node_ids and target not in main_node_ids.
        """
        main_set = {node_id.strip().upper() for node_id in main_node_ids if node_id.strip()}
        out: list[str] = []
        rel_items = relationships_payload.get("relationships", [])
        if not isinstance(rel_items, list):
            return out

        for row in rel_items:
            if not isinstance(row, dict):
                continue
            source = str(row.get("source", "")).strip().upper()
            target = str(row.get("target", "")).strip().upper()
            if not source or not target:
                continue
            if source in main_set and target not in main_set and target not in out:
                out.append(target)
        return out

    @staticmethod
    def _build_nodes_section(tag: str, node_ids: list[str], nodes_by_id: dict[str, dict[str, Any]]) -> str:
        lines = [f"<{tag}>"]
        for node_id in node_ids:
            row = nodes_by_id.get(node_id.strip().upper())
            if not isinstance(row, dict):
                continue
            article = str(row.get("Article", "")).strip()
            paragraph = str(row.get("Paragraph", "")).strip()
            text = str(row.get("Text", "")).strip()
            actual_id = str(row.get("ID", node_id)).strip()
            lines.append(f'  <node id="{actual_id}">')
            lines.append(f"    ### Article {article} Paragraph {paragraph}")
            lines.append(f"    {text}")
            lines.append("  </node>")
        lines.append(f"</{tag}>")
        return "\n".join(lines)

    @staticmethod
    def _load_search_queries(chunk_artifact_01_dir: Path) -> list[dict[str, str]]:
        """
        Read all REA result files in a chunk and collect search queries.
        """
        query_items: list[dict[str, str]] = []
        pattern = re.compile(r"rea-\d+_top_\d+\.json$", re.IGNORECASE)
        for file_path in sorted(path for path in chunk_artifact_01_dir.iterdir() if path.is_file()):
            if not pattern.search(file_path.name):
                continue
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            rea_id = str(payload.get("id", "")).strip()
            query_text = str(payload.get("search query", "")).strip()
            if rea_id or query_text:
                query_items.append({"id": rea_id, "query": query_text})
        return query_items

    @staticmethod
    def _normalize_chunk_name(chunk_name: str) -> str:
        return chunk_name.replace("_", "").strip().lower()

    @staticmethod
    def _extract_chunk_number(chunk_name: str) -> int | None:
        """
        Parse chunk index from names like: chunk1, chunk_1, CHUNK12.
        """
        match = re.search(r"chunk[_\-]?(\d+)", chunk_name, flags=re.IGNORECASE)
        if not match:
            return None
        try:
            return int(match.group(1))
        except ValueError:
            return None

    def _load_policy_chunk_from_intermediate_results(
        self,
        rea_intermediate_root_dir: Path,
        chunk_name: str,
    ) -> list[dict[str, str]]:
        """
        Load policy chunk statements from:
        intermediate_results/rea/<chunk>/<chunk>_requirements.json
        """
        normalized_chunk = self._normalize_chunk_name(chunk_name)

        candidate_dirs = [rea_intermediate_root_dir / chunk_name]
        if normalized_chunk != chunk_name.lower():
            candidate_dirs.append(rea_intermediate_root_dir / normalized_chunk)

        for directory in candidate_dirs:
            if not directory.exists() or not directory.is_dir():
                continue

            preferred_file = directory / f"{directory.name}_requirements.json"
            candidate_files = [preferred_file] if preferred_file.exists() else []
            if not candidate_files:
                candidate_files = sorted(directory.glob("*_requirements.json"))
            if not candidate_files:
                continue

            payload = self._load_json(candidate_files[0])
            if not isinstance(payload, list):
                continue

            items: list[dict[str, str]] = []
            for row in payload:
                if not isinstance(row, dict):
                    continue
                rea_id = self._normalize_spaces(str(row.get("rea_id", "")))
                text = self._normalize_spaces(str(row.get("text", "")))
                if text:
                    items.append({"id": rea_id, "query": text})
            if items:
                return items

        return []

    def _load_policy_chunk_window_from_intermediate_results(
        self,
        rea_intermediate_root_dir: Path,
        chunk_name: str,
        window_hops: int = 1,
    ) -> list[dict[str, str]]:
        """
        Load a windowed policy chunk from intermediate results:
        chunk(i-window_hops) ... chunk(i+window_hops)

        The returned items keep chronological order across neighbors.
        """
        if window_hops < 0:
            return []

        center_idx = self._extract_chunk_number(chunk_name)
        if center_idx is None:
            return []

        discovered_dirs = [path for path in rea_intermediate_root_dir.iterdir() if path.is_dir()]
        chunk_dir_by_index: dict[int, str] = {}
        for directory in discovered_dirs:
            idx = self._extract_chunk_number(directory.name)
            if idx is None:
                continue
            # If duplicates exist, keep deterministic first by lexical order.
            if idx not in chunk_dir_by_index:
                chunk_dir_by_index[idx] = directory.name

        merged_items: list[dict[str, str]] = []
        for idx in range(center_idx - window_hops, center_idx + window_hops + 1):
            chunk_dir_name = chunk_dir_by_index.get(idx)
            if not chunk_dir_name:
                continue
            items = self._load_policy_chunk_from_intermediate_results(
                rea_intermediate_root_dir=rea_intermediate_root_dir,
                chunk_name=chunk_dir_name,
            )
            if items:
                merged_items.extend(items)
        return merged_items

    @staticmethod
    def _build_target_policy_chunk_block(query_items: list[dict[str, str]]) -> str:
        lines = ["<target_policy_chunk>"]
        combined = " ".join(row.get("query", "").strip() for row in query_items if row.get("query", "").strip())
        lines.append(combined)
        lines.append("</target_policy_chunk>")
        return "\n".join(lines)

    @staticmethod
    def _load_main_entry_nodes_from_csv(chunk_artifact_01_dir: Path) -> list[dict[str, str]]:
        """
        Read main entry nodes from reg_main_clauses.csv in artifact_01 chunk.
        Expected columns: reg_id, clause
        """
        csv_path = chunk_artifact_01_dir / "reg_main_clauses.csv"
        if not csv_path.exists():
            return []

        rows: list[dict[str, str]] = []
        seen: set[str] = set()
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                reg_id = str(row.get("reg_id", "")).strip().upper()
                clause = str(row.get("clause", "")).strip()
                if not reg_id or reg_id in seen:
                    continue
                seen.add(reg_id)
                rows.append({"reg_id": reg_id, "clause": clause})
        return rows

    @staticmethod
    def _infer_main_entry_nodes_from_top_matches(
        chunk_artifact_01_dir: Path,
        rank_per_file: int = 1,
    ) -> list[dict[str, str]]:
        """
        Fallback when reg_main_clauses.csv is unavailable.
        """
        main_nodes: list[dict[str, str]] = []
        seen: set[str] = set()
        pattern = re.compile(r"rea-\d+_top_\d+\.json$", re.IGNORECASE)
        for file_path in sorted(path for path in chunk_artifact_01_dir.iterdir() if path.is_file()):
            if not pattern.search(file_path.name):
                continue
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                continue

            top_matches = payload.get("top matches", [])
            if not isinstance(top_matches, list) or not top_matches:
                continue

            idx = max(1, rank_per_file) - 1
            if idx >= len(top_matches):
                idx = 0
            selected = top_matches[idx]
            if not isinstance(selected, dict):
                continue

            reg_id = str(selected.get("ID", "")).strip().upper()
            if reg_id and reg_id not in seen:
                seen.add(reg_id)
                main_nodes.append({"reg_id": reg_id, "clause": ""})
        return main_nodes

    @staticmethod
    def _build_main_entry_nodes_block(main_entry_nodes: list[dict[str, str]]) -> str:
        lines = ["<main_entry_nodes>"]
        reg_ids = [str(row.get("reg_id", "")).strip() for row in main_entry_nodes if str(row.get("reg_id", "")).strip()]
        lines.append(", ".join(reg_ids))
        lines.append("</main_entry_nodes>")
        return "\n".join(lines)

    @staticmethod
    def _split_main_entry_nodes(
        main_entry_nodes: list[dict[str, str]],
        max_main_entry_nodes_per_prompt: int | None = None,
    ) -> list[list[dict[str, str]]]:
        """
        Split main entry nodes into prompt-sized batches.
        If max is None or <= 0, keep all nodes in one batch.
        """
        if not main_entry_nodes:
            return [[]]
        if max_main_entry_nodes_per_prompt is None or int(max_main_entry_nodes_per_prompt) <= 0:
            return [main_entry_nodes]

        size = int(max_main_entry_nodes_per_prompt)
        batches: list[list[dict[str, str]]] = []
        for i in range(0, len(main_entry_nodes), size):
            batches.append(main_entry_nodes[i : i + size])
        return batches

    def generate_user_prompts_from_chunks(
        self,
        artifact_01_chunk_dir: str | Path,
        artifact_02_chunk_dir: str | Path,
        rea_intermediate_root_dir: str | Path | None = None,
        windowed_chunk: bool = False,
        max_main_entry_nodes_per_prompt: int | None = None,
    ) -> list[str]:
        """
        Build one or multiple user prompts for a chunk.
        Each prompt contains at most `max_main_entry_nodes_per_prompt` main nodes.
        Referenced nodes are restricted to that prompt's main-node batch.
        """
        chunk_01_path = Path(artifact_01_chunk_dir).expanduser().resolve()
        chunk_02_path = Path(artifact_02_chunk_dir).expanduser().resolve()

        rel_file = chunk_02_path / "subgraph_relationships.json"
        nodes_file = chunk_02_path / "subgraph_texts.json"
        if not rel_file.exists():
            raise FileNotFoundError(f"Missing relationships file: {rel_file}")
        if not nodes_file.exists():
            raise FileNotFoundError(f"Missing nodes file: {nodes_file}")

        query_items: list[dict[str, str]] = []
        if rea_intermediate_root_dir is not None:
            rea_root = Path(rea_intermediate_root_dir).expanduser().resolve()
            if windowed_chunk:
                query_items = self._load_policy_chunk_window_from_intermediate_results(
                    rea_intermediate_root_dir=rea_root,
                    chunk_name=chunk_01_path.name,
                    window_hops=1,
                )
            else:
                query_items = self._load_policy_chunk_from_intermediate_results(
                    rea_intermediate_root_dir=rea_root,
                    chunk_name=chunk_01_path.name,
                )
        if not query_items:
            # Fallback to artifact_01 query fields if intermediate requirements file is missing.
            query_items = self._load_search_queries(chunk_01_path)

        main_entry_nodes = self._load_main_entry_nodes_from_csv(chunk_01_path)
        if not main_entry_nodes:
            main_entry_nodes = self._infer_main_entry_nodes_from_top_matches(chunk_01_path)

        relationships_payload = self._load_json(rel_file)
        nodes_payload = self._load_json(nodes_file)
        nodes_by_id = self._index_nodes_by_id(nodes_payload)
        policy_chunk_block = self._build_target_policy_chunk_block(query_items)

        prompts: list[str] = []
        for batch in self._split_main_entry_nodes(
            main_entry_nodes,
            max_main_entry_nodes_per_prompt=max_main_entry_nodes_per_prompt,
        ):
            main_entry_nodes_block = self._build_main_entry_nodes_block(batch)
            main_entry_ids = [
                str(row.get("reg_id", "")).strip().upper()
                for row in batch
                if str(row.get("reg_id", "")).strip()
            ]
            referenced_ids = self._extract_one_hop_referenced_node_ids(relationships_payload, main_entry_ids)

            main_nodes_block = self._build_nodes_section("main_nodes", main_entry_ids, nodes_by_id)
            referenced_nodes_block = self._build_nodes_section("referenced_nodes", referenced_ids, nodes_by_id)
            user_prompt = (
                f"{main_entry_nodes_block}\n\n"
                f"{main_nodes_block}\n\n"
                f"{referenced_nodes_block}\n\n"
                f"{policy_chunk_block}\n"
            )
            prompts.append(user_prompt)

        return prompts

    def generate_user_prompt_from_chunks(
        self,
        artifact_01_chunk_dir: str | Path,
        artifact_02_chunk_dir: str | Path,
        output_md_file: str | Path | None = None,
        rea_intermediate_root_dir: str | Path | None = None,
        windowed_chunk: bool = False,
        max_main_entry_nodes_per_prompt: int | None = None,
    ) -> str | Path:
        """
        Build ONE user prompt in the structure:
        <main_entry_nodes>, <main_nodes>, <referenced_nodes>, <target_policy_chunk>
        """
        prompts = self.generate_user_prompts_from_chunks(
            artifact_01_chunk_dir=artifact_01_chunk_dir,
            artifact_02_chunk_dir=artifact_02_chunk_dir,
            rea_intermediate_root_dir=rea_intermediate_root_dir,
            windowed_chunk=windowed_chunk,
            max_main_entry_nodes_per_prompt=max_main_entry_nodes_per_prompt,
        )
        user_prompt = prompts[0] if prompts else ""

        if output_md_file is None:
            return user_prompt

        output_path = Path(output_md_file).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(user_prompt, encoding="utf-8")
        return output_path

    def generate_llm_prompt_preview(
        self,
        user_prompt_md_file: str | Path,
        output_md_file: str | Path,
    ) -> Path:
        """
        Store exactly how the request to the LLM will look:
        one system prompt + one user prompt.
        """
        user_prompt_path = Path(user_prompt_md_file).expanduser().resolve()
        output_path = Path(output_md_file).expanduser().resolve()
        user_prompt = user_prompt_path.read_text(encoding="utf-8").strip()

        preview = (
            "# SYSTEM PROMPT\n\n"
            "```text\n"
            f"{self.SYSTEM_PROMPT.rstrip()}\n"
            "```\n\n"
            "# USER PROMPT\n\n"
            "```text\n"
            f"{user_prompt}\n"
            "```\n"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(preview, encoding="utf-8")
        return output_path

    def generate_llm_prompt_preview_from_text(
        self,
        user_prompt: str,
        output_md_file: str | Path,
    ) -> Path:
        """
        Store exactly how the request to the LLM will look:
        one system prompt + one user prompt, with user prompt provided in-memory.
        """
        output_path = Path(output_md_file).expanduser().resolve()
        preview = (
            "# SYSTEM PROMPT\n\n"
            "```text\n"
            f"{self.SYSTEM_PROMPT.rstrip()}\n"
            "```\n\n"
            "# USER PROMPT\n\n"
            "```text\n"
            f"{user_prompt.strip()}\n"
            "```\n"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(preview, encoding="utf-8")
        return output_path

    def generate_user_prompt(
        self,
        relationships_file: str | Path,
        nodes_file: str | Path,
        output_md_file: str | Path,
        query_text: str = "",
    ) -> Path:
        """
        Generate a user prompt markdown from artifact_02 files.
        """
        relationships_path = Path(relationships_file).expanduser().resolve()
        nodes_path = Path(nodes_file).expanduser().resolve()
        output_path = Path(output_md_file).expanduser().resolve()

        relationships_payload = self._load_json(relationships_path)
        nodes_payload = self._load_json(nodes_path)

        relationships_block = self._build_relationships_block(relationships_payload)
        nodes_block = self._build_nodes_block(nodes_payload)
        query_block = "<query>\nStatement: " + query_text.strip() + "\n</query>"

        user_prompt = f"{relationships_block}\n\n{nodes_block}\n\n{query_block}\n"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(user_prompt, encoding="utf-8")
        return output_path

    def send_prompt_to_llm(
        self,
        user_prompt_md_file: str | Path,
        output_json_file: str | Path,
        temperature: float | None = None,
        max_retries: int = 4,
        retry_base_delay_seconds: float = 2.0,
    ) -> Path:
        """
        Send user prompt markdown to GPT-4o and save raw API response to JSON.
        """
        prompt_path = Path(user_prompt_md_file).expanduser().resolve()
        output_path = Path(output_json_file).expanduser().resolve()
        user_prompt = prompt_path.read_text(encoding="utf-8")
        if not self.api_key:
            self.api_key = self._load_api_key()

        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        }
        # GPT-5 may reject explicit temperature overrides.
        # Keep API default behavior unless user explicitly sets one.
        if temperature is not None:
            payload["temperature"] = float(temperature)

        request = urllib.request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        attempts = max(1, int(max_retries) + 1)
        last_error: Exception | None = None
        response_payload: dict[str, Any] | None = None
        for attempt in range(1, attempts + 1):
            try:
                # Prefer certifi-backed context first when available to avoid local trust-store issues.
                with urllib.request.urlopen(
                    request,
                    context=self._build_ssl_context(use_certifi=True),
                    timeout=300,
                ) as response:
                    raw = response.read().decode("utf-8")
                    response_payload = json.loads(raw)
                    break
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="ignore")
                if self._is_retryable_http_status(exc.code) and attempt < attempts:
                    delay = retry_base_delay_seconds * (2 ** (attempt - 1))
                    print(f"[Retry {attempt}/{attempts - 1}] HTTP {exc.code}. Waiting {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                raise RuntimeError(f"OpenAI HTTPError {exc.code}: {body}") from exc
            except urllib.error.URLError as exc:
                # Retry once with the interpreter default trust store if certifi path failed unexpectedly.
                if self._is_ssl_cert_error(exc):
                    try:
                        with urllib.request.urlopen(request, context=self._build_ssl_context(), timeout=120) as response:
                            raw = response.read().decode("utf-8")
                            response_payload = json.loads(raw)
                            break
                    except urllib.error.HTTPError as inner_exc:
                        body = inner_exc.read().decode("utf-8", errors="ignore")
                        if self._is_retryable_http_status(inner_exc.code) and attempt < attempts:
                            delay = retry_base_delay_seconds * (2 ** (attempt - 1))
                            print(f"[Retry {attempt}/{attempts - 1}] HTTP {inner_exc.code} after SSL fallback. Waiting {delay:.1f}s...")
                            time.sleep(delay)
                            continue
                        raise RuntimeError(f"OpenAI HTTPError {inner_exc.code}: {body}") from inner_exc
                    except urllib.error.URLError as inner_exc:
                        if self._is_ssl_cert_error(inner_exc):
                            raise RuntimeError(
                                "OpenAI SSL verification failed. "
                                "Use the same interpreter where certifi is installed "
                                "(recommended: `.venv/bin/python ...`)."
                            ) from inner_exc
                        # Non-SSL URLError can be transient, retry if attempts remain.
                        last_error = inner_exc
                        if attempt < attempts:
                            delay = retry_base_delay_seconds * (2 ** (attempt - 1))
                            print(f"[Retry {attempt}/{attempts - 1}] URLError after SSL fallback: {inner_exc.reason}. Waiting {delay:.1f}s...")
                            time.sleep(delay)
                            continue
                        raise RuntimeError(
                            f"OpenAI URLError after SSL fallback: {inner_exc.reason}"
                        ) from inner_exc
                # Non-SSL URLError can be transient; retry with backoff.
                last_error = exc
                if attempt < attempts:
                    delay = retry_base_delay_seconds * (2 ** (attempt - 1))
                    print(f"[Retry {attempt}/{attempts - 1}] URLError: {exc.reason}. Waiting {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                raise RuntimeError(f"OpenAI URLError: {exc.reason}") from exc

        if response_payload is None:
            if last_error is not None:
                raise RuntimeError(f"OpenAI request failed after retries: {last_error}") from last_error
            raise RuntimeError("OpenAI request failed after retries with no response payload.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(response_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path

    def generate_prompts_for_all_chunks(
        self,
        artifact_01_dir: str | Path,
        artifact_02_dir: str | Path,
        artifact_03_dir: str | Path,
        rea_intermediate_root_dir: str | Path | None = None,
        windowed_chunk: bool = False,
        max_main_entry_nodes_per_prompt: int | None = 3,
    ) -> dict[str, Any]:
        """
        Convenience helper: generate one prompt markdown per chunk using artifact_01 + artifact_02.
        Also writes an LLM prompt preview (system + user) to artifact_03/chunk_*/llm_prompt_preview.md.
        """
        input_01_dir = Path(artifact_01_dir).expanduser().resolve()
        input_dir = Path(artifact_02_dir).expanduser().resolve()
        output_dir = Path(artifact_03_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        results: list[dict[str, str]] = []
        for chunk in sorted(path for path in input_dir.iterdir() if path.is_dir()):
            chunk_01 = input_01_dir / chunk.name
            if not chunk_01.exists():
                continue

            chunk_out = output_dir / chunk.name
            legacy_user_prompt = chunk_out / "user_prompt.md"
            if legacy_user_prompt.exists():
                legacy_user_prompt.unlink()
            # Clean stale previews from previous runs.
            for stale_preview in chunk_out.glob("llm_prompt_preview*.md"):
                stale_preview.unlink(missing_ok=True)

            prompt_texts = self.generate_user_prompts_from_chunks(
                artifact_01_chunk_dir=chunk_01,
                artifact_02_chunk_dir=chunk,
                rea_intermediate_root_dir=rea_intermediate_root_dir,
                windowed_chunk=windowed_chunk,
                max_main_entry_nodes_per_prompt=max_main_entry_nodes_per_prompt,
            )
            if not prompt_texts:
                continue

            if len(prompt_texts) == 1:
                preview_md = chunk_out / "llm_prompt_preview.md"
                saved_preview = self.generate_llm_prompt_preview_from_text(
                    user_prompt=prompt_texts[0],
                    output_md_file=preview_md,
                )
                results.append(
                    {
                        "chunk": chunk.name,
                        "prompt_index": "1",
                        "llm_prompt_preview_file": str(saved_preview),
                    }
                )
            else:
                for idx, prompt_text in enumerate(prompt_texts, start=1):
                    preview_md = chunk_out / f"llm_prompt_preview_{idx:02d}.md"
                    saved_preview = self.generate_llm_prompt_preview_from_text(
                        user_prompt=prompt_text,
                        output_md_file=preview_md,
                    )
                    results.append(
                        {
                            "chunk": chunk.name,
                            "prompt_index": str(idx),
                            "llm_prompt_preview_file": str(saved_preview),
                        }
                    )

        return {
            "artifact_01_dir": str(input_01_dir),
            "artifact_02_dir": str(input_dir),
            "artifact_03_dir": str(output_dir),
            "windowed_chunk": windowed_chunk,
            "max_main_entry_nodes_per_prompt": max_main_entry_nodes_per_prompt,
            "prompts": results,
        }

    def send_prompts_for_all_chunks(
        self,
        artifact_03_dir: str | Path,
        prompt_filename: str = "llm_prompt_preview.md",
        response_filename: str = "llm_response.json",
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """
        Send all generated prompt markdown files under artifact_03/chunk_*_b to GPT-4o.
        """
        output_dir = Path(artifact_03_dir).expanduser().resolve()
        results: list[dict[str, str]] = []
        failures: list[dict[str, str]] = []

        for chunk in sorted(path for path in output_dir.iterdir() if path.is_dir()):
            prompt_files: list[Path] = []
            explicit_prompt_file = chunk / prompt_filename
            if explicit_prompt_file.exists():
                prompt_files = [explicit_prompt_file]
            elif prompt_filename == "llm_prompt_preview.md":
                prompt_files = sorted(chunk.glob("llm_prompt_preview*.md"))

            if not prompt_files:
                continue

            for prompt_file in prompt_files:
                # Map preview filename -> response filename
                response_file_name = response_filename
                suffix_match = re.match(r"^llm_prompt_preview_(\d+)\.md$", prompt_file.name)
                if suffix_match:
                    response_file_name = f"llm_response_{suffix_match.group(1)}.json"

                try:
                    single = self.send_prompt_for_single_chunk(
                        artifact_03_dir=output_dir,
                        chunk_name=chunk.name,
                        prompt_filename=prompt_file.name,
                        response_filename=response_file_name,
                        temperature=temperature,
                    )
                    results.append(
                        {
                            "chunk": chunk.name,
                            "prompt_file": single["prompt_file"],
                            "response_file": single["response_file"],
                        }
                    )
                except Exception as exc:
                    failures.append(
                        {
                            "chunk": chunk.name,
                            "prompt_file": str(prompt_file),
                            "error": str(exc),
                        }
                    )
                    print(f"[Warning] Failed for {chunk.name} / {prompt_file.name}: {exc}")

        return {
            "artifact_03_dir": str(output_dir),
            "responses": results,
            "failures": failures,
        }

    def send_prompt_for_single_chunk(
        self,
        artifact_03_dir: str | Path,
        chunk_name: str,
        prompt_filename: str = "llm_prompt_preview.md",
        response_filename: str = "llm_response.json",
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """
        Send exactly one prompt for a specific chunk folder in artifact_03.
        Example chunk_name: "chunk1", "chunk2", ..., "chunk12"
        """
        output_dir = Path(artifact_03_dir).expanduser().resolve()
        chunk_dir = output_dir / chunk_name
        if not chunk_dir.exists() or not chunk_dir.is_dir():
            raise FileNotFoundError(f"Chunk directory not found: {chunk_dir}")

        prompt_file = chunk_dir / prompt_filename
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        prompt_text = prompt_file.read_text(encoding="utf-8")
        user_match = re.search(
            r"# USER PROMPT\s*```text\s*(.*?)\s*```",
            prompt_text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if not user_match:
            raise ValueError(f"Could not parse USER PROMPT block from: {prompt_file}")
        extracted_user_prompt = user_match.group(1).strip()

        temp_user_prompt_file = chunk_dir / "_tmp_user_prompt_for_send.md"
        temp_user_prompt_file.write_text(extracted_user_prompt, encoding="utf-8")
        response_file = chunk_dir / response_filename
        try:
            saved = self.send_prompt_to_llm(
                user_prompt_md_file=temp_user_prompt_file,
                output_json_file=response_file,
                temperature=temperature,
            )
        finally:
            if temp_user_prompt_file.exists():
                temp_user_prompt_file.unlink()
        return {
            "artifact_03_dir": str(output_dir),
            "chunk": chunk_name,
            "prompt_file": str(prompt_file),
            "response_file": str(saved),
        }


def main() -> None:
    root_dir = Path(__file__).resolve().parents[2]
    # Keep .env path explicit to reasoning folder (where your key file currently exists).
    env_path = Path(__file__).resolve().parent / ".env"
    #artifact_01 = root_dir / "intermediate_outputs" / "artifact_01"
    #artifact_02 = root_dir / "intermediate_outputs" / "artifact_02"
    #artifact_03 = root_dir / "intermediate_outputs" / "artifact_03"
    rea_intermediate = root_dir / "intermediate_results" / "rea"

    artifact_01 = root_dir / "intermediate_outputs" / "artifact_01_reranked"
    artifact_02 = root_dir / "intermediate_outputs" / "artifact_02_reranked"
    artifact_03 = root_dir / "intermediate_outputs" / "artifact_03_reranked_overlapwindows"

    #artifact_01 = root_dir / "intermediate_outputs" / "artifact_01_reranked_100"
    #artifact_02 = root_dir / "intermediate_outputs" / "artifact_02_reranked_100"
    #artifact_03 = root_dir / "intermediate_outputs" / "artifact_03_reranked_100"

    sender = PromptSender(env_path=env_path, model_name="gpt-5")
    use_windowed_chunk = True
    # Step 1: Generate prompts first

    #generation_result = sender.generate_prompts_for_all_chunks(
    #    artifact_01_dir=artifact_01,
    #    artifact_02_dir=artifact_02,
    #    artifact_03_dir=artifact_03,
    #    rea_intermediate_root_dir=rea_intermediate,
    #    windowed_chunk=use_windowed_chunk,
    #)
    #print("Generated prompts:")
    #print(json.dumps(generation_result, indent=2, ensure_ascii=False))

    # Step 2: Send prompts to LLM
    #sending_result = sender.send_prompts_for_all_chunks(
    #      artifact_03_dir=str(artifact_03),
    #      temperature=None,
    #)
    #print("LLM responses:")
    #print(json.dumps(sending_result, indent=2, ensure_ascii=False))

    # Step 2b: Send prompt for ONE chunk only
    #single_result = sender.send_prompt_for_single_chunk(
    #   artifact_03_dir=str(artifact_03),
    #    chunk_name="chunk10",
    #    temperature=None,
    #)
    #print("LLM single-chunk response:")
    #print(json.dumps(single_result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
