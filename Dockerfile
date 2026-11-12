# Package the application's committed JavaScript; no Haxe compiler is needed.
FROM node:24.22.1-alpine3.23 AS package
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev --ignore-scripts
COPY build ./build
COPY res ./res
COPY user ./user
COPY default-config.json LICENSE Dockerfile ./
COPY deploy/runtime ./deploy/runtime
COPY test/deployment ./test/deployment
# Test-only Python stays in the build stage. All upload tests run real Node streams.
RUN apk add --no-cache python3 && python3 -m unittest discover -s test/deployment -p 'test_*.py'
FROM node:24.22.1-alpine3.23
WORKDIR /app
COPY --from=package --chown=node:node /app/build ./build
COPY --from=package --chown=node:node /app/res ./res
COPY --from=package --chown=node:node /app/user /opt/synctube-user
COPY --from=package /app/default-config.json /app/LICENSE ./
COPY --from=package /app/node_modules ./node_modules
COPY --from=package /app/deploy/runtime ./deploy/runtime
USER 1000:1000
EXPOSE 4200
ENTRYPOINT ["node", "/app/deploy/runtime/launcher.cjs"]
