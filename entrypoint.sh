#!/bin/sh

set -x

cd /app || exit
flask db upgrade
gunicorn -b 0.0.0.0:5000 app:app --chdir /app
