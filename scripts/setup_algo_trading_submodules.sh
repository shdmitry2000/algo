#!/usr/bin/env bash
# Wire open_trade, close_trade, option_x into https://github.com/shdmitry2000/algo_trading
# Prerequisites:
#   1. Create three EMPTY private repos on GitHub (no README/license):
#        https://github.com/new  ->  shdmitry2000/open_trade
#                                 ->  shdmitry2000/close_trade
#                                 ->  shdmitry2000/option_x
#   2. Run this script from the algo repo root (directory that contains open_trade/, etc.).

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
USER="${GITHUB_USER:-shdmitry2000}"
BASE="https://github.com/${USER}"

push_module() {
  local name="$1"
  local dir="${ROOT}/${name}"
  [[ -d "$dir" ]] || { echo "Missing $dir"; exit 1; }
  cd "$dir"
  if [[ ! -d .git ]]; then
    git init -b main
    git add -A
    git commit -m "Initial commit: ${name} package"
  fi
  if ! git remote get-url origin &>/dev/null; then
    git remote add origin "${BASE}/${name}.git"
  fi
  echo "Pushing ${name} -> ${BASE}/${name}.git"
  git push -u origin main
}

echo "=== Push submodule repositories ==="
push_module open_trade
push_module close_trade
push_module option_x

echo ""
echo "=== Add submodules to algo_trading ==="
echo "Clone or enter your algo_trading repo, then run:"
echo ""
echo "  git clone ${BASE}/algo_trading.git"
echo "  cd algo_trading"
echo "  git submodule add ${BASE}/open_trade.git open_trade"
echo "  git submodule add ${BASE}/close_trade.git close_trade"
echo "  git submodule add ${BASE}/option_x.git option_x"
echo "  git commit -m 'Add open_trade, close_trade, option_x submodules'"
echo "  git push"
echo ""
echo "Clone with submodules: git clone --recurse-submodules ${BASE}/algo_trading.git"
