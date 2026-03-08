FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY . /app/stylist_agent

EXPOSE 8015

RUN useradd -m -s /bin/bash appuser
USER appuser

CMD ["adk", "api_server", "--port=8015", "--host=0.0.0.0"]