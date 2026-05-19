FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

ARG PIP_TRUSTED_HOSTS="--trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org"

RUN python -m pip install --upgrade pip ${PIP_TRUSTED_HOSTS}

COPY requirements.txt .
RUN pip install --no-cache-dir ${PIP_TRUSTED_HOSTS} -r requirements.txt

COPY api ./api
COPY ingestion ./ingestion
COPY ml ./ml

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
