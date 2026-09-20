"""Load the complete course from a local compiler cache or committed lesson files."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
COMPILED_COURSE = ROOT / '.sites-runtime/corpus/compiled-course.json'


def load_course(*, prefer_cache=True):
    if prefer_cache and COMPILED_COURSE.is_file():
        return json.loads(COMPILED_COURSE.read_text())
    index = json.loads((ROOT / 'content/course-index.json').read_text())
    lessons = []
    for meta in index['lessons']:
        lesson = json.loads((ROOT / 'public/course' / (meta['id'] + '.json')).read_text())
        lesson.pop('questions', None)
        lessons.append(lesson)
    return lessons
