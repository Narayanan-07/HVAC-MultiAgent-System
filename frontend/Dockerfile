# ── HVAC Multi-Agent System · Frontend image (Vite dev server) ───────────
FROM node:20-slim

WORKDIR /app

# Install deps first for layer caching
COPY package.json ./
RUN npm install

# App source
COPY . .

EXPOSE 3000

# --host exposes the dev server outside the container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
