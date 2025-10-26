FROM node:18 as base
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

FROM base as dev

FROM base as build

COPY frontend/ ./
RUN npm run build

FROM nginx:1.25-alpine

COPY --from=build /app/build /usr/share/nginx/html

RUN rm /etc/nginx/conf.d/default.conf

COPY docker/react/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]