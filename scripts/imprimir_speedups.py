"""Imprime los speedups de las corridas con 100000_data.csv y cuatro hilos."""

import csv
from pathlib import Path
from statistics import median


ARCHIVO = Path(__file__).resolve().parent.parent / "results/tiempos_100000_k4.csv"
CONFIGURACIONES = (
    ("serial", 1, 1, "Serial"),
    ("p1", 1, 4, "P1"),
    ("malla", 4, 4, "P2 (k=4)"),
)


def main():
    tiempos = {(version, k, hilos): [] for version, k, hilos, _ in CONFIGURACIONES}
    with ARCHIVO.open(newline="") as archivo:
        for fila in csv.DictReader(archivo):
            clave = (fila["version"], int(fila["k"]), int(fila["hilos"]))
            if clave in tiempos:
                tiempos[clave].append(float(fila["tiempo_s"]))

    medianas = {}
    for version, k, hilos, nombre in CONFIGURACIONES:
        valores = tiempos[(version, k, hilos)]
        if not valores:
            raise ValueError(f"Faltan mediciones para {nombre} en {ARCHIVO}")
        medianas[version] = median(valores)

    serial = medianas["serial"]
    print("Versión         Tiempo mediano (s)   Speedup")
    for version, _, _, nombre in CONFIGURACIONES:
        tiempo = medianas[version]
        print(f"{nombre:<15} {tiempo:>17.6f}   {serial / tiempo:>6.2f}x")


if __name__ == "__main__":
    main()
