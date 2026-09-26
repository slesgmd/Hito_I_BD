-- ============================================================
-- Consultas intermedias seleccionadas para el experimento
-- ============================================================

-- ---------- CONSULTA 1 -------------------------------------------------
-- Parcelas con estres hidrico: la humedad media del ultimo mes esta por
-- debajo del minimo optimo del cultivo que tienen sembrado.
SELECT f.nombre                       AS fundo,
       p.codigo_parcela,
       cu.nombre_comun                AS cultivo,
       ROUND(AVG(l.humedad_pct), 2)   AS humedad_promedio,
       MIN(cu.humedad_optima_min)     AS umbral_minimo,
       COUNT(*)                       AS lecturas_evaluadas
FROM Lectura_Suelo l
JOIN Sensor       s  ON s.id_dispositivo = l.id_dispositivo
JOIN Dispositivo  d  ON d.id_dispositivo = s.id_dispositivo
JOIN Zona_Manejo  z  ON z.id_parcela = d.id_parcela AND z.num_zona = d.num_zona
JOIN Parcela      p  ON p.id_parcela = z.id_parcela
JOIN Fundo        f  ON f.id_fundo   = p.id_fundo
JOIN Campania     ca ON ca.id_parcela = p.id_parcela AND ca.estado = 'En curso'
JOIN Cultivo      cu ON cu.id_cultivo = ca.id_cultivo
WHERE l.fecha_hora >= TIMESTAMP '2026-08-16 00:00:00'
  AND l.fecha_hora <  TIMESTAMP '2026-09-16 00:00:00'
  AND l.humedad_pct IS NOT NULL
GROUP BY f.nombre, p.codigo_parcela, cu.nombre_comun
HAVING AVG(l.humedad_pct) < MIN(cu.humedad_optima_min)
ORDER BY humedad_promedio ASC;

-- ---------- CONSULTA 2 -------------------------------------------------
-- Eficiencia hidrica por campania (litros aplicados por kilogramo cosechado),
-- restringida a las campanias que consumen mas agua que el promedio general.
WITH riego AS (
    SELECT ca.id_campania,
           SUM(er.volumen_litros) AS litros_aplicados
    FROM Evento_Riego er
    JOIN Campania ca
      ON ca.id_parcela = er.id_parcela
     AND er.fecha_hora_inicio >= ca.fecha_siembra
     AND er.fecha_hora_inicio <  ca.fecha_fin_estimada
    GROUP BY ca.id_campania
),
produccion AS (
    SELECT id_campania, SUM(cantidad_kg) AS kilos
    FROM Cosecha
    GROUP BY id_campania
)
SELECT f.nombre                                  AS fundo,
       cu.nombre_comun                           AS cultivo,
       r.id_campania,
       ROUND(r.litros_aplicados, 2)              AS litros,
       ROUND(pr.kilos, 2)                        AS kilos,
       ROUND(r.litros_aplicados / pr.kilos, 2)   AS litros_por_kilo
FROM riego r
JOIN produccion pr ON pr.id_campania = r.id_campania
JOIN Campania  ca  ON ca.id_campania = r.id_campania
JOIN Parcela   p   ON p.id_parcela   = ca.id_parcela
JOIN Fundo     f   ON f.id_fundo     = p.id_fundo
JOIN Cultivo   cu  ON cu.id_cultivo  = ca.id_cultivo
WHERE r.litros_aplicados > (SELECT AVG(litros_aplicados) FROM riego)
ORDER BY litros_por_kilo DESC;

-- ---------- CONSULTA 3 -------------------------------------------------
-- Sensores cuya proporcion de lecturas fuera del rango optimo del cultivo
-- supera la proporcion promedio de toda la red.
WITH medidas AS (
    SELECT l.id_dispositivo,
           COUNT(*) AS total,
           COUNT(*) FILTER (
               WHERE l.humedad_pct < cu.humedad_optima_min
                  OR l.humedad_pct > cu.humedad_optima_max) AS anomalas
    FROM Lectura_Suelo l
    JOIN Dispositivo d  ON d.id_dispositivo = l.id_dispositivo
    JOIN Campania   ca  ON ca.id_parcela = d.id_parcela AND ca.estado = 'En curso'
    JOIN Cultivo    cu  ON cu.id_cultivo = ca.id_cultivo
    WHERE l.humedad_pct IS NOT NULL
    GROUP BY l.id_dispositivo
)
SELECT d.codigo_serie,
       s.tipo_sensor,
       p.codigo_parcela,
       m.total,
       m.anomalas,
       ROUND(100.0 * m.anomalas / m.total, 2) AS pct_anomalas
