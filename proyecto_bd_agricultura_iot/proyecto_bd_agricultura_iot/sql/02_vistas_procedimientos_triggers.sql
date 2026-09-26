-- ============================================================
-- Vistas de usuario, procedimientos almacenados y triggers
-- ============================================================

-- ============================================================
-- A. VISTAS
-- ============================================================

-- A.1 Estado hidrico vigente de cada zona de manejo.
-- Compara la ultima lectura de humedad disponible con el rango optimo del
-- cultivo sembrado y clasifica la zona en deficit, optimo o exceso.
CREATE OR REPLACE VIEW vw_estado_hidrico_zona AS
WITH ultima AS (
    SELECT DISTINCT ON (l.id_dispositivo)
           l.id_dispositivo, l.fecha_hora, l.humedad_pct, l.conductividad_ds_m
    FROM Lectura_Suelo l
    WHERE l.humedad_pct IS NOT NULL
    ORDER BY l.id_dispositivo, l.fecha_hora DESC
)
SELECT f.nombre            AS fundo,
       p.codigo_parcela,
       z.num_zona,
       cu.nombre_comun     AS cultivo,
       u.fecha_hora        AS ultima_medicion,
       u.humedad_pct,
       cu.humedad_optima_min,
       cu.humedad_optima_max,
       CASE WHEN u.humedad_pct < cu.humedad_optima_min THEN 'Deficit'
            WHEN u.humedad_pct > cu.humedad_optima_max THEN 'Exceso'
            ELSE 'Optimo' END AS diagnostico
FROM ultima u
JOIN Dispositivo d  ON d.id_dispositivo = u.id_dispositivo
JOIN Zona_Manejo z  ON z.id_parcela = d.id_parcela AND z.num_zona = d.num_zona
JOIN Parcela     p  ON p.id_parcela = z.id_parcela
JOIN Fundo       f  ON f.id_fundo   = p.id_fundo
JOIN Campania    ca ON ca.id_parcela = p.id_parcela AND ca.estado = 'En curso'
JOIN Cultivo     cu ON cu.id_cultivo = ca.id_cultivo;

-- A.2 Resumen productivo por campania (kg totales, kg/ha e ingreso estimado).
CREATE OR REPLACE VIEW vw_produccion_campania AS
SELECT ca.id_campania,
       f.nombre         AS fundo,
       p.codigo_parcela,
       cu.nombre_comun  AS cultivo,
       ca.estado,
       p.area_ha,
       COALESCE(SUM(co.cantidad_kg), 0)                        AS kilos_totales,
       ROUND(COALESCE(SUM(co.cantidad_kg), 0) / p.area_ha, 2)  AS kilos_por_ha,
       ROUND(COALESCE(SUM(co.cantidad_kg * co.precio_kg_soles), 0), 2) AS ingreso_soles
FROM Campania ca
JOIN Parcela  p  ON p.id_parcela  = ca.id_parcela
JOIN Fundo    f  ON f.id_fundo    = p.id_fundo
JOIN Cultivo  cu ON cu.id_cultivo = ca.id_cultivo
LEFT JOIN Cosecha co ON co.id_campania = ca.id_campania
GROUP BY ca.id_campania, f.nombre, p.codigo_parcela, cu.nombre_comun, ca.estado, p.area_ha;

-- A.3 Bandeja de alertas sin atender, ordenada por severidad y antiguedad.
CREATE OR REPLACE VIEW vw_alertas_pendientes AS
SELECT a.id_alerta,
       f.nombre        AS fundo,
       p.codigo_parcela,
       d.num_zona,
       d.codigo_serie  AS sensor,
       a.tipo,
       a.severidad,
       a.valor_registrado,
       a.fecha_hora,
       ROUND(EXTRACT(EPOCH FROM (TIMESTAMP '2026-09-20 00:00:00' - a.fecha_hora)) / 3600, 1)
           AS horas_sin_atender
FROM Alerta      a
JOIN Dispositivo d ON d.id_dispositivo = a.id_dispositivo
JOIN Parcela     p ON p.id_parcela = d.id_parcela
JOIN Fundo       f ON f.id_fundo   = p.id_fundo
WHERE a.atendida = FALSE
ORDER BY CASE a.severidad WHEN 'Critica' THEN 1 WHEN 'Alta' THEN 2
                          WHEN 'Media' THEN 3 ELSE 4 END,
         a.fecha_hora;

-- ============================================================
-- B. PROCEDIMIENTOS ALMACENADOS Y FUNCIONES
-- ============================================================

