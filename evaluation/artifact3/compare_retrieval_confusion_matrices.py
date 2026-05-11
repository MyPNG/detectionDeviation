from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON: {path}")
    return payload


def _bar_chart_svg(
    title: str,
    labels: list[str],
    series: list[tuple[str, str, list[float]]],
    y_max: float,
    width: int = 1100,
    height: int = 360,
) -> str:
    ml, mr, mt, mb = 70, 20, 45, 90
    pw = width - ml - mr
    ph = height - mt - mb
    n_groups = max(1, len(labels))
    n_series = max(1, len(series))
    group_w = pw / n_groups
    bar_w = max(6, (group_w * 0.78) / n_series)

    parts: list[str] = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{ml}" y="26" font-size="18" font-family="Arial" fill="#111">{title}</text>',
        f'<line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}" stroke="#444"/>',
        f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}" stroke="#444"/>',
    ]

    for i in range(6):
        y_val = (y_max / 5) * i
        y = mt + ph - (ph * (y_val / y_max if y_max else 0))
        parts.append(f'<line x1="{ml}" y1="{y:.2f}" x2="{ml+pw}" y2="{y:.2f}" stroke="#eee"/>')
        parts.append(
            f'<text x="{ml-8}" y="{y+4:.2f}" text-anchor="end" font-size="11" font-family="Arial" fill="#666">{y_val:.2f}</text>'
        )

    for gi, label in enumerate(labels):
        gx = ml + gi * group_w
        for si, (_, color, vals) in enumerate(series):
            value = vals[gi] if gi < len(vals) else 0.0
            h = (ph * value / y_max) if y_max else 0
            x = gx + group_w * 0.11 + si * bar_w
            y = mt + ph - h
            parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{h:.2f}" fill="{color}" opacity="0.9"/>')
        lx = gx + group_w * 0.5
        parts.append(
            f'<text x="{lx:.2f}" y="{mt+ph+18}" text-anchor="middle" font-size="10" font-family="Arial" fill="#333" transform="rotate(25 {lx:.2f},{mt+ph+18})">{label}</text>'
        )

    legend_x = ml
    legend_y = height - 24
    for idx, (name, color, _) in enumerate(series):
        x = legend_x + idx * 220
        parts.append(f'<rect x="{x}" y="{legend_y-11}" width="14" height="14" fill="{color}"/>')
        parts.append(f'<text x="{x+20}" y="{legend_y}" font-size="12" font-family="Arial" fill="#222">{name}</text>')

    parts.append("</svg>")
    return "\n".join(parts)


def _line_chart_svg(
    title: str,
    labels: list[str],
    series: list[tuple[str, str, list[float]]],
    y_max: float = 1.0,
    width: int = 1100,
    height: int = 360,
) -> str:
    ml, mr, mt, mb = 70, 20, 45, 90
    pw = width - ml - mr
    ph = height - mt - mb
    n_points = max(1, len(labels))
    step_x = pw / max(1, n_points - 1)

    parts: list[str] = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{ml}" y="26" font-size="18" font-family="Arial" fill="#111">{title}</text>',
        f'<line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}" stroke="#444"/>',
        f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}" stroke="#444"/>',
    ]

    for i in range(6):
        y_val = (y_max / 5) * i
        y = mt + ph - (ph * (y_val / y_max if y_max else 0))
        parts.append(f'<line x1="{ml}" y1="{y:.2f}" x2="{ml+pw}" y2="{y:.2f}" stroke="#eee"/>')
        parts.append(
            f'<text x="{ml-8}" y="{y+4:.2f}" text-anchor="end" font-size="11" font-family="Arial" fill="#666">{y_val:.2f}</text>'
        )

    for pi, label in enumerate(labels):
        x = ml + pi * step_x
        parts.append(
            f'<text x="{x:.2f}" y="{mt+ph+18}" text-anchor="middle" font-size="10" font-family="Arial" fill="#333" transform="rotate(25 {x:.2f},{mt+ph+18})">{label}</text>'
        )

    for name, color, vals in series:
        points: list[str] = []
        for pi in range(n_points):
            value = vals[pi] if pi < len(vals) else 0.0
            x = ml + pi * step_x
            y = mt + ph - (ph * value / y_max if y_max else 0)
            points.append(f"{x:.2f},{y:.2f}")
        parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.4" points="{" ".join(points)}"/>')
        for point in points:
            px, py = point.split(",")
            parts.append(f'<circle cx="{px}" cy="{py}" r="2.4" fill="{color}"/>')

    legend_x = ml
    legend_y = height - 24
    for idx, (name, color, _) in enumerate(series):
        x = legend_x + idx * 220
        parts.append(f'<rect x="{x}" y="{legend_y-11}" width="14" height="14" fill="{color}"/>')
        parts.append(f'<text x="{x+20}" y="{legend_y}" font-size="12" font-family="Arial" fill="#222">{name}</text>')

    parts.append("</svg>")
    return "\n".join(parts)


