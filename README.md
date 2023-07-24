# slidespeak-backend

## Requirements

- Python3

## Installation

- Create a virtual env: `python3 -m venv env`
- Activate the virtual env: `source env/bin/activate`
- Install all dependencies `python3 -m pip install -r requirements.txt`
- Enable python cerificate: `sudo /Applications/Python[VERSION]/Certificates.command`
- Install unoconv: `brew install unoconv`
- Install libreoffice via `https://libreoffice.org/download/`
- Create `.env` and set all environment variables (see `.env.example`)

## Setup

_Please note:_ Both the index server and the flask backend need to run in parallel.

- Start index server `python3 index_server.py`
- Start Flask Backend `python3 flask_demo.py`

(c) Kevin Goedecke
