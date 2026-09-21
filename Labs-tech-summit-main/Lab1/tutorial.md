# Step 1. Crear un tópico en Confluent Kafka

## Crear un tópico en Confluent manualmente desde la UI

Iniciarás sesión en Confluent y crearás un tópico para las transacciones de inventario.

1. Iniciar sesión en Confluent.

2. Seleccionar un cluster de Kafka ya creado.

3. En el menú de navegación del cluster, seleccionar `Topics`.

4. Hacer click en `Add topic`.

5. Nombrar el tópico como: `inventory.transactions`.

6. Establecer `Partitions` en 1. Usar una sola partición mantiene el orden de los eventos determinístico y simplifica la consumición de eventos para este tutorial.

7. Dejar todas las otras configuraciones en sus valores por defecto.

8. Hacer click en `Create with defaults`.

9. Seleccionar la pestaña `Configuration`.

10. Hacer click en `Edit Settings` y cambiar el `Retention Time` a `infinite` y luego hacer click en `Save changes`.


# Step 2. Crear un tópico derivado en Confluent Kafka

En este paso vamos a crear un tópico derivado llamado `inventory.availability` que automáticamente calcula cuántas unidades de cada producto están disponibles en cada sucursal procesando las transacciones del primer tópico.

Vamos a usar un cluster de ksqlDB que procesará tus datos en streaming. Un cluster de ksqlDB es un motor de procesamiento que se ejecuta continuamente en segundo plano para leer datos de tópicos de Kafka, realizar cálculos y escribir resultados en otros tópicos usando comandos similares a SQL.

1. Hacer click en `ksqlDB` en el menú izquierdo.
2. Hacer click en el cluster `ksqlDB` que está corriendo.
3. Hacer click en la pestaña `Streams` y `Create in Editor`
4. Copiar y pegar el siguiente código en el editor:

```bash
CREATE STREAM inventory_transactions (
     sku VARCHAR,
     branch VARCHAR,
     quantity INT
 ) WITH (
     KAFKA_TOPIC='inventory.transactions',
     KEY_FORMAT='KAFKA',
     VALUE_FORMAT='JSON'
 );
```
5. Hacer click en `Run Query`.

6. Ahora vamos a crear una tabla llamada `inventory_availability` que calcule automáticamente la cantidad disponible agrupando las transacciones por SKU y sucursal usando la siguiente declaración SQL, y luego hacer clic en `Run Query`. Esto realiza lo siguiente:
- Agrupa todas las transacciones por SKU y sucursal.
- Suma las cantidades (positivas para los inventarios adicionales, negativas para las ventas).
- Escribe los resultados en el tópico `inventory.availability`.
- Actualiza automáticamente cuando llegan nuevas transacciones.

```bash
CREATE TABLE inventory_availability WITH (
  KAFKA_TOPIC='inventory.availability',
  KEY_FORMAT='JSON',
  VALUE_FORMAT='JSON',
  PARTITIONS=1
) AS
SELECT 
  sku,
  branch,
  SUM(quantity) AS available_quantity
FROM inventory_transactions
GROUP BY sku, branch
EMIT CHANGES;
```

# Step 3. Publicar mensajes de ejemplo al tópico

En este punto ya tenemos creados dos tópicos:
- `inventory.transactions`: Incluye todas las transacciones (positivo significa stock adicional, y negativo significa transacción de venta).

- `inventory.availability`: Este es un tópico derivado que creamos en el paso anterior para calcular la disponibilidad automáticamente.

El tópico `inventory.transactions` existe pero no tiene mensajes. Tenemos que publicar mensajes en el tópico.



## Publicar mensajes de manera manual
Para crear cada mensaje manualmente sería de esta manera:

1. Acceder al tópico `inventory.transactions` desde el menú de la izquierda.
2. Hacer click en `Messages`.
3. Hacer click en `Produce new message`.

```json
 {"sku": "LAPTOP-DELL-XPS-15", "branch": "Dot Shopping", "quantity": 50, "transaction_type": "ADDITION", "timestamp": "2025-12-29T08:00:00Z", "source": "inventory_manager", "reference": "PO-2025-001"},
```

Pero como queremos crear 20, vamos a utilizar un script de Python.

1. Abrir una terminal desde IBM Bob.
2. Si estás usando una computadora Windows, asegurarse que la terminal sea `Git Bash` en lugar de `Powershell`.
3. Moverse a la carpeta `Lab1/inventory-pipeline`:

```bash
cd Lab1/inventory-pipeline
```

4. Para computadoras Windows, abrir una terminal de `Git Bash` y ejecutar el comando. Para computadoras MAC o Linux ejecutar el siguiente comando directamente:

```bash
./setup.sh -s 3
```

5. Verificar la creación desde la UI de Confluent. Acceder al tópico `inventory.transactions` y hacer click en `Messages`.