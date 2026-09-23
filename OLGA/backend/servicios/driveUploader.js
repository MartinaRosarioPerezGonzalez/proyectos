const fs = require('fs');
const path = require('path');
const { google } = require('googleapis');
require('dotenv').config();

async function subirADrive(filePath, nombreOriginal, carpetaDriveID,auth) {
  return new Promise(async (resolve, reject) => {
    try {
      const driveService = google.drive({ version: 'v3', auth });

      const archivoMetadata = {
        name: nombreOriginal,
        parents: [carpetaDriveID],
      };

      const media = {
        mimeType: 'video/mp4',
        body: fs.createReadStream(filePath),
      };

      const respuesta = await driveService.files.create({
        resource: archivoMetadata,
        media: media,
        fields: 'id',
      });

      console.log("✅ Archivo subido a Drive con ID:", respuesta.data.id);
      resolve(respuesta.data.id);
    } catch (error) {
      console.error("❌ Error al subir a Google Drive:", error);
      reject(error);
    }
  });
}

module.exports = { subirADrive };