"""Serve synthetic test data in a temporary folder; never use a real user profile."""
import argparse
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from earthlink import env, server
from tests.fixtures import make_live

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='earthlink-fixture-') as fixture:
        live = make_live(fixture)
        data = str(Path(live).parent)
        env.data_dir = lambda: data
        env.snapshot_dir = lambda: str(Path(fixture) / 'captures')
        os.makedirs(env.snapshot_dir())
        server.serve(str(ROOT / 'shared' / 'viewer'), args.port)
