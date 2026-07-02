# Operator UI — built and served locally. No internet needed at runtime.
FROM node:20-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# Brain URL/token are read at build time as NEXT_PUBLIC_* (override via compose args).
ARG NEXT_PUBLIC_BRAIN_URL=http://localhost:8000
ARG NEXT_PUBLIC_BRAIN_TOKEN=triangle-dev-token
ENV NEXT_PUBLIC_BRAIN_URL=$NEXT_PUBLIC_BRAIN_URL
ENV NEXT_PUBLIC_BRAIN_TOKEN=$NEXT_PUBLIC_BRAIN_TOKEN
RUN npm run build

FROM node:20-slim AS run
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/.next ./.next
COPY --from=build /app/public ./public
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/node_modules ./node_modules
EXPOSE 3000
CMD ["npm", "run", "start"]
