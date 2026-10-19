# DBSCAN paralelo con OpenMP

Proyecto Apertura — Cómputo Paralelo y en la Nube (ITAM). Detección de ruido (outliers) con DBSCAN en C++: una versión serial y dos versiones paralelas con OpenMP que dividen el plano en `k` regiones (franjas y malla).

## Estructura

```
src/dbscan.cpp                       serial + franjas + malla + CLI + experimento (--bench)
scripts/graficas.py                  gráficas de speedup y resumen
data/DBSCAN_noise.ipynb              libreta del curso (genera y visualiza)
results/experimentos.csv             datos crudos (10 iteraciones por configuración)
results/*.png                        gráficas
docs/1_descripcion_codigo.md         descripción del código y la paralelización
docs/2_evaluacion_experimental.md    evaluación experimental, análisis y uso de IA
```

## Requisitos

g++ con OpenMP (C++17), Python 3 con `numpy`, `scikit-learn`, `pandas` y `matplotlib`.

## Uso

Compilar:

```
make
```

Generar las entradas (mismos parámetros que `DBSCAN_noise.ipynb`):

```
python3 - << 'PY'
import numpy as np
from sklearn.datasets import make_blobs
for n in (20000, 40000, 80000, 120000, 140000, 160000, 180000, 200000):
    pts, _ = make_blobs(n_samples=n, centers=4, cluster_std=0.06, random_state=11, center_box=(0, 1.0))
    np.savetxt(f"data/{n}_data.csv", np.round(np.abs(pts[:, ::-1]), 3), delimiter=",", fmt="%.3f")
PY
```

Una corrida (escribe `data/<N>_results.csv`, que la libreta visualiza):

```
build/dbscan data/20000_data.csv <serial|franjas|malla> [k] [hilos]
```

Etiquetas de salida: `0` ruido, `1` core, `2` core de segundo orden.

Experimento completo y gráficas:

```
build/dbscan --bench data results/experimentos.csv
python3 scripts/graficas.py
```

El experimento verifica en cada configuración que el resultado sea idéntico al de la versión serial y se detiene si no lo es.