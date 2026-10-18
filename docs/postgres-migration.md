# Moving the database to the VPS

Locally, PostgreSQL 18 runs in Docker (`docker-compose.yml`). On the Hostinger VPS (Ubuntu 26.04 LTS) it can run either in the same container setup or as a system package. Both work with the same `.env` values.

## What the database holds

- **Data tables** (`geo_country`, `geo_*_country_year`, `etl_load`): rebuilt from the sources at any time with `python manage.py etl`.
- **Blog posts and the admin users**: these exist only in the database. Move them with a dump.

## Option A: Docker on the VPS (closest to local)

1. Install Docker and the compose plugin on the VPS.
2. Copy the project and a `.env` with a new, strong `POSTGRES_PASSWORD` and `DJANGO_SECRET_KEY`, and `DJANGO_DEBUG=0`.
3. Start the database: `docker compose up -d`.
4. Move the data (step 3 below), or load it fresh: `python manage.py migrate`, then `python manage.py etl`.

## Option B: PostgreSQL as an Ubuntu package

1. Check which major version Ubuntu offers: `apt-cache policy postgresql`. If it is not 18, either use it (the site needs nothing specific to 18) or add the PostgreSQL apt repository (https://www.postgresql.org/download/linux/ubuntu/).
2. Create the user and the database with the values from `.env`:
   ```
   sudo -u postgres createuser --pwprompt datamechanics
   sudo -u postgres createdb --owner datamechanics datamechanics
   ```

## Move the data with a dump

On your machine:
```
docker exec datamechanics-db pg_dump -U datamechanics -d datamechanics --format=custom > datamechanics.dump
scp datamechanics.dump <user>@<vps>:
```

On the VPS:
```
pg_restore --no-owner --dbname "postgresql://datamechanics:<password>@127.0.0.1:5432/datamechanics" datamechanics.dump
python manage.py migrate   # applies anything newer than the dump
```

To restore into the Docker database instead, pipe the file into the container:
`docker exec -i datamechanics-db pg_restore -U datamechanics -d datamechanics --no-owner < datamechanics.dump`.

## Files that are not in the database

`media/` holds the country flags and the blog images. It is in git, so it arrives with the code. Files uploaded later through the admin need copying too, for example `rsync -a media/ <user>@<vps>:<project>/media/`.

## Keep the data fresh

Schedule the ETL, for example weekly with cron on the VPS:
```
0 4 * * 1  cd <project> && .venv/bin/python manage.py etl >> logs/etl.log 2>&1
```
