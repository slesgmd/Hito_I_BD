#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de datos sinteticos - Agricultura de Precision y Sensores IoT
Curso: Base de Datos I (CS2041) - Laboratorio 14 - 2026-2

Uso:  python generar_datos.py <total_registros> <carpeta_salida>
Ej.:  python generar_datos.py 1000000 ../data/1M

Produce un CSV por tabla. La suma de filas de todas las tablas es exactamente
<total_registros>; la tabla Lectura_Suelo absorbe el saldo.
Los parametros agronomicos (rangos optimos, rendimientos, caudales) se tomaron
de valores de referencia publicos para la agricultura peruana.
"""
import csv, os, random, sys
from datetime import date, datetime, timedelta

SEED = 20251047
INICIO_SERIE = datetime(2026, 1, 1)
FIN_SERIE = datetime(2026, 9, 15, 23, 59)
VENTANA_SEG = int((FIN_SERIE - INICIO_SERIE).total_seconds())
REF = date(2026, 9, 20)                 # fecha de corte del caso de estudio
NULO = ""                               # NULL para COPY ... NULL ''

# departamento, provincia, distrito, lat, lon, temperatura media del suelo (C)
DEPARTAMENTOS = [
    ("Ica", "Ica", "Salas Guadalupe", -14.07, -75.73, 23),
    ("La Libertad", "Viru", "Chao", -8.48, -78.72, 22),
    ("Lambayeque", "Chiclayo", "Motupe", -6.15, -79.72, 24),
    ("Piura", "Sullana", "Bellavista", -4.90, -80.69, 26),
    ("Arequipa", "Caylloma", "Majes", -16.33, -72.19, 18),
    ("Ancash", "Casma", "Comandante Noel", -9.47, -78.30, 21),
    ("Lima", "Huaral", "Chancay", -11.57, -77.27, 19),
    ("Junin", "Chanchamayo", "Perene", -10.95, -75.22, 24),
    ("San Martin", "Lamas", "Tabalosos", -6.42, -76.63, 26),
    ("Cusco", "La Convencion", "Echarate", -12.77, -72.57, 24),
    ("Cajamarca", "Jaen", "Bellavista", -5.67, -78.67, 25),
    ("Amazonas", "Utcubamba", "Bagua Grande", -5.76, -78.44, 26),
]
NOMBRES_FUNDO = ["Santa Rita", "El Algarrobal", "Los Olivares", "Pampa Verde",
                 "San Jacinto", "La Huaca", "Tierra Nueva", "El Mirador",
                 "Valle Alto", "Sol de Oro", "Las Lomas", "Buenaventura"]

# nombre, cientifico, ciclo, hmin, hmax, phmin, phmax, ce_max, t/ha, S/ por kg
CULTIVOS = [
    ("Esparrago", "Asparagus officinalis", 270, 55, 75, 6.5, 7.5, 3.0, 11, 5.5),
    ("Arandano", "Vaccinium corymbosum", 365, 60, 80, 4.5, 5.5, 1.5, 14, 12.0),
    ("Palto Hass", "Persea americana", 420, 55, 70, 5.5, 7.0, 2.0, 12, 6.0),
    ("Uva de mesa", "Vitis vinifera", 300, 45, 65, 6.0, 7.5, 2.5, 25, 7.0),
    ("Mango Kent", "Mangifera indica", 330, 50, 70, 5.5, 7.5, 2.0, 16, 2.5),
    ("Quinua", "Chenopodium quinoa", 150, 40, 60, 6.0, 8.0, 4.0, 2, 6.0),
    ("Papa Canchan", "Solanum tuberosum", 120, 60, 80, 5.0, 6.5, 2.0, 22, 1.2),
    ("Maiz amarillo", "Zea mays", 140, 55, 75, 5.8, 7.0, 3.5, 9, 1.1),
    ("Cacao", "Theobroma cacao", 400, 65, 85, 5.0, 7.5, 1.5, 1, 9.0),
    ("Cafe Caturra", "Coffea arabica", 390, 60, 80, 4.5, 6.0, 1.5, 1, 14.0),
    ("Alcachofa", "Cynara scolymus", 180, 60, 75, 6.0, 7.5, 3.0, 18, 2.2),
    ("Pimiento piquillo", "Capsicum annuum", 130, 55, 70, 6.0, 7.0, 2.5, 28, 2.8),
]
# cultivos aptos por departamento (se evita, por ejemplo, cacao en Ica)
APTOS = {
    "Ica": ["Esparrago", "Uva de mesa", "Palto Hass", "Arandano", "Pimiento piquillo"],
    "La Libertad": ["Esparrago", "Arandano", "Palto Hass", "Alcachofa", "Pimiento piquillo"],
    "Lambayeque": ["Mango Kent", "Palto Hass", "Maiz amarillo", "Uva de mesa"],
    "Piura": ["Mango Kent", "Uva de mesa", "Arandano", "Maiz amarillo"],
    "Arequipa": ["Quinua", "Alcachofa", "Papa Canchan", "Palto Hass"],
    "Ancash": ["Esparrago", "Palto Hass", "Maiz amarillo", "Mango Kent"],
    "Lima": ["Palto Hass", "Maiz amarillo", "Papa Canchan", "Alcachofa"],
    "Junin": ["Cafe Caturra", "Cacao", "Maiz amarillo"],
    "San Martin": ["Cacao", "Cafe Caturra", "Maiz amarillo"],
    "Cusco": ["Cafe Caturra", "Cacao"],
    "Cajamarca": ["Cafe Caturra", "Cacao", "Maiz amarillo"],
    "Amazonas": ["Cafe Caturra", "Cacao", "Maiz amarillo"],
}

INSUMOS = [  # nombre, tipo, unidad, costo, carencia
    ("Nitrato de amonio 33.5", "Fertilizante", "kg", 3.20, 0),
    ("Sulfato de potasio", "Fertilizante", "kg", 4.80, 0),
    ("Fosfato diamonico", "Fertilizante", "kg", 4.10, 0),
    ("Acido fosforico 85%", "Fertilizante", "L", 6.50, 0),
    ("Yeso agricola", "Enmienda", "kg", 0.90, 0),
    ("Azufre micronizado", "Enmienda", "kg", 2.30, 3),
    ("Mancozeb 80 WP", "Fungicida", "kg", 28.00, 7),
    ("Azoxistrobina 25 SC", "Fungicida", "L", 95.00, 14),
    ("Abamectina 1.8 EC", "Insecticida", "L", 78.00, 7),
    ("Imidacloprid 35 SC", "Insecticida", "L", 64.00, 21),
    ("Extracto de algas", "Bioestimulante", "L", 42.00, 0),
    ("Aminoacidos libres 20%", "Bioestimulante", "L", 55.00, 0),
    ("Quelato de hierro EDDHA", "Fertilizante", "kg", 38.00, 0),
    ("Cal dolomita", "Enmienda", "kg", 0.65, 0),
    ("Bacillus subtilis WP", "Fungicida", "kg", 61.00, 0),
]
DOSIS = {"Fertilizante": (25, 400), "Enmienda": (100, 900), "Fungicida": (0.3, 6),
         "Insecticida": (0.2, 4), "Bioestimulante": (1, 15)}
METODOS = {"Fertilizante": ["Fertirriego", "Al suelo"], "Enmienda": ["Al suelo"],
           "Fungicida": ["Foliar", "Drench"], "Insecticida": ["Foliar", "Drench"],
           "Bioestimulante": ["Foliar", "Fertirriego"]}

# tipo de sensor -> variables que mide y modelos comerciales compatibles
SENSORES = {
    "Humedad": ({"hum", "temp"}, [("SMT100", "TRUEBNER"), ("Watermark 200SS", "Irrometer")]),
    "Multiparametro": ({"hum", "temp", "ph", "ce"}, [("JXBS-3001", "JXCT")]),
    "Conductividad": ({"hum", "temp", "ce"}, [("TEROS 12", "METER Group"),
                                              ("HydraProbe", "Stevens Water")]),
    "pH": ({"ph", "temp"}, [("Sonda pH de suelo", "JXCT")]),
    "Temperatura": ({"temp"}, [("107", "Campbell Scientific")]),
}
PESOS_SENSOR = {"Humedad": 35, "Multiparametro": 40, "Conductividad": 10, "pH": 10,
                "Temperatura": 5}
UNIDAD = {"Humedad": "%", "Multiparametro": "mixto", "Conductividad": "dS/m",
          "pH": "pH", "Temperatura": "C"}
CONTROLADORES = [("NMC-Pro", "Netafim"), ("ACC2", "Hunter"),
                 ("ESP-LXME2", "Rain Bird"), ("GSI", "Galcon")]

NOMBRES = ["Juan", "Maria", "Jose", "Rosa", "Carlos", "Ana", "Luis", "Carmen", "Miguel",
           "Elena", "Pedro", "Silvia", "Jorge", "Lucia", "Victor", "Gladys", "Raul", "Martha",
           "Cesar", "Nancy", "Felipe", "Yolanda", "Hugo", "Teresa", "Marco", "Julia", "Oscar",
           "Beatriz", "Angel", "Pilar"]
APELLIDOS = ["Quispe", "Mamani", "Flores", "Rojas", "Vasquez", "Huaman", "Chavez", "Ramos",
             "Castillo", "Torres", "Vargas", "Espinoza", "Salazar", "Cordova", "Tapia",
             "Ccahuana", "Zevallos", "Palomino", "Bustamante", "Aguirre", "Nunez", "Paredes",
             "Guzman", "Lescano", "Meza"]
ROLES = ["Tecnico de campo", "Ingeniero agronomo", "Operador de riego", "Supervisor"]
SUELOS = ["Arenoso", "Franco", "Franco arenoso", "Franco arcilloso", "Arcilloso"]
TIPOS_RIEGO = ["Goteo", "Aspersion", "Microaspersion", "Gravedad tecnificada"]
FUENTES = ["Pozo", "Canal", "Reservorio", "Rio"]
VALVULAS = ["Solenoide", "Hidraulica", "Manual motorizada"]
CATEGORIAS = ["Primera", "Segunda", "Tercera", "Descarte"]

PERFILES = {
    1_000: dict(fundo=3, cultivo=8, insumo=10, operario=12, parcela=15, zona=40,
                campania=25, sensor=35, controlador=10, evento=120, alerta=30,
                cosecha=40, aplicacion=40, mantenimiento=20),
    10_000: dict(fundo=5, cultivo=10, insumo=12, operario=40, parcela=50, zona=150,
                 campania=90, sensor=130, controlador=40, evento=1_200, alerta=300,
                 cosecha=350, aplicacion=400, mantenimiento=150),
    100_000: dict(fundo=8, cultivo=12, insumo=15, operario=150, parcela=200, zona=700,
                  campania=400, sensor=620, controlador=180, evento=12_000, alerta=3_000,
                  cosecha=3_000, aplicacion=4_000, mantenimiento=1_200),
    1_000_000: dict(fundo=12, cultivo=12, insumo=15, operario=400, parcela=600, zona=2_400,
                    campania=1_500, sensor=2_200, controlador=600, evento=120_000,
                    alerta=30_000, cosecha=25_000, aplicacion=40_000, mantenimiento=8_000),
}


def w(carpeta, nombre, cabecera, filas):
    with open(os.path.join(carpeta, nombre + ".csv"), "w", newline="", encoding="utf-8") as fh:
        esc = csv.writer(fh)
        esc.writerow(cabecera)
        esc.writerows(filas)
    return len(filas)


def ts(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def instante():
    t = INICIO_SERIE + timedelta(seconds=random.randint(0, VENTANA_SEG))
    return t.replace(second=0, microsecond=0)


def generar(total, carpeta):
    random.seed(SEED + total)
    os.makedirs(carpeta, exist_ok=True)
    p = PERFILES[total]
    p["sistema"] = p["parcela"]          # un sistema de riego por parcela
    n = {}

    # ---------------------------------------------------------- FUNDO
    fundos = []
    for i in range(1, p["fundo"] + 1):
        dep, prov, dist, lat, lon, _ = DEPARTAMENTOS[i - 1]
        fundos.append([i, NOMBRES_FUNDO[i - 1], dep, prov, dist,
                       round(random.uniform(60, 900), 2),
                       round(lat + random.uniform(-0.2, 0.2), 6),
                       round(lon + random.uniform(-0.2, 0.2), 6),
                       (date(2019, 1, 1) + timedelta(days=random.randint(0, 2000))).isoformat()])
    n["Fundo"] = w(carpeta, "fundo", ["id_fundo", "nombre", "departamento", "provincia",
                   "distrito", "area_total_ha", "latitud", "longitud", "fecha_registro"], fundos)
    dep_fundo = {f[0]: f[2] for f in fundos}
    temp_dep = {d[0]: d[5] for d in DEPARTAMENTOS}

    # -------------------------------------------------------- CULTIVO
    cultivos = [[i] + list(c[:8]) for i, c in enumerate(CULTIVOS[:p["cultivo"]], start=1)]
    n["Cultivo"] = w(carpeta, "cultivo", ["id_cultivo", "nombre_comun", "nombre_cientifico",
                     "ciclo_dias", "humedad_optima_min", "humedad_optima_max", "ph_optimo_min",
                     "ph_optimo_max", "ce_maxima_ds_m"], cultivos)
    info = {i: CULTIVOS[i - 1] for i in range(1, p["cultivo"] + 1)}
    id_por_nombre = {CULTIVOS[i - 1][0]: i for i in info}

    # --------------------------------------------------------- INSUMO
    insumos = [[i] + list(x) for i, x in enumerate(INSUMOS[:p["insumo"]], start=1)]
    n["Insumo"] = w(carpeta, "insumo", ["id_insumo", "nombre", "tipo", "unidad",
                    "costo_unitario", "periodo_carencia_dias"], insumos)
    tipo_insumo = {x[0]: x[2] for x in insumos}

    # ------------------------------------------------------- OPERARIO
    dnis, operarios = set(), []
    for i in range(1, p["operario"] + 1):
        while True:
            d = str(random.randint(10000000, 79999999))
            if d not in dnis:
                dnis.add(d)
                break
        tel = NULO if random.random() < 0.08 else "9" + str(random.randint(10000000, 99999999))
        operarios.append([i, d, random.choice(NOMBRES), random.choice(APELLIDOS),
                          random.choice(ROLES), tel, random.randint(1, p["fundo"]),
                          (date(2018, 1, 1) + timedelta(days=random.randint(0, 2800))).isoformat()])
    n["Operario"] = w(carpeta, "operario", ["id_operario", "dni", "nombre", "apellido", "rol",
                      "telefono", "id_fundo", "fecha_ingreso"], operarios)

    # -------------------------------------------------------- PARCELA
    parcelas, cont = [], {}
    for i in range(1, p["parcela"] + 1):
        f = random.randint(1, p["fundo"])
        cont[f] = cont.get(f, 0) + 1
        parcelas.append([i, f, "P-%03d" % cont[f], round(random.uniform(1.5, 35.0), 2),
                         random.choice(SUELOS), round(random.uniform(0, 12), 1),
                         (date(2020, 1, 1) + timedelta(days=random.randint(0, 1800))).isoformat()])
    n["Parcela"] = w(carpeta, "parcela", ["id_parcela", "id_fundo", "codigo_parcela", "area_ha",
                     "tipo_suelo", "pendiente_pct", "fecha_habilitacion"], parcelas)
    area = {r[0]: float(r[3]) for r in parcelas}
    fundo_parcela = {r[0]: r[1] for r in parcelas}

    # ---------------------------------------------------- ZONA_MANEJO
    zonas, zxp = [], {}
    for idp in range(1, p["parcela"] + 1):
        zxp[idp] = [1]
        zonas.append([idp, 1, round(area[idp] / 2, 2), "Zona de manejo 1"])
    while len(zonas) < p["zona"]:
        idp = random.randint(1, p["parcela"])
        k = len(zxp[idp]) + 1
        if k > 8:
            continue
        zxp[idp].append(k)
        zonas.append([idp, k, round(max(0.2, area[idp] / (k + 1)), 2), "Zona de manejo %d" % k])
    n["Zona_Manejo"] = w(carpeta, "zona_manejo", ["id_parcela", "num_zona", "area_ha",
                         "descripcion"], zonas)
    lista_zonas = [(z[0], z[1]) for z in zonas]

    # -------------------------------------------------- SISTEMA_RIEGO
    # caudal de 15 a 180 m3/h, coherente con riego sectorizado de 1.5 a 35 ha
    sistemas, sis_parcela, caudal = [], {}, {}
    for i in range(1, p["sistema"] + 1):
        c = round(random.uniform(15000, 180000), 2)
        sistemas.append([i, i, random.choice(TIPOS_RIEGO), c, random.choice(FUENTES),
                         (date(2021, 1, 1) + timedelta(days=random.randint(0, 1500))).isoformat(),
                         "Operativo" if random.random() > 0.07 else "Averiado"])
        sis_parcela[i] = i
        caudal[i] = c
    n["Sistema_Riego"] = w(carpeta, "sistema_riego", ["id_sistema", "id_parcela", "tipo",
                           "caudal_nominal_lph", "fuente_agua", "fecha_instalacion", "estado"],
                           sistemas)

    # ------------------------------------------------------- CAMPANIA
    # Cadenas hacia atras desde REF: la primera campania de cada parcela es la
    # vigente y las anteriores se encadenan sin solaparse.
    campanias, cursor = [], {}
    i, idp = 0, 0
    while i < p["campania"]:
        idp = idp % p["parcela"] + 1
        dep = dep_fundo[fundo_parcela[idp]]
        aptos = [id_por_nombre[c] for c in APTOS[dep] if c in id_por_nombre] or list(info)
        idc = random.choice(aptos)
        ciclo = info[idc][2]
        if idp not in cursor:
            siembra = REF - timedelta(days=int(ciclo * random.uniform(0.15, 0.85)))
            estado = "En curso" if random.random() > 0.10 else "Perdida"
        else:
            fin_prev = cursor[idp] - timedelta(days=random.randint(10, 60))
            siembra = fin_prev - timedelta(days=ciclo)
            estado = "Cerrada" if random.random() > 0.08 else "Perdida"
        fin = siembra + timedelta(days=ciclo)
        cursor[idp] = siembra
        i += 1
        campanias.append([i, idp, idc, siembra.isoformat(), fin.isoformat(),
                          random.choice([1200, 1600, 2500, 3300, 5000, 8000, 62500]), estado, 0])
    n["Campania"] = w(carpeta, "campania", ["id_campania", "id_parcela", "id_cultivo",
                      "fecha_siembra", "fecha_fin_estimada", "densidad_plantas_ha", "estado",
                      "rendimiento_kg_ha"], campanias)
    cultivo_vigente = {c[1]: c[2] for c in campanias if c[6] == "En curso"}

    # ------------------------------------------ DISPOSITIVO Y SUBCLASES
    n_disp = p["sensor"] + p["controlador"]
    disp, sens, ctrl, tipo_de = [], [], [], {}
    for i in range(1, n_disp + 1):
        idp, nz = lista_zonas[(i - 1) % len(lista_zonas)]
        if i <= p["sensor"]:
            t = random.choices(list(PESOS_SENSOR), weights=list(PESOS_SENSOR.values()))[0]
            modelo, fab = random.choice(SENSORES[t][1])
            tipo_de[i] = t
            sens.append([i, t, random.choice([10, 20, 30, 40, 60]),
                         random.choice([5, 10, 15, 30, 60]), UNIDAD[t], NULO, NULO])
        else:
            modelo, fab = random.choice(CONTROLADORES)
            ctrl.append([i, idp, round(random.uniform(4, 50), 2), random.choice(VALVULAS)])
        disp.append([i, "SN-%07d" % (400000 + i), modelo, fab,
                     (date(2023, 1, 1) + timedelta(days=random.randint(0, 900))).isoformat(),
                     "Activo" if random.random() > 0.06 else
                     random.choice(["Mantenimiento", "Inactivo"]), idp, nz])
    n["Dispositivo"] = w(carpeta, "dispositivo", ["id_dispositivo", "codigo_serie", "modelo",
                         "fabricante", "fecha_instalacion", "estado", "id_parcela", "num_zona"],
                         disp)
    n["Sensor"] = w(carpeta, "sensor", ["id_dispositivo", "tipo_sensor", "profundidad_cm",
                    "frecuencia_min", "unidad_medida", "rango_min", "rango_max"], sens)
    n["Controlador"] = w(carpeta, "controlador", ["id_dispositivo", "id_sistema",
                         "caudal_max_lps", "tipo_valvula"], ctrl)
    zona_de = {d[0]: (d[6], d[7]) for d in disp}

    # -------------------------------------------------- LECTURA_SUELO
    n_lect = total - sum(n.values()) - p["evento"] - p["alerta"] - p["cosecha"] \
        - p["aplicacion"] - p["mantenimiento"]
    assert n_lect > 0, "perfil mal dimensionado"
    con_cultivo = sorted(cultivo_vigente) or list(range(1, p["parcela"] + 1))
    secas = set(random.sample(con_cultivo, max(1, int(len(con_cultivo) * 0.22))))
    lecturas, vistos, cand_hum, cand_bat = [], set(), [], []
    for k in range(n_lect):
        sid = sens[k % len(sens)][0]
        mide = SENSORES[tipo_de[sid]][0]
        idp, nz = zona_de[sid]
        idc = cultivo_vigente.get(idp)
        hmin, hmax = (info[idc][3], info[idc][4]) if idc else (50, 75)
        while True:
            t = instante()
            if (sid, t) not in vistos:
                vistos.add((sid, t))
                break
        hum = None
        if "hum" in mide:
            base = hmin - 8 if idp in secas else (hmin + hmax) / 2
            hum = round(max(0.5, min(99.5, random.gauss(base, 6 if idp in secas else 7))), 2)
        tmp = round(random.gauss(temp_dep[dep_fundo[fundo_parcela[idp]]], 3.5), 2)
        phv = round(min(9.5, max(3.5, random.gauss(6.6, 0.7))), 2) if "ph" in mide else None
        cev = round(abs(random.gauss(1.8, 0.8)), 2) if "ce" in mide else None
        # descarga en diente de sierra: la bateria se reemplaza cada ~120 dias
        bat = int(max(3, min(100, 100 - ((t - INICIO_SERIE).days + sid * 7) % 120 * 0.8
                             + random.gauss(0, 2))))
        # faltantes por fallas de transmision (distintos de los nulos estructurales)
        fila = [sid, ts(t),
                NULO if hum is None or random.random() < 0.02 else hum,
                NULO if random.random() < 0.01 else tmp,
                NULO if phv is None or random.random() < 0.04 else phv,
                NULO if cev is None or random.random() < 0.03 else cev,
                NULO if random.random() < 0.05 else bat]
        lecturas.append(fila)
        if fila[2] != NULO and hum < hmin and len(cand_hum) < p["alerta"] * 3:
            cand_hum.append((sid, t, hum, hmin))
        if fila[6] != NULO and bat < 15 and len(cand_bat) < p["alerta"]:
            cand_bat.append((sid, t, bat))
    lecturas.sort(key=lambda r: r[1])      # orden de llegada real: cronologico
    n["Lectura_Suelo"] = w(carpeta, "lectura_suelo", ["id_dispositivo", "fecha_hora",
                           "humedad_pct", "temperatura_c", "ph", "conductividad_ds_m",
                           "bateria_pct"], lecturas)
    del lecturas, vistos

    # --------------------------------------------------------- ALERTA
    random.shuffle(cand_hum)
    random.shuffle(cand_bat)
    n_bat = min(len(cand_bat), int(p["alerta"] * 0.15))
    alertas, ventana = [], []
    for sid, t, val, hmin in cand_hum[:p["alerta"] - n_bat]:
        deficit = hmin - val
        sev = "Critica" if deficit > 20 else ("Alta" if deficit > 10 else "Media")
        at = random.random() < 0.62
        alertas.append([len(alertas) + 1, sid, ts(t), "Humedad baja", sev, val,
                        "true" if at else "false",
                        ts(t + timedelta(minutes=random.randint(20, 400))) if at else NULO,
                        random.randint(1, p["operario"]) if at else NULO])
        ventana.append((zona_de[sid][0], zona_de[sid][1], t))
    for sid, t, val in cand_bat[:p["alerta"] - len(alertas)]:
        at = random.random() < 0.8
        alertas.append([len(alertas) + 1, sid, ts(t), "Bateria baja",
                        "Alta" if val < 8 else "Media", val, "true" if at else "false",
                        ts(t + timedelta(hours=random.randint(2, 72))) if at else NULO,
                        random.randint(1, p["operario"]) if at else NULO])
    alertas.sort(key=lambda r: r[2])
    for k, r in enumerate(alertas, start=1):
        r[0] = k
    n["Alerta"] = w(carpeta, "alerta", ["id_alerta", "id_dispositivo", "fecha_hora", "tipo",
                    "severidad", "valor_registrado", "atendida", "fecha_atencion",
                    "id_operario"], alertas)

    # --------------------------------------------------- EVENTO_RIEGO
    # 55 % de los eventos responden a una alerta de humedad en menos de 6 horas
    eventos, claves = [], set()

    def agregar_evento(idp, nz, t, modos):
        if (idp, nz, t) in claves:
            return
        claves.add((idp, nz, t))
        dur = random.randint(20, 300)
        sis = idp                                  # sistema de la propia parcela
        vol = round(caudal[sis] * dur / 60 * random.uniform(0.55, 1.0), 2)
        eventos.append([len(eventos) + 1, sis, idp, nz, random.randint(1, p["operario"]),
                        ts(t), dur, vol, random.choice(modos)])

    for j in range(int(p["evento"] * 0.55)):
        if not ventana:
            break
        idp, nz, t0 = ventana[j % len(ventana)]
        agregar_evento(idp, nz, t0 + timedelta(minutes=random.randint(15, 355)),
                       ["Automatico", "Programado"])
    while len(eventos) < p["evento"]:
        idp, nz = random.choice(lista_zonas)
        agregar_evento(idp, nz, instante(), ["Automatico", "Manual", "Programado"])
    eventos.sort(key=lambda r: r[5])
    for k, r in enumerate(eventos, start=1):
        r[0] = k
    n["Evento_Riego"] = w(carpeta, "evento_riego", ["id_evento", "id_sistema", "id_parcela",
                          "num_zona", "id_operario", "fecha_hora_inicio", "duracion_min",
                          "volumen_litros", "modo"], eventos)
    del eventos, claves

    # -------------------------------------------------------- COSECHA
    # Solo se cosechan campanias cerradas o vigentes con mas de 70 % de avance.
    tope = date(2026, 9, 15)
    aptas = []
    for c in campanias:
        s, f, ciclo = date.fromisoformat(c[3]), date.fromisoformat(c[4]), info[c[2]][2]
        inicio = s + timedelta(days=int(ciclo * 0.7))
        if c[6] == "Cerrada" or (c[6] == "En curso" and inicio < tope - timedelta(days=5)):
            aptas.append((c, inicio, min(f, tope)))
    reparto = {}
    for i in range(p["cosecha"]):
        reparto[aptas[i % len(aptas)][0][0]] = reparto.get(aptas[i % len(aptas)][0][0], 0) + 1
    cosechas = []
    for c, ini, fin in aptas:
        veces = reparto.get(c[0], 0)
        if veces == 0:
            continue
        esperado = info[c[2]][8] * 1000 * area[c[1]] * random.uniform(0.65, 1.15)
        if c[6] == "En curso":
            esperado *= random.uniform(0.3, 0.7)
        precio = info[c[2]][9]
        dias = max(1, (fin - ini).days)
        for _ in range(veces):
            cosechas.append([len(cosechas) + 1, c[0], random.randint(1, p["operario"]),
                             (ini + timedelta(days=random.randint(0, dias))).isoformat(),
                             round(max(1, esperado / veces * random.uniform(0.7, 1.3)), 2),
                             random.choices(CATEGORIAS, weights=[55, 27, 13, 5])[0],
                             NULO if random.random() < 0.10 else round(random.uniform(8, 82), 2),
                             NULO if random.random() < 0.06 else
                             round(precio * random.uniform(0.75, 1.25), 2)])
    cosechas.sort(key=lambda r: r[3])
    for k, r in enumerate(cosechas, start=1):
        r[0] = k
    n["Cosecha"] = w(carpeta, "cosecha", ["id_cosecha", "id_campania", "id_operario", "fecha",
                     "cantidad_kg", "categoria", "humedad_producto_pct", "precio_kg_soles"],
                     cosechas)

    # ---------------------------------------------- APLICACION_INSUMO
    apl, claves = [], set()
    while len(apl) < p["aplicacion"]:
        idp, nz = random.choice(lista_zonas)
        ins, ope, t = random.randint(1, p["insumo"]), random.randint(1, p["operario"]), instante()
        t = t.replace(minute=random.choice([0, 15, 30, 45]))
        if (idp, nz, ins, ope, t) in claves:
            continue
        claves.add((idp, nz, ins, ope, t))
        lo, hi = DOSIS[tipo_insumo[ins]]
        apl.append([idp, nz, ins, ope, ts(t), round(random.uniform(lo, hi), 2),
                    random.choice(METODOS[tipo_insumo[ins]])])
    apl.sort(key=lambda r: r[4])
    n["Aplicacion_Insumo"] = w(carpeta, "aplicacion_insumo", ["id_parcela", "num_zona",
                               "id_insumo", "id_operario", "fecha_hora", "dosis", "metodo"], apl)

    # -------------------------------------------------- MANTENIMIENTO
    mant, claves = [], set()
    while len(mant) < p["mantenimiento"]:
        d, o = random.randint(1, n_disp), random.randint(1, p["operario"])
        f = date(2025, 1, 1) + timedelta(days=random.randint(0, 620))
        if (d, o, f) in claves:
            continue
        claves.add((d, o, f))
        tipo = random.choices(["Preventivo", "Correctivo", "Calibracion"], weights=[50, 30, 20])[0]
        obs = {"Preventivo": "Limpieza de contactos y revision de cableado",
               "Correctivo": "Reemplazo de bateria y sellado de carcasa",
               "Calibracion": "Calibracion con muestra gravimetrica de suelo"}[tipo]
        mant.append([d, o, f.isoformat(), tipo, NULO if random.random() < 0.25 else obs,
                     round(random.uniform(25, 780), 2)])
    n["Mantenimiento"] = w(carpeta, "mantenimiento", ["id_dispositivo", "id_operario", "fecha",
                           "tipo", "observacion", "costo"], mant)
    return n


if __name__ == "__main__":
    tot, dest = int(sys.argv[1]), sys.argv[2]
    conteo = generar(tot, dest)
    for k, v in conteo.items():
        print("%-18s %10d" % (k, v))
    print("%-18s %10d" % ("TOTAL", sum(conteo.values())))
