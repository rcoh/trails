find -name '*__pycache__*' | xargs rm -rf
docker build . -t trails-prod
docker tag trails-prod gcr.io/$(gcloud config get-value project)/trails-app:$TAG
docker push gcr.io/$(gcloud config get-value project)/trails-app:$TAG

