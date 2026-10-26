cd "$(dirname "$0")"

if ! python3 -c "import sys; sys.exit(sys.version_info < (3, 12))" 2>/dev/null; then
  echo "ShuttleStep needs Python 3.12 or newer. Install it from https://www.python.org/downloads/"
  echo "and then double-click this file again."
  read -p "Press Enter to close."
  exit 1
fi

if [ ! -d venv ]; then
  echo "First-time setup: installing what ShuttleStep needs (this takes a few minutes)..."
  python3 -m venv venv || { read -p "Setup failed. Press Enter to close."; exit 1; }
  ./venv/bin/pip install --upgrade pip
fi

if ! cmp -s requirements.txt venv/installed-requirements.txt; then
  ./venv/bin/pip install -r requirements.txt || { read -p "Setup failed. Press Enter to close."; exit 1; }
  cp requirements.txt venv/installed-requirements.txt
fi

./venv/bin/python app.py
