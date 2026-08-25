FROM python:3.12-bookworm

RUN apt-get update \
  && apt-get install -y --no-install-recommends curl ca-certificates \
  && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
  && apt-get install -y --no-install-recommends nodejs \
  && corepack enable \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY server/requirements.txt /app/server/requirements.txt
RUN pip install --no-cache-dir -r /app/server/requirements.txt

COPY server /app/server
COPY web /app/web
WORKDIR /app/web
RUN pnpm install --frozen-lockfile && pnpm build

COPY scripts/start-prod.sh /app/scripts/start-prod.sh
RUN chmod +x /app/scripts/start-prod.sh

ENV ENGINE_URL=http://127.0.0.1:8764
ENV PORT=43124
EXPOSE 43124
WORKDIR /app
CMD ["/app/scripts/start-prod.sh"]
