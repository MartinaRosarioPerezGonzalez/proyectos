const fs = require('fs');
const path = require('path');
const readline = require('readline');
const { google } = require('googleapis');

// Cargar credenciales
const CREDENTIALS_PATH = path.join(__dirname, 'credentials.json');
const TOKEN_PATH = path.join(__dirname, 'token.json');

fs.readFile(CREDENTIALS_PATH, (err, content) => {
  if (err) return console.error('Error al leer credentials.json:', err);
  authorize(JSON.parse(content));
});

function authorize(credentials) {
  const { client_secret, client_id, redirect_uris } = credentials.installed;
  const oAuth2Client = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0]);

  // ELIMINAR la verificación del token existente para forzar renovación
  console.log('🔄 Generando nuevos tokens...');

  // Generar URL con prompt: 'consent' para forzar nueva autorización
  const authUrl = oAuth2Client.generateAuthUrl({
    access_type: 'offline',
    scope: ['https://www.googleapis.com/auth/drive.file'],
    prompt: 'consent' 
  });

  console.log('\n👉 Abrí este link en el navegador y copiá el código de autorización:\n');
  console.log(authUrl);

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  rl.question('\nPegá el código aquí: ', (code) => {
    rl.close();
    oAuth2Client.getToken(code, (err, token) => {
      if (err) return console.error('❌ Error al obtener el token', err);
      oAuth2Client.setCredentials(token);
      fs.writeFileSync(TOKEN_PATH, JSON.stringify(token, null, 2)); // Formato bonito
      console.log('✅ Token guardado en token.json');
      console.log('🎉 ¡Autorización completada! Ya podés usar tu aplicación.');
    });
  });
}