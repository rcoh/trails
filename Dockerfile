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
COPY --from=bundles /app/webpack-stats.json /app/webpack-stats.json
ENV ENV prod
RUN python manage.py collectstatic
