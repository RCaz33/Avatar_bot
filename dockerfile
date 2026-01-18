FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm

WORKDIR /workspace

COPY packages.txt* requirements.txt* ./

RUN if [ -f packages.txt ]; then \
    apt-get update && \
    apt-get upgrade -y && \
    xargs apt-get install -y < packages.txt && \
    rm -rf /var/lib/apt/lists/*; \
    fi

RUN if [ -f requirements.txt ]; then \
    pip3 install --user -r requirements.txt; \
    fi && \
    pip3 install --user streamlit

COPY . .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app/Welcome.py", "--server.enableCORS", "false", "--server.enableXsrfProtection", "false", "--server.port", "8501", "--server.address", "0.0.0.0"]