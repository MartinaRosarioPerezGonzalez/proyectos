document.addEventListener("DOMContentLoaded", () => {
  document.getElementById('btn-subir-video').addEventListener('click', subirVideo);
});

async function subirVideo(event) {
  event.preventDefault();

  const archivoInput = document.getElementById("inputArchivo");
  const programa = document.getElementById("programaArchivo").value;
  const acepta = document.getElementById("aceptoArchivo").checked;

  if (!archivoInput.files.length) {
    alert("Por favor, seleccioná un archivo.");
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
  formData.append("video", archivoInput.files[0]);
  formData.append("programa", programa);
  formData.append("acepto", acepta);

  try {
    const response = await fetch("http://localhost:3000/upload", {
      method: "POST",
      body: formData
    });

    if (!response.ok) {
      throw new Error("Error al subir el video");
    }

    const resultado = await response.json();
    console.log("✅ Video subido:", resultado);

    // Redirige al HTML de éxito
    window.location.href = "./indexExito.html";
  } catch (error) {
    console.error("❌ Error:", error);

    // Redirige al HTML de error (le faltaba ".html")
    window.location.href = "./indexError.html";
  }
  

}


