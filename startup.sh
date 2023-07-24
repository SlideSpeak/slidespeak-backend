#!/usr/bin/env bash

python3 -m venv env
source env/bin/activate
python3 -m pip install -r /servers/slidespeak-backend/requirements.txt

python3 /servers/slidespeak-backend/app.py