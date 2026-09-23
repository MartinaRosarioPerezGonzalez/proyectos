# Dockerfile para Node.js + Python (Code Engine)
FROM node:20-alpine

# Instala Python, pip y dependencias necesarias
RUN apk add --no-cache python3 py3-pip gcc musl-dev libffi-dev

# Instala yt-dlp usando pip3 con --break-system-packages
RUN pip3 install --break-system-packages yt-dlp

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos de dependencias de Node.js
COPY package.json package-lock.json* ./

# Instala dependencias de Node.js
RUN npm install --production

# Copia el resto de la aplicación
COPY . .

# Crea carpeta de uploads si no existe
RUN mkdir -p servicios/uploads

# Expone el puerto para Code Engine
EXPOSE 3000

# Usa variable de entorno PORT por defecto
ENV PORT=3000

# Comando por defecto para iniciar la app
CMD ["node", "index.js"]