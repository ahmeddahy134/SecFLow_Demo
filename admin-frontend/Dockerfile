# Multi-stage build for production optimization
FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=builder /app/build /usr/share/nginx/html
COPY start-nginx.sh /start-nginx.sh
RUN chmod +x /start-nginx.sh && \
    mkdir -p /var/cache/nginx /var/log/nginx /var/run /etc/nginx/conf.d && \
    chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/log/nginx /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown nginx:nginx /var/run/nginx.pid

# Run as unprivileged nginx user
USER nginx

EXPOSE 5030

CMD ["/start-nginx.sh"]
