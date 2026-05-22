#!/usr/bin/env bash
set -e

DIR="$(dirname "$0")"

echo "=== Query A ==="
bash "$DIR/run_query.sh" a

echo ""
echo "=== Query B ==="
bash "$DIR/run_query.sh" b

echo ""
echo "=== Query C1 ==="
bash "$DIR/run_query.sh" c1

echo ""
echo "=== Query C2 (no-clear) ==="
bash "$DIR/run_query.sh" c2 --no-clear

echo ""
echo "=== Query D ==="
bash "$DIR/run_query.sh" d
