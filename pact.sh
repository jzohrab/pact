#!/bin/bash
python3 -m venv .venv
source .venv/bin/activate
echo Running pact in $VIRTUAL_ENV

python main.py

deactivate
