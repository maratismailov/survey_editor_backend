FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7

RUN pip install graphene

COPY ./app /app