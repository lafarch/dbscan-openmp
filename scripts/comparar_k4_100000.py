"""Mide serial, P1 y P2 sobre 100000_data.csv y grafica sus outliers."""

import csv
import re
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "data/100000_data.csv"
SALIDA_CPP = RAIZ / "data/100000_results.csv"
VERSIONES = ("serial", "p1", "malla")
NOMBRES = {"serial": "Serial", "p1": "P1", "malla": "P2 (k=4)"}
REPETICIONES = 5


def main():
    tiempos = {version: [] for version in VERSIONES}
    etiquetas = {}
    puntos = None

    for _ in range(REPETICIONES):
        for version in VERSIONES:
            # El algoritmo serial usa un hilo; ambas versiones paralelas usan cuatro.
            hilos = 1 if version == "serial" else 4
            corrida = subprocess.run(
                [str(RAIZ / "build/dbscan"), str(ENTRADA), version, "4", str(hilos)],
                check=True, capture_output=True, text=True,
            )
            coincidencia = re.search(r"Tiempo:\s*([0-9.eE+-]+)\s*s", corrida.stdout)
            if not coincidencia:
                raise RuntimeError(f"Falta el tiempo de {version}: {corrida.stdout}")
            tiempos[version].append(float(coincidencia.group(1)))

            resultado = np.loadtxt(SALIDA_CPP, delimiter=",")
            if puntos is None:
                puntos = resultado[:, :2]
            elif not np.array_equal(puntos, resultado[:, :2]):
                raise RuntimeError(f"Las coordenadas cambiaron en {version}")
            nuevas = resultado[:, 2].astype(np.uint8)
            if version in etiquetas and not np.array_equal(etiquetas[version], nuevas):
                raise RuntimeError(f"Las etiquetas cambiaron entre corridas de {version}")
            etiquetas[version] = nuevas

    for version in VERSIONES[1:]:
        if not np.array_equal(etiquetas["serial"], etiquetas[version]):
            raise RuntimeError(f"Las etiquetas de {version} difieren de serial")

    resultados = RAIZ / "results"
    resultados.mkdir(exist_ok=True)
    csv_tiempos = resultados / "tiempos_100000_k4.csv"
    with csv_tiempos.open("w", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(("version", "k", "hilos", "iteracion", "tiempo_s", "n_ruido"))
        for version in VERSIONES:
            for iteracion, tiempo in enumerate(tiempos[version]):
                escritor.writerow((version, 4 if version == "malla" else 1,
                                  1 if version == "serial" else 4, iteracion,
                                  tiempo, int(np.count_nonzero(etiquetas[version] == 0))))

    figura, ejes = plt.subplots(1, 3, figsize=(15, 4.5), sharex=True, sharey=True)
    for eje, version in zip(ejes, VERSIONES):
        ruido = etiquetas[version] == 0
        eje.scatter(puntos[~ruido, 0], puntos[~ruido, 1], s=1,
                    color="#999999", alpha=0.18, linewidths=0)
        eje.scatter(puntos[ruido, 0], puntos[ruido, 1], s=9,
                    color="#d62728", linewidths=0, label=f"Outliers: {ruido.sum()}")
        eje.set_title(NOMBRES[version])
        eje.set_xlabel("x")
        eje.legend(loc="upper right")
    ejes[0].set_ylabel("y")
    figura.suptitle("Outliers DBSCAN | 100,000 puntos | ε=0.03 | min_samples=10")
    figura.tight_layout()
    png = resultados / "outliers_100000_k4.png"
    figura.savefig(png, dpi=180)
    plt.close(figura)

    serial = float(np.median(tiempos["serial"]))
    print(f"Entrada: {ENTRADA.name}; {REPETICIONES} corridas por versión")
    print(f"Serial (1 hilo): {serial:.6f} s; speedup 1.00x")
    for version in VERSIONES[1:]:
        tiempo = float(np.median(tiempos[version]))
        print(f"{NOMBRES[version]} (4 hilos): {tiempo:.6f} s; speedup {serial / tiempo:.2f}x")
    print(f"Outliers idénticos: {np.count_nonzero(etiquetas['serial'] == 0)}")
    print(f"Gráfica: {png}")
    print(f"Mediciones: {csv_tiempos}")


if __name__ == "__main__":
    main()
