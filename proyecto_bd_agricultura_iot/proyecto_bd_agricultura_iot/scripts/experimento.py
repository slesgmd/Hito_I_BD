#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Experimento de optimizacion.

Fase 1: 5 consultas x 4 escenarios x 2 condiciones x 5 iteraciones.
Fase 2 (1M): comparacion entre tipos de indice para las consultas 1 y 5.
Fase 3 (1M): costo de los indices en inserciones y actualizaciones.

Salidas: resultados/resultados.json, resultados/resultados.csv,
         resultados/planes_1M.txt
"""
import json, os, re, statistics, time
import psycopg2

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
SQL = os.path.join(RAIZ, "sql")
RES = os.path.join(RAIZ, "resultados")
ESC = [("1K", "agro1k", 1_000), ("10K", "agro10k", 10_000),
       ("100K", "agro100k", 100_000), ("1M", "agro1m", 1_000_000)]
IT = 5
APAGAR = "SET enable_indexscan = OFF; SET enable_bitmapscan = OFF; SET enable_indexonlyscan = OFF;"
PRENDER = "SET enable_indexscan = ON; SET enable_bitmapscan = ON; SET enable_indexonlyscan = ON;"


def conectar(db):
    con = psycopg2.connect(dbname=db, user=os.environ.get("PGUSER", "postgres"))
    con.autocommit = True
    return con


def leer_consultas():
    texto = open(os.path.join(SQL, "03_consultas.sql"), encoding="utf-8").read()
    partes = re.split(r"-- -+ CONSULTA \d+ -+\n", texto)[1:]
    out = ["\n".join(l for l in p.strip().splitlines() if not l.lstrip().startswith("--")).strip()
           for p in partes]
    assert len(out) == 5
    return out


def leer_indices():
    texto = open(os.path.join(SQL, "04_indices.sql"), encoding="utf-8").read()
    return texto, re.findall(r"CREATE INDEX IF NOT EXISTS (\w+)", texto)


def medir(cur, sql):
    cur.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql)
    plan = cur.fetchone()[0][0]
    return plan["Execution Time"], plan


def plan_texto(cur, sql):
    cur.execute("EXPLAIN (ANALYZE, COSTS OFF) " + sql)
    return "\n".join(r[0] for r in cur.fetchall())


def resumen(nodo, prof=0, acc=None):
    acc = [] if acc is None else acc
    e = ("Parallel " if nodo.get("Parallel Aware") else "") + nodo.get("Node Type", "")
    if nodo.get("Relation Name"):
        e += " on " + nodo["Relation Name"]
    if nodo.get("Index Name"):
        e += " using " + nodo["Index Name"]
    acc.append("  " * prof + "-> " + e)
    for h in nodo.get("Plans", []):
        resumen(h, prof + 1, acc)
    return acc


def serie(cur, sql, preparar, n=IT, vacuum="VACUUM (ANALYZE);"):
    t = []
    plan = None
    for _ in range(n):
        cur.execute(vacuum)
        cur.execute(preparar)
        v, plan = medir(cur, sql)
        t.append(round(v, 3))
    return t, plan


# ------------------------------------------------------------------ fase 1
def fase_consultas(consultas, texto_idx, nombres_idx, escenarios=None, condiciones=("sin", "con")):
    res, planes = [], []
    for etq, db, total in (escenarios or ESC):
        for cond in condiciones:
            con = conectar(db)
            cur = con.cursor()
            if cond == "sin":
                for ix in nombres_idx:
                    cur.execute("DROP INDEX IF EXISTS %s;" % ix)
            else:
                cur.execute(texto_idx)
            cur.execute("VACUUM (FULL, ANALYZE);")
            for q, sql in enumerate(consultas, start=1):
                t, plan = serie(cur, sql, APAGAR if cond == "sin" else PRENDER)
                res.append(dict(escenario=etq, registros=total, condicion=cond, consulta=q,
                                tiempos=t, promedio=round(statistics.mean(t), 4),
                                desviacion=round(statistics.stdev(t), 4),
                                filas=plan["Plan"].get("Actual Rows"),
                                plan="\n".join(resumen(plan["Plan"]))))
                if etq == "1M":
                    cur.execute(APAGAR if cond == "sin" else PRENDER)
                    planes.append(("Consulta %d - %s indices - 1 000 000 de registros"
                                   % (q, "sin" if cond == "sin" else "con"), plan_texto(cur, sql)))
                print("%-4s %-3s C%d  %10.3f ms  sd %8.3f" % (etq, cond, q, res[-1]["promedio"],
                                                             res[-1]["desviacion"]), flush=True)
            cur.close()
            con.close()
    return res, planes


# ------------------------------------------------------------------ fase 2
def fase_tipos(consultas, texto_idx):
    variantes = [
        (1, "Lectura_Suelo", ["DROP INDEX IF EXISTS idx_lectura_fecha;"], [
            ("B+ tree con INCLUDE (propuesto)",
             "CREATE INDEX v_idx ON Lectura_Suelo USING btree (fecha_hora) "
             "INCLUDE (id_dispositivo, humedad_pct);"),
            ("B+ tree simple", "CREATE INDEX v_idx ON Lectura_Suelo USING btree (fecha_hora);"),
            ("BRIN (32 paginas por rango)",
             "CREATE INDEX v_idx ON Lectura_Suelo USING brin (fecha_hora) "
             "WITH (pages_per_range = 32);"),
            ("Sin indice sobre fecha_hora", None)]),
        (5, "Evento_Riego", ["ALTER TABLE Evento_Riego DROP CONSTRAINT IF EXISTS uq_evento;",
                             "DROP INDEX IF EXISTS idx_evento_parcela_fecha;"], [
            ("B+ tree compuesto (zona, fecha)",
             "CREATE INDEX v_idx ON Evento_Riego USING btree "
             "(id_parcela, num_zona, fecha_hora_inicio);"),
            ("Hash sobre id_parcela", "CREATE INDEX v_idx ON Evento_Riego USING hash (id_parcela);"),
            ("B+ tree sobre fecha_hora_inicio",
             "CREATE INDEX v_idx ON Evento_Riego USING btree (fecha_hora_inicio);"),
            ("Sin indice sobre Evento_Riego", None)]),
    ]
    con = conectar("agro1m")
    cur = con.cursor()
    restaurar(cur, texto_idx)
    res = []
    for q, tabla, retirar, lista in variantes:
        for s in retirar:
            cur.execute(s)
        for nombre, ddl in lista:
            cur.execute("DROP INDEX IF EXISTS v_idx;")
            construccion, tam = 0.0, 0
            if ddl:
                t0 = time.perf_counter()
                cur.execute(ddl)
                construccion = time.perf_counter() - t0
                cur.execute("SELECT pg_relation_size('v_idx');")
                tam = cur.fetchone()[0]
            cur.execute("VACUUM ANALYZE %s;" % tabla)
            t, plan = serie(cur, consultas[q - 1], PRENDER)
            res.append(dict(consulta=q, variante=nombre, construccion_s=round(construccion, 3),
                            tamano_bytes=tam, tiempos=t, promedio=round(statistics.mean(t), 4),
                            desviacion=round(statistics.stdev(t), 4),
                            plan="\n".join(resumen(plan["Plan"]))))
            print("tipos C%d %-34s %10.3f ms  indice %8.1f KB  build %.2f s" %
                  (q, nombre, res[-1]["promedio"], tam / 1024, construccion), flush=True)
        cur.execute("DROP INDEX IF EXISTS v_idx;")
    cur.execute("ALTER TABLE Evento_Riego ADD CONSTRAINT uq_evento "
                "UNIQUE (id_parcela, num_zona, fecha_hora_inicio);")
    cur.execute(texto_idx)
    cur.execute("VACUUM ANALYZE;")
    cur.close()
    con.close()
    return res


# ------------------------------------------------------------------ fase 3
OPERACIONES = [
    ("Insercion de 20 000 lecturas", "Lectura_Suelo", """
