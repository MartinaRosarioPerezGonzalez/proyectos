# OLGA — Compartí tu Momento

Frontend para que fans de **OLGA** suban videos o links de sus momentos favoritos con los programas del canal. El usuario elige un programa, sube su contenido y acepta que puede ser compartido en pantalla.

---

## Flujo de la app

```
Inicio → Elegir tipo (video / link) → Seleccionar programa → Subir contenido → Confirmación
```

Pantallas:
- **`indexSeleccion.html`** — Selección de tipo de contenido
- **`indexVideo.html`** — Formulario para subir un video
- **`indexLink.html`** — Formulario para enviar un link
- **`indexExito.html`** — Confirmación de envío exitoso
- **`indexError.html`** — Pantalla de error

---

## Stack

- HTML / CSS / JavaScript vanilla
- Bootstrap 5

---

## Backend

> ⚠️ El backend no está disponible en este repositorio. Próximamente.

El frontend espera un servidor corriendo en `http://localhost:3000` con los siguientes endpoints:

| Endpoint | Descripción |
|----------|-------------|
| `POST /upload` | Recibe el video y datos del formulario |
| `POST /link` | Recibe el link y datos del formulario |

---

## Cómo correr el frontend

Abrí `index.html` directamente en el navegador o servilo con cualquier servidor estático:

```bash
npx serve .
```

> Sin el backend activo, los formularios redirigen a la pantalla de error.
