#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orquestador del proyecto. Funciona en Windows, Linux y macOS.

Requisitos: PostgreSQL 16 o superior, Python 3.10+, psycopg2-binary y matplotlib
    pip install psycopg2-binary matplotlib

Conexion: variables estandar de PostgreSQL (PGHOST, PGPORT, PGUSER, PGPASSWORD).
En Windows, por ejemplo:
    set PGUSER=postgres
    set PGPASSWORD=tu_clave

Uso:
    python ejecutar_todo.py cargar        genera los datos y crea agro1k ... agro1m
    python ejecutar_todo.py experimento   corre todas las mediciones (unos 10 min)
    python ejecutar_todo.py graficos      genera las figuras del informe
    python ejecutar_todo.py todo          las tres fases en orden
"""
import json, os, sys, time
import psycopg2

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
SQL = os.path.join(RAIZ, "sql")
DATOS = os.path.join(RAIZ, "datos")
RES = os.path.join(RAIZ, "resultados")
sys.path.insert(0, AQUI)

ESCENARIOS = [("1K", "agro1k", 1_000), ("10K", "agro10k", 10_000),
              ("100K", "agro100k", 100_000), ("1M", "agro1m", 1_000_000)]

ORDEN_CARGA = ["fundo", "cultivo", "insumo", "operario", "parcela", "zona_manejo",
               "sistema_riego", "campania", "dispositivo", "sensor", "controlador",
               "lectura_suelo", "alerta", "evento_riego", "cosecha",
               "aplicacion_insumo", "mantenimiento"]

SECUENCIAS = [("fundo", "id_fundo"), ("parcela", "id_parcela"), ("cultivo", "id_cultivo"),
              ("operario", "id_operario"), ("campania", "id_campania"),
              ("sistema_riego", "id_sistema"), ("dispositivo", "id_dispositivo"),
              ("evento_riego", "id_evento"), ("alerta", "id_alerta"),
              ("cosecha", "id_cosecha"), ("insumo", "id_insumo")]

RECALCULO_RENDIMIENTO = """
UPDATE Campania ca
   SET rendimiento_kg_ha = ROUND(t.kilos / p.area_ha, 2)
  FROM (SELECT id_campania, SUM(cantidad_kg) AS kilos
          FROM Cosecha GROUP BY id_campania) t,
       Parcela p
 WHERE t.id_campania = ca.id_campania
   AND p.id_parcela  = ca.id_parcela;
"""


def conectar(db="postgres"):
    con = psycopg2.connect(dbname=db, user=os.environ.get("PGUSER", "postgres"))
    con.autocommit = True
    return con


def ejecutar_archivo(cur, nombre):
    with open(os.path.join(SQL, nombre), encoding="utf-8") as fh:
        cur.execute(fh.read())


def cargar():
    import generar_datos
    os.makedirs(RES, exist_ok=True)
    bitacora = []
    for etiqueta, db, total in ESCENARIOS:
        carpeta = os.path.join(DATOS, etiqueta)
        t0 = time.perf_counter()
        conteo = generar_datos.generar(total, carpeta)
        t_gen = time.perf_counter() - t0

        con = conectar("postgres")
        cur = con.cursor()
        cur.execute("DROP DATABASE IF EXISTS %s;" % db)
        cur.execute("CREATE DATABASE %s ENCODING 'UTF8' TEMPLATE template0;" % db)
        cur.close()
        con.close()

        con = conectar(db)
        cur = con.cursor()
        ejecutar_archivo(cur, "01_ddl.sql")
        ejecutar_archivo(cur, "01b_comentarios.sql")

        t0 = time.perf_counter()
        for tabla in ORDEN_CARGA:
            with open(os.path.join(carpeta, tabla + ".csv"), encoding="utf-8") as fh:
                cur.copy_expert("COPY %s FROM STDIN WITH (FORMAT csv, HEADER true, NULL '')"
                                % tabla, fh)
        t_copy = time.perf_counter() - t0

        for tabla, col in SECUENCIAS:
            cur.execute("SELECT setval(pg_get_serial_sequence('%s','%s'), COALESCE(MAX(%s),1)) "
                        "FROM %s;" % (tabla, col, col, tabla))
        # el atributo derivado se calcula una sola vez tras la carga masiva;
        # desde aqui en adelante lo mantiene el trigger trg_rendimiento
        cur.execute(RECALCULO_RENDIMIENTO)

        # los objetos programables se crean despues de la carga para que los
        # triggers no se disparen una vez por cada fila copiada
        ejecutar_archivo(cur, "02_vistas_procedimientos_triggers.sql")
        t0 = time.perf_counter()
        ejecutar_archivo(cur, "04_indices.sql")
        t_idx = time.perf_counter() - t0
        cur.execute("VACUUM ANALYZE;")
        cur.execute("SELECT pg_database_size(current_database());")
        tam = cur.fetchone()[0]
        cur.close()
        con.close()

        bitacora.append(dict(escenario=etiqueta, registros=sum(conteo.values()), filas=conteo,
                             generacion_s=round(t_gen, 2), copy_s=round(t_copy, 2),
                             indices_s=round(t_idx, 2), tamano_bytes=tam))
        print("%-5s %9d filas  generacion %.1f s  COPY %.1f s  indices %.1f s  %.1f MB"
              % (etiqueta, sum(conteo.values()), t_gen, t_copy, t_idx, tam / 1048576),
              flush=True)

    with open(os.path.join(RES, "carga.json"), "w", encoding="utf-8") as fh:
        json.dump(bitacora, fh, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    fase = sys.argv[1] if len(sys.argv) > 1 else "todo"
    if fase in ("cargar", "todo"):
        cargar()
    if fase in ("experimento", "todo"):
        import experimento
        experimento.main()
    if fase in ("graficos", "todo"):
        import graficos
        graficos.main()
