#!/bin/bash

echo "Creating environment ..."
python3 -m venv .venv
source .venv/bin/activate

echo "Running pact in $VIRTUAL_ENV ..."
python main.py "$@"

deactivate
