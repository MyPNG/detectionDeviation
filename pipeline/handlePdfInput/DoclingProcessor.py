import logging
import json
import re
import tempfile
from pathlib import Path
from docling.document_converter import DocumentConverter


class DoclingProcessor:
    def __init__(self):
        # Initialize the converter once to reuse models across conversions
        self.converter = DocumentConverter()

    def markdown_to_json(self, md_path: str | Path, include_articles: list[int | str] | None = None) -> dict:
        """
        Converts a Markdown file to a JSON-serializable Docling dict.
        If include_articles is provided, Markdown is filtered first.
        """
        try:
            source_path = Path(md_path).expanduser().resolve()
            source = str(source_path)
            print(f" Converting Markdown to JSON: {source}...")

            if include_articles:
                markdown_text = source_path.read_text(encoding="utf-8", errors="ignore")
                filtered_markdown = self.filter_markdown_by_articles(markdown_text, include_articles)
                with tempfile.NamedTemporaryFile(mode="w", suffix=".md", encoding="utf-8", delete=False) as tmp_file:
                    tmp_file.write(filtered_markdown)
                    tmp_path = tmp_file.name
                conversion_result = self.converter.convert(tmp_path)
                Path(tmp_path).unlink(missing_ok=True)
            else:
                conversion_result = self.converter.convert(source)
            return conversion_result.document.export_to_dict()

        except Exception as e:
            logging.error(f"Failed to convert markdown: {e}")
            raise RuntimeError(f"Could not convert Markdown to JSON: {md_path}") from e

    def filter_markdown_by_articles(self, markdown_text: str, include_articles: list[int | str]) -> str:
        """
        Keep only selected GDPR article sections from a Markdown document.
        Article boundaries are detected via headings like: '## Article 13'.
        """
        include_set: set[int] = set()
        for value in include_articles:
            candidate = str(value).strip()
            if not candidate:
                continue
            if candidate.isdigit():
                include_set.add(int(candidate))
                continue
            match = re.search(r"(\d+)", candidate)
            if match:
                include_set.add(int(match.group(1)))
        if not include_set:
            return ""

        heading_pattern = re.compile(r"^\s{0,3}#{1,6}\s*Article\s+(\d+)\b", flags=re.IGNORECASE)
        lines = markdown_text.splitlines()

        article_starts: list[tuple[int, int]] = []
        for idx, line in enumerate(lines):
            match = heading_pattern.match(line)
            if match:
                article_starts.append((idx, int(match.group(1))))

        if not article_starts:
            return ""

        kept_chunks: list[str] = []
        for i, (start_idx, article_number) in enumerate(article_starts):
            if article_number not in include_set:
                continue
            end_idx = article_starts[i + 1][0] if i + 1 < len(article_starts) else len(lines)
            chunk = "\n".join(lines[start_idx:end_idx]).strip()
            if chunk:
                kept_chunks.append(chunk)

        return "\n\n".join(kept_chunks).strip() + ("\n" if kept_chunks else "")

    def pdf_to_markdown_for_articles(self, pdf_path: str | Path, include_articles: list[int | str] | None = None) -> str:
        """
        Convert PDF to Markdown.
        If include_articles is provided, keep only requested article sections.
        """
        try:
            source = str(Path(pdf_path).expanduser())
            print(f" Converting PDF to Markdown: {source}...")

            conversion_result = self.converter.convert(source)
            markdown_text = conversion_result.document.export_to_markdown()
            if not include_articles:
                return markdown_text
            return self.filter_markdown_by_articles(markdown_text, include_articles)

        except Exception as e:
            logging.error(f"Failed to convert document: {e}")
            raise RuntimeError(f"Could not convert PDF to Markdown: {pdf_path}") from e


if __name__ == "__main__":
    processor = DoclingProcessor()

    project_root = Path(__file__).resolve().parents[2]
    pdf_path = project_root / "input" / "reg_eu_ai_act" / "EU_AI_ACT.pdf"
    md_path = project_root / "input" / "reg_eu_ai_act" / "eu_ai_act.md"
    json_path = project_root / "input" / "reg_eu_ai_act" / "eu_ai_act.json"
    include_articles: list[int] | None = None
    # Example filter:
    # main:8, 9, 10, 11, 12, 13, 14, 15
    # 1-depth: 72, 79, 60, 97, 26
    include_articles = [8, 9, 10, 11, 12, 13, 14, 15, 72, 79, 60, 97, 26 ]



    # pdf to json
    markdown_output = processor.pdf_to_markdown_for_articles(pdf_path, include_articles=include_articles)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown_output, encoding="utf-8")

    # md file to json
    json_payload = processor.markdown_to_json(md_path, include_articles=include_articles)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(json_payload, indent=2, ensure_ascii=False), encoding="utf-8")
