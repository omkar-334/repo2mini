#!/usr/bin/env bash
# Sparse clones of the source repositories into repos/, pinned to the commits used in the study.
# Only the directories the tasks need are checked out. Run from the repo root: bash scripts/fetch_repos.sh
set -euo pipefail
mkdir -p repos
clone() { # name url commit paths...
  local name=$1 url=$2 commit=$3; shift 3
  if [ ! -d "repos/$name/.git" ]; then
    git clone --filter=blob:none --no-checkout "$url" "repos/$name"
  fi
  git -C "repos/$name" sparse-checkout init --no-cone
  git -C "repos/$name" sparse-checkout set "$@"
  git -C "repos/$name" checkout "$commit"
}
clone transformers https://github.com/huggingface/transformers 66f51e76efd8542232b8bdd40ade7d1edbaac46f \
  /src/transformers/models/gpt2/ /src/transformers/models/llama/ /src/transformers/models/opt/ /src/transformers/models/bert/ \
  /src/transformers/generation/ /src/transformers/pytorch_utils.py /src/transformers/activations.py /src/transformers/modeling_utils.py /src/transformers/cache_utils.py
clone sortedcontainers https://github.com/grantjenks/python-sortedcontainers 3ac358631f58c1347f1d6d2d92784117db0f38ed /
clone numpy https://github.com/numpy/numpy f2821ffbc2b2e5e366458cb7959acaa2eaf3ac24 /numpy/lib/ /doc/source/reference/routines.statistics.rst
clone pandas https://github.com/pandas-dev/pandas aac259de677878b6328f6272d5537a3922aa0735 \
  /pandas/core/reshape/ /pandas/core/algorithms.py /pandas/core/dtypes/ /pandas/core/arrays/categorical.py /pandas/core/indexes/interval.py
clone trackers https://github.com/roboflow/trackers df8b9a74b6696d87e5ccb8e993620b13ebf3dc59 /trackers/ /src/ /docs/ /README.md
echo done
