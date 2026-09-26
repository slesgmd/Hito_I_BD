#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arma informe/informe.tex a partir de las plantillas, los scripts SQL, los
resultados del experimento y el catalogo de PostgreSQL (bases agro1k..agro1m).
Uso: python construir_informe.py
"""
import json, math, os, platform, re
import psycopg2

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
SQL, RES, INF = (os.path.join(RAIZ, x) for x in ("sql", "resultados", "informe"))
ESC = ["1K", "10K", "100K", "1M"]
BD = dict(zip(ESC, ["agro1k", "agro10k", "agro100k", "agro1m"]))
TABLAS = ["Fundo", "Parcela", "Zona_Manejo", "Cultivo", "Operario", "Campania", "Sistema_Riego",
          "Dispositivo", "Sensor", "Controlador", "Lectura_Suelo", "Evento_Riego", "Alerta",
          "Cosecha", "Insumo", "Aplicacion_Insumo", "Mantenimiento", "Auditoria_Campania"]
NOMBRE = {t.lower(): t for t in TABLAS}
REL_CLAVE = {1: "lectura_suelo", 2: "evento_riego", 3: "lectura_suelo", 4: "cosecha",
             5: "evento_riego"}


def conectar(db):
    c = psycopg2.connect(dbname=db, user=os.environ.get("PGUSER", "postgres"))
    c.autocommit = True
    return c


def esc(s):
    s = str(s)
    s = s.replace("\\", "\x00")
    for a, b in (("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"), ("_", r"\_"),
                 ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"),
                 ("^", r"\textasciicircum{}")):
        s = s.replace(a, b)
    return s.replace("\x00", r"\textbackslash{}")


def num(x, d=2):
    return ("{:,.%df}" % d).format(x).replace(",", "\\,")


def ms(x):
    return num(x, 3 if x < 10 else 2)


def listado(texto, estilo="sql", titulo=None):
    if estilo == "plano":   # reduce la sangria de los planes para que quepan en la pagina
        texto = "\n".join(re.sub(r"^( +)", lambda m: " " * (len(m.group(1)) // 3), l)
                          for l in texto.splitlines())
    cab = "[style=%s%s]" % (estilo, (", title={%s}" % titulo) if titulo else "")
    return "\\begin{lstlisting}%s\n%s\n\\end{lstlisting}\n" % (cab, texto.rstrip())


def tabla(cols, filas, caption, label=None, ancho=None, chico=True, resize=False):
    cuerpo = "\\toprule\n" + " & ".join(cols) + " \\\\\n\\midrule\n"
    cuerpo += "\n".join(" & ".join(f) + " \\\\" for f in filas) + "\n\\bottomrule\n"
    spec = ancho or ("l" + "r" * (len(cols) - 1))
    t = "\\begin{tabular}{%s}\n%s\\end{tabular}" % (spec, cuerpo)
    if resize:
        t = "\\resizebox{\\textwidth}{!}{%s}" % t
    return ("\\begin{table}[H]\n\\centering%s\n%s\n\\caption{%s}%s\n\\end{table}\n" %
            ("\\small" if chico else "", t, caption, ("\\label{%s}" % label) if label else ""))


# ------------------------------------------------------------------ catalogo
def columnas(cur, t):
    cur.execute("""SELECT a.attnum, a.attname, format_type(a.atttypid, a.atttypmod), a.attnotnull,
                          pg_get_expr(d.adbin, d.adrelid), col_description(a.attrelid, a.attnum)
                   FROM pg_attribute a LEFT JOIN pg_attrdef d
                        ON d.adrelid = a.attrelid AND d.adnum = a.attnum
                   WHERE a.attrelid = %s::regclass AND a.attnum > 0 AND NOT a.attisdropped
                   ORDER BY a.attnum""", (t,))
    return cur.fetchall()


def restricciones(cur, t, tipo):
    cur.execute("""SELECT conname, conkey, confrelid::regclass::text, pg_get_constraintdef(oid)
                   FROM pg_constraint WHERE conrelid = %s::regclass AND contype = %s
                   ORDER BY conname""", (t, tipo))
    return cur.fetchall()


def tipo_sql(ft, defecto):
    t = ft.replace("character varying", "varchar").replace("timestamp without time zone",
                                                          "timestamp").upper()
    if defecto and defecto.startswith("nextval("):
        t = {"INTEGER": "SERIAL", "BIGINT": "BIGSERIAL"}.get(t, t)
    return t


def info_tabla(cur, t):
    cols = columnas(cur, t)
    nombres = {c[0]: c[1] for c in cols}
    pk = set()
    for _, k, _, _ in restricciones(cur, t, "p"):
        pk |= {nombres[x] for x in k}
    fk = {}
    for _, k, ref, _ in restricciones(cur, t, "f"):
        for x in k:
            fk[nombres[x]] = NOMBRE.get(ref.lower(), ref)
    uq = set()
    for _, k, _, _ in restricciones(cur, t, "u"):
        uq |= {nombres[x] for x in k}
    checks = [(n, re.sub(r"::(character varying|text|numeric|integer|bigint|smallint|date|"
                         r"timestamp without time zone)(\[\])?", "", d))
              for n, _, _, d in restricciones(cur, t, "c")]
    return cols, pk, fk, uq, checks


def esquema_relacional(cur):
    out = ["\\begin{itemize}[leftmargin=1.2em,itemsep=0.3em]"]
    for t in TABLAS:
        cols, pk, fk, _, _ = info_tabla(cur, t)
        partes = []
        for c in cols:
            s = esc(c[1])
            if c[1] in fk:
                s = "\\fk{%s}{%s}" % (s, esc(fk[c[1]]))
            if c[1] in pk:
                s = "\\pk{%s}" % s
            partes.append(s)
        out.append("\\item \\textsc{%s}(%s)" % (esc(t), ", ".join(partes)))
    out.append("\\end{itemize}")
    return "\n".join(out)


def diccionario(cur):
    out = []
    for t in TABLAS:
        cols, pk, fk, uq, checks = info_tabla(cur, t)
        cur.execute("SELECT obj_description(%s::regclass, 'pg_class')", (t,))
        desc = cur.fetchone()[0] or ""
        out.append("\\subsubsection*{%s}\n%s\n" % (esc(t), esc(desc)))
        out.append("{\\footnotesize\n\\begin{longtable}{>{\\raggedright\\arraybackslash}p{3.3cm}"
                   ">{\\raggedright\\arraybackslash}p{2.5cm}c>{\\raggedright\\arraybackslash}p{2.2cm}"
                   ">{\\raggedright\\arraybackslash}p{6.1cm}}\n\\toprule\n\\textbf{Columna} & "
                   "\\textbf{Tipo} & \\textbf{Nulo} & \\textbf{Clave} & \\textbf{Descripción} "
                   "\\\\\n\\midrule\n\\endhead\n")
        for _, nombre, ft, notnull, defecto, com in cols:
            claves = []
            if nombre in pk:
                claves.append("PK")
            if nombre in fk:
                claves.append("FK $\\to$ " + esc(fk[nombre]))
            if nombre in uq and nombre not in pk:
                claves.append("UQ")
            d = esc(com or "")
            if defecto and not defecto.startswith("nextval("):
                d += " Por defecto: \\texttt{%s}." % esc(defecto.split("::")[0])
            out.append("\\texttt{%s} & %s & %s & %s & %s \\\\\n" % (
                esc(nombre), esc(tipo_sql(ft, defecto)), "No" if notnull else "Sí",
                ", ".join(claves), d))
        out.append("\\bottomrule\n\\end{longtable}}\n")
        if checks:
            out.append("{\\footnotesize\\textbf{Restricciones CHECK:} " + "; ".join(
                "\\tb{%s}: \\tb{%s}" % (esc(n), esc(d.replace("CHECK ", "")))
                for n, d in checks) + "\\par}\n\\medskip\n")
    return "".join(out)


# ------------------------------------------------------------------ SQL
def leer(nombre):
    return open(os.path.join(SQL, nombre), encoding="utf-8").read()


def bloque_02(clave):
    lineas = leer("02_vistas_procedimientos_triggers.sql").splitlines()
    pos = {}
    for i, l in enumerate(lineas):
        for k, patron in (("A", "-- A. "), ("B", "-- B. "), ("C", "-- C. "), ("D", "-- D. "),
                          ("D1", "-- D.1 "), ("D2", "-- D.2 ")):
            if l.startswith(patron):
                pos[k] = i
    rangos = {"A": (pos["A"] - 1, pos["B"] - 1), "B": (pos["B"] - 1, pos["C"] - 1),
              "C": (pos["C"] - 1, pos["D"] - 1), "D1": (pos["D"] - 1, pos["D2"]),
              "D2": (pos["D2"], len(lineas))}
    a, b = rangos[clave]
    return "\n".join(lineas[a:b]).strip()


def consulta(q):
    partes = re.split(r"(-- -+ CONSULTA \d+ -+\n)", leer("03_consultas.sql"))
    return partes[2 * q].strip()


def indices(q):
    partes = re.split(r"(-- ---- Consulta \d+[^\n]*\n)", leer("04_indices.sql"))
    for i in range(1, len(partes), 2):
        if partes[i].startswith("-- ---- Consulta %d" % q):
            return (partes[i] + partes[i + 1]).strip()
    return ""


# ------------------------------------------------------------------ resultados
def planes():
    texto = open(os.path.join(RES, "planes_1M.txt"), encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"=+\nConsulta (\d) - (sin|con)[^\n]*\n=+\n(.*?)(?=\n=+\nConsulta|\Z)",
                         texto, re.S):
        out[(int(m.group(1)), m.group(2))] = m.group(3).strip()
    return out


def acceso(plan, q):
    rel = REL_CLAVE[q]
    for l in plan.splitlines():
        if " on " + rel in l:
            nodo = l.strip().lstrip("-> ").split(" on ")[0].split(" using ")[0]
            m = re.search(r"using (\w+)", l)
            abrev = {"Seq Scan": "Seq", "Parallel Seq Scan": "Seq paralelo",
                     "Index Only Scan": "Index Only", "Index Scan": "Index",
                     "Bitmap Heap Scan": "Bitmap"}.get(nodo, nodo)
            s = abrev + (" (%s)" % esc(m.group(1)) if m else "")
            if "Memoize" in plan and "Index" in nodo:
                s = "Nested Loop + " + s
            return s
    return "--"


def main():
    d = json.load(open(os.path.join(RES, "resultados.json"), encoding="utf-8"))
    carga = json.load(open(os.path.join(RES, "carga.json"), encoding="utf-8"))
    tab = {(r["consulta"], r["escenario"], r["condicion"]): r for r in d["consultas"]}
    rep = {}

    con = conectar("agro1m")
    cur = con.cursor()

    # ---- marcadores de la seccion 1
    cur.execute("SELECT count(*) FROM Fundo")
    rep["@@FUNDOS@@"] = str(cur.fetchone()[0])
    cur.execute("SELECT count(*), round(sum(area_ha)) FROM Parcela")
    n, area = cur.fetchone()
    rep["@@PARCELAS@@"], rep["@@AREA@@"] = num(n, 0), num(float(area), 0)
    cur.execute("SELECT count(*) FROM Zona_Manejo")
    rep["@@ZONAS@@"] = num(cur.fetchone()[0], 0)
    cur.execute("SELECT (SELECT count(*) FROM Sensor), (SELECT count(*) FROM Controlador)")
    ns, nc = cur.fetchone()
    rep["@@SENSORES@@"], rep["@@CONTROLADORES@@"] = num(ns, 0), num(nc, 0)
    cur.execute("SELECT pg_database_size(current_database())")
    rep["@@TAM1M@@"] = num(cur.fetchone()[0] / 1048576, 1) + "~MB"
    cur.execute("""SELECT c.relname, c.reltuples::bigint, pg_relation_size(c.oid),
                          pg_indexes_size(c.oid), pg_total_relation_size(c.oid)
                   FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                   WHERE n.nspname = 'public' AND c.relkind = 'r'
                   ORDER BY pg_total_relation_size(c.oid) DESC""")
    tams = cur.fetchall()
    total = sum(t[4] for t in tams)
    lect = [t for t in tams if t[0] == "lectura_suelo"][0]
    cur.execute("SELECT count(*) FROM Lectura_Suelo")
    nlect = cur.fetchone()[0]
    bpl = lect[4] / nlect
    rep["@@PCTLECT@@"] = num(100 * lect[4] / total, 1) + "~\\%"
    rep["@@BYTESLECT@@"] = num(bpl, 0)
    anio = ns * 96 * 365
    rep["@@LECTANIO@@"] = num(anio / 1e6, 1)
    rep["@@GBANIO@@"] = num(anio * bpl / 1e9, 1)
    filas = []
    for t in tams[:8]:
        filas.append([esc(NOMBRE.get(t[0], t[0])), num(t[1], 0), num(t[2] / 1048576, 1),
                      num(t[3] / 1048576, 1), num(t[4] / 1048576, 1)])
    resto = tams[8:]
    filas.append(["Otras %d tablas" % len(resto), num(sum(t[1] for t in resto), 0),
                  num(sum(t[2] for t in resto) / 1048576, 1),
                  num(sum(t[3] for t in resto) / 1048576, 1),
                  num(sum(t[4] for t in resto) / 1048576, 1)])
    filas.append(["\\textbf{Total}", "", "", "", "\\textbf{%s}" % num(total / 1048576, 1)])
    rep["%%TABLA_TAMANOS%%"] = tabla(["Tabla", "Filas", "Datos (MB)", "Índices (MB)",
                                      "Total (MB)"], filas,
                                     "Espacio ocupado por tabla en el escenario de un millón.",
                                     "tab:tamanos")

    # ---- modelo relacional y diccionario
    rep["%%ESQUEMA_RELACIONAL%%"] = esquema_relacional(cur)
    rep["%%DICCIONARIO%%"] = diccionario(cur)

    # ---- listados SQL
    for nombre in ("01_ddl.sql", "07_verificacion.sql", "03c_consulta5_materializada.sql"):
        rep["%%SQL_ARCHIVO:" + nombre + "%%"] = listado(leer(nombre), titulo=esc(nombre))
    for k in ("A", "B", "C", "D1", "D2"):
        rep["%%SQL_BLOQUE:" + k + "%%"] = listado(bloque_02(k))
    for q in range(1, 6):
        rep["%%%%CONSULTA:%d%%%%" % q] = listado(consulta(q), titulo="Consulta %d" % q)
        rep["%%%%INDICES:%d%%%%" % q] = listado(indices(q))

    # ---- carga
    orden = ["Fundo", "Cultivo", "Insumo", "Operario", "Parcela", "Zona_Manejo", "Sistema_Riego",
             "Campania", "Dispositivo", "Sensor", "Controlador", "Lectura_Suelo", "Alerta",
             "Evento_Riego", "Cosecha", "Aplicacion_Insumo", "Mantenimiento"]
    c = {x["escenario"]: x for x in carga}
    filas = [[esc(t)] + [num(c[e]["filas"][t], 0) for e in ESC] for t in orden]
    filas.append(["\\textbf{Total}"] + ["\\textbf{%s}" % num(c[e]["registros"], 0) for e in ESC])
    filas.append(["\\midrule Generación de CSV (s)"] + [num(c[e]["generacion_s"], 1) for e in ESC])
    filas.append(["Carga con COPY (s)"] + [num(c[e]["copy_s"], 1) for e in ESC])
    filas.append(["Creación de índices (s)"] + [num(c[e]["indices_s"], 1) for e in ESC])
    filas.append(["Tamaño de la base (MB)"] + [num(c[e]["tamano_bytes"] / 1048576, 1) for e in ESC])
    rep["%%TABLA_CARGA%%"] = tabla(["Tabla"] + ESC, filas,
                                   "Filas por tabla y tiempos de carga por escenario.", "tab:carga")

    # ---- verificacion
    etiquetas = ["Riegos con el sistema de otra parcela", "Controladores de otra parcela",
                 "Parcelas con dos campañas vigentes", "Campañas superpuestas",
                 "Cosechas anteriores a la siembra", "Cosechas en campañas perdidas",
                 "Dispositivos fuera de la jerarquía Is-A", "Rendimientos desactualizados"]
    res = {}
    for e in ESC:
        cx = conectar(BD[e])
        cu = cx.cursor()
        cu.execute(leer("07_verificacion.sql"))
        res[e] = cu.fetchone()
        cx.close()
    filas = [[etiquetas[i]] + [str(res[e][i]) for e in ESC] for i in range(len(etiquetas))]
    rep["%%VERIFICACION%%"] = tabla(["Regla verificada (violaciones)"] + ESC, filas,
                                    "Resultado de la verificación de consistencia.",
                                    "tab:verificacion")

    # ---- nulos
    cur.execute("""SELECT s.tipo_sensor, count(*),
        round(100.0 * count(*) FILTER (WHERE humedad_pct IS NULL) / count(*), 1),
        round(100.0 * count(*) FILTER (WHERE temperatura_c IS NULL) / count(*), 1),
        round(100.0 * count(*) FILTER (WHERE ph IS NULL) / count(*), 1),
        round(100.0 * count(*) FILTER (WHERE conductividad_ds_m IS NULL) / count(*), 1),
        round(100.0 * count(*) FILTER (WHERE bateria_pct IS NULL) / count(*), 1)
        FROM Lectura_Suelo l JOIN Sensor s USING (id_dispositivo) GROUP BY 1 ORDER BY 2 DESC""")
    filas = [[esc(r[0]), num(r[1], 0)] + ["%s" % num(float(x), 1) for x in r[2:]]
             for r in cur.fetchall()]
    rep["%%NULOS%%"] = tabla(["Tipo de sensor", "Lecturas", "Humedad", "Temp.", "pH", "CE",
                              "Batería"], filas,
                             "Porcentaje de valores nulos por variable y tipo de sensor (1M). "
                             "Un 100~\\% indica un nulo estructural.", "tab:nulos")

    # ---- vistas
    for v in ("vw_estado_hidrico_zona", "vw_produccion_campania", "vw_alertas_pendientes"):
        cur.execute("SELECT * FROM %s LIMIT 5" % v)
        cols = [esc(x.name) for x in cur.description]
        filas = [[esc(x) if x is not None else "--" for x in r] for r in cur.fetchall()]
        rep["%%VISTA:" + v + "%%"] = tabla(["\\texttt{%s}" % x for x in cols], filas,
                                           "Primeras filas de \\tb{%s}." % esc(v),
                                           ancho="l" * len(cols), resize=True)

    # ---- pruebas
    pr = open(os.path.join(RES, "pruebas.txt"), encoding="utf-8").read()
    pr = re.sub(r"psql:06_pruebas\.sql:\d+: ", "", pr)
    rep["%%PRUEBAS%%"] = listado(pr, "plano")

    # ---- plataforma
    cpu = platform.processor() or platform.machine()
    ram = ""
    try:
        for l in open("/proc/cpuinfo"):
            if l.startswith("model name"):
                cpu = l.split(":", 1)[1].strip()
                break
        for l in open("/proc/meminfo"):
            if l.startswith("MemTotal"):
                ram = num(int(l.split()[1]) / 1048576, 1) + " GB"
    except OSError:
        pass
    so = platform.platform()
    try:
        for l in open("/etc/os-release"):
            if l.startswith("PRETTY_NAME"):
                so = l.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    a = d["ajustes"]
    filas = [["Procesador", esc(cpu)], ["Núcleos disponibles", str(os.cpu_count())],
             ["Memoria RAM", ram or "--"], ["Sistema operativo", esc(so)],
             ["Gestor de base de datos", esc(d["version"].split(" on ")[0])],
             ["shared\\_buffers / work\\_mem", "%s / %s" % (a["shared_buffers"], a["work_mem"])],
             ["effective\\_cache\\_size", a["effective_cache_size"]],
             ["max\\_parallel\\_workers\\_per\\_gather", a["max_parallel_workers_per_gather"]],
             ["random\\_page\\_cost", a["random_page_cost"]],
             ["Cliente", "Python %s, psycopg2 %s" % (platform.python_version(),
                                                    psycopg2.__version__.split()[0])]]
    rep["%%PLATAFORMA%%"] = tabla(["Componente", "Especificación"], filas,
                                  "Plataforma de pruebas.", "tab:plataforma", ancho="ll")

    # ---- iteraciones
    for cond, txt in (("sin", "sin índices"), ("con", "con índices")):
        for q in range(1, 6):
            filas = []
            for e in ESC:
                r = tab[(q, e, cond)]
                filas.append([e] + [ms(x) for x in r["tiempos"]] +
                             ["\\textbf{%s}" % ms(r["promedio"]), ms(r["desviacion"])])
            rep["%%%%TABLA_ITER:%s:%d%%%%" % (cond, q)] = tabla(
                ["Escenario", "It. 1", "It. 2", "It. 3", "It. 4", "It. 5", "Promedio", "Desv. est."],
                filas, "Consulta %d %s: tiempo de ejecución por iteración (ms)." % (q, txt),
                "tab:%s%d" % (cond, q))

    # ---- resumen por consulta y global
    def rel(s, c):
        f = s / c
        return num(f, 2) + ("" if f >= 1 else " (más lenta)")
    for q in range(1, 6):
        filas = [[e, ms(tab[(q, e, "sin")]["promedio"]), ms(tab[(q, e, "con")]["promedio"]),
                  rel(tab[(q, e, "sin")]["promedio"], tab[(q, e, "con")]["promedio"]),
                  str(tab[(q, e, "con")]["filas"])] for e in ESC]
        rep["%%%%RESUMEN_Q:%d%%%%" % q] = tabla(
            ["Escenario", "Sin índices (ms)", "Con índices (ms)", "Relación sin/con",
             "Filas devueltas"], filas, "Consulta %d: promedios y relación de mejora." % q)
    filas = [["C%d" % q] + [num(tab[(q, e, "sin")]["promedio"] / tab[(q, e, "con")]["promedio"], 2)
                            for e in ESC] for q in range(1, 6)]
    rep["%%TABLA_RESUMEN%%"] = tabla(["Consulta"] + ESC, filas,
                                     "Relación entre el tiempo sin índices y con índices. "
                                     "Un valor mayor que 1 indica mejora.", "tab:resumen")

    pl = planes()
    filas = []
    for q in range(1, 6):
        for cond in ("sin", "con"):
            fila = ["C%d" % q if cond == "sin" else "", cond]
            for e in ESC:
                txt = pl[(q, cond)] if e == "1M" else tab[(q, e, cond)]["plan"]
                fila.append(acceso(txt, q))
            filas.append(fila)
    rep["%%TABLA_PLANES%%"] = tabla(
        ["Consulta", "Índices"] + ESC, filas,
        "Método de acceso a la tabla principal de cada consulta (C1 y C3: lecturas; C2 y C5: "
        "riegos; C4: cosechas).", "tab:planes",
        ancho="llp{3.1cm}p{3.1cm}p{3.1cm}p{3.1cm}", resize=True)
    for q in range(1, 6):
        for cond in ("sin", "con"):
            rep["%%%%PLAN:%d:%s%%%%" % (q, cond)] = listado(pl[(q, cond)], "plano")

    # ---- tipos de indice
    base = {q: [r for r in d["tipos_indice"] if r["consulta"] == q][-1]["promedio"] for q in (1, 5)}
    filas = []
    for r in d["tipos_indice"]:
        filas.append(["C%d" % r["consulta"], esc(r["variante"]),
                      num(r["construccion_s"], 2) if r["tamano_bytes"] else "--",
                      num(r["tamano_bytes"] / 1024, 0) if r["tamano_bytes"] else "--",
                      "\\textbf{%s}" % ms(r["promedio"]), ms(r["desviacion"]),
                      num(base[r["consulta"]] / r["promedio"], 1)])
    rep["%%TABLA_TIPOS%%"] = tabla(["Consulta", "Variante", "Construcción (s)", "Tamaño (KB)",
                                    "Promedio (ms)", "Desv. (ms)", "Mejora"], filas,
                                   "Comparación entre tipos de índice con un millón de registros. "
                                   "La mejora se calcula contra la variante sin índice.",
                                   "tab:tipos", ancho="llrrrrr", resize=True)

    # ---- escritura
    ops = []
    for r in d["escritura"]:
        if r["operacion"] not in ops:
            ops.append(r["operacion"])
    e2 = {(r["operacion"], r["condicion"]): r for r in d["escritura"]}
    filas = []
    for o in ops:
        s, c2 = e2[(o, "sin")], e2[(o, "con")]
        filas.append([esc(o), num(c2["filas"] or 0, 0), ms(s["promedio"]), ms(s["desviacion"]),
                      ms(c2["promedio"]), ms(c2["desviacion"]),
                      "+" + num(100 * (c2["promedio"] / s["promedio"] - 1), 0) + "~\\%"])
    rep["%%TABLA_ESCRITURA%%"] = tabla(["Operación", "Filas", "Sin (ms)", "Desv.", "Con (ms)",
                                        "Desv.", "Sobrecosto"], filas,
                                       "Costo de escritura con y sin los índices de optimización "
                                       "(1M, 5 iteraciones).", "tab:escritura",
                                       ancho="lrrrrrr", resize=True)
    cur.execute("""SELECT t.relname, i.relname, am.amname, pg_relation_size(i.oid),
                          x.indisprimary, x.indisunique
                   FROM pg_index x JOIN pg_class i ON i.oid = x.indexrelid
                   JOIN pg_class t ON t.oid = x.indrelid JOIN pg_am am ON am.oid = i.relam
                   JOIN pg_namespace n ON n.oid = t.relnamespace
                   WHERE n.nspname = 'public' AND t.relname IN ('lectura_suelo','evento_riego',
                         'alerta','cosecha','campania','dispositivo')
                   ORDER BY t.relname, pg_relation_size(i.oid) DESC""")
    filas = [[esc(NOMBRE[r[0]]), "\\texttt{%s}" % esc(r[1]),
              {"btree": "B+ tree", "hash": "Hash", "brin": "BRIN"}.get(r[2], r[2]),
              num(r[3] / 1024, 0), "Clave primaria" if r[4] else ("UNIQUE" if r[5] else
                                                                  "Optimización")]
             for r in cur.fetchall()]
    rep["%%TABLA_INDICES_TAM%%"] = tabla(["Tabla", "Índice", "Tipo", "Tamaño (KB)", "Origen"],
                                         filas, "Índices de las tablas involucradas (1M).",
                                         "tab:tamidx", ancho="lllrl")

    # ---- reescritura
    r4 = d.get("reescritura", [])
    en_linea = [x for x in r4 if "MATERIALIZED" not in x["version"]]
    mat = [x for x in r4 if "MATERIALIZED" in x["version"]]
    if not mat:   # medicion previa guardada aparte (solo si la fase 4 no la incluyo)
        ruta = os.path.join(RES, "parcial", "reescritura_mat.json")
        mat = json.load(open(ruta, encoding="utf-8")) if os.path.exists(ruta) else []

    def buscar(lista, cond, inicio):
        for x in lista:
            if x["condicion"] == cond and x["version"].startswith(inicio):
                return x
    filas = []
    for nombre, lista, clave in (("Original (EXISTS en dos lugares)", en_linea, "Original"),
                                 ("CTE en línea", en_linea, "Reescrita"),
                                 ("CTE con \\texttt{AS MATERIALIZED}", mat, "Reescrita")):
        s, c2 = buscar(lista, "sin", clave), buscar(lista, "con", clave)
        if not s or not c2:
            continue
        filas.append([nombre, "%s (%d it.)" % (ms(s["promedio"]), len(s["tiempos"])),
                      "%s (%d it.)" % (ms(c2["promedio"]), len(c2["tiempos"]))])
    rep["%%TABLA_REESCRITURA%%"] = tabla(["Versión de la consulta 5", "Sin índices (ms)",
                                          "Con índices (ms)"], filas,
                                         "Efecto de reescribir la consulta 5 (1M). Las tres "
                                         "versiones devuelven exactamente las mismas filas.",
                                         "tab:reescritura", ancho="lrr")

    # ---- crecimiento
    filas = []
    for q in range(1, 6):
        for cond in ("sin", "con"):
            t = [tab[(q, e, cond)]["promedio"] for e in ESC]
            filas.append(["C%d" % q if cond == "sin" else "", cond] +
                         [num(t[i + 1] / t[i], 1) for i in range(3)] +
                         [num(math.log10(t[3] / t[2]), 2)])
    rep["%%TABLA_CRECIMIENTO%%"] = tabla(["Consulta", "Índices", "1K$\\to$10K", "10K$\\to$100K",
                                          "100K$\\to$1M", "Exponente $b$"], filas,
                                         "Factor de crecimiento del tiempo cuando los datos se "
                                         "multiplican por diez.", "tab:crecimiento",
                                         ancho="llrrrr")

    # ---- dumps y generador
    filas = []
    for e in ESC:
        ruta = os.path.join(RAIZ, "dumps", "agro_%s.dump" % e)
        if os.path.exists(ruta):
            filas.append(["\\texttt{agro\\_%s.dump}" % e, num(c[e]["registros"], 0),
                          num(os.path.getsize(ruta) / 1048576, 2)])
    rep["%%TABLA_DUMPS%%"] = tabla(["Archivo", "Registros", "Tamaño (MB)"], filas,
                                   "Respaldos entregados.", "tab:dumps", ancho="lrr")
    rep["%%CODIGO_GENERADOR%%"] = listado(open(os.path.join(AQUI, "generar_datos.py"),
                                               encoding="utf-8").read(), "py")
    cur.close()
    con.close()

    texto = "".join(open(os.path.join(INF, p), encoding="utf-8").read()
                    for p in ("plantilla_1.tex", "plantilla_2.tex"))
    for k, v in rep.items():
        texto = texto.replace(k, v)
    faltan = sorted(set(re.findall(r"%%[A-Z_]+[^%\n]*%%|@@[A-Z0-9]+@@", texto)))
    with open(os.path.join(INF, "informe.tex"), "w", encoding="utf-8") as fh:
        fh.write(texto)
    print("informe.tex generado; marcadores sin reemplazar:", faltan or "ninguno")


if __name__ == "__main__":
    main()
