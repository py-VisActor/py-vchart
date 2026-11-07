"""Build, fingerprint and validate release bytes in external installations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import venv

ROOT = Path(__file__).resolve().parents[1]
PROJECT = tomllib.loads((ROOT / 'pyproject.toml').read_text('utf-8'))['project']


def identity(path):
    return {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def command(argv, cwd, out):
    result = subprocess.run(list(map(str, argv)), cwd=cwd, capture_output=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix('.stdout.log').write_bytes(result.stdout)
    out.with_suffix('.stderr.log').write_bytes(result.stderr)
    out.with_suffix('.json').write_text(json.dumps({'argv': list(map(str, argv)), 'cwd': str(cwd),
        'exitCode': result.returncode}, indent=2) + '\n', 'utf-8')
    if result.returncode:
        raise RuntimeError(f'Command failed ({result.returncode}); see {out}.stderr.log')


def source_identity():
    paths = [p for p in (ROOT / 'src/py_vchart').rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [ROOT / name for name in ('pyproject.toml', 'README.md')]
    paths += list(ROOT.glob('LICENSE*'))
    files = {p.relative_to(ROOT).as_posix(): identity(p)['sha256'] for p in sorted(paths)}
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


def build(out, *, allow_dirty=False):
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=normal'], cwd=ROOT))
    if dirty and not allow_dirty:
        raise RuntimeError('Commit the reviewed candidate before release build; use --allow-dirty only for development artifacts')
    source_sha = source_identity()
    out.mkdir(parents=True, exist_ok=False)
    command([sys.executable, '-m', 'build', '--outdir', out / 'packages'], ROOT, out / 'build')
    files = sorted((out / 'packages').iterdir())
    assert len(files) == 2 and any(p.suffix == '.whl' for p in files) and any(p.name.endswith('.tar.gz') for p in files)
    manifest = {'project': PROJECT['name'], 'version': PROJECT['version'], 'tag': 'v' + PROJECT['version'],
        'sourceCommit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'sourceTreeSha256': source_sha, 'dirtySource': dirty,
        'distributions': {p.name: identity(p) for p in files}}
    assert source_identity() == source_sha, 'Source changed during build'
    (out / 'packages/release-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', 'utf-8')
    return manifest


def install(manifest_path, packages, out, canvas):
    manifest = json.loads(manifest_path.read_text('utf-8'))
    assert manifest['project'] == PROJECT['name'] and manifest['version'] == PROJECT['version']
    out.mkdir(parents=True, exist_ok=False)
    results = {}
    for name, expected in manifest['distributions'].items():
        file = (packages / name).resolve(strict=True)
        assert file.name == name and identity(file) == expected, 'Distribution fingerprint differs'
        mode = 'wheel' if name.endswith('.whl') else 'sdist'
        target = out / mode
        target.mkdir()
        with tempfile.TemporaryDirectory(prefix='py-vchart-release-') as temporary:
            external = Path(temporary)
            venv.create(external / 'env', with_pip=True)
            python = external / 'env' / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
            command([python, '-m', 'pip', 'install', file, 'py-skia-canvas==' + canvas, 'Pillow>=10'],
                    external, target / 'install')
            command([python, '-m', 'pip', 'check'], external, target / 'pip-check')
            command([python, '-I', '-m', 'unittest', 'discover', '-s', ROOT / 'tests',
                     '-p', 'test_native*.py', '-v'], external, target / 'native-host-contracts')
            command([python, '-I', ROOT / 'tools/release_smoke.py', '--out', target / 'render',
                     '--expected-version', manifest['version'], '--forbid-source', ROOT / 'src'],
                    external, target / 'smoke')
        results[mode] = {'distribution': expected, 'status': 'PASS'}
    (out / 'result.json').write_text(json.dumps({'status': 'PASS', 'canvas': canvas, 'installations': results}, indent=2) + '\n', 'utf-8')
    return results


def pypi(manifest_path, out):
    import urllib.request
    manifest = json.loads(manifest_path.read_text('utf-8'))
    url = f"https://pypi.org/pypi/{manifest['project']}/{manifest['version']}/json"
    with urllib.request.urlopen(url, timeout=60) as response:
        metadata = json.load(response)
    assets = {asset['filename']: asset for asset in metadata['urls']}
    out.mkdir(parents=True, exist_ok=False)
    for name, expected in manifest['distributions'].items():
        assert assets[name]['digests']['sha256'] == expected['sha256']
        with urllib.request.urlopen(assets[name]['url'], timeout=120) as response:
            raw = response.read()
        target = out / name
        target.write_bytes(raw)
        assert identity(target) == expected
    (out / 'release-manifest.json').write_bytes(manifest_path.read_bytes())
    return {'status': 'PASS', 'url': metadata['info']['project_url']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['build', 'install', 'pypi'])
    p.add_argument('--manifest', type=Path)
    p.add_argument('--packages', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--canvas', default='0.1.0a18', choices=['0.1.0a18', '0.1.0a19'])
    p.add_argument('--allow-dirty', action='store_true', help='Development build only; GitHub release transport rejects it')
    args = p.parse_args()
    if args.action == 'build':
        result = build(args.out.resolve(), allow_dirty=args.allow_dirty)
    elif args.action == 'install':
        result = install(args.manifest.resolve(), args.packages.resolve(), args.out.resolve(), args.canvas)
    else:
        result = pypi(args.manifest.resolve(), args.out.resolve())
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
