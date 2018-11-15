# trailsto.run

## Local Development
Clone the backend:
```
git clone git@github.com:rcoh/trails.git
```

You'll need to create a sibling directory next to `trails` called `trails-data`. This directory will be mounted into the docker
container.

For local development, the frontend and backend run separately. To run the frontend, you'll need `node` and `yarn` (`nvm` is recommended to manage node versions).

### Frontend
To start the frontend: 
```bash
nvm install 9.10.0
nvm use 8.10.0
cd web
yarn install
yarn start
```

If you see the UI, it worked! This is live updating (just edit files in the web directory and it will change immediately.

### Backend
The backend requires `docker` & `docker-compose` to run locally
```
cd app
docker-compose up

# Exec into the docker container
docker exec -it app_app_1 bash
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
