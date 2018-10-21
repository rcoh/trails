#!/bin/bash
docker run -it -v /home/russell/code/trails/app/trails/:/app/  -v /home/russell/code/trails/app/trails-db/:/db/ -v /home/russell/code/trails-data/:/trail-data/ -p 8000:8000  --cap-add=SYS_PTRACE trails-prod-test bash
