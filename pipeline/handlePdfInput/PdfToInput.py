from __future__ import annotations

import json
from pathlib import Path

from docling.document_converter import DocumentConverter


class PdfToInput:
    def __init__(self):
        self.converter = DocumentConverter()

    def convert_pdf_to_md(self, input_pdf_path: str | Path, output_md_path: str | Path) -> Path:
        source = Path(input_pdf_path).expanduser().resolve()
        target = Path(output_md_path).expanduser().resolve()

        conversion_result = self.converter.convert(str(source))
        markdown_output = conversion_result.document.export_to_markdown()

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(markdown_output, encoding="utf-8")
        return target

    def convert_md_to_json(self, input_md_path: str | Path, output_json_path: str | Path) -> Path:
        source = Path(input_md_path).expanduser().resolve()
        target = Path(output_json_path).expanduser().resolve()

        conversion_result = self.converter.convert(str(source))
        payload = conversion_result.document.export_to_dict()

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return target

    def convert_txt_to_md(self, input_txt_path: str | Path, output_md_path: str | Path) -> Path:
        source = Path(input_txt_path).expanduser().resolve()
        target = Path(output_md_path).expanduser().resolve()

        text_content = source.read_text(encoding="utf-8", errors="ignore")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text_content, encoding="utf-8")
        return target


def main() -> None:
    converter = PdfToInput()
    input_pdf = "/Users/my/Documents/projects/detectionDeviation/datasets/rea/rea_pdf.pdf"
    output_md = "/Users/my/Documents/projects/detectionDeviation/datasets/rea/rea_pdf.md"
    output_json = "/Users/my/Documents/projects/detectionDeviation/datasets/rea/rea_pdf.json"

    saved_md = converter.convert_pdf_to_md(input_pdf, output_md)
    saved_json = converter.convert_md_to_json(output_md, output_json)
    # print(f"Saved markdown: {output_md}")
    # print(f"Saved json: {saved_json}")




if __name__ == "__main__":
    main()
