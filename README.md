# Dr. Walker's Database Website

This is the source code for Dr. Walker's Chemical Database.
All python code is stored in a single app.py for convenience.

# Production

1. Get SSH access to your server. Install docker, the only dependency.
2. `cd` into a directory of your choice (this is where any app-related data will be
   stored as well)
3. Run the following script (it will also prompt you for the port which the app
   should expose, the default being 5000):
```sh
sh -c "$(curl -sSL https://raw.githubusercontent.com/teikimm307/ExposomeDB/master/setup.sh)"
```

To restart the app, rerun the above script. To kill it, run `docker kill chemicaldb-web`.

You will likely want to enable https through a reverse proxy like nginx.

# Development

You need to have poetry installed on your system.

1. Clone this repository
2. Install poetry dependencies with `poetry install`
3. Activate the poetry virtual environment with `poetry shell`
4. Start the development server by executing the `app.py` file.

## Testing Deployment in Development

Just use the built-in docker compose and run `docker-compose up`.
