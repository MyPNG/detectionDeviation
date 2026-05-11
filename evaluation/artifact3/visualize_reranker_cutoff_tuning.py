from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON: {path}")
    return payload


def _line_chart_svg(
    title: str,
    x_labels: list[str],
    series: list[tuple[str, str, list[float]]],
    y_max: float = 1.0,
    width: int = 1100,
    height: int = 360,
) -> str:
    ml, mr, mt, mb = 70, 20, 45, 85
    pw = width - ml - mr
    ph = height - mt - mb
    n = max(1, len(x_labels))
    step_x = pw / max(1, n - 1)

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
        '<rect x="0" y="0" width="100_20_4%" height="100_20_4%" fill="#fff"/>',
        f'<text x="{ml}" y="26" font-size="18" font-family="Arial" fill="#111">{title}</text>',
        f'<line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}" stroke="#444"/>',
        f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}" stroke="#444"/>',
    ]

    for i in range(6):
        yv = (y_max / 5) * i
        y = mt + ph - (ph * (yv / y_max if y_max else 0))
        parts.append(f'<line x1="{ml}" y1="{y:.2f}" x2="{ml+pw}" y2="{y:.2f}" stroke="#eee"/>')
        parts.append(
            f'<text x="{ml-8}" y="{y+4:.2f}" text-anchor="end" font-size="11" font-family="Arial" fill="#666">{yv:.2f}</text>'
        )

    for i, label in enumerate(x_labels):
        x = ml + i * step_x
        parts.append(
            f'<text x="{x:.2f}" y="{mt+ph+18}" text-anchor="middle" font-size="10" font-family="Arial" fill="#333">{label}</text>'
        )

    for name, color, vals in series:
        pts = []
        for i in range(n):
            v = vals[i] if i < len(vals) else 0.0
            x = ml + i * step_x
            y = mt + ph - (ph * v / y_max if y_max else 0)
            pts.append(f"{x:.2f},{y:.2f}")
        parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.4" points="{" ".join(pts)}"/>')
        for pt in pts:
            px, py = pt.split(",")
            parts.append(f'<circle cx="{px}" cy="{py}" r="2.2" fill="{color}"/>')

    lx, ly = ml, height - 24
    for i, (name, color, _) in enumerate(series):
        x = lx + i * 190
        parts.append(f'<rect x="{x}" y="{ly-11}" width="14" height="14" fill="{color}"/>')
        parts.append(f'<text x="{x+20}" y="{ly}" font-size="12" font-family="Arial" fill="#222">{name}</text>')

    parts.append("</svg>")
    return "\n".join(parts)