INSERT INTO Lectura_Suelo (id_dispositivo, fecha_hora, humedad_pct, temperatura_c,
                           ph, conductividad_ds_m, bateria_pct)
SELECT s.ids[1 + (g % array_length(s.ids, 1))],
       TIMESTAMP '2026-09-16 00:00:00' + g * INTERVAL '1 minute',
       round((35 + random() * 40)::numeric, 2), round((15 + random() * 12)::numeric, 2),
       NULL, NULL, 90
FROM generate_series(1, 20000) g,
     (SELECT array_agg(id_dispositivo ORDER BY id_dispositivo) AS ids
        FROM Sensor WHERE tipo_sensor IN ('Humedad','Multiparametro','Conductividad')) s"""),
    ("Actualizacion de humedad (sensores 1 a 60)", "Lectura_Suelo", """
UPDATE Lectura_Suelo SET humedad_pct = humedad_pct + 0.5
WHERE id_dispositivo BETWEEN 1 AND 60 AND humedad_pct < 99"""),
    ("Insercion de 5 000 eventos de riego", "Evento_Riego", """
INSERT INTO Evento_Riego (id_sistema, id_parcela, num_zona, id_operario,
                          fecha_hora_inicio, duracion_min, volumen_litros, modo)
SELECT z.ps[1 + (g % z.n)], z.ps[1 + (g % z.n)], z.zs[1 + (g % z.n)], NULL,
       TIMESTAMP '2026-09-16 00:00:00' + g * INTERVAL '1 minute', 60, 50000, 'Manual'
