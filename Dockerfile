FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt 

RUN uv add -r requirements.txt

COPY . .

EXPOSE 8000

CMD [ "uvicorn", "main:app", "--host", "0.0.0.0","--port","8000" ]
