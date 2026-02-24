FROM python:3.11

WORKDIR /app

RUN pip install --no-cache-dir mlx-vlm uvicorn

EXPOSE 8080

CMD ["mlx_vlm.server", "--host", "0.0.0.0", "--port", "8080"]
