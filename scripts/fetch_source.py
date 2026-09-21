"""Pull the resume data from the single source of truth: github.com/qwert11/resume2.

The YAML files live in resume2/data. A copy is kept in this repository so the build
still works offline (and so a diff shows what changed upstream), but every build
refreshes it first.
"""
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
import sys

RAW = 'https://raw.githubusercontent.com/qwert11/resume2/main/data/'
FILES = [
    'master.yaml',
    'experience.yaml',
    'projects.yaml',
    'skills.yaml',
    'achievements.yaml',
    'education.yaml',
    'languages.yaml',
    'domain.yaml',
    'side_projects.yaml',
]
DATA = Path(__file__).resolve().parents[1] / 'data'


def fetch(strict=False):
    DATA.mkdir(parents=True, exist_ok=True)
    fetched, failed = [], []
    for name in FILES:
        try:
            with urlopen(RAW + name, timeout=20) as r:
                body = r.read().decode('utf-8')
        except (URLError, HTTPError, TimeoutError) as e:
            failed.append((name, e))
            continue
        (DATA / name).write_text(body, encoding='utf-8')
        fetched.append(name)

    for name in fetched:
        print(f'  fetched {name}')
    for name, err in failed:
        local = (DATA / name).exists()
        print(f'  {name}: {err} — {"using local copy" if local else "MISSING"}')
        if strict or not local:
            raise SystemExit(f'cannot build without {name}')
    return fetched


if __name__ == '__main__':
    fetch(strict='--strict' in sys.argv)
