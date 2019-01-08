FROM python:3.6-alpine

COPY app.py /app/
COPY requirements.txt /app/

WORKDIR /app/

RUN python -m venv venv
RUN venv/bin/pip install -r requirements.txt

ENTRYPOINT [ "venv/bin/flask" ]
CMD ["run","--host=0.0.0.0"]