# Dashboard de Gastos Personales — Power BI

Reporte interactivo de seguimiento mensual de gastos personales, límites por categoría y desvíos frente al presupuesto. Construido en Power BI con modelo estrella, medidas DAX y limpieza de datos en Power Query.

---

## Vistas del reporte

| Vista | Descripción |
|-------|-------------|
| **Panel de Presupuesto** | Resumen del período: gasto real vs límite, % consumido y categorías excedidas |
| **Desglose por Categoría** | Análisis por categoría y subcategoría |
| **Detalle por Naturaleza** | Vista por naturaleza del gasto (fijo, variable, etc.) |
| **Desglose de Matriz** | Tabla cruzada con múltiples dimensiones |
| **Tablero y Storytelling** | Vista narrativa del período |

Filtros disponibles: Año, Mes, Categoría, Subcategoría, Naturaleza y Método de pago.

---

## Capturas

![Panel de Presupuesto](assets/Resumen%20e%20Indicadores%20Iniciales.png)

---

## Técnicas aplicadas

- **Modelado estrella** — tablas de hechos y dimensiones
- **Power Query** — limpieza y transformación de datos
- **Medidas DAX** — KPIs calculados (% consumido, desvío vs límite, variación mensual)
- **Interacción entre visuales** — filtros cruzados entre gráficos

---

## Cómo usar

1. Abrí `Reporte de Gastos 2026.pbix` con **Power BI Desktop**
2. Reemplazá la fuente de datos con tu propio archivo de gastos
3. Ajustá las categorías y límites según tu presupuesto personal
