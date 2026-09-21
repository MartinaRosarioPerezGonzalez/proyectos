# Cómo ejecutar el pipeline de inventario

Este proyecto monta un pipeline de Kafka en 3 pasos sobre una instalación de **Conflu ent
Platform en Minikube** dentro de tu VM de TechZone:

1. Crea el topic origen inventory.transactions
2. Crea un stream + tabla CTAS en ksqlDB que deriva inventory.availability
    (SUM(quantity) agrupado por sku, branch)
3. Publica 20 transacciones de inventario de ejemplo

## Requisitos

```
Una shell unix con ssh y scp (macOS, Linux o WSL en Windows)
Una VM de TechZone con CP sobre Minikube ya provisionada
El archivo .pem con la clave SSH de tu VM
No necesitas Python ni kubectl localmente — todo corre dentro de la VM
```
## Pasos para arrancar

```bash
# 1. Clona el repositorio y entra en la carpeta raíz
cd Labs-tech-summit

# 2. Copia tu .pem dentro de Lab1/inventory-pipeline/
cp /ruta/a/tu-clave.pem Lab1/inventory-pipeline/

# 3. Crea tu .env en la raíz del proyecto a partir de la plantilla
cp .env.example .env

# 4. Edita .env y configura las siguientes variables:
nano .env  # o el editor que prefieras
```

**Variables que DEBES editar en `.env`:**
- `SSH_HOST=root@YOUR_VM_IP` → Tu IP de VM (ej: `root@163.66.90.186`)
- `SSH_KEY=Lab1/inventory-pipeline/your-key.pem` → Nombre de tu archivo .pem
- `KSQLDB_PASSWORD=YOUR_KSQLDB_PASSWORD` → Obtener del secret `ksqldb-users`
- `KAFKA_SASL_PASSWORD=YOUR_KAFKA_PASSWORD` → Obtener del secret `kafka-external-plain-users`
- `KSQLDB_ENDPOINT_EXTERNAL=https://YOUR_VM_IP/ksqldb/` → Tu IP de VM para Lab2

**Cómo obtener las credenciales:**
```bash
# Credenciales de ksqlDB
ssh -i Lab1/inventory-pipeline/tu-clave.pem root@TU_VM_IP \
  "kubectl get secret ksqldb-users -n confluent -o jsonpath='{.data.basic\.txt}' | base64 -d"

# Credenciales de Kafka
ssh -i Lab1/inventory-pipeline/tu-clave.pem root@TU_VM_IP \
  "kubectl get secret kafka-external-plain-users -n confluent -o jsonpath='{.data.plain-users\.json}' | base64 -d"
```

```bash
# 5. Ejecuta el pipeline completo
cd Lab1/inventory-pipeline
./setup.sh
```
Deberías ver tres bloques ==> Step:, cada uno terminando en OK:.

## Ejecutar pasos individuales

```bash
./setup.sh -s 1  # solo crea el topic origen
./setup.sh -s 2  # solo crea el stream + tabla derivada en ksqlDB
./setup.sh -s 3  # solo publica los 20 mensajes de ejemplo
```

## Opciones de limpieza

```bash
./setup.sh -C     # Solo limpia (elimina tópicos y objetos ksqlDB) - NO ejecuta setup
./setup.sh -c     # Limpia Y LUEGO ejecuta todos los pasos
./setup.sh -c -s 1  # Limpia Y LUEGO ejecuta solo el paso 1
```

**Diferencia entre `-c` y `-C`:**
- `-c` (minúscula): Limpia → Continúa con setup
- `-C` (MAYÚSCULA): Limpia → Sale (no hace setup)
## Pasar host / clave SSH sin editar el .env

```bash
# Con flags (máxima prioridad)
./setup.sh -h root@1.2.3.4 -i Lab1/inventory-pipeline/mi-clave.pem

# Con variables de entorno
SSH_HOST=root@1.2.3.4 SSH_KEY=Lab1/inventory-pipeline/mi-clave.pem ./setup.sh
```
Prioridad: **flag > variable de entorno > valor del .env**.

**Nota:** El script busca primero el `.env` en la raíz del proyecto (`../../.env`), y si no existe, usa el `.env` local de `Lab1/inventory-pipeline/.env`.

## Verificar el resultado

Una vez ejecutados los tres pasos, consulta la tabla derivada para ver una fila por (sku, branch) con la cantidad acumulada. LAPTOP-DELL en Unicenter queda intencionadamente agotado (neto 0) para que lo puedas identificar:

```bash
ssh -i Lab1/inventory-pipeline/tu-clave.pem root@IP_DE_TU_VM \
  'kubectl -n confluent exec ksqldb-0 -c ksqldb -- \
   curl -sS -X POST http://localhost:8088/query \
   -H "Accept: application/vnd.ksql.v1+json" \
   -H "Authorization: Basic $(echo -n admin:TU_PASSWORD | base64)" \
   -d "{\"ksql\":\"SELECT sku, branch, available_quantity FROM inventory_availability EMIT CHANGES LIMIT 12;\"}"'
```

**Nota:** Reemplaza `TU_PASSWORD` con tu password de ksqlDB, o usa las credenciales directamente en el header de autorización.
## Problemas comunes

**Load key ...: invalid format** → a tu .pem le falta el salto de línea final (típico cuando se descarga por navegador). setup.sh lo corrige automáticamente; si lo ves antes de ejecutarlo:

```bash
printf '\n' >> Lab1/inventory-pipeline/tu-clave.pem
chmod 600 Lab1/inventory-pipeline/tu-clave.pem
```

**Permission denied (publickey...)** → revisa que SSH_HOST coincida exactamente con el usuario@ip de tu VM y que SSH_KEY apunte al .pem correcto. Confirma también `chmod 600` en tu .pem (SSH rechaza claves legibles por todos).

**Authentication failed / Unauthorized (401)** → Las credenciales de Kafka o ksqlDB son incorrectas. Verifica que hayas obtenido las credenciales correctas de los secrets:
```bash
# Para ksqlDB
kubectl get secret ksqldb-users -n confluent -o jsonpath='{.data.basic\.txt}' | base64 -d

# Para Kafka
kubectl get secret kafka-external-plain-users -n confluent -o jsonpath='{.data.plain-users\.json}' | base64 -d
```

**SSL handshake failed / certificate verify failed** → Los scripts ya están configurados para deshabilitar la verificación de certificados SSL (necesario para certificados autofirmados en desarrollo). Si aún ves este error, verifica que las variables `KAFKA_SECURITY_PROTOCOL=SASL_SSL` estén correctamente configuradas.

**Un paso falla o se queda colgado** → vuelve a lanzar solo ese paso con `-s N` y lee los logs del pod que se muestran en pantalla. El Job y su ConfigMap se recrean en cada ejecución, así que reintentarlo es seguro.

**El cleanup falla** → Asegúrate de que el script `delete_topics.py` esté incluido en los archivos que se suben. El cleanup requiere las mismas credenciales de autenticación que el setup.

