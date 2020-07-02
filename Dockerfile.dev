FROM python:3.7
WORKDIR /app/
# pyosmium dependencies
RUN apt-get update 
RUN apt-get install -y build-essential libboost-python-dev \
                     libexpat1-dev zlib1g-dev libbz2-dev
RUN apt-get install -y gdal-bin libsqlite3-mod-spatialite

RUN apt-get install -y htop vim
RUN apt-get install -y postgresql-client

RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -
RUN echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list
RUN apt-get update && apt-get install -y yarn
COPY trails/package.json /app/package.json
COPY trails/yarn.lock /app/yarn.lock
RUN yarn install

# Hack for pyosmium (https://github.com/osmcode/pyosmium/issues/52)
RUN rm /usr/lib/x86_64-linux-gnu/libboost_python.so
RUN ln -s /usr/lib/x86_64-linux-gnu/libboost_python-py35.so /usr/lib/x86_64-linux-gnu/libboost_python.so
RUN pip install pipenv
COPY trails/Pipfile /app/
COPY trails/Pipfile.lock /app/
RUN pipenv install --pre --system && rm -r ~/.cache
RUN pip install  SRTM.py
COPY trails/ /app/
EXPOSE 8000
RUN python manage.py check
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
