# Hands-on: Agente de RRHH con watsonx Orchestrate

Lab práctico para construir un agente conversacional de Recursos Humanos usando **IBM watsonx Orchestrate**. El agente permite a los empleados consultar su perfil, saldo de vacaciones, actualizar su cargo y solicitar tiempo libre — todo via lenguaje natural.

---

## Qué vas a construir

Un agente de RRHH que combina:
- **Base de conocimiento** — responde preguntas sobre beneficios de la empresa (licencias, trabajo flexible, etc.) a partir de un PDF
- **Herramientas OpenAPI** — conecta con un sistema de RRHH para leer y actualizar datos reales del empleado

---

## Archivos incluidos

| Archivo | Descripción |
|---------|-------------|
| [`hands-on-lab-askHR.md`](hands-on-lab-askHR.md) | Tutorial principal paso a paso |
| [`tutorial-free-trial.md`](tutorial-free-trial.md) | Cómo crear una cuenta y acceder a watsonx Orchestrate |
| [`hr.yaml`](hr.yaml) | Especificación OpenAPI de las herramientas de RRHH |
| [`Employee-Benefits.pdf`](Employee-Benefits.pdf) | Documento de beneficios para la base de conocimiento |
| [`users_data.xlsx`](users_data.xlsx) | Lista de empleados de prueba |

---

## Cómo empezar

1. Si no tenés acceso a watsonx Orchestrate, seguí el tutorial de [configuración de cuenta](tutorial-free-trial.md)
2. Seguí el [lab paso a paso](hands-on-lab-askHR.md)
