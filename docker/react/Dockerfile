# docker/react/Dockerfile

# --- Етап 1: 'base' (Встановлення залежностей) ---
# Цей етап буде спільним для dev і prod
FROM node:18 as base
WORKDIR /app
# Копіюємо package.json та package-lock.json
COPY frontend/package.json frontend/package-lock.json ./
# Встановлюємо залежності (використовуємо --no-cache, щоб гарантовано підхопити chart.js)
RUN npm install

# --- Етап 2: 'dev' (Ціль для docker-compose.yml) ---
# Цей етап існує ТІЛЬКИ для того, щоб dev-compose міг на нього 
# посилатися (target: dev). Він просто копіює 'base'.
FROM base as dev


# --- Етап 3: 'build' (Ціль для docker-compose.prod.yml) ---
# Цей етап збирає React-додаток для production
FROM base as build
# Копіюємо решту коду (це не копіює node_modules завдяки .dockerignore)
COPY frontend/ ./
# Збираємо production-білд
RUN npm run build

# --- Етап 4: 'Serve' (Фінальний образ для prod) ---
# Використовуємо легкий образ Nginx
FROM nginx:1.25-alpine

# Копіюємо зібрані файли з етапу "build"
COPY --from=build /app/build /usr/share/nginx/html

# Видаляємо стандартний конфіг Nginx
RUN rm /etc/nginx/conf.d/default.conf

# Копіюємо наш власний конфіг для React
COPY docker/react/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]