def _bar_chart_svg(
    title: str,
    labels: list[str],
    values: list[float],
    color: str = "#4d7fcf",
    width: int = 1100,
    height: int = 330,
) -> str:
    ml, mr, mt, mb = 70, 20, 45, 85
    pw = width - ml - mr
    ph = height - mt - mb
    n = max(1, len(labels))
    gw = pw / n
    bw = max(8, gw * 0.62)
    vmax = max(1.0, *values)

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
        '<rect x="0" y="0" width="100_20_4%" height="100_20_4%" fill="#fff"/>',
        f'<text x="{ml}" y="26" font-size="18" font-family="Arial" fill="#111">{title}</text>',
        f'<line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}" stroke="#444"/>',
        f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}" stroke="#444"/>',
    ]

    for i in range(6):
        yv = (vmax / 5) * i
        y = mt + ph - (ph * (yv / vmax if vmax else 0))
        parts.append(f'<line x1="{ml}" y1="{y:.2f}" x2="{ml+pw}" y2="{y:.2f}" stroke="#eee"/>')
        parts.append(
            f'<text x="{ml-8}" y="{y+4:.2f}" text-anchor="end" font-size="11" font-family="Arial" fill="#666">{yv:.0f}</text>'
        )

    for i, label in enumerate(labels):
        xg = ml + i * gw
        v = values[i] if i < len(values) else 0.0
        h = ph * (v / vmax if vmax else 0)
        x = xg + (gw - bw) / 2
        y = mt + ph - h
        parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bw:.2f}" height="{h:.2f}" fill="{color}" opacity="0.9"/>')
        parts.append(
            f'<text x="{xg+gw/2:.2f}" y="{mt+ph+18}" text-anchor="middle" font-size="10" font-family="Arial" fill="#333">{label}</text>'
        )
        parts.append(
            f'<text x="{xg+gw/2:.2f}" y="{y-6:.2f}" text-anchor="middle" font-size="10" font-family="Arial" fill="#222">{int(v)}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


def build_visual_report(tuning_json: Path, output_html: Path) -> None:
    data = _load_json(tuning_json)
    sweep = data.get("sweep", [])
    if not isinstance(sweep, list) or not sweep:
        raise ValueError("Invalid tuning JSON: missing or empty 'sweep'.")

    k_labels = [f"k={int(row.get('top_k', 0))}" for row in sweep if isinstance(row, dict)]
    precision_vals = [float(row.get("precision", 0.0)) for row in sweep if isinstance(row, dict)]
    recall_vals = [float(row.get("recall", 0.0)) for row in sweep if isinstance(row, dict)]
    f1_vals = [float(row.get("f1", 0.0)) for row in sweep if isinstance(row, dict)]
    tp_vals = [float(row.get("tp", 0.0)) for row in sweep if isinstance(row, dict)]
    fp_vals = [float(row.get("fp", 0.0)) for row in sweep if isinstance(row, dict)]
    fn_vals = [float(row.get("fn", 0.0)) for row in sweep if isinstance(row, dict)]

    best_k = data.get("best_top_k", "N/A")
    best_metrics = data.get("best_overall_metrics", {})
    objective = data.get("objective", "f1")

    score_chart = _line_chart_svg(
        title="Cutoff Sweep: Precision / Recall / F1 vs k",
        x_labels=k_labels,
        series=[
            ("Precision", "#c95f5f", precision_vals),
            ("Recall", "#2f9d57", recall_vals),
            ("F1", "#4d7fcf", f1_vals),
        ],
        y_max=1.0,
    )
    error_chart = _line_chart_svg(
        title="Cutoff Sweep: TP / FP / FN vs k",
        x_labels=k_labels,
        series=[
            ("TP", "#2f9d57", tp_vals),
            ("FP", "#c95f5f", fp_vals),
            ("FN", "#d1a238", fn_vals),
        ],
        y_max=max(1.0, *(tp_vals + fp_vals + fn_vals)),
    )
    best_bar = _bar_chart_svg(
        title=f"Best k={best_k} Metrics",
        labels=["Precision", "Recall", "F1"],
        values=[
            float(best_metrics.get("precision", 0.0)) * 100,
            float(best_metrics.get("recall", 0.0)) * 100,
            float(best_metrics.get("f1", 0.0)) * 100,
        ],
        color="#4d7fcf",
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Reranker Cutoff Tuning Visualizer</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #111; background: #fafafa; }}
    h1 {{ margin-bottom: 8px; }}
    .meta {{ margin-bottom: 18px; color: #444; }}
    .card {{ border: 1px solid #ddd; border-radius: 10px; padding: 14px; margin-bottom: 18px; background: #fff; }}
    code {{ background: #f5f5f5; padding: 1px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>Reranker Cutoff Tuning Report</h1>
  <div class="meta">
    <div><strong>Input JSON:</strong> <code>{tuning_json}</code></div>
    <div><strong>Objective:</strong> <code>{objective}</code></div>
    <div><strong>Best k:</strong> <code>{best_k}</code></div>
  </div>
  <div class="card">{score_chart}</div>
  <div class="card">{error_chart}</div>
  <div class="card">{best_bar}</div>
</body>
</html>
"""
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(html, encoding="utf-8")


def main() -> None:
    input_json = Path(
        "/Users/my/Documents/projects/detectionDeviation/evaluation/artifact3/with_reranker/reranker_cutoff_tuning_reranked100.json"
    )
    output_html = Path(
        "/Users/my/Documents/projects/detectionDeviation/evaluation/artifact3/compare_reranker_visuals/reranker_cutoff_tuning_visuals.html"
    )
    build_visual_report(input_json, output_html)
    print(f"Saved tuning visual report: {output_html}")


if __name__ == "__main__":
    main()