def _value_to_heat_color(value: float) -> str:
    """
    Map [0,1] value to a red-yellow-green background color.
    """
    v = max(0.0, min(1.0, float(value)))
    # 0 -> red-ish, 0.5 -> yellow-ish, 1 -> green-ish
    if v < 0.5:
        # red(255,220,220) -> yellow(255,245,200)
        t = v / 0.5
        r = 255
        g = int(220 + (245 - 220) * t)
        b = int(220 + (200 - 220) * t)
    else:
        # yellow(255,245,200) -> green(210,245,210)
        t = (v - 0.5) / 0.5
        r = int(255 + (210 - 255) * t)
        g = 245
        b = int(200 + (210 - 200) * t)
    return f"rgb({r},{g},{b})"


def _metric_heatmap_table_html(
    title: str,
    labels: list[str],  # experiment names
    chunk_labels: list[str],
    chunk_maps: dict[str, dict[str, dict[str, float]]],
    metric_key: str,  # precision | recall
) -> str:
    header_cells = "".join(f"<th>{chunk}</th>" for chunk in chunk_labels)
    rows_html: list[str] = []

    for exp in labels:
        cmap = chunk_maps.get(exp, {})
        value_cells: list[str] = []
        for chunk in chunk_labels:
            value = float(cmap.get(chunk, {}).get(metric_key, 0.0))
            bg = _value_to_heat_color(value)
            value_cells.append(
                f'<td style="background:{bg}; text-align:center; font-variant-numeric: tabular-nums;">{value:.3f}</td>'
            )
        rows_html.append(f"<tr><th>{exp}</th>{''.join(value_cells)}</tr>")

    return f"""
<div class="card">
  <h3>{title}</h3>
  <div style="overflow:auto;">
    <table>
      <thead>
        <tr><th>Experiment</th>{header_cells}</tr>
      </thead>
      <tbody>
        {''.join(rows_html)}
      </tbody>
    </table>
  </div>
</div>
"""


def _chunk_sort_key(chunk_name: str) -> tuple[int, int, str]:
    lowered = chunk_name.strip().lower()
    match = re.search(r"chunk\D*(\d+)", lowered)
    if match:
        return (0, int(match.group(1)), lowered)
    return (1, 10**9, lowered)


def _retrieval_chunk_metrics(report: dict[str, Any]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    chunks = report.get("chunks", [])
    if not isinstance(chunks, list):
        return out
    for item in chunks:
        if not isinstance(item, dict):
            continue
        chunk = str(item.get("chunk", "")).strip()
        metrics = item.get("metrics", {})
        if not chunk or not isinstance(metrics, dict):
            continue
        out[chunk] = {
            "precision": float(metrics.get("precision", 0.0)),
            "recall": float(metrics.get("recall", 0.0)),
        }
    return out


def _analysis_chunk_metrics(report: dict[str, Any]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    chunks = report.get("chunks", [])
    if not isinstance(chunks, list):
        return out
    for item in chunks:
        if not isinstance(item, dict):
            continue
        chunk = str(item.get("chunk", "")).strip()
        metrics = item.get("calculation_matrix", {})
        if not chunk or not isinstance(metrics, dict):
            continue
        out[chunk] = {
            "precision": float(metrics.get("precision", 0.0)),
            "recall": float(metrics.get("recall", 0.0)),
        }
    return out


def _collect_retrieval_reports(root: Path) -> dict[str, dict[str, Any]]:
    reports: dict[str, dict[str, Any]] = {}
    for folder in sorted(path for path in root.iterdir() if path.is_dir()):
        file_path = folder / "retrieval_confusion_matrix.json"
        if not file_path.exists():
            continue
        reports[folder.name] = _load_json(file_path)
    return reports


def _collect_analysis_reports(root: Path) -> dict[str, dict[str, Any]]:
    reports: dict[str, dict[str, Any]] = {}
    for folder in sorted(path for path in root.iterdir() if path.is_dir()):
        file_path = folder / "analysis_confusion_matrix.json"
        if not file_path.exists():
            continue
        reports[folder.name] = _load_json(file_path)
    return reports


def _retrieval_overall(report: dict[str, Any]) -> dict[str, float]:
    metrics = report.get("overall_metrics", {})
    if not isinstance(metrics, dict):
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "tp": 0.0, "fp": 0.0, "fn": 0.0}
    return {
        "precision": float(metrics.get("precision", 0.0)),
        "recall": float(metrics.get("recall", 0.0)),
        "f1": float(metrics.get("f1", 0.0)),
        "tp": float(metrics.get("tp", 0.0)),
        "fp": float(metrics.get("fp", 0.0)),
        "fn": float(metrics.get("fn", 0.0)),
    }


def _analysis_overall(report: dict[str, Any]) -> dict[str, float]:
    metrics = report.get("overall_calculation_matrix", {})
    if not isinstance(metrics, dict):
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "accuracy": 0.0, "tp": 0.0, "fp": 0.0, "fn": 0.0}
    return {
        "precision": float(metrics.get("precision", 0.0)),
        "recall": float(metrics.get("recall", 0.0)),
        "f1": float(metrics.get("f1", 0.0)),
        "accuracy": float(metrics.get("accuracy", 0.0)),
        "tp": float(metrics.get("tp", 0.0)),
        "fp": float(metrics.get("fp", 0.0)),
        "fn": float(metrics.get("fn", 0.0)),
    }


