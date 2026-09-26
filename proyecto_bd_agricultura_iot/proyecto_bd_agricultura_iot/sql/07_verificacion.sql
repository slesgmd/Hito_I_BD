-- ============================================================
-- Verificacion de consistencia posterior a la carga masiva.
-- Cada columna cuenta violaciones; el resultado esperado es 0.
-- ============================================================
SELECT
 (SELECT count(*) FROM Evento_Riego e JOIN Sistema_Riego s USING (id_sistema)
   WHERE s.id_parcela <> e.id_parcela)                                   AS riego_otra_parcela,
 (SELECT count(*) FROM Controlador c JOIN Dispositivo d USING (id_dispositivo)
   JOIN Sistema_Riego s USING (id_sistema)
   WHERE s.id_parcela <> d.id_parcela)                                   AS controlador_otra_parcela,
 (SELECT count(*) FROM (SELECT id_parcela FROM Campania WHERE estado = 'En curso'
   GROUP BY id_parcela HAVING count(*) > 1) x)                           AS parcelas_dos_vigentes,
 (SELECT count(*) FROM Campania a JOIN Campania b
     ON a.id_parcela = b.id_parcela AND a.id_campania < b.id_campania
    AND a.fecha_siembra < b.fecha_fin_estimada
    AND a.fecha_fin_estimada > b.fecha_siembra)                          AS campanias_superpuestas,
 (SELECT count(*) FROM Cosecha co JOIN Campania ca USING (id_campania)
   WHERE co.fecha < ca.fecha_siembra)                                    AS cosechas_antes_siembra,
 (SELECT count(*) FROM Cosecha co JOIN Campania ca USING (id_campania)
   WHERE ca.estado = 'Perdida')                                          AS cosechas_campania_perdida,
 (SELECT count(*) FROM Dispositivo d
   WHERE (EXISTS (SELECT 1 FROM Sensor s WHERE s.id_dispositivo = d.id_dispositivo))::int
       + (EXISTS (SELECT 1 FROM Controlador c WHERE c.id_dispositivo = d.id_dispositivo))::int
       <> 1)                                                             AS fuera_jerarquia_isa,
 (SELECT count(*) FROM Campania ca
   WHERE ca.rendimiento_kg_ha <> COALESCE((SELECT ROUND(SUM(co.cantidad_kg) / MAX(p.area_ha), 2)
          FROM Cosecha co JOIN Parcela p ON p.id_parcela = ca.id_parcela
          WHERE co.id_campania = ca.id_campania), 0))                    AS rendimiento_desactualizado;
