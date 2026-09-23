//Módulos del sistema
const fs = require('fs');
const path = require('path');
//Librerías Back
const express = require('express');
const multer = require('multer');
const cors = require('cors');
//Archivos ha utilizar
const { google } = require('googleapis')
const { exec } = require('child_process');
const { subirADrive } = require('./servicios/driveUploader');
const { ejecutarDescarga } = require('./servicios/videoDownloader');
require('dotenv').config();


const app = express();
app.use(cors());
const PORT = process.env.PORT || 3000;
const upload = multer({ dest: path.join(__dirname, 'servicios', 'uploads') });

//Mapea carpetas destino por programa
const CARPETAS_POR_PROGRAMA = {
  tdt: process.env.TDT,
  golgana: process.env.GOLGANA,
  primo: process.env.PRIMO,
  Paraiso: process.env.PARAISO,
  Increible: process.env.INCREIBLE,
  Laburo: process.env.LABURO,
  Volaba: process.env.VOLABA,
  Cualquiera: process.env.CUALQUIERA
};

//Set de la carpeta por default
const CARPETA_DRIVE_ID = process.env.ID_CARPETA_DRIVE;

const CREDENTIALS_PATH = path.join(__dirname,'credentials.json')
const TOKEN_PATH = path.join(__dirname,'token.json');

app.use(express.static(path.join(__dirname, '..', 'frontend')))

function esLinkValido(link) {
  try {
    if (!/^https?:\/\//i.test(link)) link = "https://" + link;

    const url = new URL(link);
    const dominio = url.hostname.toLowerCase();

    // YouTube
    if ((dominio === "youtube.com" || dominio.endsWith(".youtube.com")) && url.pathname.startsWith("/watch")) return true;
    if (dominio === "youtu.be") return true;

    // Instagram
    if ((dominio === "instagram.com" || dominio.endsWith(".instagram.com")) &&
        (url.pathname.startsWith("/p/") || url.pathname.startsWith("/reel/"))) return true;

    // TikTok
    if ((dominio === "tiktok.com" || dominio.endsWith(".tiktok.com")) &&
        url.pathname.includes("/video/")) return true;

    // X - aceptar cualquier subdominio
    if (dominio.endsWith("x.com")) return true;

    return false;
  } catch (err) {
    return false;
  }
}


function getOAuthClient() {
  const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH));
  const token = JSON.parse(fs.readFileSync(TOKEN_PATH));
  const { client_secret, client_id, redirect_uris } = credentials.installed;

  const oAuth2Client = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0]);
  oAuth2Client.setCredentials(token);
  return oAuth2Client;
}

// Endpoint para subir archivo
app.post('/upload', upload.single('video'), async (req, res) => {
  const archivo = req.file;
  const link = req.body.linkVideo?.trim();
  const usuario = (req.body.usuario || req.body.nombre || "").trim();
  
  const auth = getOAuthClient()
  
  //Reconocimiento de carpetas por porgrama
  const programa = req.body.programa?.trim();
  const carpetaDestino = CARPETAS_POR_PROGRAMA[programa] || CARPETA_DRIVE_ID;
  // Validación de exclusividad
  if (archivo && link) {
    return res.status(400).send('No podés subir un archivo y un link al mismo tiempo.');
  }

  if (link && !esLinkValido(link)){
    return res.status(400).json({ error: "Faltan campos obligatorios" });
  }

  // Subida directa del archivo
  if (archivo) {
    let url;

    try {
      // Intentar subir a drive
      try {
        console.log("📤 [SUBIDA] Iniciando subida a Drive...");
        const rutaLocal = archivo.path;
        const nombreArchivo = archivo.originalname;

        // Construir nombre final para Drive: "<base> - <usuario><ext>"
        const ext = path.extname(nombreArchivo);
        const base = path.basename(nombreArchivo, ext);
        const nombreParaDrive = usuario ? `${base} - ${usuario}${ext}` : nombreArchivo;

        url = await subirADrive(rutaLocal, nombreParaDrive, carpetaDestino, auth);
        console.log("✅ [SUBIDA] Archivo subido correctamente a Drive. URL:", url);
      } catch (err) {
        throw new Error("SUBIR_Drive: " + err.message);
      }

      // Intentar borrar archivo local
      try {
        fs.unlinkSync(archivo.path);
        console.log("✅ [BORRADO] Archivo eliminado del servidor local");
      } catch (err) {
        console.warn("⚠️ [BORRADO] Falló al eliminar archivo local:", err.message);
        // No detenemos el flujo si solo falló el borrado local
      }

      // Éxito total
      return res.status(200).json({ success: true });

    } catch (err) {
      console.error("❌ [ERROR GENERAL] Error en flujo de subida:", err.message);
      return res.status(500).json({ success: false, error: err.message });
    }
  } 

  // Si se recibió un link
  if (link) {

    let nombreArchivo;
    let rutaLocal;
    let url;

    try {
      //Descarga de video
      try {
        console.log("📥 [DESCARGA] Iniciando descarga desde link:", link);
        nombreArchivo = await ejecutarDescarga(link, programa);
        rutaLocal = path.join(__dirname, 'servicios','uploads', nombreArchivo);

        console.log("✅ [DESCARGA] Video descargado:", nombreArchivo);
      } 
      catch (err) {
        throw new Error("DESCARGA_PYTHON: " + err.message);
      }
      //Subir a Drive
      const ext = path.extname(nombreArchivo);
      const base = path.basename(nombreArchivo, ext);
      const nombreParaDrive = usuario ? `${base} - ${usuario}${ext}` : nombreArchivo;
      
      try {
        console.log("📤 [SUBIDA] Iniciando subida a Drive...");
        url = await subirADrive(rutaLocal,nombreParaDrive, carpetaDestino,auth);
        console.log("✅ [SUBIDA] Archivo subido correctamente a Drive. URL:", url);
      }
      catch (err) {
        throw new Error("SUBIR_Drive: " + err.message);
      }
      //Borrar Archivo local
      try {
        fs.unlinkSync(rutaLocal);
        console.log("✅ [BORRADO] Archivo eliminado del servidor local");
      } 
      catch (err) {
        console.warn("⚠️ [BORRADO] Falló al eliminar archivo local:", err.message);
      }

      return res.status(200).json({ success: true });
    } 
    catch (err) {
      console.error("❌ [ERROR LINK] Fallo en el flujo de descarga/subida:", err.message);
      return res.status(500).json({ success: false, error: err.message });
    }
  }
})

app.listen(PORT, () => {
  console.log(`🚀 Servidor corriendo en http://localhost:${PORT}`);
});













