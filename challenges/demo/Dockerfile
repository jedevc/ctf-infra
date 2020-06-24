FROM python:3-alpine

WORKDIR /usr/src/app/
RUN pip install --no-cache-dir flask

COPY app.py flag.txt ./

CMD ["python", "./app.py"]
