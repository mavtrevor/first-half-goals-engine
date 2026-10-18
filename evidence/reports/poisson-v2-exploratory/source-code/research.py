"""Explicit offline import and frozen evaluation commands."""
import argparse
import json
from pathlib import Path
import sys

from backtest import walk_forward
from data import ROOT, connect, ingest_snapshot, latest_matches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('import', 'backtest', 'audit'))
    parser.add_argument('--run', default='v1', choices=('v1', 'lag48-sensitivity'))
    args = parser.parse_args()
    folder = ROOT/'data'
    folder.mkdir(exist_ok=True)
    db = connect(folder/'research.sqlite')
    try:
        if args.command == 'import':
            audit = json.loads((folder/'source-audit.json').read_text(encoding='utf-8-sig'))
            corrections = json.loads((folder/'verified-score-corrections.json').read_text(encoding='utf-8-sig'))
            for item in audit['seasons']:
                season = int(item['url'].rsplit('/', 1)[1])
                payload = (folder/f'raw/openligadb-bl1-{season}.json').read_bytes()
                selected = [c for c in corrections if int(c['season'].split('-')[0]) == season]
                sid = ingest_snapshot(db, payload, {'source': 'OpenLigaDB', 'season': season,
                    'observed_at': item['retrievedUtc'], 'source_url': item['url'], 'license': 'ODbL-1.0'}, selected)
                print(f'Imported season {season}: snapshot {sid}', flush=True)
        elif args.command == 'backtest':
            protocol = json.loads((ROOT/'config/evaluation-protocol.json').read_text())
            if args.run == 'lag48-sensitivity':
                protocol.update(name='bundesliga-retrospective-v1-lag48', lag_hours=48)
            report = walk_forward(db, protocol, folder/'reports'/args.run, progress=lambda s: print(s, flush=True))
            print(json.dumps({k: report[k] for k in ('development', 'holdout')}, indent=2), flush=True)
        else:
            rows = latest_matches(db)
            print(json.dumps({'matches': len(rows), 'quarantined': sum(r['quality'] == 'quarantined' for r in rows),
                              'corrected': sum('correction' in r for r in rows),
                              'valid_finished_scores': sum(r.get('target') in (0, 1) for r in rows),
                              'live_access': 'disabled', 'operational_forecasts': 'locked'}, indent=2))
    finally:
        db.close()


if __name__ == '__main__':
    main()
