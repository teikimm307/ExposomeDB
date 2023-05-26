#!/bin/sh

if ! command -V docker 2> /dev/null; then
  echo "Installation requires docker to be present. Please re-run this script after doing so."
fi

printf "Please enter the port you would like to: "
read -r PORT
test -z "$PORT" && PORT=5000
echo "Will run application on port $PORT"

docker kill chemicaldb-web & sleep 5s
mkdir -p instance
docker run -d -t --rm -v ./chemicaldb-database-instance:/app/instance -p "$PORT:5000" --name chemicaldb-web junikimm717/chemicaldb || exit 1
