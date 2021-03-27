FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7

COPY requirements.txt /tmp

WORKDIR /tmp

RUN pip install -r requirements.txt

COPY ./app /app