"""Genera gráficas de las versiones serial, P1 y P2 desde experimentos.csv."""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

RESULTADOS = Path(__file__).resolve().parent.parent / "results"

datos = pd.read_csv(RESULTADOS / "experimentos.csv")
medias = datos.groupby(["version", "k", "n", "hilos"], as_index=False)["tiempo_s"].mean()

serial = medias[medias.version == "serial"].sort_values("n")
p1 = medias[medias.version == "p1"].sort_values("n")
p2 = medias[medias.version == "malla"].sort_values("n")
tiempo_serial = serial.set_index("n")["tiempo_s"]

hilos = sorted(p1.hilos.unique())
h_ref = hilos[-2] if len(hilos) > 1 else hilos[0]  # normalmente, procesadores lógicos
k_ref = int(p2.k.max())
n_max = int(medias.n.max())


def guardar(figura, nombre):
    figura.tight_layout()
    figura.savefig(RESULTADOS / nombre, dpi=170)
    plt.close(figura)


# 1) Tiempo según N: las dos versiones paralelas usan los mismos hilos.
fig, ax = plt.subplots(figsize=(8, 5))
for grupo, nombre, color in (
    (serial, "Serial (1 hilo)", "#555555"),
    (p1[p1.hilos == h_ref], f"P1 ({h_ref} hilos)", "#0072B2"),
    (p2[(p2.hilos == h_ref) & (p2.k == k_ref)],
     f"P2 (k={k_ref}, {h_ref} hilos)", "#D55E00"),
):
    ax.plot(grupo.n, grupo.tiempo_s, marker="o", linewidth=2, label=nombre, color=color)
ax.set_yscale("log")
ax.set_xlabel("Número de puntos (N)")
ax.set_ylabel("Tiempo medio (s, escala logarítmica)")
ax.set_title("Tiempo de ejecución según el tamaño de entrada")
ax.grid(alpha=0.25)
ax.legend()
guardar(fig, "tiempo_vs_n.png")


# 2) Aceleración contra serial según los hilos, con N máximo.
fig, ax = plt.subplots(figsize=(8, 5))
for grupo, nombre, color in (
    (p1[p1.n == n_max], "P1: región completa", "#0072B2"),
    (p2[(p2.n == n_max) & (p2.k == k_ref)], f"P2: k={k_ref}", "#D55E00"),
):
    grupo = grupo.sort_values("hilos")
    ax.plot(grupo.hilos, tiempo_serial[n_max] / grupo.tiempo_s,
            marker="o", linewidth=2, label=nombre, color=color)
ax.axhline(1, color="gray", linestyle="--", linewidth=1, label="Serial")
ax.set_xticks(hilos)
ax.set_xlabel("Hilos")
ax.set_ylabel("Aceleración frente a serial")
ax.set_title(f"Aceleración por hilos (N = {n_max:,})")
ax.grid(alpha=0.25)
ax.legend()
guardar(fig, "speedup_vs_hilos.png")


# 3) Efecto de k sobre P2 para distintos números de hilos.
fig, ax = plt.subplots(figsize=(8, 5))
for h, grupo in p2[p2.n == n_max].groupby("hilos"):
    grupo = grupo.sort_values("k")
    ax.plot(grupo.k, grupo.tiempo_s * 1000, marker="o", linewidth=2,
            label=f"{h} hilos")
ax.set_xscale("log", base=2)
ax.set_xticks(sorted(p2.k.unique()), sorted(p2.k.unique()))
ax.set_xlabel("Número de regiones (k)")
ax.set_ylabel("Tiempo medio (ms)")
ax.set_title(f"Efecto de la partición en P2 (N = {n_max:,})")
ax.grid(alpha=0.25)
ax.legend()
guardar(fig, "tiempo_vs_k_p2.png")


# 4) Comparación directa: valores > 1 indican que P2 tarda menos que P1.
comparacion = p1.merge(
    p2[p2.k == k_ref], on=["n", "hilos"], suffixes=("_p1", "_p2")
)
comparacion["razon"] = comparacion.tiempo_s_p1 / comparacion.tiempo_s_p2
fig, ax = plt.subplots(figsize=(8, 5))
for h, grupo in comparacion.groupby("hilos"):
    grupo = grupo.sort_values("n")
    ax.plot(grupo.n, grupo.razon, marker="o", linewidth=2, label=f"{h} hilos")
ax.axhline(1, color="gray", linestyle="--", linewidth=1)
ax.set_xlabel("Número de puntos (N)")
ax.set_ylabel("Tiempo P1 / tiempo P2")
ax.set_title(f"Ventaja de la partición (P2 con k={k_ref})")
ax.grid(alpha=0.25)
ax.legend()
guardar(fig, "p1_vs_p2.png")


print(f"Mediciones: {len(datos)}; N máximo: {n_max:,}; hilos de comparación: {h_ref}; k de P2: {k_ref}")
print(f"Serial con N máximo: {tiempo_serial[n_max]:.6f} s")
for nombre, grupo in (("P1", p1), ("P2", p2)):
    grupo = grupo.copy()
    grupo["speedup"] = grupo.n.map(tiempo_serial) / grupo.tiempo_s
    mejor = grupo.loc[grupo.speedup.idxmax()]
    print(f"{nombre}: aceleración máxima {mejor.speedup:.2f}x "
          f"(N={int(mejor.n)}, k={int(mejor.k)}, hilos={int(mejor.hilos)})")
