from pathlib import Path
import json, hashlib, sys
from jsonschema import Draft202012Validator
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]

def load(rel):
    return json.loads((ROOT/rel).read_text())

def validate(schema_rel, instance):
    schema=load(schema_rel)
    errs=sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e:list(e.path))
    if errs:
        raise AssertionError(f"{schema_rel}: " + " | ".join(e.message for e in errs[:10]))

# Preserve all Phase-2 artefact checks by importing the old validator functions indirectly is avoided;
# execute it as a script first.
import subprocess
r=subprocess.run([sys.executable,str(ROOT/'tests/validate_phase2.py')],cwd=ROOT,text=True,capture_output=True)
if r.returncode!=0:
    raise AssertionError('Phase-2 regression failed: '+r.stdout+r.stderr)

# New Phase-3 schema validity
for rel in [
 'schemas/legal-action.schema.json','schemas/resolution-trace.schema.json','schemas/solver-request.schema.json',
 'schemas/solver-fixture-catalog.schema.json','schemas/recommendation.schema.json','schemas/rules-profile.schema.json']:
    Draft202012Validator.check_schema(load(rel))

# Schema instances
validate('schemas/rules-profile.schema.json', load('examples/rules-profile.verified.json'))
validate('schemas/solver-fixture-catalog.schema.json', load('data/solver/verified-rules-fixtures.v1.0.0.json'))
validate('schemas/legal-action.schema.json', load('examples/legal-action.indecision.json'))
validate('schemas/resolution-trace.schema.json', load('examples/resolution-trace.synthetic.json'))
validate('schemas/solver-request.schema.json', load('examples/solver-request.synthetic.json'))
validate('schemas/recommendation.schema.json', load('examples/recommendation.synthetic.json'))

catalog=load('data/solver/verified-rules-fixtures.v1.0.0.json')
assert catalog['fixtureCount']==len(catalog['fixtures'])==1
ids=[f['fixtureId'] for f in catalog['fixtures']]
assert len(ids)==len(set(ids)) and ids == ['F-101']

rules=load('data/rule-catalog.json')
rule_ids={r['id'] for r in rules['rules']}
assert rules['catalogVersion']=='1.0.0'
for required in [f'R-{n:03d}' for n in range(39,55)]:
    assert required in rule_ids
for f in catalog['fixtures']:
    assert set(f['focusRuleIds']) <= rule_ids

# Verified formula and geometry anchors
assert {(x['start'],x['casts'],x['matchingWhiteHits'],x['next']) for x in catalog['resourceTransitions']} >= {(2,2,0,0),(2,0,2,4),(3,0,2,4),(2,2,1,1)}
assert len(catalog['indecision']['legalOffsets']) == 4
assert len(catalog['indecision']['illegalDiagonalOffsets']) == 4

ranking=load('data/solver/ranking-policy.v0.5.0.json')
assert ranking['rankingPolicyId']=='ranking-lexicographic-v0.5.0'
assert [k['index'] for k in ranking['keys']]==list(range(1,len(ranking['keys'])+1))
assert [k['id'] for k in ranking['keys']][:3]==[
    'mandatory_movement_and_black_safety',
    'cast_count',
    'resource_resilience',
]
assert ranking['canonicalSpellOrder']==['indecision','reflection','repulsion','attraction']

status=load('data/solver/status-precedence.v0.5.0.json')
assert {x['status'] for x in status['precedence']}=={'solved','confirmation_required','blocked_unverified_rule','no_safe_solution','invalid_state'}

deps=load('data/solver/rule-dependency-map.v0.5.0.json')
for d in deps['dependencies']:
    assert set(d['ruleIds']) <= rule_ids

# Version consistency for principal instances
for rel in ['data/arena/arena-model.draft-v0.5.0.json','data/arena/reference-turn.manual.json','examples/manual-editor-session.reference.json','examples/turn-state.synthetic.json']:
    obj=load(rel)
    if 'schemaVersion' in obj:
        assert obj['schemaVersion']=='0.5.0', rel

# Required Phase-3 docs
for rel in [
 'docs/solver/SOLVER_BEHAVIOUR_SPEC.md','docs/solver/ACTION_ENUMERATION.md','docs/solver/STATE_TRANSITION_TRACE.md',
 'docs/solver/STATUS_AND_AMBIGUITY.md','docs/solver/CANDIDATE_RANKING.md','docs/solver/TEST_ORACLE_SPEC.md','docs/solver/PROPERTY_TEST_SPEC.md',
 'docs/workflow/PHASE_4_CHAT_BRIEF.md']:
    p=ROOT/rel
    assert p.exists() and p.stat().st_size>100, rel

print('PASS: Phase-2 regression plus Phase-3 schemas, policies, fixtures, formulas and documentation validated.')
