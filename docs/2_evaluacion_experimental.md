# Evaluación experimental de desempeño

Cómputo Paralelo y en la Nube — Proyecto Apertura: DBSCAN paralelo con OpenMP.
Autor: Jorge Daniel Lafarga Axotla. Datos: `results/experimentos.csv`. Código: `src/dbscan.cpp`.

## 1. Definición del experimento

**Versiones comparadas.** Serial (toda la matriz como una sola región) y dos paralelas que dividen el plano en `k` regiones: *franjas* (k tiras verticales) y *malla* (celdas casi cuadradas). Ver `docs/1_descripcion_codigo.md`.

**Parámetros del experimento.**

| Parámetro | Valores |
|---|---|
| k (divisiones) | 2, 4, 8, 16, 32, 64 |
| Número de puntos | 20000, 40000, 80000, 120000, 140000, 160000, 180000, 200000 |
| Hilos | 1, 4, 8, 16 (1, cores virtuales/2, cores virtuales y cores virtuales × 2, con 8 cores virtuales) |
| Iteraciones por configuración | 10 (se promedian) |

La versión serial se ejecuta una vez por cada tamaño (10 iteraciones). Cada versión paralela se ejecuta en las 6 × 4 combinaciones de k e hilos para cada tamaño: en total 3,840 corridas paralelas y 80 seriales.

**Datos de entrada.** Puntos aleatorios generados con el código de `DBSCAN_noise.ipynb` (`make_blobs` con 4 centros, `cluster_std = 0.06`, `random_state = 11`, coordenadas en valor absoluto y redondeadas a 3 decimales). Parámetros de DBSCAN: ε = 0.03, `min_samples` = 10. Con 20,000 puntos se detectan 45 puntos de ruido.

**Qué se mide.** Tiempo de pared (`omp_get_wtime`) de la ejecución del algoritmo, incluyendo la construcción de la partición y las regiones en las versiones paralelas, y excluyendo la lectura del archivo. Por cada configuración se reportan las 10 iteraciones y su media.

**Métricas.**

- *Speedup contra la serial* = tiempo medio serial (mismo N) / tiempo medio de la configuración.
- *Speedup contra 1 hilo* = tiempo medio de la misma versión, k y N con 1 hilo / tiempo medio con h hilos.

Se separan porque la versión paralela con 1 hilo ya es más rápida que la serial: dividir en regiones acorta las listas de puntos que se comparan, aunque no haya paralelismo. El primer speedup mide el efecto total; el segundo, solo el de los hilos.

**Corrección.** En cada configuración se verifica que las etiquetas sean idénticas a las de la serial; el programa se detiene si no lo son. Esto no ocurrió en ninguna corrida.

## 2. Equipo

| | |
|---|---|
| CPU | Intel Core i5-9300H @ 2.40 GHz |
| Cores / hilos | 4 cores físicos, 2 hilos por core: 8 cores virtuales, 1 socket |
| Caché | L2: 1 MiB en total (4 instancias, 256 KiB por core); L3: 8 MiB |
| RAM | (completar con la salida de `free -h`) |
| Sistema operativo | Ubuntu 24.04 sobre WSL2 (kernel 6.18.54.1-microsoft-standard-WSL2), en Windows |
| Compilador | g++ 13.3.0 (Ubuntu 13.3.0-6ubuntu2~24.04.1) |
| Banderas | `-O3 -march=native -std=c++17 -fopenmp -Wall -Wextra` |
| Paralelismo | OpenMP |

## 3. Resultados

Speedup contra la serial con N = 200,000 (tiempo serial medio: 0.3366 s):

| k | franjas 1 | franjas 4 | franjas 8 | franjas 16 | malla 1 | malla 4 | malla 8 | malla 16 |
|---|---|---|---|---|---|---|---|---|
| 2 | 1.90 | 3.37 | 3.14 | 3.14 | 1.35 | 2.72 | 3.09 | 3.24 |
| 4 | 3.20 | 5.97 | 4.85 | 5.68 | 2.96 | 5.30 | 5.43 | 5.44 |
| 8 | 4.73 | 12.08 | 10.37 | 11.15 | 4.74 | 10.61 | 10.65 | 10.82 |
| 16 | 5.12 | 12.10 | 11.04 | 14.49 | 6.23 | 15.14 | 13.86 | 14.46 |
| 32 | 5.00 | 11.70 | 9.50 | 13.87 | 6.94 | 17.13 | 17.66 | 18.93 |
| 64 | 2.46 | 8.25 | 7.66 | 8.70 | 5.83 | 15.41 | 14.99 | 16.86 |

