# CD di Natale 24

## Development
To start a development environment, clone this repo first.

Copy `sample_configs/.env`, `sample_configs/database.env` and `sample_configs/service.env` in the root folder. Edit 
according to instructions in these files.

Copy `docker-compose.dev.yaml` into a new file called `docker-compose.override.yaml`.

Use the script to download and setup Bootstrap:
```
cd bootstrap
./download_bootstrap.sh
```

Start the database:
```
docker compose up -d db
```

Set up the database running the migrations:
```
docker compose run --rm worker migrate
```

Create the first user:
```
docker compose run --rm worker createsuperuser 
```

At last, start everything else up: 
```
docker compose up -d 
```

You can now visit http://localhost:8000. 