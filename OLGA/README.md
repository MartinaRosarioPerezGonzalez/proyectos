# OLGA – Sistema de envío de videos

Plataforma que permite a los oyentes subir videos (archivo o link) para su almacenamiento automático en las carpetas de Google Drive de OLGA.

## Funcionalidades

- Subida de archivos de video (.mp4) desde celular o computadora
- Envío de videos desde link (YouTube, Instagram, TikTok, X)
- Procesamiento y subida a Google Drive mediante la API oficial
- Uso de cookies para autenticación en descargas desde redes sociales

## Estructura del Proyecto

```
OLGA/
├── backend/
│   ├── servicios/
│   │   ├── uploads/          ← archivos temporales (ignorado por git)
│   │   ├── descargador.py    ← descarga videos con yt-dlp
│   │   ├── driveUploader.js  ← sube archivos a Google Drive
│   │   └── videoDownloader.js
│   ├── .env.example          ← plantilla de variables de entorno
│   ├── authorize.js          ← script de autorización OAuth (correr 1 vez)
│   ├── cookies.txt           ← cookies de sesión (no subir a git)
│   ├── credentials.json      ← credenciales OAuth (no subir a git)
│   ├── Dockerfile
│   ├── index.js              ← servidor Express
│   ├── package.json
│   └── requirements.txt
└── frontend/
    ├── css/
    ├── fonts/
    ├── img/
    ├── js/
    │   ├── mainlink.js
    │   └── mainvideo.js
    ├── index.html
    ├── indexError.html
    ├── indexExito.html
    ├── indexLink.html
    └── indexVideo.html
```

## Tecnologías

- **Node.js + Express** — servidor backend
- **Python + yt-dlp** — descarga de videos desde links
- **Google Drive API** — almacenamiento de videos
- **HTML + CSS + JS Vanilla + Bootstrap 5** — frontend

---

## Requisitos Previos

### 1. Node.js (v18+)
```bash
node -v
npm -v
```

### 2. Python (v3.10+)
```bash
python --version
```
> En Windows: marcar **"Add Python to PATH"** durante la instalación.

### 3. Cuenta de Google con Google Drive API habilitada
- Crear proyecto en [Google Cloud Console](https://console.cloud.google.com/)
- Habilitar la **Google Drive API**
- Crear credenciales **OAuth 2.0 → Aplicación de escritorio**
- Descargar el JSON y guardarlo como `backend/credentials.json`
- Agregar tu cuenta como usuario de prueba en [OAuth consent screen → Audience](https://console.cloud.google.com/auth/audience/)

---

## Instalación

```bash
cd OLGA/backend
npm install
pip install yt-dlp
```

---

## Configuración

### 1. Crear el archivo `.env`
Copiá `.env.example` como `.env` y completá los IDs de carpetas de Drive:
```bash
cp .env.example .env
```

### 2. Completar `credentials.json`
Reemplazá `backend/credentials.json` con el archivo descargado de Google Cloud Console.

### 3. Obtener `cookies.txt`
Necesario para descargar videos de Instagram, TikTok y X:
1. Instalar extensión [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) en Chrome
2. Iniciar sesión en Instagram, TikTok y X
3. Exportar cookies y guardarlas como `backend/cookies.txt`

### 4. Autorizar Google Drive (solo la primera vez)
```bash
node authorize.js
```
Seguí el link que aparece en consola, autorizá la app y pegá el código. Se generará `token.json` automáticamente.

---

## Ejecución

```bash
cd OLGA/backend
node index.js
```

El servidor arranca en `http://localhost:3000` y sirve el frontend automáticamente.

---

## Despliegue con Docker

```bash
cd OLGA/backend
docker build -t olga-backend .
docker run -p 3000:3000 --env-file .env olga-backend
```
