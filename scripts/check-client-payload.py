"""Check actual production artifacts for accidental full-corpus client imports."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
chunks=ROOT/'dist/client/_next/static/chunks'
course=list(chunks.glob('course-*.js'))
plan=list(chunks.glob('study-plan-*.js'))
assert len(course)==len(plan)==1,'Build the production site before checking payloads.'
assert course[0].stat().st_size<500_000,'The navigation catalog should stay below 500 KB.'
assert plan[0].stat().st_size<200_000,'Repeated task text and review IDs should stay compact.'
assert all('lineStats' not in path.read_text() for path in chunks.glob('*.js')),'Full corpus statistics leaked into the browser.'
report={'scope':'Uncompressed emitted JavaScript sizes; not a network or Core Web Vitals benchmark.',
        'courseCatalogBytes':course[0].stat().st_size,'studyPlanBytes':plan[0].stat().st_size,
        'fullCorpusStatisticsInBrowser':False,'productionPayloadChecks':'passed'}
(ROOT/'docs/client-payload.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