FROM generate_series(1, 5000) g,
     (SELECT array_agg(id_parcela ORDER BY id_parcela, num_zona) AS ps,
             array_agg(num_zona  ORDER BY id_parcela, num_zona) AS zs,
             count(*)::int AS n
        FROM Zona_Manejo) z"""),
]


def fase_escritura(texto_idx, nombres_idx):
    con = conectar("agro1m")
    cur = con.cursor()
    res = []
    for cond in ("sin", "con"):
        if cond == "sin":
            for ix in nombres_idx:
                cur.execute("DROP INDEX IF EXISTS %s;" % ix)
        else:
            cur.execute(texto_idx)
        cur.execute("VACUUM (FULL, ANALYZE);")
        cur.execute(PRENDER)
        for nombre, tabla, sql in OPERACIONES:
            t, filas = [], None
            for _ in range(IT):
                cur.execute("VACUUM ANALYZE %s;" % tabla)
                cur.execute("BEGIN;")
                cur.execute("ALTER TABLE %s DISABLE TRIGGER USER;" % tabla)
                cur.execute("EXPLAIN (ANALYZE, FORMAT JSON) " + sql)
                plan = cur.fetchone()[0][0]
                cur.execute("ROLLBACK;")
                t.append(round(plan["Execution Time"], 3))
                hijos = plan["Plan"].get("Plans", [])
                filas = hijos[0].get("Actual Rows") if hijos else None
            res.append(dict(operacion=nombre, condicion=cond, filas=filas, tiempos=t,
                            promedio=round(statistics.mean(t), 4),
                            desviacion=round(statistics.stdev(t), 4)))
            print("escritura %-3s %-42s %10.3f ms" % (cond, nombre, res[-1]["promedio"]),
                  flush=True)
    cur.execute("""SELECT s.relname, s.indexrelname, pg_relation_size(s.indexrelid)
                   FROM pg_stat_user_indexes s ORDER BY 1, 2;""")
    indices = [dict(tabla=a, indice=b, bytes=c) for a, b, c in cur.fetchall()]
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    ajustes = {}
    for k in ("shared_buffers", "work_mem", "effective_cache_size",
              "max_parallel_workers_per_gather", "random_page_cost"):
        cur.execute("SHOW %s;" % k)
        ajustes[k] = cur.fetchone()[0]
    cur.close()
    con.close()
    return res, indices, version, ajustes


def restaurar(cur, texto_idx):
    """Deja agro1m en su estado nominal (por si una corrida previa se interrumpio)."""
    cur.execute("DROP INDEX IF EXISTS v_idx;")
    cur.execute("SELECT 1 FROM pg_constraint WHERE conname = 'uq_evento';")
    if cur.fetchone() is None:
        cur.execute("ALTER TABLE Evento_Riego ADD CONSTRAINT uq_evento "
                    "UNIQUE (id_parcela, num_zona, fecha_hora_inicio);")
    cur.execute(texto_idx)



def fase_reescritura(consultas):
    """Compara la consulta 5 original con su version reescrita en 1M."""
    def leer(nombre):
        texto = open(os.path.join(SQL, nombre), encoding="utf-8").read()
        return "\n".join(l for l in texto.splitlines() if not l.lstrip().startswith("--"))
    reescrita = leer("03b_consulta5_reescrita.sql")
    materializada = leer("03c_consulta5_materializada.sql")
    con = conectar("agro1m")
    cur = con.cursor()
    res = []
    for cond in ("sin", "con"):
        for nombre, sql in (("Original (EXISTS duplicado)", consultas[4]),
                            ("Reescrita (CTE en linea)", reescrita),
                            ("Reescrita (CTE MATERIALIZED)", materializada)):
            t, plan = serie(cur, sql, APAGAR if cond == "sin" else PRENDER)
            cur.execute(APAGAR if cond == "sin" else PRENDER)
            cur.execute(sql)
            filas = cur.fetchall()
            res.append(dict(condicion=cond, version=nombre, tiempos=t,
                            promedio=round(statistics.mean(t), 4),
                            desviacion=round(statistics.stdev(t), 4),
                            resultado=[list(map(str, r)) for r in filas]))
            print("reescritura %-3s %-28s %10.3f ms" % (cond, nombre, res[-1]["promedio"]),
                  flush=True)
    cur.close()
    con.close()
    return res

PARCIAL = os.path.join(RES, "parcial")


def guardar(nombre, obj):
    os.makedirs(PARCIAL, exist_ok=True)
    with open(os.path.join(PARCIAL, nombre + ".json"), "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)


def cargar_parcial(nombre):
    ruta = os.path.join(PARCIAL, nombre + ".json")
    return json.load(open(ruta, encoding="utf-8")) if os.path.exists(ruta) else None


def unir():
    r1, planes = [], []
    for etq, _, _ in ESC:
        for cond in ("sin", "con"):
            p = cargar_parcial("consultas_%s_%s" % (etq, cond))
            if p is None:
                raise SystemExit("falta la corrida %s %s" % (etq, cond))
            r1 += p["res"]
            planes += p["planes"]
    orden = {"sin": 0, "con": 1}
    planes.sort(key=lambda x: (x[0].split(" - ")[0], orden[x[0].split(" - ")[1].split()[0]]))
    r2 = cargar_parcial("tipos")
    e = cargar_parcial("escritura")
    salida = dict(consultas=r1, tipos_indice=r2, escritura=e["res"], indices=e["indices"],
                  version=e["version"], ajustes=e["ajustes"],
                  reescritura=cargar_parcial("reescritura") or [])
    with open(os.path.join(RES, "resultados.json"), "w", encoding="utf-8") as fh:
        json.dump(salida, fh, indent=1, ensure_ascii=False)
    with open(os.path.join(RES, "resultados.csv"), "w", encoding="utf-8") as fh:
        fh.write("escenario,registros,condicion,consulta,it1,it2,it3,it4,it5,promedio,desviacion\n")
        for r in r1:
            fh.write("%s,%d,%s,%d,%s,%.4f,%.4f\n" % (r["escenario"], r["registros"], r["condicion"],
                     r["consulta"], ",".join("%.3f" % x for x in r["tiempos"]),
                     r["promedio"], r["desviacion"]))
    with open(os.path.join(RES, "planes_1M.txt"), "w", encoding="utf-8") as fh:
        for titulo, texto in planes:
            fh.write("=" * 78 + "\n" + titulo + "\n" + "=" * 78 + "\n" + texto + "\n\n")
    print("resultados unidos en", RES)


def main(argv=None):
    """Sin argumentos corre todo. Con argumentos permite correr por tramos:
       consultas <1K|10K|100K|1M> <sin|con> | tipos | escritura | unir"""
    import sys
    argv = sys.argv[1:] if argv is None else argv
    os.makedirs(RES, exist_ok=True)
    consultas = leer_consultas()
    texto_idx, nombres_idx = leer_indices()
    tramos = []
    if not argv:
        tramos = [("consultas", e, c) for e, _, _ in ESC for c in ("sin", "con")]
        tramos += [("tipos",), ("escritura",), ("reescritura",), ("unir",)]
    else:
        tramos = [tuple(argv)]
    for t in tramos:
        if t[0] == "consultas":
            esc = [x for x in ESC if x[0] == t[1]]
            res, planes = fase_consultas(consultas, texto_idx, nombres_idx, esc, (t[2],))
            guardar("consultas_%s_%s" % (t[1], t[2]), dict(res=res, planes=planes))
        elif t[0] == "tipos":
            guardar("tipos", fase_tipos(consultas, texto_idx))
        elif t[0] == "escritura":
            res, indices, version, ajustes = fase_escritura(texto_idx, nombres_idx)
            guardar("escritura", dict(res=res, indices=indices, version=version, ajustes=ajustes))
        elif t[0] == "reescritura":
            guardar("reescritura", fase_reescritura(consultas))
        elif t[0] == "unir":
            unir()
    print("tramo terminado:", " ".join(argv) or "todo")


if __name__ == "__main__":
    main()
