"""Installed-package verification against the fixed 225-case upstream corpus.

This is the native Canvas contract, separate from the unchanged strict
reference-pixel suite. It checks type coverage, text/mark structure, actual
encoded dimensions, all static formats, and absence of a Skia Python runtime.
Numeric and pixel differences remain diagnostic artifacts for visual review.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
from io import BytesIO
import json
import math
from pathlib import Path
import struct
import sys
import traceback
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]


def native_filling_policy(name, raw, scene, png, reference):
    if name not in ('wordCloud/default-filling', 'wordCloud/filled-mask'):
        return None
    # This is a developer verifier, not a runtime package/source fallback.
    path = ROOT / 'tools/native_wordcloud_policy.py'
    definition = importlib.util.spec_from_file_location('native_filling_verifier', path)
    module = importlib.util.module_from_spec(definition)
    definition.loader.exec_module(module)
    return module.check(name, raw, scene, png, reference)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text('utf-8-sig'))


def strings(value):
    if isinstance(value, dict):
        return sum((strings(v) for v in value.values()), Counter())
    if isinstance(value, (tuple, list)):
        return sum((strings(v) for v in value), Counter())
    return Counter([value]) if isinstance(value, str) else Counter()


def structure(value):
    if isinstance(value, dict):
        return {k: structure(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [structure(v) for v in value]
    if value is None:
        return None
    return 'text' if isinstance(value, str) else 'number' if isinstance(value, (int, float)) else type(value).__name__


def numeric_differences(actual, expected, path=''):
    changes = []
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in expected.keys() & actual.keys():
            changes += numeric_differences(actual[key], expected[key], path + '/' + key)
    elif isinstance(expected, list) and isinstance(actual, list):
        for i, (a, e) in enumerate(zip(actual, expected)):
            changes += numeric_differences(a, e, path + '/' + str(i))
    elif type(actual) in (int, float) and type(expected) in (int, float):
        if not math.isclose(actual, expected, abs_tol=1e-6, rel_tol=0):
            changes.append({'path': path, 'expected': expected, 'actual': actual})
    return changes


def validate_encoding(data, fmt, width, height):
    from PIL import Image
    assert data, 'Empty export'
    if fmt in ('png', 'jpg', 'webp'):
        with Image.open(BytesIO(data)) as image:
            assert image.size == (width, height), (fmt, image.size, width, height)
            assert image.format.lower() == {'png': 'png', 'jpg': 'jpeg', 'webp': 'webp'}[fmt]
    elif fmt == 'svg':
        root = ElementTree.fromstring(data)
        assert root.tag.split('}')[-1] == 'svg'
        assert len(list(root.iter())) > 1, 'Empty SVG document'
    elif fmt == 'pdf':
        assert data.startswith(b'%PDF-') and b'%%EOF' in data[-2048:], 'Invalid PDF framing'


def run(args):
    import importlib.metadata
    import py_vchart
    from py_vchart import VChart
    from PIL import Image, ImageChops, ImageStat
    if args.expected_version:
        assert py_vchart.__version__ == args.expected_version
    module = Path(py_vchart.__file__).resolve()
    if args.forbid_source:
        assert not module.is_relative_to(args.forbid_source.resolve()), 'Imported checkout rather than installed distribution'
    kinds = set(VChart.supported_types())
    assert len(kinds) == 68, 'Registry denominator changed; review before release'
    cases = sorted(args.fixtures.glob('*/*/spec.json'))
    assert len(cases) == 225, 'Incomplete fixed upstream input corpus'
    args.out.mkdir(parents=True, exist_ok=False)
    rows = []
    seen = set()
    for spec_path in cases:
        case = spec_path.parent
        name = case.parent.name + '/' + case.name
        target = args.out / name
        target.mkdir(parents=True)
        row = {'id': name, 'type': case.parent.name, 'status': 'FAIL'}
        try:
            raw = spec_path.read_bytes()
            source = load(spec_path)
            capture = load(case / 'capture.json')
            expected_png = (case / 'expected.png').read_bytes()
            assert sha(raw) == capture['inputSha256'] and sha(expected_png) == capture['pngSha256']
            expected_scene = load(case / 'expected.scene.json')
            maps, svgs = {}, {}
            if source['type'] == 'map':
                geo = (case / 'geo.json').read_bytes()
                assert sha(geo) == capture['geojsonSha256']
                maps[source['map']] = load(case / 'geo.json')
            if source['type'] == 'pictogram':
                svg = (case / 'source.svg').read_bytes()
                assert sha(svg) == capture['svgSha256']
                svgs[source['svg']] = svg.decode('utf-8')
            chart = VChart(source, backend=args.backend, text_engine='canvas', maps=maps, svgs=svgs).render()
            png = chart.to_png()
            validate_encoding(png, 'png', chart.width, chart.height)
            (target / 'actual.png').write_bytes(png)
            (target / 'expected.png').write_bytes(expected_png)
            (target / 'spec.json').write_bytes(raw)
            (target / 'expected.scene.json').write_bytes((case / 'expected.scene.json').read_bytes())
            (target / 'actual.scene.json').write_text(json.dumps(chart.scene, ensure_ascii=True, indent=2, allow_nan=False) + '\n', 'utf-8')
            text_equal = strings(chart.scene) == strings(expected_scene)
            structure_equal = structure(chart.scene) == structure(expected_scene)
            differences = numeric_differences(chart.scene, expected_scene)
            with Image.open(BytesIO(expected_png)).convert('RGBA') as expected, Image.open(BytesIO(png)).convert('RGBA') as actual:
                assert actual.size == expected.size
                if len(expected.getcolors(expected.width * expected.height) or ()) > 1:
                    assert len(actual.getcolors(actual.width * actual.height) or ()) > 1, 'Visible upstream content became a blank image'
                diff = ImageChops.difference(expected, actual)
                metrics = {'meanChannelDifference': ImageStat.Stat(diff).mean,
                           'bbox': diff.getbbox(alpha_only=False), 'exactBytes': png == expected_png}
                diff.save(target / 'diff.png')
            font_policy = native_filling_policy(name, raw, chart.scene, png, expected_scene)
            if font_policy is not None:
                # Font-dependent decorative repetition is not primary input
                # loss. Keep exact mismatch fields truthful and additionally
                # require independent public-Canvas glyph and analytic mask
                # checks for these two byte-locked reviewed cases only.
                (target / 'native-font-policy.json').write_text(json.dumps(font_policy, indent=2) + '\n', 'utf-8')
                assert font_policy['status'] == 'PASS', 'Independent native filling contract failed: ' + str(font_policy['errors'])
            else:
                assert text_equal, 'Visible text/mark string multiset differs from independent upstream scene'
                assert structure_equal, 'Scene mark/label structure differs from independent upstream scene'
            exports = {'png': {'sha256': sha(png), 'bytes': len(png)}}
            if source['type'] not in seen or args.all_formats:
                for fmt in ('jpg', 'webp', 'svg', 'pdf'):
                    data = chart.to_buffer(fmt)
                    validate_encoding(data, fmt, chart.width, chart.height)
                    (target / ('actual.' + fmt)).write_bytes(data)
                    exports[fmt] = {'sha256': sha(data), 'bytes': len(data)}
                if source['type'] == 'bar':
                    svg = (target / 'actual.svg').read_bytes()
                    assert b'<image' not in svg, 'Simple bars were replaced with a full-frame raster image'
                seen.add(source['type'])
            assert 'skia' not in sys.modules, 'Default native rendering imported skia-python'
            if args.backend == 'gpu':
                assert chart.engine.get('renderer') == 'GPU', 'GPU request was silently downgraded'
            if args.backend == 'cpu':
                assert chart.engine.get('renderer') != 'GPU', 'CPU request used GPU'
            row.update(status='PASS', source={'specSha256': sha(raw), 'expectedPngSha256': sha(expected_png),
                        'expectedSceneSha256': sha((case / 'expected.scene.json').read_bytes())},
                       textEqual=text_equal, structureEqual=structure_equal, nativeFontPolicy=font_policy,
                       numericDifferenceCount=len(differences),
                       numericDifferences=differences, pixelsDiagnostic=metrics, exports=exports,
                       engine=chart.engine, width=chart.width, height=chart.height)
        except Exception as exc:
            row.update(error=str(exc), traceback=traceback.format_exc())
        (target / 'result.json').write_text(json.dumps(row, ensure_ascii=True, indent=2, allow_nan=False) + '\n', 'utf-8')
        rows.append(row)
        print(name, row['status'], row.get('error', ''), flush=True)
    passed = all(row['status'] == 'PASS' for row in rows) and seen == kinds
    result = {'status': 'PASS' if passed else 'FAIL', 'mode': 'native-canvas', 'backend': args.backend,
              'python': sys.version, 'module': str(module), 'version': py_vchart.__version__,
              'canvas': importlib.metadata.version('py-skia-canvas'), 'types': sorted(kinds), 'exportedTypes': sorted(seen),
              'packages': {name: importlib.metadata.version(name) for name in ('py-visactor-vchart', 'py-skia-canvas', 'numpy', 'Pillow')},
              'cases': len(rows), 'passed': sum(row['status'] == 'PASS' for row in rows),
              'gate': 'independent upstream text/mark structure, valid encodings and backend; pixel/numeric differences diagnostic, require visual review',
              'results': rows}
    (args.out / 'result.json').write_text(json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False) + '\n', 'utf-8')
    return passed


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--fixtures', type=Path, default=ROOT / 'tests/cases')
    p.add_argument('--expected-version')
    p.add_argument('--forbid-source', type=Path)
    p.add_argument('--backend', choices=['cpu', 'auto', 'gpu'], default='cpu')
    p.add_argument('--all-formats', action='store_true')
    args = p.parse_args()
    return 0 if run(args) else 1


if __name__ == '__main__':
    raise SystemExit(main())
