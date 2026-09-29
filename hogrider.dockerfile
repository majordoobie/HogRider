FROM python:3.14-slim

# Do not buffer stdout/stderr just dump it asap
ENV PYTHONUNBUFFERED=1

ARG WORKDIR=/opt/code
WORKDIR ${WORKDIR}

# Install dependencies with uv into /opt/venv. The venv lives outside of
# ${WORKDIR} because docker-compose bind-mounts the repo over ${WORKDIR}.
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ${WORKDIR}/
RUN uv sync --locked --no-install-project

# This "enables" the venv by adding it to ${PATH}
ENV PATH="/opt/venv/bin:${PATH}"
RUN echo 'alias ll="ls -lart --color=auto"' >> ~/.bashrc

# Entry point of dev null used for debugging
#ENTRYPOINT ["tail", "-f", "/dev/null"]
CMD ["python", "main.py", "--live" ]
