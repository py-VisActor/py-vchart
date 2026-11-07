import argparse
import hashlib
import io
import os
from html import escape
from urllib.parse import quote
import json
import math
from pathlib import Path

from PIL import Image

from pixels import compare, passes
from py_vchart import VChart
from py_vchart.core import CARTESIAN_RENDERERS, GEOMETRY_RENDERERS, POLAR_RENDERERS, RENDERERS

ROOT = Path(__file__).resolve().parents[2]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def same_scene(actual, expected):
    if isinstance(expected, dict):
        return (actual.keys() == expected.keys()
                and all(same_scene(actual[k], val) for k, val in expected.items()))
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(map(same_scene, actual, expected))
    if isinstance(expected, (float, int)):
        return math.isclose(actual, expected, rel_tol=0, abs_tol=1e-6)
    return actual == expected


def check_case(output, case):
    target = output / case.name
    target.mkdir(parents=True, exist_ok=True)
    spec = case / "spec.json"
    baseline = case / "expected.png"
    manifest = read_json(case / "capture.json")
    for key, path in [("inputSha256", spec), ("pngSha256", baseline)]:
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest[key]:
            raise ValueError(f"{case.name}: {key} differs from captured baseline")
    source = read_json(spec)
    if source.get("type") == "map":
        geo = case / "geo.json"
        if hashlib.sha256(geo.read_bytes()).hexdigest() != manifest["geojsonSha256"]:
            raise ValueError(f"{case.name}: geographic source differs from baseline")
        VChart.register_map(source["map"], read_json(geo))
    if source.get("type") == "pictogram":
        svg = (case / "source.svg").read_bytes()
        if hashlib.sha256(svg).hexdigest() != manifest["svgSha256"]:
            raise ValueError("SVG source differs from captured reference")
        VChart.register_svg_source(source["svg"], svg)
    # This suite preserves the reviewed 0.1.0 calibrated reference contract.
    # Native Canvas is checked separately; its font pixels are not substituted
    # for this baseline and no historical pixel gate is relaxed.
    chart = VChart(source, text_engine="reference").render()
    png = chart.to_png()
    (target / "actual.png").write_bytes(png)
    (target / "actual.scene.json").write_text(json.dumps(chart.scene, indent=2))
    with Image.open(baseline) as expected, Image.open(io.BytesIO(png)) as actual:
        metrics, diff = compare(expected, actual)
        diff.point(lambda x: min(255, x * 4)).save(target / "diff.png")
    geometry = same_scene(chart.scene, read_json(case / "expected.scene.json"))
    peak_ok = True
    policy_path = case / "pixel-policy.json"
    if policy_path.exists():
        policy = read_json(policy_path)
        outside = diff.copy()
        for region in policy["regions"]:
            peak_ok &= diff.crop(region).getextrema()[1] <= policy["peak_limit"]
            outside.paste(0, tuple(region))
        metrics["peak_outside_glyphs"] = outside.getextrema()[1]
    checked = metrics | {"peak_channel_error": metrics.get("peak_outside_glyphs", metrics["peak_channel_error"])}
    return dict(passed=geometry and peak_ok and passes(checked), scene_equal=geometry, **metrics)


def run(output, kind="bar"):
    cases = sorted((ROOT / "tests/cases" / kind).iterdir())
    if not cases:
        raise ValueError(f"No baselines for {kind}")
    results = {}
    for case in cases:
        try:
            results[case.name] = check_case(output, case)
        except (ValueError, OSError, TypeError, KeyError, RuntimeError) as error:
            results[case.name] = {"passed": False, "error": str(error)}
    (output / "report.json").write_text(json.dumps(results, indent=2))
    for case, result in results.items():
        print(case, result)
    return all(r["passed"] for r in results.values())


def write_gallery(output, results):
    parts = ["""<!doctype html><html lang="zh"><meta charset="utf-8">
<title>图表渲染对照</title><style>
body{font:16px system-ui;margin:2rem}article{border-top:1px solid #ccc}
section{display:flex;gap:1rem}figure{margin:0;flex:1}img{width:100%;max-width:640px}
</style><h1>图表渲染对照</h1>"""]
    for kind, cases in results.items():
        parts.append(f"<h2>{escape(kind)}</h2>")
        for case, metrics in cases.items():
            status = "通过" if metrics["passed"] else "失败"
            parts.append(f"<article><h3>{escape(case)} · {status}</h3><section>")
            baseline = ROOT / "tests/cases" / kind / case / "expected.png"
            actual = output / kind / case
            for title, path in [("上游", baseline), ("Python", actual / "actual.png"), ("差异 ×4", actual / "diff.png")]:
                url = quote(Path(os.path.relpath(path, output)).as_posix())
                parts.append(f'<figure><figcaption>{title}</figcaption><img loading="lazy" src="{url}" alt="{title}"></figure>')
            parts.append("</section></article>")
    (output / "index.html").write_text("".join(parts), encoding="utf-8")


def run_batch(output, renderers=CARTESIAN_RENDERERS):
    results = {}
    for kind in sorted(renderers):
        run(output / kind, kind)
        results[kind] = read_json(output / kind / "report.json")
    passed = all(case["passed"] for cases in results.values() for case in cases.values())
    summary = {"passed": passed, "types": len(results), "cases": sum(map(len, results.values())),
               "results": results}
    (output / "report.json").write_text(json.dumps(summary, indent=2))
    write_gallery(output, results)
    return passed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--type", choices=sorted(RENDERERS), default="bar")
    group.add_argument("--all", action="store_true")
    group.add_argument("--batch", choices=["cartesian", "polar", "geometry"])
    args = parser.parse_args()
    if args.all or args.batch:
        batch = args.batch or "all"
        kinds = {"cartesian": CARTESIAN_RENDERERS, "polar": POLAR_RENDERERS, "geometry": GEOMETRY_RENDERERS, "all": RENDERERS}[batch]
        return 0 if run_batch(args.output or ROOT / "test-runs" / (batch + "-batch"), kinds) else 1
    return 0 if run(args.output or ROOT / "test-runs" / args.type, args.type) else 1


if __name__ == "__main__":
    raise SystemExit(main())
