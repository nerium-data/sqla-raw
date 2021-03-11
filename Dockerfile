FROM python:3.8-buster
WORKDIR /home/raw

# install psql
# see https://www.postgresql.org/download/linux/ubuntu/
RUN apt-get update && apt-get install -y lsb-release && \
    sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list' && \
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - && \
    apt-get update && \
    apt-get -y install postgresql-client-13

# raw
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY raw ./raw

# tests
COPY tests ./tests
RUN pip install -r ./tests/requirements.txt
