FROM python:3.7
WORKDIR /app/
# pyosmium dependencies
RUN apt-get update 
RUN apt-get install -y build-essential libboost-python-dev \
                     libexpat1-dev zlib1g-dev libbz2-dev
RUN apt-get install -y gdal-bin libsqlite3-mod-spatialite


# Hack for pyosmium (https://github.com/osmcode/pyosmium/issues/52)
RUN rm /usr/lib/x86_64-linux-gnu/libboost_python.so
RUN ln -s /usr/lib/x86_64-linux-gnu/libboost_python-py35.so /usr/lib/x86_64-linux-gnu/libboost_python.so
RUN pip install pipenv
COPY Pipfile /app/
RUN pip install SRTM.py
RUN pipenv install --pre
COPY . /app/
EXPOSE 8000
CMD ["pipenv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