-- B.1 Registra una lectura validando que el sensor exista y este activo.
CREATE OR REPLACE PROCEDURE sp_registrar_lectura(
    p_sensor  INTEGER,
    p_fecha   TIMESTAMP,
    p_humedad NUMERIC,
    p_temp    NUMERIC,
    p_ph      NUMERIC DEFAULT NULL,
    p_ce      NUMERIC DEFAULT NULL,
    p_bateria INTEGER DEFAULT NULL)
LANGUAGE plpgsql AS $$
DECLARE
    v_estado VARCHAR(15);
BEGIN
    SELECT d.estado INTO v_estado
    FROM Dispositivo d JOIN Sensor s ON s.id_dispositivo = d.id_dispositivo
    WHERE d.id_dispositivo = p_sensor;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'El dispositivo % no existe o no es un sensor', p_sensor;
    END IF;
    IF v_estado <> 'Activo' THEN
        RAISE EXCEPTION 'El sensor % esta en estado % y no puede reportar', p_sensor, v_estado;
    END IF;

    INSERT INTO Lectura_Suelo(id_dispositivo, fecha_hora, humedad_pct, temperatura_c,
                              ph, conductividad_ds_m, bateria_pct)
    VALUES (p_sensor, date_trunc('minute', p_fecha), p_humedad, p_temp, p_ph, p_ce, p_bateria)
    ON CONFLICT (id_dispositivo, fecha_hora) DO NOTHING;
END;
$$;

-- B.2 Cierra una campania, calcula su rendimiento y deja registro de auditoria.
CREATE OR REPLACE PROCEDURE sp_cerrar_campania(p_campania INTEGER)
LANGUAGE plpgsql AS $$
DECLARE
    v_area  NUMERIC;
    v_kilos NUMERIC;
BEGIN
    SELECT p.area_ha INTO v_area
    FROM Campania ca JOIN Parcela p ON p.id_parcela = ca.id_parcela
    WHERE ca.id_campania = p_campania;

    IF v_area IS NULL THEN
        RAISE EXCEPTION 'La campania % no existe', p_campania;
    END IF;

    SELECT COALESCE(SUM(cantidad_kg), 0) INTO v_kilos
    FROM Cosecha WHERE id_campania = p_campania;

    UPDATE Campania
       SET estado = 'Cerrada',
           rendimiento_kg_ha = ROUND(v_kilos / v_area, 2)
     WHERE id_campania = p_campania;
END;
$$;

-- B.3 Balance hidrico de una parcela en un intervalo: agua aplicada por zona
--     y humedad media registrada en el mismo periodo.
CREATE OR REPLACE FUNCTION fn_balance_hidrico(
    p_parcela INTEGER, p_desde TIMESTAMP, p_hasta TIMESTAMP)
RETURNS TABLE (num_zona SMALLINT, litros NUMERIC, eventos BIGINT, humedad_media NUMERIC)
LANGUAGE sql AS $$
    SELECT z.num_zona,
           COALESCE(SUM(er.volumen_litros), 0) AS litros,
           COUNT(er.id_evento)                 AS eventos,
           (SELECT ROUND(AVG(l.humedad_pct), 2)
              FROM Lectura_Suelo l
              JOIN Dispositivo d2 ON d2.id_dispositivo = l.id_dispositivo
             WHERE d2.id_parcela = z.id_parcela
               AND d2.num_zona   = z.num_zona
               AND l.fecha_hora BETWEEN p_desde AND p_hasta) AS humedad_media
    FROM Zona_Manejo z
    LEFT JOIN Evento_Riego er
           ON er.id_parcela = z.id_parcela AND er.num_zona = z.num_zona
          AND er.fecha_hora_inicio BETWEEN p_desde AND p_hasta
    WHERE z.id_parcela = p_parcela
    GROUP BY z.id_parcela, z.num_zona
    ORDER BY z.num_zona;
$$;

-- B.4 Costo de insumos aplicados a una parcela en un rango de fechas.
CREATE OR REPLACE FUNCTION fn_costo_insumos(
    p_parcela INTEGER, p_desde DATE, p_hasta DATE)
RETURNS NUMERIC
LANGUAGE sql AS $$
    SELECT COALESCE(ROUND(SUM(ap.dosis * i.costo_unitario), 2), 0)
    FROM Aplicacion_Insumo ap
    JOIN Insumo i ON i.id_insumo = ap.id_insumo
    WHERE ap.id_parcela = p_parcela
      AND ap.fecha_hora::date BETWEEN p_desde AND p_hasta;
$$;

-- ============================================================
-- C. TRIGGERS
-- ============================================================

