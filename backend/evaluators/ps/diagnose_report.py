"""Read-only diagnostics of existing pilot JSON. No API or writes."""
import argparse
import json
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    data = json.loads(args.report.read_text(encoding='utf-8-sig'))
    for case in data.get('cases', []):
        print('CASE', case.get('id'))
        for code, result in case.get('results', {}).items():
            dec = result.get('decision', {})
            print(' ', code, dec.get('status'), dec.get('score'), dec.get('reason'))
        for event in case.get('events', []):
            if event.get('source') == 'blocked':
                print('  EVENT', event.get('code'), event.get('stage'), event.get('exception_type',''))
                if event.get('traceback'):
                    print(event['traceback'])
if __name__ == '__main__':
    main()
