document.addEventListener("DOMContentLoaded", () => {
  document.getElementById('btn-enviar-link').addEventListener('click', subirLink);
});

async function subirLink(e) {
  e.preventDefault();

  const link = document.getElementById("linkVideo").value;
  const programa = document.getElementById("programaLink").value;
  const acepta = document.getElementById("aceptoLink").checked;

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

  try {
    const response = await fetch("http://localhost:3000/upload", {
      method: "POST",
      body: formData
    });

    if (!response.ok) {
      throw new Error("Error al subir el link");
    }

    const resultado = await response.json();
    console.log("✅ Link enviado:", resultado);

    document.getElementById("formLink").reset();
    window.location.href = './indexExito.html';

  } catch (error) {
    console.error("❌ Error:", error);
    window.location.href = './indexError.html';
  }
};

