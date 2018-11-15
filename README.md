# trailsto.run

## Local Development
For local development, the frontend and backend run separately. To run the frontend, you'll need `node` and `yarn` (`nvm` is recommended to manage node versions).

### Frontend
To start the frontend: 
```
cd web
yarn start
```

### Backend
The backend requires `docker` & `docker-compose` to run locally
```
cd app
docker-compose up
```

Then, any commands you want to run, will need to be run within the backend docker container:
```
docker exec -it app_app_1 bash
```

## Importing Data
