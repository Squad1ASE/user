FROM python:3.8-alpine

ADD . /user
WORKDIR /user

RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev
RUN pip install -r requirements.txt
RUN python setup.py develop

EXPOSE 5060