FROM medidas m
JOIN Sensor      s ON s.id_dispositivo = m.id_dispositivo
JOIN Dispositivo d ON d.id_dispositivo = m.id_dispositivo
JOIN Parcela     p ON p.id_parcela = d.id_parcela
WHERE m.total >= 5
  AND 1.0 * m.anomalas / m.total >
      (SELECT SUM(anomalas)::numeric / NULLIF(SUM(total), 0) FROM medidas)
ORDER BY pct_anomalas DESC, m.total DESC;

-- ---------- CONSULTA 4 -------------------------------------------------
-- Ranking de rendimiento (kg/ha) por fundo usando funcion de ventana,
-- considerando solo la produccion de primera y segunda categoria.
WITH rendimiento AS (
    SELECT f.id_fundo,
           f.nombre           AS fundo,
           cu.nombre_comun    AS cultivo,
           ca.id_campania,
           p.area_ha,
           SUM(co.cantidad_kg) AS kilos
    FROM Cosecha  co
    JOIN Campania ca ON ca.id_campania = co.id_campania
    JOIN Parcela  p  ON p.id_parcela   = ca.id_parcela
    JOIN Fundo    f  ON f.id_fundo     = p.id_fundo
    JOIN Cultivo  cu ON cu.id_cultivo  = ca.id_cultivo
    WHERE co.categoria IN ('Primera','Segunda')
    GROUP BY f.id_fundo, f.nombre, cu.nombre_comun, ca.id_campania, p.area_ha
)
SELECT fundo,
       cultivo,
       id_campania,
       ROUND(kilos / area_ha, 2) AS kg_por_ha,
       RANK() OVER (PARTITION BY id_fundo ORDER BY kilos / area_ha DESC) AS puesto,
       ROUND(AVG(kilos / area_ha) OVER (PARTITION BY id_fundo), 2) AS promedio_fundo
FROM rendimiento
ORDER BY fundo, puesto;

-- ---------- CONSULTA 5 -------------------------------------------------
-- Tiempo de respuesta operativa: porcentaje de alertas de humedad baja que
-- recibieron riego en la zona afectada dentro de las 6 horas siguientes.
SELECT f.nombre AS fundo,
       COUNT(*) AS alertas,
       COUNT(*) FILTER (WHERE EXISTS (
            SELECT 1
            FROM Evento_Riego er
            WHERE er.id_parcela = d.id_parcela
              AND er.num_zona   = d.num_zona
              AND er.fecha_hora_inicio >  a.fecha_hora
              AND er.fecha_hora_inicio <= a.fecha_hora + INTERVAL '6 hours'
       )) AS atendidas_con_riego,
       ROUND(100.0 * COUNT(*) FILTER (WHERE EXISTS (
            SELECT 1
            FROM Evento_Riego er
            WHERE er.id_parcela = d.id_parcela
              AND er.num_zona   = d.num_zona
              AND er.fecha_hora_inicio >  a.fecha_hora
              AND er.fecha_hora_inicio <= a.fecha_hora + INTERVAL '6 hours'
       )) / COUNT(*), 2) AS pct_respuesta
FROM Alerta       a
JOIN Dispositivo  d ON d.id_dispositivo = a.id_dispositivo
JOIN Parcela      p ON p.id_parcela = d.id_parcela
JOIN Fundo        f ON f.id_fundo   = p.id_fundo
WHERE a.tipo = 'Humedad baja'
  AND a.severidad IN ('Alta','Critica')
GROUP BY f.nombre
HAVING COUNT(*) > 3
ORDER BY pct_respuesta ASC;
