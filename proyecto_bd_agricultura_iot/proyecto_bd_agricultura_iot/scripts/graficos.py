#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera las figuras del informe a partir de resultados/resultados.json."""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
FIG = os.path.join(RAIZ, "informe", "figuras")
ESC = ["1K", "10K", "100K", "1M"]
ROJO, AZUL = "#b03a2e", "#1f618d"
TIT = {1: "Consulta 1: parcelas con estrés hídrico",
       2: "Consulta 2: eficiencia hídrica por campaña",
       3: "Consulta 3: sensores con lecturas anómalas",
       4: "Consulta 4: ranking de rendimiento por fundo",
       5: "Consulta 5: respuesta de riego ante alertas"}


def guardar(fig, nombre):
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, nombre), dpi=170)
    plt.close(fig)


def main():
    os.makedirs(FIG, exist_ok=True)
    d = json.load(open(os.path.join(RAIZ, "resultados", "resultados.json"), encoding="utf-8"))
    tab = {(r["consulta"], r["escenario"], r["condicion"]): r["promedio"] for r in d["consultas"]}

    for q in range(1, 6):
        sin = [tab[(q, e, "sin")] for e in ESC]
        con = [tab[(q, e, "con")] for e in ESC]
        fig, ax = plt.subplots(figsize=(6.4, 3.5))
        ax.plot(range(4), sin, marker="o", lw=1.8, color=ROJO, label="Sin índices")
        ax.plot(range(4), con, marker="s", lw=1.8, color=AZUL, label="Con índices")
        ax.set_xticks(range(4))
        ax.set_xticklabels(ESC)
        ax.set_yscale("log")
        ax.set_xlabel("Registros en la base de datos")
        ax.set_ylabel("Tiempo promedio (ms, escala log)")
        ax.set_title(TIT[q], fontsize=10)
        ax.grid(True, which="both", ls=":", lw=0.6, alpha=0.6)
        ax.legend(fontsize=8)
        for x, (a, b) in enumerate(zip(sin, con)):
            arriba = a >= b
            ax.annotate("%.2f" % a, (x, a), textcoords="offset points",
                        xytext=(0, 7 if arriba else -12), ha="center", fontsize=7, color=ROJO)
            ax.annotate("%.2f" % b, (x, b), textcoords="offset points",
                        xytext=(0, -12 if arriba else 7), ha="center", fontsize=7, color=AZUL)
        guardar(fig, "consulta%d.png" % q)

    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    sin = [tab[(q, "1M", "sin")] for q in range(1, 6)]
    con = [tab[(q, "1M", "con")] for q in range(1, 6)]
    w = 0.36
    ax.bar([i - w / 2 for i in range(5)], sin, w, color=ROJO, label="Sin índices")
    ax.bar([i + w / 2 for i in range(5)], con, w, color=AZUL, label="Con índices")
    ax.set_xticks(range(5))
    ax.set_xticklabels(["C1", "C2", "C3", "C4", "C5"])
    ax.set_yscale("log")
    ax.set_ylabel("Tiempo promedio (ms, escala log)")
    ax.set_title("Comparativo con 1 000 000 de registros", fontsize=10)
    ax.grid(axis="y", which="both", ls=":", lw=0.6, alpha=0.6)
    ax.legend(fontsize=8)
    for i, (a, b) in enumerate(zip(sin, con)):
        ax.text(i - w / 2, a * 1.12, "%.1f" % a, ha="center", fontsize=7)
        ax.text(i + w / 2, b * 1.12, "%.1f" % b, ha="center", fontsize=7)
    guardar(fig, "comparativo1m.png")

    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.3), sharey=True)
    for ax, cond, titulo in ((axs[0], "sin", "Sin índices"), (axs[1], "con", "Con índices")):
        for q in range(1, 6):
            ax.plot(range(4), [tab[(q, e, cond)] for e in ESC], marker="o", lw=1.4,
                    label="C%d" % q)
        ax.set_xticks(range(4))
        ax.set_xticklabels(ESC)
        ax.set_yscale("log")
        ax.set_title(titulo, fontsize=10)
        ax.grid(True, which="both", ls=":", lw=0.6, alpha=0.6)
    axs[0].set_ylabel("Tiempo promedio (ms, escala log)")
    axs[1].legend(fontsize=7, ncol=1, loc="upper left")
    guardar(fig, "escalamiento.png")

    fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.6))
    for ax, q in ((axs[0], 1), (axs[1], 5)):
        filas = [r for r in d["tipos_indice"] if r["consulta"] == q]
        nombres = [r["variante"].replace(" (", "\n(").replace(" sobre ", "\nsobre ")
                   for r in filas]
        valores = [r["promedio"] for r in filas]
        barras = ax.barh(range(len(filas)), valores, color=[AZUL, "#5dade2", "#a9cce3", ROJO])
        ax.set_yticks(range(len(filas)))
        ax.set_yticklabels(nombres, fontsize=7)
        ax.invert_yaxis()
        ax.set_xscale("log")
        ax.set_xlabel("Tiempo promedio (ms, escala log)", fontsize=8)
        ax.set_title("Consulta %d (1M)" % q, fontsize=10)
        ax.grid(axis="x", which="both", ls=":", lw=0.6, alpha=0.6)
        for b, v in zip(barras, valores):
            ax.text(v * 1.08, b.get_y() + b.get_height() / 2, "%.1f" % v, va="center",
                    fontsize=7)
    guardar(fig, "tipos_indice.png")

    fig, ax = plt.subplots(figsize=(6.4, 3.3))
    ops = []
    for r in d["escritura"]:
        if r["operacion"] not in ops:
            ops.append(r["operacion"])
    esc = {(r["operacion"], r["condicion"]): r["promedio"] for r in d["escritura"]}
    etiquetas = [o.replace(" de ", "\nde ", 1) for o in ops]
    ax.bar([i - w / 2 for i in range(len(ops))], [esc[(o, "sin")] for o in ops], w,
           color=ROJO, label="Sin índices de optimización")
    ax.bar([i + w / 2 for i in range(len(ops))], [esc[(o, "con")] for o in ops], w,
           color=AZUL, label="Con índices de optimización")
    ax.set_xticks(range(len(ops)))
    ax.set_xticklabels(etiquetas, fontsize=8)
    ax.set_ylabel("Tiempo promedio (ms)")
    ax.set_title("Costo de escritura con 1 000 000 de registros", fontsize=10)
    ax.grid(axis="y", ls=":", lw=0.6, alpha=0.6)
    ax.legend(fontsize=8)
    for i, o in enumerate(ops):
        ax.text(i - w / 2, esc[(o, "sin")] * 1.02, "%.0f" % esc[(o, "sin")], ha="center",
                fontsize=7)
        ax.text(i + w / 2, esc[(o, "con")] * 1.02, "%.0f" % esc[(o, "con")], ha="center",
                fontsize=7)
    guardar(fig, "escritura.png")
    print("figuras generadas en", FIG)


if __name__ == "__main__":
    main()
