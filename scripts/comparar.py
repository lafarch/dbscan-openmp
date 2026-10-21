"""Compara serial, P1 y P2 sobre un archivo de puntos y grafica los outliers detectados.

Uso: python scripts/comparar.py data/100000_data.csv [hilos=4] [k=64]
"""
import re
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
REPETICIONES = 5

entrada = Path(sys.argv[1])
hilos = sys.argv[2] if len(sys.argv) > 2 else "4"
k = sys.argv[3] if len(sys.argv) > 3 else "64"
salida = entrada.with_name(entrada.name.replace("_data.csv", "_results.csv"))

# nombre -> (versión del programa, hilos)
versiones = {"Serial": ("serial", "1"), "P1": ("p1", hilos), "P2": ("malla", hilos)}

tiempos, etiquetas = {}, {}
for nombre, (version, h) in versiones.items():
    medidas = []
    for _ in range(REPETICIONES):
        corrida = subprocess.run([str(RAIZ / "build" / "dbscan"), str(entrada), version, k, h],
                                capture_output=True, text=True, check=True)
        medidas.append(float(re.search(r"Tiempo: (\S+) s", corrida.stdout).group(1)))
    tiempos[nombre] = np.mean(medidas)
    resultado = np.loadtxt(salida, delimiter=",")       # lo escribió la última corrida
    etiquetas[nombre] = resultado[:, 2]
puntos = resultado[:, :2]

print(f"{entrada.name}: {len(puntos)} puntos | {hilos} hilos | P2 con k={k} | media de {REPETICIONES} corridas")
for nombre, t in tiempos.items():
    print(f"{nombre:7s} {t:.5f} s | speedup {tiempos['Serial'] / t:5.2f}x | outliers: {int((etiquetas[nombre] == 0).sum())}")
iguales = all(np.array_equal(etiquetas["Serial"], e) for e in etiquetas.values())
print("Etiquetas idénticas en las 3 versiones:", iguales)

# Outliers (rojo) sobre el resto de los puntos (gris), una gráfica por versión.
fig, ejes = plt.subplots(1, 3, figsize=(15, 5), sharex=True, sharey=True)
for ax, (nombre, e) in zip(ejes, etiquetas.items()):
    ruido = e == 0
    ax.scatter(puntos[~ruido, 0], puntos[~ruido, 1], s=2, color="lightgray")
    ax.scatter(puntos[ruido, 0], puntos[ruido, 1], s=8, color="red")
    ax.set_title(f"{nombre}: {int(ruido.sum())} outliers")
    ax.set_xticks([])
    ax.set_yticks([])
fig.suptitle(f"Outliers detectados ({entrada.name}, {hilos} hilos)")
fig.tight_layout()
destino = RAIZ / "results" / f"outliers_{entrada.name.replace('_data.csv', '')}.png"
fig.savefig(destino, dpi=150)
print("Gráfica:", destino)