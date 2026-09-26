-- ============================================================
-- Pruebas de procedimientos, funciones y triggers.
-- Todo corre dentro de una transaccion que se revierte al final,
-- de modo que la base queda intacta.
-- ============================================================
\set ON_ERROR_STOP off
\pset footer off
BEGIN;
SELECT ca.id_parcela AS par, ca.id_campania AS camp FROM Campania ca
 WHERE ca.estado = 'En curso' ORDER BY ca.id_parcela LIMIT 1 \gset
SELECT id_sistema AS sis FROM Sistema_Riego WHERE id_parcela = :par LIMIT 1 \gset
SELECT id_sistema AS sis_otro FROM Sistema_Riego WHERE id_parcela <> :par LIMIT 1 \gset

\echo '--- P1. sp_registrar_dispositivo crea la superclase y la subclase'
CALL sp_registrar_dispositivo('Sensor', 'SN-PRUEBA-01', 'TEROS 12', 'METER Group',
                              :par, 1, 'Conductividad', 30);
SELECT d.id_dispositivo, d.modelo, s.tipo_sensor, s.profundidad_cm
  FROM Dispositivo d JOIN Sensor s USING (id_dispositivo)
 WHERE d.codigo_serie = 'SN-PRUEBA-01';
SELECT id_dispositivo AS nuevo FROM Dispositivo WHERE codigo_serie = 'SN-PRUEBA-01' \gset

\echo '--- P2. Si falla la subclase no queda un dispositivo huerfano'
SAVEPOINT p2;
CALL sp_registrar_dispositivo('Controlador', 'SN-PRUEBA-02', 'ACC2', 'Hunter', :par, 1);
ROLLBACK TO p2;
SELECT count(*) AS filas_con_serie_prueba_02 FROM Dispositivo WHERE codigo_serie = 'SN-PRUEBA-02';

\echo '--- P3. Disjuncion: el sensor no puede registrarse ademas como controlador'
SAVEPOINT p3;
INSERT INTO Controlador VALUES (:nuevo, :sis, 5.0, 'Solenoide');
ROLLBACK TO p3;

\echo '--- P4. Una lectura con humedad critica y bateria baja genera dos alertas'
CALL sp_registrar_lectura(:nuevo, '2026-09-19 07:00', 10.0, 21.5, NULL, 1.10, 6);
SELECT tipo, severidad, valor_registrado FROM Alerta WHERE id_dispositivo = :nuevo ORDER BY tipo;

\echo '--- P5. Una lectura repetida en el mismo minuto se ignora'
CALL sp_registrar_lectura(:nuevo, '2026-09-19 07:00', 55.0, 21.5);
SELECT count(*) AS lecturas_del_sensor, max(humedad_pct) AS humedad_guardada
  FROM Lectura_Suelo WHERE id_dispositivo = :nuevo;

\echo '--- P6. Un riego con el sistema de otra parcela se rechaza'
SAVEPOINT p6;
INSERT INTO Evento_Riego (id_sistema, id_parcela, num_zona, fecha_hora_inicio, duracion_min,
                          volumen_litros, modo)
VALUES (:sis_otro, :par, 1, '2026-09-19 06:00', 30, 0, 'Manual');
ROLLBACK TO p6;

\echo '--- P7. Si el volumen llega en cero se calcula con el caudal nominal'
INSERT INTO Evento_Riego (id_sistema, id_parcela, num_zona, fecha_hora_inicio, duracion_min,
                          volumen_litros, modo)
VALUES (:sis, :par, 1, '2026-09-19 06:00', 30, 0, 'Manual');
SELECT e.duracion_min, s.caudal_nominal_lph, e.volumen_litros
  FROM Evento_Riego e JOIN Sistema_Riego s USING (id_sistema)
 WHERE e.id_parcela = :par AND e.num_zona = 1 AND e.fecha_hora_inicio = '2026-09-19 06:00';

\echo '--- P8. No se permite una campania superpuesta con la vigente'
SAVEPOINT p8;
INSERT INTO Campania (id_parcela, id_cultivo, fecha_siembra, fecha_fin_estimada,
                      densidad_plantas_ha, estado)
SELECT id_parcela, id_cultivo, DATE '2026-09-01', DATE '2026-12-01', 2500, 'Planificada'
  FROM Campania WHERE id_campania = :camp;
ROLLBACK TO p8;

\echo '--- P9. Una cosecha nueva actualiza el rendimiento derivado'
SELECT rendimiento_kg_ha AS rendimiento_antes FROM Campania WHERE id_campania = :camp;
INSERT INTO Cosecha (id_campania, id_operario, fecha, cantidad_kg, categoria)
VALUES (:camp, 1, '2026-09-19', 5000, 'Primera');
SELECT ca.rendimiento_kg_ha AS rendimiento_despues, p.area_ha
  FROM Campania ca JOIN Parcela p USING (id_parcela) WHERE ca.id_campania = :camp;

\echo '--- P10. sp_cerrar_campania cierra la campania y deja rastro en la auditoria'
CALL sp_cerrar_campania(:camp);
SELECT estado, rendimiento_kg_ha FROM Campania WHERE id_campania = :camp;
SELECT estado_anterior, estado_nuevo, usuario_bd FROM Auditoria_Campania WHERE id_campania = :camp;

\echo '--- P11. Una alerta no puede marcarse como atendida sin fecha de atencion'
SAVEPOINT p11;
UPDATE Alerta SET atendida = TRUE, fecha_atencion = NULL
 WHERE id_alerta = (SELECT min(id_alerta) FROM Alerta WHERE NOT atendida);
ROLLBACK TO p11;

\echo '--- P12. Funciones de consulta'
SELECT * FROM fn_balance_hidrico(:par, '2026-08-01', '2026-09-15');
SELECT fn_costo_insumos(:par, '2026-01-01', '2026-09-15') AS costo_insumos_soles;

ROLLBACK;
