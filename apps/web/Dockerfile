FROM node:20-alpine

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@9.15.1 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
COPY apps/web/package.json ./apps/web/
COPY packages/ ./packages/

RUN pnpm install --frozen-lockfile

COPY apps/web/ ./apps/web/

RUN rm -rf ./apps/web/node_modules

WORKDIR /app/apps/web

RUN pnpm install

ENV PATH="/app/apps/web/node_modules/.bin:/app/node_modules/.bin:$PATH"

EXPOSE 23000

CMD ./node_modules/.bin/next dev -p 23000