-- C.1 Genera alertas a partir de cada lectura nueva: humedad por debajo del
--     minimo del cultivo vigente o bateria por debajo de 15 %.
CREATE OR REPLACE FUNCTION trg_fn_alerta_lectura() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
DECLARE
    v_min NUMERIC;
BEGIN
    IF NEW.humedad_pct IS NOT NULL THEN
        SELECT cu.humedad_optima_min INTO v_min
        FROM Dispositivo d
        JOIN Campania ca ON ca.id_parcela = d.id_parcela AND ca.estado = 'En curso'
        JOIN Cultivo  cu ON cu.id_cultivo = ca.id_cultivo
        WHERE d.id_dispositivo = NEW.id_dispositivo;

        IF v_min IS NOT NULL AND NEW.humedad_pct < v_min THEN
            INSERT INTO Alerta(id_dispositivo, fecha_hora, tipo, severidad, valor_registrado)
            VALUES (NEW.id_dispositivo, NEW.fecha_hora, 'Humedad baja',
                    CASE WHEN NEW.humedad_pct < v_min - 20 THEN 'Critica'
                         WHEN NEW.humedad_pct < v_min - 10 THEN 'Alta'
                         ELSE 'Media' END,
                    NEW.humedad_pct)
            ON CONFLICT (id_dispositivo, fecha_hora, tipo) DO NOTHING;
        END IF;
    END IF;

    IF NEW.bateria_pct IS NOT NULL AND NEW.bateria_pct < 15 THEN
        INSERT INTO Alerta(id_dispositivo, fecha_hora, tipo, severidad, valor_registrado)
        VALUES (NEW.id_dispositivo, NEW.fecha_hora, 'Bateria baja',
                CASE WHEN NEW.bateria_pct < 8 THEN 'Alta' ELSE 'Media' END,
                NEW.bateria_pct)
        ON CONFLICT (id_dispositivo, fecha_hora, tipo) DO NOTHING;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_alerta_lectura ON Lectura_Suelo;
CREATE TRIGGER trg_alerta_lectura
AFTER INSERT ON Lectura_Suelo
FOR EACH ROW EXECUTE FUNCTION trg_fn_alerta_lectura();

-- C.2 Verifica que la zona regada pertenezca a la parcela que abastece el
--     sistema y, si el controlador no reporta volumen, lo calcula con el caudal.
CREATE OR REPLACE FUNCTION trg_fn_evento_riego() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
DECLARE
    v_parcela INTEGER;
    v_caudal  NUMERIC;
BEGIN
    SELECT id_parcela, caudal_nominal_lph INTO v_parcela, v_caudal
    FROM Sistema_Riego WHERE id_sistema = NEW.id_sistema;

    IF v_parcela IS DISTINCT FROM NEW.id_parcela THEN
        RAISE EXCEPTION 'El sistema % no abastece a la parcela %',
              NEW.id_sistema, NEW.id_parcela;
    END IF;
    IF NEW.volumen_litros IS NULL OR NEW.volumen_litros = 0 THEN
        NEW.volumen_litros := ROUND(v_caudal * NEW.duracion_min / 60.0, 2);
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_evento_riego ON Evento_Riego;
CREATE TRIGGER trg_evento_riego
BEFORE INSERT OR UPDATE ON Evento_Riego
FOR EACH ROW EXECUTE FUNCTION trg_fn_evento_riego();

-- C.3 Mantiene actualizado el atributo derivado rendimiento_kg_ha.
CREATE OR REPLACE FUNCTION trg_fn_rendimiento() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
DECLARE
    v_camp INTEGER := COALESCE(NEW.id_campania, OLD.id_campania);
    v_area NUMERIC;
BEGIN
    SELECT p.area_ha INTO v_area
    FROM Campania ca JOIN Parcela p ON p.id_parcela = ca.id_parcela
    WHERE ca.id_campania = v_camp;

    UPDATE Campania
       SET rendimiento_kg_ha = ROUND(
             (SELECT COALESCE(SUM(cantidad_kg), 0) FROM Cosecha WHERE id_campania = v_camp)
             / NULLIF(v_area, 0), 2)
     WHERE id_campania = v_camp;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_rendimiento ON Cosecha;
CREATE TRIGGER trg_rendimiento
AFTER INSERT OR UPDATE OR DELETE ON Cosecha
FOR EACH ROW EXECUTE FUNCTION trg_fn_rendimiento();

