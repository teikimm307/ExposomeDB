FROM fnndsc/python-poetry

WORKDIR /app/

# plz install everything globally in docker
RUN apt-get update && apt-get install -y build-essential
RUN poetry config virtualenvs.create false

# install our dependencies first
COPY pyproject.toml poetry.lock /app/

RUN poetry install --no-dev

# now copy over everything
COPY . /app/

ENTRYPOINT ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]