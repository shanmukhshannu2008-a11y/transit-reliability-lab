import argparse
import subprocess
import sys
import time
from pathlib import Path

parser = argparse.ArgumentParser(
    description="Collect several SEPTA snapshots in one session."
)
parser.add_argument("--count", type=int, default=3)
parser.add_argument("--interval", type=int, default=60)
args = parser.parse_args()

if args.count < 1:
    parser.error("--count must be at least 1")

if args.interval < 60:
    parser.error("--interval must be at least 60 seconds")

collector = Path(__file__).resolve().parent / "collect_snapshot.py"

successful = 0
failed = 0

try:
    for attempt in range(1, args.count + 1):
        print(f"\nAttempt {attempt}/{args.count}", flush=True)

        try:
            result = subprocess.run(
                [sys.executable, str(collector)],
                timeout=45,
                check=False,
            )

            if result.returncode == 0:
                successful += 1
            else:
                failed += 1
                print("Collection failed; continuing to the next attempt.")

        except subprocess.TimeoutExpired:
            failed += 1
            print("Collection timed out; continuing to the next attempt.")

        if attempt < args.count:
            time.sleep(args.interval)

except KeyboardInterrupt:
    print("\nSession stopped by you.")

print(f"\nCompleted attempts: {successful} successful, {failed} failed")