FROM node:18-alpine

WORKDIR /app

# Copy package manifests first for better layer caching
COPY package.json package-lock.json* ./

# Install dependencies (will be persisted via named volume in compose)
RUN npm install

# Expose Vite dev server port
EXPOSE 3000

# Default command (overridable in docker-compose)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000", "--open", "false"]
