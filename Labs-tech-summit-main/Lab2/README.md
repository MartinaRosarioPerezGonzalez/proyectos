# Lab 2 — IA Agéntica con Confluent y watsonx Orchestrate

Este laboratorio muestra cómo construir un sistema multi-agente para **Las Marías** (yerba mate Rosamonte) usando **Confluent Cloud** (Kafka + ksqlDB), **IBM watsonx Orchestrate** y **Exa MCP** para web scraping.

## Arquitectura del Sistema

El lab implementa dos experiencias diferenciadas:

### Experiencia Interna (Empleados)
- **Las Marías Commercial Orchestrator**: Asistente comercial que coordina:
  - **Inventory Availability Agent**: Consulta inventario en tiempo real desde Confluent
  - **Competitive Intelligence Agent**: Análisis competitivo mediante web scraping con Exa MCP

### Experiencia Externa (Clientes)
- **Product Visual Advisor Agent**: Asesor conversacional independiente que:
  - Recopila preferencias del cliente mediante preguntas
  - Recomienda productos con imágenes desde catálogo estructurado
  - Maneja valores por defecto cuando el usuario no responde

## Estructura del repositorio

```
Lab2/
├── tutorial.md                                    # Guía paso a paso del laboratorio
└── confluent_agents/
    ├── .env.example                               # Plantilla de variables de entorno
    ├── get_sku_availability.py                    # MCP tool: consulta inventario vía ksqlDB
    ├── visual_product_tool.py                     # Tool: recomendaciones visuales de yerba mate
    ├── catalog_example.json                       # Catálogo de productos Las Marías
    ├── Inventory_Availability_Agent.yaml          # Agente de disponibilidad (uso interno)
    ├── Competitive_Intelligence_Agent.yaml        # Agente de análisis competitivo (uso interno)
    ├── Product_Visual_Advisor_Agent.yaml          # Agente visual conversacional (uso externo)
    ├── Las_Marias_Commercial_Orchestrator.yaml    # Orquestador para empleados (uso interno)
    └── requirements.txt                           # Dependencias Python
```

## Configuración Inicial

1. Posicionate en la carpeta del lab:

```bash
cd Lab2/confluent_agents
```

2. Copiá el archivo de variables de entorno y completá con tus credenciales:

```bash
cp .env.example .env
```

Editá `.env` con el endpoint y credenciales de tu entorno Confluent. Ver `.env.example` para referencia de cada variable.

3. Instalá las dependencias Python:

```bash
pip install -r requirements.txt
```

## Siguientes Pasos

Seguí el tutorial paso a paso en **[tutorial.md](tutorial.md)**.