# Build the React frontend into static assets.
FROM node:20-alpine AS frontend-build

WORKDIR /src/web-react
COPY web-react/package.json web-react/package-lock.json ./
RUN npm ci
COPY web-react/ ./
RUN npm run build

# Serve the static app and proxy API requests to the separate FastAPI service.
FROM nginx:1.27-alpine

COPY --from=frontend-build /src/web-react/dist/ /usr/share/nginx/html/
COPY deploy/nginx.conf /etc/nginx/nginx.conf

EXPOSE 5174
CMD ["nginx", "-g", "daemon off;"]
