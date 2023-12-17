FROM python:3.12-slim

RUN apt-get update -qq && apt-get -y install libsqlclient-dev libssl-dev default-libmysqlclient-dev \
    libpq-dev gettext make
WORKDIR /app

RUN pip install gunicorn
COPY requirements.txt /app
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["make", "run"]
