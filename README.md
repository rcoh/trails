# Every Single Trail
https://everysingletrail.com

## Local Development
Clone the backend:
```
git clone git@github.com:rcoh/trails.git
```

You'll need to create a sibling directory next to `trails` called `trails-data`. This directory will be mounted into the docker
container.


### Backend
The backend requires `docker` & `docker-compose` to run locally
```
cd app
docker-compose up

# Exec into the docker container
docker-compose exec backend bash

# Run the DB migrations
python manage.py migrate
```
All the commands below assume that you're inside the docker container.

#### Running Tests
```
pytest
```

#### Run the backend
```
python manage.py runserver 0.0.0.0:8000
```

#### Importing Data
Go to https://www.openstreetmap.org/ and navigate to a nearby park and trail system. Click `Export` -- if it doesn't work, pick a smaller area.
Save this file into the `trails-data` sibling directory you created.

From inside the docker container:
```
python manage.py import_data /trail-data/<somefile>.osm
```
It may take a bit to download the elevation tiles.

## Dokku Initialization (launch a new production instance)
```
dokku apps:create est
sudo dokku plugin:install https://github.com/dokku/dokku-postgres.git
sudo dokku plugin:install https://github.com/dokku/dokku-redis.git redis
export POSTGRES_IMAGE="mdillon/postgis" 
export POSTGRES_IMAGE_VERSION="latest"
dokku postgres:create est-db
dokku postgres:link est est-db

dokku plugin:install https://github.com/dokku/dokku-letsencrypt.git
dokku config:set --no-restart est DOKKU_LETSENCRYPT_EMAIL=rcoh@rcoh.me
dokku domains:set est everysingletrail.com

dokku letsencrypt est


```
