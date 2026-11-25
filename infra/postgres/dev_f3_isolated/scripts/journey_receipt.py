"""Validate and sanitize the two-owner shared-journey SQL snapshot."""
import json
import re
import sys
from pathlib import Path

STAGES = {'before', 'after-refresh', 'after-send', 'after-restore'}
MODES = {'sql-only-ci', 'verified-idp'}


def require(ok, label):
    if not ok:
        raise ValueError('STOP_JOURNEY_' + label)


def expected_owner(label):
    require(label in {'a', 'b'}, 'LABEL')
    def conv(n):
        return f'{label}0000000-0000-4000-8000-00000000000{n}'
    def msg(n):
        return f'{label}1000000-0000-4000-8000-00000000000{n}'
    return {
        'list': [[conv(n), f'journey-{label}-{n}'] for n in (3, 2, 1)],
        'page1': [conv(3), conv(2)], 'page2': [conv(1)],
        'detail': [[msg(n), f'journey-{label}-message-{n}', 'user'] for n in (1, 2, 3)],
        'counts': [3, 3, 0, 0, 0, 0], 'foreign': [0, 0],
    }


def validate(work, stage, mode, sha):
    require(stage in STAGES and mode in MODES and re.fullmatch('[a-f0-9]{40}', sha), 'INPUT')
    p = Path(work)
    observed = {}
    for label in ('a', 'b'):
        lines = (p / f'journey-{stage}-{label}.private').read_text().splitlines()
        require(len(lines) == 2, 'SQL_OUTPUT')
        doc, empty = map(json.loads, lines)
        # Canonical JSON comparison also rejects bools masquerading as 0/1.
        require(json.dumps(doc, sort_keys=True) == json.dumps(expected_owner(label), sort_keys=True)
                and json.dumps(empty) == '[0, 0]', 'OWNER_OR_DATA')
        observed[label] = {'data': doc, 'no_context': empty}
    if stage != 'before':
        baseline = json.loads((p / 'journey-before.json').read_text())
        require(baseline.get('owners') == observed and baseline.get('source_sha') == sha
                and baseline.get('identity_mode') == mode and baseline.get('stage') == 'before'
                and baseline.get('contract_version') == 'f3.db.shared_journey.sql.v1', 'BASELINE_DRIFT')
    return {'contract_version': 'f3.db.shared_journey.sql.v1', 'stage': stage,
            'source_sha': sha, 'identity_mode': mode, 'owners': observed,
            'role': 'history_app', 'tls': 'verify-full', 'pg': '17.11',
            'migration_range': '001-010', 'force_rls_tables': 14,
            'global_history_counts': [6, 6, 0, 0, 0, 0],
            'independent_restore_cluster': stage == 'after-restore',
            'http_browser_action': 'NOT_VERIFIED_BY_SQL', 'formal_acceptance': 'NOT_ACCEPTED'}


def emit(work, stage, mode, sha):
    receipt = validate(work, stage, mode, sha)
    with (Path(work) / f'journey-{stage}.json').open('x') as f:
        json.dump(receipt, f, indent=2, sort_keys=True)
        f.write('\n')
    return receipt


if __name__ == '__main__':
    try:
        emit(*sys.argv[1:])
    except (ValueError, OSError, TypeError, KeyError):
        # No raw SQL output or identities in error logs.
        raise SystemExit('STOP_JOURNEY_RECEIPT_INVALID') from None
    print('JOURNEY_SQL_' + sys.argv[2].upper().replace('-', '_') + '=PASS')
