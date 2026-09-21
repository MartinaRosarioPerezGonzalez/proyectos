# Evolución del Ecosistema Python (2016–2025)

Análisis topológico comparativo de la red de dependencias de PyPI en dos snapshots temporales: 2016 y 2025. El estudio modela el ecosistema como grafos dirigidos para identificar cómo cambió la arquitectura de la red a lo largo de nueve años.

---

## Autores

**Facultad de Ciencias Exactas y Naturales — Universidad de Buenos Aires**

Carlos Sarraute · Martina Rosario Pérez · Juan Ignacio Catania · Mateo Guerrero Schmidt · Sofía Gutierrez

---

## Hallazgos principales

| Métrica | 2016 | 2025 |
|---------|------|------|
| Nodos | 25,819 | 405,872 |
| Aristas | 72,189 | 2,076,516 |
| Grado promedio | 5.59 | 10.23 |
| Componente gigante | 24,823 nodos | 399,758 nodos |
| Modularidad (Louvain) | 0.615 | 0.489 |

**1. Pivote hacia Data Science e IA**
En 2016 los paquetes más centrales eran herramientas web (`Django`, `Six`, `Sphinx`). En 2025 el ecosistema está dominado por librerías de datos y ML (`NumPy`, `Pandas`, `SciPy`, `Torch`).

**2. Profesionalización del desarrollo**
`Pytest` emerge como nodo de alta centralidad en 2025, reflejando la adopción masiva de testing automatizado como práctica estándar.

**3. Densificación y difuminación de comunidades**
El grado promedio se duplicó (5.59 → 10.23) y la modularidad cayó (0.615 → 0.489), indicando que las librerías "ubicuas" conectan nichos antes aislados.

---

## Stack

- **Análisis de grafos**: NetworkX
- **Métricas de centralidad**: Degree, Closeness, PageRank, Betweenness (k=500)
- **Detección de comunidades**: Algoritmo de Louvain (`python-louvain`)
- **Visualización**: Matplotlib, WordCloud, exportación a Gephi (`.gexf`)
- **Datos**: Pandas, NumPy, Parquet

---

## Uso

Instalar dependencias:

```bash
pip install pandas numpy networkx matplotlib wordcloud python-louvain
```

Configurar los paths en `main.py` y ejecutar:

```python
analyze_datasets(
    Y2016="data/clean_data_2016.csv",
    Y2025="data/raw.parquet"
)
```

```bash
python main.py
```

Los resultados se guardan en `output/` (imágenes, CSVs, archivos Gephi).

---

## Datos

Los datasets no están incluidos por tamaño. Descargarlos desde:

- [Google Drive](https://drive.google.com/drive/folders/1Bt5uy-JHgx4GVeh-iZuBsOC8VdQzcVtO?usp=sharing)
- [Zenodo — DOI 10.5281/zenodo.18912507](https://doi.org/10.5281/zenodo.18912507)

Colocar los archivos en la carpeta `data/` antes de ejecutar.

---

## Estructura

```
Evolucion-ecosistema-python/
├── main.py                 ← Entry point — orquesta el análisis completo
├── src/
│   ├── cleaning.py         ← Limpieza y normalización del dataset
│   ├── metrics.py          ← Cálculo de métricas de red y centralidades
│   └── visualization.py    ← Gráficos, wordclouds y exportación
├── data/                   ← Datasets (no incluidos — ver sección Datos)
└── output/                 ← Resultados generados (imágenes, CSV, Gephi)
```
