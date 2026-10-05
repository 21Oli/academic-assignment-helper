FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies (generates lockfile inside the container)
RUN npm install --no-audit --no-fund

# Copy the rest of the source
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

# Build the Next.js app
RUN npm run build

EXPOSE 3000
ENV PORT=3000

CMD ["npm", "start"]
