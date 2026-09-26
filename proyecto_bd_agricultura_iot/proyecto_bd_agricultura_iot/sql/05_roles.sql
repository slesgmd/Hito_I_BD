-- ============================================================
-- Roles y permisos (opcional). Ejecutar con un superusuario en cada
-- base de datos. Los roles son de todo el cluster; el bloque DO evita
-- errores si ya existen. Despues se asignan a personas con:
--   CREATE USER kiara LOGIN PASSWORD '...' IN ROLE rol_agronomo;
-- ============================================================
DO $$
DECLARE r TEXT;
BEGIN
    FOREACH r IN ARRAY ARRAY['rol_gerencia', 'rol_agronomo', 'rol_operador_riego',
                             'rol_tecnico_campo', 'rol_plataforma_iot'] LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
            EXECUTE format('CREATE ROLE %I NOLOGIN', r);
        END IF;
    END LOOP;
END $$;

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO rol_gerencia, rol_agronomo, rol_operador_riego,
      rol_tecnico_campo, rol_plataforma_iot;

-- Gerencia: solo indicadores ya calculados
GRANT SELECT ON vw_estado_hidrico_zona, vw_produccion_campania, vw_alertas_pendientes
      TO rol_gerencia;

-- Ingeniero agronomo: lectura total; administra campanias y catalogos
GRANT SELECT ON ALL TABLES IN SCHEMA public TO rol_agronomo;
GRANT INSERT, UPDATE ON Campania, Cultivo, Insumo TO rol_agronomo;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO rol_agronomo;
GRANT EXECUTE ON PROCEDURE sp_cerrar_campania(INTEGER) TO rol_agronomo;

-- Operador de riego: registra riegos y atiende alertas
GRANT SELECT ON Lectura_Suelo, Alerta, Evento_Riego, Zona_Manejo, Parcela, Sistema_Riego,
      Dispositivo, Sensor, vw_estado_hidrico_zona, vw_alertas_pendientes TO rol_operador_riego;
GRANT INSERT ON Evento_Riego TO rol_operador_riego;
GRANT UPDATE (atendida, fecha_atencion, id_operario) ON Alerta TO rol_operador_riego;
GRANT USAGE ON SEQUENCE evento_riego_id_evento_seq TO rol_operador_riego;

-- Tecnico de campo: aplicaciones, cosechas y mantenimientos
GRANT SELECT ON Zona_Manejo, Parcela, Insumo, Campania, Dispositivo TO rol_tecnico_campo;
GRANT INSERT ON Aplicacion_Insumo, Cosecha, Mantenimiento TO rol_tecnico_campo;
GRANT USAGE ON SEQUENCE cosecha_id_cosecha_seq TO rol_tecnico_campo;

-- Plataforma IoT: solo puede llamar al procedimiento de registro.
-- SECURITY DEFINER hace que el procedimiento inserte con los permisos
-- de su propietario, sin dar acceso directo a la tabla.
ALTER PROCEDURE sp_registrar_lectura(INTEGER, TIMESTAMP, NUMERIC, NUMERIC, NUMERIC, NUMERIC, INTEGER)
      SECURITY DEFINER SET search_path = public;
REVOKE EXECUTE ON PROCEDURE sp_registrar_lectura(INTEGER, TIMESTAMP, NUMERIC, NUMERIC, NUMERIC,
       NUMERIC, INTEGER) FROM PUBLIC;
GRANT EXECUTE ON PROCEDURE sp_registrar_lectura(INTEGER, TIMESTAMP, NUMERIC, NUMERIC, NUMERIC,
      NUMERIC, INTEGER) TO rol_plataforma_iot;
