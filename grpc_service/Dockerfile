FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/grpc_service/generated

WORKDIR /app

COPY grpc_service/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY proto ./proto
COPY grpc_service ./grpc_service
RUN mkdir -p grpc_service/generated && \
    python -m grpc_tools.protoc \
      -I ./proto \
      --python_out=./grpc_service/generated \
      --grpc_python_out=./grpc_service/generated \
      ./proto/domain.proto

EXPOSE 50051

CMD ["python", "-m", "grpc_service.server"]

