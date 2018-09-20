find -name '*__pycache__*' | xargs sudo rm -r
docker build . -t trails-prod
