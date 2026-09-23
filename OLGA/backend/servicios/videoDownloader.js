//Importación de módulos
const { exec } = require('child_process');
const path = require('path');

function ejecutarDescarga(link, programa) {
  return new Promise((resolve, reject) => {
    if (!link || !programa) {
      return reject(new Error("DESCARGA_PYTHON: Faltan argumentos link o programa"));
    }
    //Construye ruta y llama al archivo
    const scriptPath = path.join(__dirname, '../servicios/descargador.py');
    const comando = `python "${scriptPath}" "${link}" "${programa}"`;

    console.log("📥 [DESCARGA] Ejecutando Python:", comando);

    exec(comando, { cwd: path.join(__dirname, '../') }, (error, stdout, stderr) => {
      if (error) {
        console.error("❌ [DESCARGA_PYTHON] Error de ejecución:", stderr || error.message);
        return reject(new Error("DESCARGA_PYTHON: " + (stderr || error.message)));
      }

      const nombreArchivo = stdout.trim();

      //Manejo de errores silenciosos
      if (!nombreArchivo) {
        console.error("⚠️ [DESCARGA_PYTHON] El script no devolvió el nombre del archivo");
        return reject(new Error("DESCARGA_PYTHON: stdout vacío"));
      }

      console.log("✅ [DESCARGA_PYTHON] Nombre de archivo recibido:", nombreArchivo);
      resolve(nombreArchivo);
    });
  });
}

module.exports = { ejecutarDescarga };
