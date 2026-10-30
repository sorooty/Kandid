"""Stands in for `claude` in tests: replays a recorded `stream-json` run.

Environment: FAKE_CLAUDE_STREAM (file to replay, default stream.jsonl), FAKE_CLAUDE_ARGS (file
where the received arguments are written), FAKE_CLAUDE_SLEEP (seconds to wait before the last
line, to test stopping a run), FAKE_CLAUDE_EXIT (exit code).
"""

import json
import os
import sys
import time
from pathlib import Path

here = Path(__file__).resolve().parent
if args_file := os.environ.get("FAKE_CLAUDE_ARGS"):
    Path(args_file).write_text(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd(),
                                           "home": os.environ.get("KANDID_HOME")}),
                               encoding="utf-8")  # fmt: skip
lines = Path(os.environ.get("FAKE_CLAUDE_STREAM", here / "stream.jsonl")).read_bytes().splitlines()
for index, line in enumerate(lines):
    if index == len(lines) - 1 and (pause := os.environ.get("FAKE_CLAUDE_SLEEP")):
        time.sleep(float(pause))
    sys.stdout.buffer.write(line + b"\n")
    sys.stdout.buffer.flush()
sys.exit(int(os.environ.get("FAKE_CLAUDE_EXIT", "0")))
