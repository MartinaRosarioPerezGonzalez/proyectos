document.addEventListener("DOMContentLoaded", () => {
  document.getElementById('btn-enviar-link').addEventListener('click', subirLink);
});


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

async function subirLink(e) {
  e.preventDefault();

  const link = document.getElementById("linkVideo").value;
  const programa = document.getElementById("programaLink").value;
  const acepta = document.getElementById("aceptoLink").checked;
  const spinner = document.getElementById("spinner-video");
  const form = document.getElementById("formLink");
  const usuario = (document.getElementById("inputUsuario")?.value || "").trim();


  if (!esLinkValido(link)) {
    alert("El link debe ser de Youtube, Instagram, X o TikTok.");
    return;
  }
  
  if (!link) {
    alert("Por favor, ingresá un link.");
    return;
  }

  if (!programa) {
    alert("Seleccioná un programa.");
    return;
  }

  if (!acepta) {
    alert("Debés aceptar que el video puede compartirse.");
    return;
  }

  const formData = new FormData();
  formData.append("linkVideo", link);
  formData.append("programa", programa);
  formData.append("acepto", acepta);
  formData.append("usuario", usuario);
  spinner.classList.remove("d-none");
  form.classList.add("d-none");

  try {
    const response = await fetch("/upload", {
      method: "POST",
      body: formData
    });

    if (!response.ok) {
      throw new Error("Error al subir el link");
    }

    const resultado = await response.json();
    console.log("✅ Link enviado:", resultado);

    document.getElementById("formLink").reset();
    window.location.href = './indexexito.html';

  } catch (error) {
    console.error("❌ Error:", error);
    window.location.href = './indexerror.html';
  } finally {
    // Ocultar spinner (por si no redirecciona)
    spinner.classList.add("d-none");    
  
  }
};

