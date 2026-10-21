# DBSCAN paralelo con OpenMP

Proyecto Apertura — Cómputo Paralelo y en la Nube (ITAM). Detección de ruido (outliers) con DBSCAN en C++: una versión serial, P1 paralela sobre todos los puntos y P2 paralela con el plano dividido en `k` celdas.

## Estructura

```
src/dbscan.cpp                       serial + P1 + P2 (malla) + experimento (--bench)
scripts/graficas.py                  gráficas de tiempos, aceleración y resumen
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
build/dbscan data/20000_data.csv <serial|p1|malla> [k] [hilos]
```

`serial` procesa todos los puntos con un hilo; `p1` procesa todos los puntos en paralelo; `malla` divide el plano en `k` regiones y las procesa en paralelo. `k` solo se usa en `malla`; use potencias de 2 para obtener exactamente `k` regiones. El experimento usa `k = 2, 4, 8, 16, 32, 64`.

Etiquetas de salida: `0` ruido, `1` core, `2` core de segundo orden.

Experimento completo y gráficas:

```
build/dbscan --bench data results/experimentos.csv
python3 scripts/graficas.py
```

El experimento verifica en cada configuración que el resultado sea idéntico al de la versión serial y se detiene si no lo es. Genera mediciones para P1 y P2; el script produce cuatro gráficas: tiempo según `N`, aceleración según hilos, efecto de `k` en P2 y comparación directa entre P1 y P2.
