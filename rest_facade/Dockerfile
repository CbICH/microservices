FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/rest_facade/generated

WORKDIR /app

COPY rest_facade/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY proto ./proto
COPY rest_facade ./rest_facade
RUN mkdir -p rest_facade/generated && \
    python -m grpc_tools.protoc \
      -I ./proto \
      --python_out=./rest_facade/generated \
      --grpc_python_out=./rest_facade/generated \
      ./proto/domain.proto

EXPOSE 8000

CMD ["uvicorn", "rest_facade.main:app", "--host", "0.0.0.0", "--port", "8000"]