(Columnas: versión y número de hilos.)

Speedup contra 1 hilo (misma versión y k) con N = 200,000:

| k | franjas 1 | franjas 4 | franjas 8 | franjas 16 | malla 1 | malla 4 | malla 8 | malla 16 |
|---|---|---|---|---|---|---|---|---|
| 2 | 1.00 | 1.78 | 1.65 | 1.65 | 1.00 | 2.02 | 2.29 | 2.40 |
| 4 | 1.00 | 1.86 | 1.51 | 1.77 | 1.00 | 1.79 | 1.84 | 1.84 |
| 8 | 1.00 | 2.55 | 2.19 | 2.36 | 1.00 | 2.24 | 2.25 | 2.28 |
| 16 | 1.00 | 2.36 | 2.16 | 2.83 | 1.00 | 2.43 | 2.22 | 2.32 |
| 32 | 1.00 | 2.34 | 1.90 | 2.77 | 1.00 | 2.47 | 2.54 | 2.73 |
| 64 | 1.00 | 3.36 | 3.12 | 3.54 | 1.00 | 2.65 | 2.57 | 2.89 |

Gráficas:

![Speedup contra la serial según el número de puntos](../results/speedup_vs_n.png)

![Escalamiento por hilos con N = 200,000](../results/speedup_vs_hilos.png)

![Cociente de tiempos franjas / malla con N = 200,000](../results/franjas_vs_malla.png)

## 4. Interpretación y análisis

### 4.1 Cumplimiento del requisito de speedup

Ambas versiones superan ampliamente el speedup de 1.5 que pide la NOTA 1. El máximo de todo el experimento es 25.14. Con N = 200,000, el mejor resultado de franjas es 14.49 (k = 16, 16 hilos) y el de malla, 18.93 (k = 32, 16 hilos).

### 4.2 Dos efectos: partición e hilos

Con 1 hilo las versiones paralelas ya son entre 2.5 y 7 veces más rápidas que la serial para k ≥ 8 (por ejemplo, malla con k = 32: 6.94). No es paralelismo: es el efecto de dividir. Cada región compara cada punto contra una lista corta (sus puntos más el halo) en vez de contra los n puntos, y esas listas se guardan contiguas en memoria y, al crecer k, son lo bastante pequeñas para aprovechar mejor la caché (L2 de 256 KiB por core), mientras que la serial recorre arreglos de 200,000 puntos (unos 3.2 MB para x e y) que no caben en L2 y se leen desde L3. La parte atribuible a la localidad de caché es una explicación consistente con los datos, pero no se midió con contadores de hardware.

Los hilos aportan un factor adicional de 1.5 a 3.5 (tabla de speedup contra 1 hilo). Es modesto porque la máquina tiene 4 cores físicos: pasar de 4 a 8 o 16 hilos casi no mejora y en varios casos empeora, lo que es esperable cuando los hilos adicionales son hyperthreads que comparten unidades de ejecución y caché con otro hilo, o simplemente están sobresuscritos. Con malla, k = 16 y 4 hilos, el speedup de 2.43 corresponde, según la ley de Amdahl con 4 cores, a una fracción paralelizable de alrededor de 78 % y un máximo teórico de unas 4.7 veces. El resto es trabajo que no escala: cálculo de los límites de la caja, reserva de memoria, la fracción de construcción de regiones y el desbalance entre regiones (los clusters concentran los puntos en pocas celdas).

### 4.3 Efecto de k

El mejor k es intermedio y depende de la versión: 16 para franjas y 32 para malla. Subir k acorta las listas de candidatos, pero tiene dos costos: construir las regiones cuesta O(k·n) en total (cada región recorre los n puntos para reunir sus candidatos) y el halo crece en proporción al número de regiones. Con k = 64 ambos costos pesan: franjas cae a 2.46 con 1 hilo y malla baja de 6.94 a 5.83.

Con k = 2 solo hay 2 regiones, por lo que más de 2 hilos no pueden acelerar el cálculo por región; por eso 4, 8 y 16 hilos dan resultados parecidos (3.37, 3.14 y 3.14 en franjas).

