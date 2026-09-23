document.addEventListener("DOMContentLoaded", () => {
  document.getElementById('btn-subir-video').addEventListener('click', subirVideo);
});

async function subirVideo(event) {
  event.preventDefault();

  const archivoInput = document.getElementById("inputArchivo");
  const programa = document.getElementById("programaArchivo").value;
  const acepta = document.getElementById("aceptoArchivo").checked;
  const spinner = document.getElementById("spinner-video");
  const form = document.getElementById("formVideo");
  const nombre = (document.getElementById("inputNombre")?.value || "").trim();


  if (!archivoInput.files.length) {
    alert("Por favor, seleccioná un archivo.");
    return;
  }

  const archivo = archivoInput.files[0];

  // ✅ Validación de tipo de archivo: solo videos
  if (!archivo.type.startsWith("video/")) {
    alert("Solo se permiten archivos de video.");
    return;
  }

  // ✅ Validación de tamaño (100 MB máximo)
  const maxSizeMB = 100;
  if (archivo.size > maxSizeMB * 1024 * 1024) {
    alert(`El video no puede superar los ${maxSizeMB} MB.`);
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
  formData.append("video", archivo);
  formData.append("programa", programa);
  formData.append("acepto", acepta);
  formData.append("usuario", nombre);
  spinner.classList.remove("d-none");
  form.classList.add("d-none");

  try {
    const response = await fetch("/upload", {
      method: "POST",
      body: formData
    });

    if (!response.ok) {
      throw new Error("Error al subir el video");
    }

    const resultado = await response.json();
    console.log("✅ Video subido:", resultado);

    window.location.href = "./indexexito.html";
  } catch (error) {
    console.error("❌ Error:", error);
    window.location.href = "./indexerror.html";
  } finally {
    spinner.classList.add("d-none");
  }
}



