"""Rebuild dependent course artifacts in order, then check their consistency.

Run after authoring contextual selections and editorial overrides. This does
not run translation models, synthesize speech, or change lesson scheduling.
Missing source selections or audio remain explicit validation failures.
"""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full-audio', action='store_true',
                        help='Also hash every local audio file during validation.')
    args = parser.parse_args()
    steps = [
        ['apply-context.py'],
        ['build-study-plan.py'],
        ['build-course-index.py'],
        ['build-content-notice.py'],
        ['validate-course.py', *([] if args.full_audio else ['--metadata-only'])],
    ]
    for script, *options in steps:
        print(f'Rebuilding: {script}', flush=True)
        subprocess.run([sys.executable, str(ROOT/'scripts'/script), *options],
                       cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