### 4.4 ¿Por qué una versión paralela fue mejor que la otra?

Las dos versiones usan el mismo algoritmo, la misma estrategia de consistencia y los mismos kernels; solo cambia la forma de las regiones. Esa forma determina cuánto halo debe copiarse y recorrerse. Si el dominio es aproximadamente un cuadrado unitario y ε = 0.03, la lista de candidatos de una región (propios más halo) es, de forma aproximada, este múltiplo de sus puntos propios, sin considerar efectos de borde ni que la densidad no es uniforme:

| k | franjas | malla |
|---|---|---|
| 2 | 1.1 | 1.1 |
| 4 | 1.2 | 1.3 |
| 8 | 1.5 | 1.4 |
| 16 | 2.0 | 1.5 |
| 32 | 2.9 | 1.8 |
| 64 | 4.8 | 2.2 |

(Para franjas es (w + 2ε)/w con w = 1/k; para la malla, el producto de ese cociente en cada eje.)

Una franja de k = 64 mide apenas ≈ 0.016 de ancho, menos que ε = 0.03: su halo es más grande que la propia franja y cada región compara contra unas cinco veces más puntos de los que le pertenecen. En la malla 8×8 el factor es de unas dos veces. Por eso, a partir de k = 16 malla es mejor o igual que franjas y la ventaja crece con k (k = 64 con 1 hilo: 5.83 contra 2.46; k = 32 con 4 hilos: 17.13 contra 11.70). Con k = 8 son equivalentes (4.73 contra 4.74 con 1 hilo), que coincide con que el factor de halo es casi igual para ambas.

Franjas escala algo mejor con los hilos en k = 64 (3.54 contra 2.89 al pasar de 1 a 16 hilos), pero porque parte de una base mucho más lenta: tiene más trabajo repetido en los halos que sí se puede repartir. En tiempo absoluto, malla sigue siendo más rápida.

### 4.5 Variabilidad de las medidas

Para k = 2, `franjas` y `malla` producen exactamente la misma partición (2×1), y sin embargo con 1 hilo se midió 1.90 en una y 1.35 en la otra. Esa diferencia es variabilidad de la medición (el experimento corre en WSL2 sobre una laptop), no de las versiones, y da una idea del margen de error: diferencias menores a ~30–40 % entre configuraciones no son concluyentes. Las conclusiones de las secciones anteriores se apoyan en diferencias mayores (por ejemplo, 5.83 contra 2.46 o 17.13 contra 11.70).

## 5. Limitaciones

- Un solo equipo, de 4 cores físicos, ejecutado sobre WSL2; el overhead de WSL2 y la gestión de energía de una laptop pueden afectar los tiempos.
- Una sola semilla de datos (`random_state = 11`) y una distribución fija (4 clusters gaussianos); los tiempos dependen de la densidad y de cuántos puntos son ruido.
- Se reportan medias de 10 iteraciones sin calentamiento previo; una iteración atípica puede mover la media (por ejemplo, en la serial con 20,000 puntos hay una iteración de 0.0656 s contra ~0.027 s en las demás).
- Las explicaciones de caché y de Amdahl son interpretaciones consistentes con los datos, no mediciones directas con contadores de hardware.

## 6. Uso responsable y ético de IA generativa

Se usó Claude (Anthropic) como asistente para: interpretar el enunciado, proponer el diseño de las dos versiones paralelas (franjas y malla con halo de ancho ε y dos fases), escribir y revisar `src/dbscan.cpp` y `scripts/graficas.py`, y redactar un borrador de estos documentos a partir de los resultados del experimento.

Qué se verificó por cuenta propia: el código se compiló y ejecutó; la corrección se comprobó comparando las tres versiones entre sí y contra `sklearn.cluster.DBSCAN`; el experimento completo se ejecutó en mi equipo y las tablas y gráficas de este documento salen de esos datos. El autor es responsable del contenido entregado y puede explicar cada parte del programa.

## 7. Archivos

- `results/experimentos.csv`: datos crudos. Columnas: `version, k, n, hilos, iteracion, tiempo_s, n_ruido`.
- `results/speedup_vs_n.png`, `results/speedup_vs_hilos.png`, `results/franjas_vs_malla.png`.