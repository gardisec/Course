FROM python:3.12

ARG UID=10001
ARG GID=10001

RUN apt-get update && apt-get install -y logrotate
COPY logrotate.conf /etc/logrotate.d/logrotate.conf
RUN pip install flask psycopg2 werkzeug 

WORKDIR /app

COPY . . 

RUN groupadd -g $GID tester && \
    useradd -u $UID -g $GID -m tester


RUN chown -R tester:tester /app

USER tester


EXPOSE 5432
EXPOSE 8080

CMD ["python3", "server.py"]

