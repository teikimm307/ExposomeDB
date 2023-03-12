#!/bin/sh

set -x

#flask db upgrade
./initialize_db.py
#gunicorn -b 0.0.0.0:5000 'app.__init__.create_app()' --chdir /app
gunicorn -b 0.0.0.0:5000 app:app --chdir /app
