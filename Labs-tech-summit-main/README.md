# Tech Summit — Labs de IA Agéntica y Streaming

Workshop de dos laboratorios que combina **Confluent Cloud** (Kafka + ksqlDB) con **IBM watsonx Orchestrate** para construir un pipeline de inventario en tiempo real y un sistema multi-agente para retail.

El caso de uso está basado en **Las Marías** (Rosamonte) como empresa ejemplo.

---

## Laboratorios

### Lab 1 — Pipeline de Inventario con Confluent Kafka
Creación de un pipeline de eventos de inventario usando Confluent Cloud: tópicos Kafka, tópico derivado con ksqlDB y producción de mensajes desde Python.

→ [Ver Lab 1](Lab1/tutorial.md)

### Lab 2 — Sistema Multi-Agente con Confluent y watsonx Orchestrate
Construcción de un sistema de cuatro agentes especializados: disponibilidad de inventario en tiempo real, inteligencia competitiva vía web scraping, asesor visual de productos y un orquestador comercial.

→ [Ver Lab 2](Lab2/tutorial.md)

---

## Resultado esperado

Al finalizar ambos labs tendrás un sistema donde los agentes de IA consultan datos de inventario en tiempo real desde Kafka para responder consultas de empleados y clientes.

---

## Prerrequisitos

- Cuenta en [Confluent Cloud](https://confluent.io)
- Acceso a IBM watsonx Orchestrate
- Python 3.9+
