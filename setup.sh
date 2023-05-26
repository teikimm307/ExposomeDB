#!/bin/sh

if ! command -V docker; then
  echo "Installation requires docker to be present. Please re-run this script after doing so."
fi

printf "Please enter the port you would like to: "
read -r PORT

docker kill chemicaldb-web
mkdir -p instance
docker run -d -t --rm -v ./chemicaldb-database-instance:/app/instance -p "$PORT:5000" --name chemicaldb-web junikimm717/chemicaldb || exit 1
