#!/usr/bin/env bash
# Refresh the caveman eval snapshot (subset: caveman + caveman-compress) and
# print the measured token savings. Run after 00:00 Europe/Berlin so the
# claude session limit has reset.
set -u
REPO="C:/Users/faupe/Documents/BrainFiles/Werkstatt/caveman"
cd "$REPO" || { echo "FAIL: cannot cd $REPO"; exit 1; }

export CAVEMAN_EVAL_MODEL=claude-haiku-4-5
export CAVEMAN_EVAL_SKILLS=caveman,caveman-compress

echo "=== refresh (start $(date '+%H:%M:%S')) ==="
uv run python evals/llm_run.py 2>&1 | tail -15
RC=${PIPESTATUS[0]}
if [ "$RC" -ne 0 ]; then
  echo "FAIL: llm_run.py exit $RC (session limit may still be active)"
  exit "$RC"
fi

echo
echo "=== measure ==="
uv run --with tiktoken python evals/measure.py 2>&1
echo
echo "=== done $(date '+%H:%M:%S') ==="
