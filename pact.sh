#!/bin/bash

echo "Creating environment ..."
source .venv/bin/activate

echo "Running pact in $VIRTUAL_ENV ..."
python main.py "$@"

deactivate
