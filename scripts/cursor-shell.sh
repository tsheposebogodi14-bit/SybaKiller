#!/usr/bin/env bash
# Source in ~/.bashrc:  source /home/syba/Ghost/scripts/cursor-shell.sh
export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
if [[ -f "${HOME}/Ghost/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "${HOME}/Ghost/.venv/bin/activate"
elif [[ -f "/home/syba/Ghost/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "/home/syba/Ghost/.venv/bin/activate"
fi
