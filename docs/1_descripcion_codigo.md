# Descripción del código y estrategias de paralelización

Cómputo Paralelo y en la Nube — Proyecto Apertura: DBSCAN paralelo para la detección de ruido con OpenMP.
Autor: Jorge Daniel Lafarga Axotla. Código: `src/dbscan.cpp`.

## 1. Problema

Dado un conjunto de puntos en el plano, cada punto se clasifica con dos parámetros: ε (distancia) y `min_samples` (número mínimo de puntos a distancia ≤ ε para considerar densa una zona). Se usan los del notebook del curso: ε = 0.03 y `min_samples` = 10 (el propio punto cuenta, igual que en sklearn).

Etiquetas de salida:

- **Core (1.er orden), etiqueta 1:** tiene al menos `min_samples` puntos a distancia ≤ ε.
- **Core de 2.º orden, etiqueta 2:** no es core, pero tiene un core a distancia ≤ ε.
- **Ruido, etiqueta 0:** el resto.

Solo se detecta ruido: no se asignan identificadores de cluster, así que no hace falta expandir clusters ni unir componentes conexas.

La distancia euclidiana d = √((x₂−x₁)² + (y₂−y₁)²) se evalúa como d² ≤ ε², que es equivalente y evita la raíz.

## 2. Organización del código

| Elemento | Función |
|---|---|
| `marcar_cores` | Fase 1: decide si cada punto propio de una región es core. |
| `etiquetar` | Fase 2: asigna core, core de 2.º orden o ruido. |
| `dbscan_serial` | P1: una sola región con toda la matriz. |
| `dbscan_particionado` | Núcleo de P2: divide el plano en `gx × gy` regiones, las procesa en paralelo y mantiene la consistencia. |
| `dbscan_franjas` / `dbscan_malla` | Las dos versiones paralelas: solo cambian la forma de la partición. |
| `construir_region` | Reúne los puntos de una celda y su halo. |
| `bench` | Experimento completo (sección 6). |

Las tres versiones comparten exactamente los mismos kernels (`marcar_cores` y `etiquetar`), de modo que la comparación de tiempos mide la estrategia de partición y no diferencias de implementación.

## 3. Versión serial (P1)

Construye una única región que contiene todos los puntos, ejecuta la fase 1 y luego la fase 2. En la fase 1 el conteo de vecinos de un punto se detiene al llegar a `min_samples` (un punto core no necesita más). En la fase 2 la búsqueda de un core vecino se detiene en cuanto aparece uno. Un punto de ruido sí recorre todos los puntos en ambas fases.

## 4. Versiones paralelas (P2)

### 4.1 Partición

Con `k` regiones, el plano (caja que contiene a los puntos) se divide en una malla de `gx × gy` celdas con `gx·gy = k`:

- **Franjas:** `gx = k`, `gy = 1` (k tiras verticales).
- **Malla:** celdas casi cuadradas, con `gx` la menor potencia de 2 tal que `gx² ≥ k` y `gy = k/gx`. Para k ∈ {2, 4, 8, 16, 32, 64} resultan 2×1, 2×2, 4×2, 4×4, 8×4 y 8×8.

Cada punto pertenece a una sola celda (su dueño), calculada en un `parallel for`.

### 4.2 ¿Cómo unir los resultados para mantener consistencia?

El problema de dividir la matriz es que un punto cerca de una frontera tiene vecinos en la región contigua. Se resuelve con dos mecanismos:

1. **Halo de ancho ε.** Cada región trabaja con una lista de candidatos formada por sus puntos propios y todos los puntos de otras celdas que estén a distancia ≤ ε de su rectángulo (`construir_region`). El margen usado es ε + 10⁻⁹ para absorber redondeo.
2. **Dos fases separadas por una barrera.** En la fase 1 cada región calcula si sus puntos propios son core y lo escribe en un arreglo global `es_core`. Al terminar el `parallel for` hay una barrera implícita; después, en la fase 2, cada región consulta `es_core` (global) para decidir el re-etiquetado.

**Por qué el resultado es idéntico al serial.** Sea p un punto propio de una región y q cualquier punto con |p − q| ≤ ε. Como p está dentro del rectángulo de su región, la distancia de q a ese rectángulo es ≤ ε, así que q está en la lista de candidatos. Por lo tanto:

- el conteo de vecinos de p en la fase 1 es el mismo que en la serial, y `es_core[p]` también;
- en la fase 2, todos los vecinos de p están en la lista y su valor de `es_core` ya es definitivo gracias a la barrera.

No se necesita una etapa de "unión" posterior: cada punto se etiqueta una sola vez, por su dueño, con información completa.

### 4.3 Uso de OpenMP

- `#pragma omp parallel for` para calcular la celda de cada punto.
- `#pragma omp parallel for schedule(dynamic, 1)` sobre las regiones, en ambas fases. Las regiones tienen costos muy distintos (los clusters son densos y el resto casi está vacío), por lo que el reparto dinámico equilibra la carga mejor que uno estático.
- **Sin condiciones de carrera:** en la fase 1 cada elemento de `es_core` lo escribe un solo hilo (su dueño) y en la fase 2 se lee, junto con `etiqueta`, que también tiene un solo escritor por elemento. Se usan arreglos separados (`es_core` y `etiqueta`) para que en la fase 2 nadie lea una posición que otro hilo esté escribiendo.
- Cada región es un objeto independiente (`Region`) con copias contiguas de sus coordenadas, lo que mejora la localidad de caché.

### 4.4 Costos de la partición

Construir la región de una celda recorre los n puntos, así que construir todas cuesta O(k·n) (repartido entre los hilos). A cambio, cada región compara contra una lista de candidatos mucho más corta que n. Por eso aumentar `k` primero ayuda y después deja de ayudar (ver el documento de evaluación). El tamaño del halo depende de la geometría: franjas angostas tienen proporcionalmente mucho más halo que celdas casi cuadradas.

## 5. Entrada y salida

- **Entrada:** `.csv` con dos columnas `x,y` sin encabezado, generado con la libreta `DBSCAN_noise.ipynb`.
- **Salida:** `<N>_results.csv` con columnas `x,y,etiqueta`, en la misma carpeta que la entrada, que se visualiza con la misma libreta.

## 6. Verificación y experimento

- El modo `--bench` recorre todas las configuraciones y registra el tiempo de cada iteración en `results/experimentos.csv`. En cada configuración compara las etiquetas con las de la versión serial y se detiene si difieren. En el experimento completo no se detectó ninguna diferencia.
- Además se comparó el conjunto de puntos de ruido contra `sklearn.cluster.DBSCAN` (ε = 0.03, `min_samples` = 10) con 4,000 y 20,000 puntos: no hubo diferencias.

## 7. Compilación y uso

```
make
build/dbscan data/4000_data.csv malla 4 8
build/dbscan --bench data results/experimentos.csv
```

Se compila con `g++ -O3 -march=native -std=c++17 -fopenmp`.