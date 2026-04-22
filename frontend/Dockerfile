# Build stage
FROM node:24-alpine as build
RUN npm install -g pnpm
WORKDIR /app
COPY package.json ./
RUN pnpm install --no-frozen-lockfile
COPY . .
RUN pnpm run build

# Production stage
FROM nginx:stable-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
