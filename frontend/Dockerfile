# Use Node.js image
FROM node:20-alpine

# Set working directory
WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the code
COPY . .

# Build React app
RUN npm run build

# Use nginx to serve the build
FROM nginx:stable-alpine
COPY --from=0 /app/build /usr/share/nginx/html

# Expose port 3000 (or 80)
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]