"""Genera las gráficas de speedup y el resumen a partir de results/experimentos.csv."""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

RESULTADOS = Path(__file__).resolve().parent.parent / "results"
VERSIONES = ["franjas", "malla"]

datos = pd.read_csv(RESULTADOS / "experimentos.csv")

# Tiempo medio de las 10 iteraciones de cada configuración.
medias = datos.groupby(["version", "k", "n", "hilos"], as_index=False)["tiempo_s"].mean()
serial = medias[medias.version == "serial"].set_index("n")["tiempo_s"]
par = medias[medias.version != "serial"].copy()

# Speedup contra la versión serial (mismo número de puntos).
par["speedup"] = par["n"].map(serial) / par["tiempo_s"]

# Speedup solo por hilos: misma configuración (versión, k, n) contra su corrida con 1 hilo.
un_hilo = par[par.hilos == 1][["version", "k", "n", "tiempo_s"]].rename(columns={"tiempo_s": "t1"})
par = par.merge(un_hilo, on=["version", "k", "n"])
par["speedup_hilos"] = par["t1"] / par["tiempo_s"]

hilos = sorted(par.hilos.unique())
n_max = par.n.max()


def guardar(figura, nombre):
    figura.tight_layout()
    figura.savefig(RESULTADOS / nombre, dpi=150)
    plt.close(figura)


# 1) Speedup contra la serial según el número de puntos (fila: versión, columna: hilos).
fig, ejes = plt.subplots(2, len(hilos), figsize=(4 * len(hilos), 7), sharex=True, sharey=True, squeeze=False)
for fila, v in enumerate(VERSIONES):
    for col, h in enumerate(hilos):
        ax = ejes[fila][col]
        for k, g in par[(par.version == v) & (par.hilos == h)].groupby("k"):
            ax.plot(g.n, g.speedup, marker="o", label=f"k={k}")
        ax.axhline(1.5, color="gray", linestyle="--", linewidth=1)
        ax.set_title(f"{v}, {h} hilos")
        if fila == 1:
            ax.set_xlabel("Número de puntos")
        if col == 0:
            ax.set_ylabel("Speedup vs serial")
ejes[0][0].legend(fontsize=8)
fig.suptitle("Speedup contra la versión serial (línea punteada: 1.5)")
guardar(fig, "speedup_vs_n.png")

# 2) Efecto de los hilos con N máximo: cada configuración contra sí misma con 1 hilo.
fig, ejes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
for ax, v in zip(ejes, VERSIONES):
    for k, g in par[(par.version == v) & (par.n == n_max)].groupby("k"):
        ax.plot(g.hilos, g.speedup_hilos, marker="o", label=f"k={k}")
    ax.set_xscale("log", base=2)
    ax.set_xticks(hilos, hilos)
    ax.set_title(v)
    ax.set_xlabel("Hilos")
ejes[0].set_ylabel("Speedup vs 1 hilo")
ejes[0].legend(fontsize=8)
fig.suptitle(f"Escalamiento por hilos (N = {n_max})")
guardar(fig, "speedup_vs_hilos.png")

# 3) Franjas contra malla con N máximo: cociente de tiempos.
t = par[par.n == n_max].pivot_table(index=["k", "hilos"], columns="version", values="tiempo_s")
razon = (t["franjas"] / t["malla"]).rename("razon").reset_index()
fig, ax = plt.subplots(figsize=(6, 4))
for h, g in razon.groupby("hilos"):
    ax.plot(g.k, g.razon, marker="o", label=f"{h} hilos")
ax.axhline(1, color="gray", linestyle="--", linewidth=1)
ax.set_xscale("log", base=2)
ax.set_xticks(sorted(razon.k.unique()), sorted(razon.k.unique()))
ax.set_xlabel("k")
ax.set_ylabel("tiempo franjas / tiempo malla")
ax.set_title(f"Malla es más rápida si > 1 (N = {n_max})")
ax.legend(fontsize=8)
guardar(fig, "franjas_vs_malla.png")

# Resumen en consola.
tope = par[par.n == n_max]
print(f"N = {n_max}: tiempo serial = {serial[n_max]:.4f} s")
for v, g in tope.groupby("version"):
    m = g.loc[g.speedup.idxmax()]
    print(f"{v}: mejor speedup {m.speedup:.2f} (k={int(m.k)}, hilos={int(m.hilos)})")
print(f"Speedup máximo en todo el experimento: {par.speedup.max():.2f} (NOTA 1 exige > 1.5)")
print("\nSpeedup vs serial, N máximo:")
print(tope.pivot_table(index="k", columns=["version", "hilos"], values="speedup").round(2).to_string())
print("\nSpeedup vs 1 hilo, N máximo:")
print(tope.pivot_table(index="k", columns=["version", "hilos"], values="speedup_hilos").round(2).to_string())