-- C.4 Impide que una parcela tenga dos campanias con periodos superpuestos.
CREATE OR REPLACE FUNCTION trg_fn_campania_sin_solape() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM Campania c
        WHERE c.id_parcela = NEW.id_parcela
          AND c.id_campania <> COALESCE(NEW.id_campania, -1)
          AND NEW.fecha_siembra      < c.fecha_fin_estimada
          AND NEW.fecha_fin_estimada > c.fecha_siembra
    ) THEN
        RAISE EXCEPTION 'La parcela % ya tiene una campania activa en ese periodo',
              NEW.id_parcela;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_campania_sin_solape ON Campania;
CREATE TRIGGER trg_campania_sin_solape
BEFORE INSERT OR UPDATE ON Campania
FOR EACH ROW EXECUTE FUNCTION trg_fn_campania_sin_solape();

-- C.5 Bitacora de cambios de estado de una campania.
CREATE OR REPLACE FUNCTION trg_fn_auditoria_campania() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.estado IS DISTINCT FROM OLD.estado THEN
        INSERT INTO Auditoria_Campania(id_campania, estado_anterior, estado_nuevo)
        VALUES (OLD.id_campania, OLD.estado, NEW.estado);
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_auditoria_campania ON Campania;
CREATE TRIGGER trg_auditoria_campania
AFTER UPDATE ON Campania
FOR EACH ROW EXECUTE FUNCTION trg_fn_auditoria_campania();

-- ============================================================
-- D. INTEGRIDAD DE LA JERARQUIA IS-A (cobertura total y disjunta)
-- ============================================================

-- D.1 Disjuncion: un dispositivo no puede ser sensor y controlador a la vez.
CREATE OR REPLACE FUNCTION trg_fn_subclase_exclusiva() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME = 'sensor' AND EXISTS
       (SELECT 1 FROM Controlador WHERE id_dispositivo = NEW.id_dispositivo) THEN
        RAISE EXCEPTION 'El dispositivo % ya figura como controlador', NEW.id_dispositivo;
    ELSIF TG_TABLE_NAME = 'controlador' AND EXISTS
       (SELECT 1 FROM Sensor WHERE id_dispositivo = NEW.id_dispositivo) THEN
        RAISE EXCEPTION 'El dispositivo % ya figura como sensor', NEW.id_dispositivo;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sensor_exclusivo ON Sensor;
CREATE TRIGGER trg_sensor_exclusivo
BEFORE INSERT OR UPDATE ON Sensor
FOR EACH ROW EXECUTE FUNCTION trg_fn_subclase_exclusiva();

DROP TRIGGER IF EXISTS trg_controlador_exclusivo ON Controlador;
CREATE TRIGGER trg_controlador_exclusivo
BEFORE INSERT OR UPDATE ON Controlador
FOR EACH ROW EXECUTE FUNCTION trg_fn_subclase_exclusiva();

-- D.2 Cobertura total: el alta de un equipo crea la superclase y su subclase
--     dentro de la misma transaccion; si una de las dos falla, no queda nada.
CREATE OR REPLACE PROCEDURE sp_registrar_dispositivo(
    p_clase       VARCHAR,
    p_serie       VARCHAR,
    p_modelo      VARCHAR,
    p_fabricante  VARCHAR,
    p_parcela     INTEGER,
    p_zona        INTEGER,
    p_tipo_sensor VARCHAR DEFAULT NULL,
    p_profundidad INTEGER DEFAULT NULL,
    p_sistema     INTEGER DEFAULT NULL,
    p_caudal_lps  NUMERIC DEFAULT NULL,
    p_valvula     VARCHAR DEFAULT NULL)
LANGUAGE plpgsql AS $$
DECLARE
    v_id INTEGER;
BEGIN
    IF p_clase NOT IN ('Sensor', 'Controlador') THEN
        RAISE EXCEPTION 'Clase de dispositivo no valida: %', p_clase;
    END IF;

    INSERT INTO Dispositivo(codigo_serie, modelo, fabricante, fecha_instalacion,
                            id_parcela, num_zona)
    VALUES (p_serie, p_modelo, p_fabricante, CURRENT_DATE, p_parcela, p_zona)
    RETURNING id_dispositivo INTO v_id;

    IF p_clase = 'Sensor' THEN
        INSERT INTO Sensor(id_dispositivo, tipo_sensor, profundidad_cm)
        VALUES (v_id, p_tipo_sensor, p_profundidad);
    ELSE
        INSERT INTO Controlador(id_dispositivo, id_sistema, caudal_max_lps, tipo_valvula)
        VALUES (v_id, p_sistema, p_caudal_lps, p_valvula);
    END IF;
    RAISE NOTICE 'Dispositivo % registrado como %', v_id, p_clase;
END;
$$;
