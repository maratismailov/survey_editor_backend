#!/bin/bash
`python3 -m venv env`
source env/bin/activate
pip install -U pip
pip install fastapi
pip install uvicorn
pip install graphene
pip install sqlalchemy
pip install psycopg2-binary
pip freeze -> requirements.txt
