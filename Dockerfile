FROM node:10 as bundles
WORKDIR /app/
COPY trails/package.json /app/package.json
COPY trails/yarn.lock /app/yarn.lock
RUN yarn install
COPY trails/ /app/
RUN yarn run webpack --mode=production

FROM python:3.7 as python
WORKDIR /app/
RUN apt-get update && apt-get install -y gdal-bin
RUN pip install pipenv
COPY trails/Pipfile /app/
COPY trails/Pipfile.lock /app/
RUN pipenv install --pre --system && rm -r ~/.cache
COPY trails/ /app/
RUN rm -rf /app/assets/bundles/
COPY --from=bundles /app/assets/bundles /app/assets/bundles
ENV ENV prod
CMD ["bin/run-prod.sh"]

#RUN pip install  SRTM.py
#EXPOSE 8000
#RUN python manage.py check
#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