def _build_retrieval_html(reports: dict[str, dict[str, Any]], input_root: Path) -> str:
    labels = sorted(reports.keys())
    overall = {name: _retrieval_overall(report) for name, report in reports.items()}
    chunk_maps = {name: _retrieval_chunk_metrics(report) for name, report in reports.items()}
    chunk_labels = sorted(
        {chunk for cmap in chunk_maps.values() for chunk in cmap.keys()},
        key=_chunk_sort_key,
    )

    score_chart = _bar_chart_svg(
        title="Retrieval Overall Scores by Experiment",
        labels=labels,
        series=[
            ("Precision", "#c95f5f", [overall[n]["precision"] for n in labels]),
            ("Recall", "#2f9d57", [overall[n]["recall"] for n in labels]),
            ("F1", "#4d7fcf", [overall[n]["f1"] for n in labels]),
        ],
        y_max=1.0,
    )
    count_chart = _bar_chart_svg(
        title="Retrieval Confusion Counts by Experiment",
        labels=labels,
        series=[
            ("TP", "#2f9d57", [overall[n]["tp"] for n in labels]),
            ("FP", "#c95f5f", [overall[n]["fp"] for n in labels]),
            ("FN", "#d1a238", [overall[n]["fn"] for n in labels]),
        ],
        y_max=max(
            1.0,
            *[overall[n]["tp"] for n in labels],
            *[overall[n]["fp"] for n in labels],
            *[overall[n]["fn"] for n in labels],
        ),
    )

    table_rows = "\n".join(
        [
            f"<tr><td>{name}</td><td>{overall[name]['precision']:.6f}</td><td>{overall[name]['recall']:.6f}</td><td>{overall[name]['f1']:.6f}</td><td>{int(overall[name]['tp'])}</td><td>{int(overall[name]['fp'])}</td><td>{int(overall[name]['fn'])}</td></tr>"
            for name in labels
        ]
    )

    colors = ["#4d7fcf", "#c95f5f", "#2f9d57", "#d1a238", "#8e62c2", "#2f9fb0", "#8b5a2b", "#7f7f7f"]
    precision_series: list[tuple[str, str, list[float]]] = []
    recall_series: list[tuple[str, str, list[float]]] = []
    for idx, name in enumerate(labels):
        color = colors[idx % len(colors)]
        cmap = chunk_maps.get(name, {})
        precision_series.append((name, color, [cmap.get(c, {}).get("precision", 0.0) for c in chunk_labels]))
        recall_series.append((name, color, [cmap.get(c, {}).get("recall", 0.0) for c in chunk_labels]))

    per_chunk_precision_chart = _line_chart_svg(
        title="Per-Chunk Precision by Experiment",
        labels=chunk_labels,
        series=precision_series,
        y_max=1.0,
    )
    per_chunk_recall_chart = _line_chart_svg(
        title="Per-Chunk Recall by Experiment",
        labels=chunk_labels,
        series=recall_series,
        y_max=1.0,
    )
    precision_heatmap = _metric_heatmap_table_html(
        title="Per-Chunk Precision Table (Exact Values)",
        labels=labels,
        chunk_labels=chunk_labels,
        chunk_maps=chunk_maps,
        metric_key="precision",
    )
    recall_heatmap = _metric_heatmap_table_html(
        title="Per-Chunk Recall Table (Exact Values)",
        labels=labels,
        chunk_labels=chunk_labels,
        chunk_maps=chunk_maps,
        metric_key="recall",
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Retrieval Confusion Matrix Multi-Compare</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #111; background: #fafafa; }}
    .meta {{ color: #444; margin-bottom: 16px; }}
    .card {{ border: 1px solid #ddd; border-radius: 10px; padding: 14px; margin-bottom: 18px; background: #fff; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background: #f5f5f5; }}
    code {{ background: #f5f5f5; padding: 1px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>Retrieval Comparison (Multiple Experiments)</h1>
  <div class="meta"><strong>Input folder:</strong> <code>{input_root}</code></div>
  <div class="card">{score_chart}</div>
  <div class="card">{count_chart}</div>
  {precision_heatmap}
  {recall_heatmap}
  <div class="card">{per_chunk_precision_chart}</div>
  <div class="card">{per_chunk_recall_chart}</div>
  <div class="card">
    <h3>Overall Metrics Table</h3>
    <table>
      <thead>
        <tr><th>Experiment</th><th>Precision</th><th>Recall</th><th>F1</th><th>TP</th><th>FP</th><th>FN</th></tr>
      </thead>
      <tbody>{table_rows}</tbody>
    </table>
  </div>
</body>
</html>
"""


def _build_analysis_html(reports: dict[str, dict[str, Any]], input_root: Path) -> str:
    labels = sorted(reports.keys())
    overall = {name: _analysis_overall(report) for name, report in reports.items()}
    chunk_maps = {name: _analysis_chunk_metrics(report) for name, report in reports.items()}
    chunk_labels = sorted(
        {chunk for cmap in chunk_maps.values() for chunk in cmap.keys()},
        key=_chunk_sort_key,
    )

    score_chart = _bar_chart_svg(
        title="Analysis Overall Scores by Experiment",
        labels=labels,
        series=[
            ("Precision", "#c95f5f", [overall[n]["precision"] for n in labels]),
            ("Recall", "#2f9d57", [overall[n]["recall"] for n in labels]),
            ("F1", "#4d7fcf", [overall[n]["f1"] for n in labels]),
            ("Accuracy", "#8e62c2", [overall[n]["accuracy"] for n in labels]),
        ],
        y_max=1.0,
    )
    count_chart = _bar_chart_svg(
        title="Analysis Confusion Counts by Experiment",
        labels=labels,
        series=[
            ("TP", "#2f9d57", [overall[n]["tp"] for n in labels]),
            ("FP", "#c95f5f", [overall[n]["fp"] for n in labels]),
            ("FN", "#d1a238", [overall[n]["fn"] for n in labels]),
        ],
        y_max=max(
            1.0,
            *[overall[n]["tp"] for n in labels],
            *[overall[n]["fp"] for n in labels],
            *[overall[n]["fn"] for n in labels],
        ),
    )

    table_rows = "\n".join(
        [
            f"<tr><td>{name}</td><td>{overall[name]['precision']:.6f}</td><td>{overall[name]['recall']:.6f}</td><td>{overall[name]['f1']:.6f}</td><td>{overall[name]['accuracy']:.6f}</td><td>{int(overall[name]['tp'])}</td><td>{int(overall[name]['fp'])}</td><td>{int(overall[name]['fn'])}</td></tr>"
            for name in labels
        ]
    )

    colors = ["#4d7fcf", "#c95f5f", "#2f9d57", "#d1a238", "#8e62c2", "#2f9fb0", "#8b5a2b", "#7f7f7f"]
    precision_series: list[tuple[str, str, list[float]]] = []
    recall_series: list[tuple[str, str, list[float]]] = []
    for idx, name in enumerate(labels):
        color = colors[idx % len(colors)]
        cmap = chunk_maps.get(name, {})
        precision_series.append((name, color, [cmap.get(c, {}).get("precision", 0.0) for c in chunk_labels]))
        recall_series.append((name, color, [cmap.get(c, {}).get("recall", 0.0) for c in chunk_labels]))

    per_chunk_precision_chart = _line_chart_svg(
        title="Per-Chunk Precision by Experiment",
        labels=chunk_labels,
        series=precision_series,
        y_max=1.0,
    )
    per_chunk_recall_chart = _line_chart_svg(
        title="Per-Chunk Recall by Experiment",
        labels=chunk_labels,
        series=recall_series,
        y_max=1.0,
    )
    precision_heatmap = _metric_heatmap_table_html(
        title="Per-Chunk Precision Table (Exact Values)",
        labels=labels,
        chunk_labels=chunk_labels,
        chunk_maps=chunk_maps,
        metric_key="precision",
    )
    recall_heatmap = _metric_heatmap_table_html(
        title="Per-Chunk Recall Table (Exact Values)",
        labels=labels,
        chunk_labels=chunk_labels,
        chunk_maps=chunk_maps,
        metric_key="recall",
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Analysis Confusion Matrix Multi-Compare</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #111; background: #fafafa; }}
    .meta {{ color: #444; margin-bottom: 16px; }}
    .card {{ border: 1px solid #ddd; border-radius: 10px; padding: 14px; margin-bottom: 18px; background: #fff; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background: #f5f5f5; }}
    code {{ background: #f5f5f5; padding: 1px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>Analysis Comparison (Multiple Experiments)</h1>
  <div class="meta"><strong>Input folder:</strong> <code>{input_root}</code></div>
  <div class="card">{score_chart}</div>
  <div class="card">{count_chart}</div>
  {precision_heatmap}
  {recall_heatmap}
  <div class="card">{per_chunk_precision_chart}</div>
  <div class="card">{per_chunk_recall_chart}</div>
  <div class="card">
    <h3>Overall Metrics Table</h3>
    <table>
      <thead>
        <tr><th>Experiment</th><th>Precision</th><th>Recall</th><th>F1</th><th>Accuracy</th><th>TP</th><th>FP</th><th>FN</th></tr>
      </thead>
      <tbody>{table_rows}</tbody>
    </table>
  </div>
</body>
</html>
"""


def visualize_from_folder(comparison_input_folder: str | Path, output_dir: str | Path) -> dict[str, str]:
    """
    Auto-compare all experiment folders under comparison_input_folder.
    Any subfolder with `retrieval_confusion_matrix.json` is included.
    Any subfolder with `analysis_confusion_matrix.json` is included.
    """
    input_root = Path(comparison_input_folder).expanduser().resolve()
    out_root = Path(output_dir).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    retrieval_reports = _collect_retrieval_reports(input_root)
    if len(retrieval_reports) < 2:
        raise ValueError(
            f"Need at least 2 retrieval reports to compare. Found: {len(retrieval_reports)} in {input_root}"
        )

    retrieval_html = _build_retrieval_html(retrieval_reports, input_root)
    retrieval_html_path = out_root / "comparison_visuals.html"
    retrieval_html_path.write_text(retrieval_html, encoding="utf-8")

    retrieval_summary = {
        name: _retrieval_overall(report) for name, report in sorted(retrieval_reports.items(), key=lambda x: x[0])
    }
    retrieval_summary_path = out_root / "comparison_summary.json"
    retrieval_summary_path.write_text(json.dumps(retrieval_summary, indent=2, ensure_ascii=False), encoding="utf-8")

    result = {
        "retrieval_html": str(retrieval_html_path),
        "retrieval_summary_json": str(retrieval_summary_path),
    }

    analysis_reports = _collect_analysis_reports(input_root)
    if len(analysis_reports) >= 2:
        analysis_html = _build_analysis_html(analysis_reports, input_root)
        analysis_html_path = out_root / "analysis_comparison_visuals.html"
        analysis_html_path.write_text(analysis_html, encoding="utf-8")
        analysis_summary = {
            name: _analysis_overall(report) for name, report in sorted(analysis_reports.items(), key=lambda x: x[0])
        }
        analysis_summary_path = out_root / "analysis_comparison_summary.json"
        analysis_summary_path.write_text(json.dumps(analysis_summary, indent=2, ensure_ascii=False), encoding="utf-8")
        result["analysis_html"] = str(analysis_html_path)
        result["analysis_summary_json"] = str(analysis_summary_path)

    return result


def main() -> None:
    comparison_input_folder = "/Users/my/Documents/projects/detectionDeviation/evaluation/artifact3"
    output_dir = "/Users/my/Documents/projects/detectionDeviation/evaluation/artifact3/compare_reranker_visuals"
    result = visualize_from_folder(comparison_input_folder, output_dir)
    print("Saved comparison visuals:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
