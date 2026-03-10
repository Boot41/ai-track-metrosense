FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv pip install --system --no-cache -r pyproject.toml

COPY . .

EXPOSE 8020

CMD ["uv", "run", "adk", "api_server", "--host", "0.0.0.0", "--port", "8020", "."]
