import os
import sys
import subprocess
from pathlib import Path
import io
import json

# Para asegurar que los prints soporten UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Validación de argumentos
if len(sys.argv) < 3:
    print("ERROR: Faltan argumentos (link y programa)", file=sys.stderr)
    sys.exit(1)

link = sys.argv[1].strip()
programa = sys.argv[2].strip().lower()

# Ruta de salida
base_dir = os.path.dirname(__file__)
output_dir = os.path.join(base_dir, "uploads")
os.makedirs(output_dir, exist_ok=True)

# Archivo de cookies
cookies_path = os.path.join(base_dir, "..", "cookies.txt")
if not os.path.exists(cookies_path):
    print("ERROR: El archivo cookies.txt no existe", file=sys.stderr)
    sys.exit(1)

# Obtener info del video sin descargar
info_cmd = [
    "python", "-m", "yt_dlp",
    "--cookies", cookies_path,
    "--dump-json",
    "--no-playlist",
    link
]

try:
    result_info = subprocess.run(info_cmd, check=True, capture_output=True, text=True)
    info_json = json.loads(result_info.stdout)
    size_bytes = info_json.get("filesize") or info_json.get("filesize_approx") or 0

    if size_bytes > 100 * 1024 * 1024:
        print("ERROR: El video supera los 100MB", file=sys.stderr)
        sys.exit(1)

    # Formato de salida del archivo
    output_template = os.path.join(output_dir, "%(title).80s.%(ext)s")

    # Comando para descargar
    download_cmd = [
        "python", "-m", "yt_dlp",
        "--cookies", cookies_path,
        "-o", output_template,
        "--no-playlist",
        link
    ]

    resultado = subprocess.run(download_cmd, check=True, capture_output=True, text=True)

    # Buscar el archivo descargado más reciente
    archivos = list(Path(output_dir).glob("*"))
    if not archivos:
        print("ERROR: No se encontró ningún archivo descargado", file=sys.stderr)
        sys.exit(1)

    archivo_mas_reciente = max(archivos, key=lambda f: f.stat().st_mtime)
    print(archivo_mas_reciente.name)

except subprocess.CalledProcessError as e:
    print(f"ERROR: yt-dlp falló: {e.stderr}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {str(e)}", file=sys.stderr)
    sys.exit(1)
