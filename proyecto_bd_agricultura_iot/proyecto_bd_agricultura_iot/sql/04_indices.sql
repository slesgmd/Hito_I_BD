-- ============================================================
-- Indices propuestos para el experimento de optimizacion
-- Nota: PostgreSQL ya crea un B+ tree por cada PRIMARY KEY y UNIQUE.
-- No se duplican: uq_evento (id_parcela, num_zona, fecha_hora_inicio),
-- uq_campania (id_parcela, fecha_siembra) y uq_parcela_codigo
-- (id_fundo, codigo_parcela) ya cubren esos caminos de acceso.
-- ============================================================

-- ---- Consulta 1: filtro por rango de fechas sobre la tabla de lecturas
CREATE INDEX IF NOT EXISTS idx_lectura_fecha
    ON Lectura_Suelo USING btree (fecha_hora) INCLUDE (id_dispositivo, humedad_pct);
CREATE INDEX IF NOT EXISTS idx_campania_vigente
    ON Campania USING btree (id_parcela) WHERE estado = 'En curso';
CREATE INDEX IF NOT EXISTS idx_dispositivo_zona
    ON Dispositivo USING btree (id_parcela, num_zona);

-- ---- Consulta 2: union por rango entre eventos de riego y campanias
CREATE INDEX IF NOT EXISTS idx_evento_parcela_fecha
    ON Evento_Riego USING btree (id_parcela, fecha_hora_inicio);
CREATE INDEX IF NOT EXISTS idx_cosecha_campania
    ON Cosecha USING hash (id_campania);

-- ---- Consulta 3: agregacion por sensor sobre toda la serie
CREATE INDEX IF NOT EXISTS idx_lectura_disp_humedad
    ON Lectura_Suelo USING btree (id_dispositivo) INCLUDE (humedad_pct);

-- ---- Consulta 4: ranking de rendimiento por fundo
CREATE INDEX IF NOT EXISTS idx_cosecha_categoria
    ON Cosecha USING btree (categoria, id_campania) INCLUDE (cantidad_kg);
CREATE INDEX IF NOT EXISTS idx_campania_cultivo
    ON Campania USING btree (id_cultivo);

-- ---- Consulta 5: alertas criticas de humedad (la subconsulta correlacionada
--      sobre Evento_Riego usa el indice de la restriccion uq_evento)
CREATE INDEX IF NOT EXISTS idx_alerta_humedad_baja
    ON Alerta USING btree (severidad, id_dispositivo, fecha_hora)
    WHERE tipo = 'Humedad baja';
