-- ============================================================
-- Proyecto: Agricultura de Precision y Sensores IoT Agropecuarios
-- Curso: Base de Datos I (CS2041) - Laboratorio 14 - 2026-2
-- Archivo: 01_ddl.sql  (creacion de esquema)
-- Motor: PostgreSQL 16
-- ============================================================

DROP TABLE IF EXISTS Auditoria_Campania CASCADE;
DROP TABLE IF EXISTS Mantenimiento      CASCADE;
DROP TABLE IF EXISTS Aplicacion_Insumo  CASCADE;
DROP TABLE IF EXISTS Insumo             CASCADE;
DROP TABLE IF EXISTS Cosecha            CASCADE;
DROP TABLE IF EXISTS Alerta             CASCADE;
DROP TABLE IF EXISTS Evento_Riego       CASCADE;
DROP TABLE IF EXISTS Lectura_Suelo      CASCADE;
DROP TABLE IF EXISTS Controlador        CASCADE;
DROP TABLE IF EXISTS Sensor             CASCADE;
DROP TABLE IF EXISTS Dispositivo        CASCADE;
DROP TABLE IF EXISTS Sistema_Riego      CASCADE;
DROP TABLE IF EXISTS Campania           CASCADE;
DROP TABLE IF EXISTS Cultivo            CASCADE;
DROP TABLE IF EXISTS Operario           CASCADE;
DROP TABLE IF EXISTS Zona_Manejo        CASCADE;
DROP TABLE IF EXISTS Parcela            CASCADE;
DROP TABLE IF EXISTS Fundo              CASCADE;

-- ------------------------------------------------------------
-- 1. FUNDO  (entidad fuerte)
-- ------------------------------------------------------------
CREATE TABLE Fundo (
    id_fundo        SERIAL,
    nombre          VARCHAR(60)  NOT NULL,
    departamento    VARCHAR(40)  NOT NULL,
    provincia       VARCHAR(40)  NOT NULL,
    distrito        VARCHAR(40),
    area_total_ha   NUMERIC(8,2) NOT NULL,
    latitud         NUMERIC(9,6),
    longitud        NUMERIC(9,6),
    fecha_registro  DATE         NOT NULL DEFAULT CURRENT_DATE,
    CONSTRAINT pk_fundo          PRIMARY KEY (id_fundo),
    CONSTRAINT uq_fundo_nombre   UNIQUE (nombre, departamento),
    CONSTRAINT ck_fundo_area     CHECK (area_total_ha > 0),
    CONSTRAINT ck_fundo_lat      CHECK (latitud  BETWEEN -19 AND 1),
    CONSTRAINT ck_fundo_lon      CHECK (longitud BETWEEN -82 AND -68)
);

-- ------------------------------------------------------------
-- 2. PARCELA  (entidad fuerte, dependiente de Fundo por FK)
-- ------------------------------------------------------------
CREATE TABLE Parcela (
    id_parcela         SERIAL,
    id_fundo           INTEGER      NOT NULL,
    codigo_parcela     VARCHAR(15)  NOT NULL,
    area_ha            NUMERIC(7,2) NOT NULL,
    tipo_suelo         VARCHAR(20)  NOT NULL,
    pendiente_pct      NUMERIC(4,1),
    fecha_habilitacion DATE,
    CONSTRAINT pk_parcela        PRIMARY KEY (id_parcela),
    CONSTRAINT fk_parcela_fundo  FOREIGN KEY (id_fundo) REFERENCES Fundo(id_fundo)
                                 ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT uq_parcela_codigo UNIQUE (id_fundo, codigo_parcela),
    CONSTRAINT ck_parcela_area   CHECK (area_ha > 0),
    CONSTRAINT ck_parcela_pend   CHECK (pendiente_pct BETWEEN 0 AND 100),
    CONSTRAINT ck_parcela_suelo  CHECK (tipo_suelo IN
        ('Arenoso','Franco','Franco arenoso','Franco arcilloso','Arcilloso'))
);

-- ------------------------------------------------------------
-- 3. ZONA_MANEJO  (entidad debil: depende de Parcela)
--    Clave parcial: num_zona. Clave primaria: (id_parcela, num_zona)
-- ------------------------------------------------------------
CREATE TABLE Zona_Manejo (
    id_parcela   INTEGER      NOT NULL,
    num_zona     SMALLINT     NOT NULL,
    area_ha      NUMERIC(6,2) NOT NULL,
    descripcion  VARCHAR(80),
    CONSTRAINT pk_zona       PRIMARY KEY (id_parcela, num_zona),
    CONSTRAINT fk_zona_parc  FOREIGN KEY (id_parcela) REFERENCES Parcela(id_parcela)
                             ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT ck_zona_num   CHECK (num_zona > 0),
    CONSTRAINT ck_zona_area  CHECK (area_ha > 0)
);

-- ------------------------------------------------------------
-- 4. CULTIVO  (catalogo)
-- ------------------------------------------------------------
CREATE TABLE Cultivo (
    id_cultivo          SERIAL,
    nombre_comun        VARCHAR(40)  NOT NULL,
    nombre_cientifico   VARCHAR(60),
    ciclo_dias          INTEGER      NOT NULL,
    humedad_optima_min  NUMERIC(5,2) NOT NULL,
    humedad_optima_max  NUMERIC(5,2) NOT NULL,
    ph_optimo_min       NUMERIC(4,2) NOT NULL,
    ph_optimo_max       NUMERIC(4,2) NOT NULL,
    ce_maxima_ds_m      NUMERIC(5,2),
    CONSTRAINT pk_cultivo      PRIMARY KEY (id_cultivo),
    CONSTRAINT uq_cultivo_nom  UNIQUE (nombre_comun),
    CONSTRAINT ck_cultivo_hum  CHECK (humedad_optima_min < humedad_optima_max),
    CONSTRAINT ck_cultivo_ph   CHECK (ph_optimo_min < ph_optimo_max
                                      AND ph_optimo_min >= 0 AND ph_optimo_max <= 14),
    CONSTRAINT ck_cultivo_cic  CHECK (ciclo_dias > 0)
);

-- ------------------------------------------------------------
-- 5. OPERARIO
-- ------------------------------------------------------------
CREATE TABLE Operario (
    id_operario    SERIAL,
    dni            CHAR(8)     NOT NULL,
    nombre         VARCHAR(40) NOT NULL,
    apellido       VARCHAR(40) NOT NULL,
    rol            VARCHAR(25) NOT NULL,
    telefono       VARCHAR(9),
    id_fundo       INTEGER,
    fecha_ingreso  DATE,
    CONSTRAINT pk_operario      PRIMARY KEY (id_operario),
    CONSTRAINT uq_operario_dni  UNIQUE (dni),
    CONSTRAINT fk_operario_fun  FOREIGN KEY (id_fundo) REFERENCES Fundo(id_fundo)
                                ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT ck_operario_dni  CHECK (dni ~ '^[0-9]{8}$'),
    CONSTRAINT ck_operario_tel  CHECK (telefono IS NULL OR telefono ~ '^[0-9]{9}$'),
    CONSTRAINT ck_operario_rol  CHECK (rol IN
        ('Tecnico de campo','Ingeniero agronomo','Operador de riego','Supervisor'))
);

-- ------------------------------------------------------------
-- 6. CAMPANIA  (entidad asociativa Parcela x Cultivo con clave propia)
-- ------------------------------------------------------------
CREATE TABLE Campania (
    id_campania          SERIAL,
    id_parcela           INTEGER      NOT NULL,
    id_cultivo           INTEGER      NOT NULL,
    fecha_siembra        DATE         NOT NULL,
    fecha_fin_estimada   DATE         NOT NULL,
    densidad_plantas_ha  INTEGER,
    estado               VARCHAR(15)  NOT NULL DEFAULT 'En curso',
    rendimiento_kg_ha    NUMERIC(10,2) NOT NULL DEFAULT 0,
    CONSTRAINT pk_campania       PRIMARY KEY (id_campania),
    CONSTRAINT fk_campania_parc  FOREIGN KEY (id_parcela) REFERENCES Parcela(id_parcela)
                                 ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_campania_cult  FOREIGN KEY (id_cultivo) REFERENCES Cultivo(id_cultivo)
                                 ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT uq_campania       UNIQUE (id_parcela, fecha_siembra),
    CONSTRAINT ck_campania_fech  CHECK (fecha_fin_estimada > fecha_siembra),
    CONSTRAINT ck_campania_dens  CHECK (densidad_plantas_ha IS NULL OR densidad_plantas_ha > 0),
    CONSTRAINT ck_campania_est   CHECK (estado IN ('Planificada','En curso','Cerrada','Perdida')),
    CONSTRAINT ck_campania_rend  CHECK (rendimiento_kg_ha >= 0)
);

-- ------------------------------------------------------------
-- 7. SISTEMA_RIEGO
-- ------------------------------------------------------------
CREATE TABLE Sistema_Riego (
    id_sistema         SERIAL,
    id_parcela         INTEGER      NOT NULL,
    tipo               VARCHAR(25)  NOT NULL,
    caudal_nominal_lph NUMERIC(8,2) NOT NULL,
    fuente_agua        VARCHAR(20)  NOT NULL,
    fecha_instalacion  DATE,
    estado             VARCHAR(15)  NOT NULL DEFAULT 'Operativo',
    CONSTRAINT pk_sistema        PRIMARY KEY (id_sistema),
    CONSTRAINT fk_sistema_parc   FOREIGN KEY (id_parcela) REFERENCES Parcela(id_parcela)
                                 ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT ck_sistema_caudal CHECK (caudal_nominal_lph > 0),
    CONSTRAINT ck_sistema_tipo   CHECK (tipo IN
        ('Goteo','Aspersion','Microaspersion','Gravedad tecnificada')),
    CONSTRAINT ck_sistema_fuente CHECK (fuente_agua IN ('Pozo','Canal','Reservorio','Rio')),
    CONSTRAINT ck_sistema_estado CHECK (estado IN ('Operativo','Averiado','Fuera de servicio'))
);

-- ------------------------------------------------------------
-- 8. DISPOSITIVO  (superclase de la jerarquia Is-A)
-- ------------------------------------------------------------
CREATE TABLE Dispositivo (
    id_dispositivo    SERIAL,
    codigo_serie      VARCHAR(20) NOT NULL,
    modelo            VARCHAR(30) NOT NULL,
    fabricante        VARCHAR(30),
    fecha_instalacion DATE        NOT NULL,
    estado            VARCHAR(15) NOT NULL DEFAULT 'Activo',
    id_parcela        INTEGER     NOT NULL,
    num_zona          SMALLINT    NOT NULL,
    CONSTRAINT pk_dispositivo      PRIMARY KEY (id_dispositivo),
    CONSTRAINT uq_dispositivo_ser  UNIQUE (codigo_serie),
    CONSTRAINT fk_dispositivo_zona FOREIGN KEY (id_parcela, num_zona)
                                   REFERENCES Zona_Manejo(id_parcela, num_zona)
                                   ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT ck_dispositivo_est  CHECK (estado IN ('Activo','Inactivo','Mantenimiento','Baja'))
);

-- ------------------------------------------------------------
-- 9. SENSOR  (subclase de Dispositivo)
-- ------------------------------------------------------------
CREATE TABLE Sensor (
    id_dispositivo INTEGER      NOT NULL,
    tipo_sensor    VARCHAR(20)  NOT NULL,
    profundidad_cm SMALLINT     NOT NULL,
    frecuencia_min SMALLINT     NOT NULL DEFAULT 15,
    unidad_medida  VARCHAR(10),
    rango_min      NUMERIC(7,2),
    rango_max      NUMERIC(7,2),
    CONSTRAINT pk_sensor       PRIMARY KEY (id_dispositivo),
    CONSTRAINT fk_sensor_disp  FOREIGN KEY (id_dispositivo) REFERENCES Dispositivo(id_dispositivo)
                               ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT ck_sensor_tipo  CHECK (tipo_sensor IN
        ('Humedad','Multiparametro','pH','Conductividad','Temperatura')),
    CONSTRAINT ck_sensor_prof  CHECK (profundidad_cm BETWEEN 0 AND 200),
    CONSTRAINT ck_sensor_frec  CHECK (frecuencia_min > 0),
    CONSTRAINT ck_sensor_rango CHECK (rango_min IS NULL OR rango_max IS NULL OR rango_min < rango_max)
);

-- ------------------------------------------------------------
-- 10. CONTROLADOR  (subclase de Dispositivo)
-- ------------------------------------------------------------
CREATE TABLE Controlador (
    id_dispositivo  INTEGER      NOT NULL,
    id_sistema      INTEGER      NOT NULL,
    caudal_max_lps  NUMERIC(6,2) NOT NULL,
    tipo_valvula    VARCHAR(20)  NOT NULL,
    CONSTRAINT pk_controlador      PRIMARY KEY (id_dispositivo),
    CONSTRAINT fk_controlador_disp FOREIGN KEY (id_dispositivo) REFERENCES Dispositivo(id_dispositivo)
                                   ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_controlador_sis  FOREIGN KEY (id_sistema) REFERENCES Sistema_Riego(id_sistema)
                                   ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT ck_controlador_cau  CHECK (caudal_max_lps > 0),
    CONSTRAINT ck_controlador_val  CHECK (tipo_valvula IN ('Solenoide','Hidraulica','Manual motorizada'))
);

-- ------------------------------------------------------------
-- 11. LECTURA_SUELO  (entidad debil: depende del Sensor)
--     Clave parcial: fecha_hora. PK: (id_dispositivo, fecha_hora)
-- ------------------------------------------------------------
CREATE TABLE Lectura_Suelo (
    id_dispositivo     INTEGER      NOT NULL,
    fecha_hora         TIMESTAMP    NOT NULL,
    humedad_pct        NUMERIC(5,2),
    temperatura_c      NUMERIC(5,2),
    ph                 NUMERIC(4,2),
    conductividad_ds_m NUMERIC(5,2),
    bateria_pct        SMALLINT,
    CONSTRAINT pk_lectura       PRIMARY KEY (id_dispositivo, fecha_hora),
    CONSTRAINT fk_lectura_sens  FOREIGN KEY (id_dispositivo) REFERENCES Sensor(id_dispositivo)
                                ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT ck_lectura_hum   CHECK (humedad_pct   IS NULL OR humedad_pct BETWEEN 0 AND 100),
    CONSTRAINT ck_lectura_temp  CHECK (temperatura_c IS NULL OR temperatura_c BETWEEN -10 AND 60),
    CONSTRAINT ck_lectura_ph    CHECK (ph IS NULL OR ph BETWEEN 0 AND 14),
    CONSTRAINT ck_lectura_ce    CHECK (conductividad_ds_m IS NULL OR conductividad_ds_m >= 0),
    CONSTRAINT ck_lectura_bat   CHECK (bateria_pct IS NULL OR bateria_pct BETWEEN 0 AND 100)
);

-- ------------------------------------------------------------
-- 12. EVENTO_RIEGO
-- ------------------------------------------------------------
CREATE TABLE Evento_Riego (
    id_evento         BIGSERIAL,
    id_sistema        INTEGER       NOT NULL,
    id_parcela        INTEGER       NOT NULL,
    num_zona          SMALLINT      NOT NULL,
    id_operario       INTEGER,
    fecha_hora_inicio TIMESTAMP     NOT NULL,
    duracion_min      INTEGER       NOT NULL,
    volumen_litros    NUMERIC(10,2) NOT NULL,
    modo              VARCHAR(12)   NOT NULL,
    CONSTRAINT pk_evento       PRIMARY KEY (id_evento),
    CONSTRAINT fk_evento_sis   FOREIGN KEY (id_sistema) REFERENCES Sistema_Riego(id_sistema)
                               ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_evento_zona  FOREIGN KEY (id_parcela, num_zona)
                               REFERENCES Zona_Manejo(id_parcela, num_zona)
                               ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_evento_oper  FOREIGN KEY (id_operario) REFERENCES Operario(id_operario)
                               ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT uq_evento       UNIQUE (id_parcela, num_zona, fecha_hora_inicio),
    CONSTRAINT ck_evento_dur   CHECK (duracion_min > 0 AND duracion_min <= 720),
    CONSTRAINT ck_evento_vol   CHECK (volumen_litros >= 0),
    CONSTRAINT ck_evento_modo  CHECK (modo IN ('Automatico','Manual','Programado'))
);

-- ------------------------------------------------------------
-- 13. ALERTA  (se origina en una lectura concreta)
-- ------------------------------------------------------------
CREATE TABLE Alerta (
    id_alerta        BIGSERIAL,
    id_dispositivo   INTEGER      NOT NULL,
    fecha_hora       TIMESTAMP    NOT NULL,
    tipo             VARCHAR(25)  NOT NULL,
    severidad        VARCHAR(10)  NOT NULL,
    valor_registrado NUMERIC(7,2),
    atendida         BOOLEAN      NOT NULL DEFAULT FALSE,
    fecha_atencion   TIMESTAMP,
    id_operario      INTEGER,
    CONSTRAINT pk_alerta       PRIMARY KEY (id_alerta),
    CONSTRAINT fk_alerta_lect  FOREIGN KEY (id_dispositivo, fecha_hora)
                               REFERENCES Lectura_Suelo(id_dispositivo, fecha_hora)
                               ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_alerta_oper  FOREIGN KEY (id_operario) REFERENCES Operario(id_operario)
                               ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT uq_alerta       UNIQUE (id_dispositivo, fecha_hora, tipo),
    CONSTRAINT ck_alerta_tipo  CHECK (tipo IN
        ('Humedad baja','Humedad alta','pH fuera de rango','Salinidad alta','Bateria baja')),
    CONSTRAINT ck_alerta_sev   CHECK (severidad IN ('Baja','Media','Alta','Critica')),
    CONSTRAINT ck_alerta_aten  CHECK ((atendida = FALSE AND fecha_atencion IS NULL)
                                   OR (atendida = TRUE  AND fecha_atencion IS NOT NULL))
);

-- ------------------------------------------------------------
-- 14. COSECHA
-- ------------------------------------------------------------
CREATE TABLE Cosecha (
    id_cosecha           SERIAL,
    id_campania          INTEGER       NOT NULL,
    id_operario          INTEGER,
    fecha                DATE          NOT NULL,
    cantidad_kg          NUMERIC(10,2) NOT NULL,
    categoria            VARCHAR(12)   NOT NULL,
    humedad_producto_pct NUMERIC(5,2),
    precio_kg_soles      NUMERIC(7,2),
    CONSTRAINT pk_cosecha       PRIMARY KEY (id_cosecha),
    CONSTRAINT fk_cosecha_camp  FOREIGN KEY (id_campania) REFERENCES Campania(id_campania)
                                ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_cosecha_oper  FOREIGN KEY (id_operario) REFERENCES Operario(id_operario)
                                ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT ck_cosecha_kg    CHECK (cantidad_kg > 0),
    CONSTRAINT ck_cosecha_cat   CHECK (categoria IN ('Primera','Segunda','Tercera','Descarte')),
    CONSTRAINT ck_cosecha_hum   CHECK (humedad_producto_pct IS NULL
                                       OR humedad_producto_pct BETWEEN 0 AND 100),
    CONSTRAINT ck_cosecha_prec  CHECK (precio_kg_soles IS NULL OR precio_kg_soles >= 0)
);

-- ------------------------------------------------------------
-- 15. INSUMO
-- ------------------------------------------------------------
CREATE TABLE Insumo (
    id_insumo             SERIAL,
    nombre                VARCHAR(50)  NOT NULL,
    tipo                  VARCHAR(20)  NOT NULL,
    unidad                VARCHAR(10)  NOT NULL,
    costo_unitario        NUMERIC(8,2) NOT NULL,
    periodo_carencia_dias SMALLINT,
    CONSTRAINT pk_insumo      PRIMARY KEY (id_insumo),
    CONSTRAINT uq_insumo_nom  UNIQUE (nombre),
    CONSTRAINT ck_insumo_tipo CHECK (tipo IN
        ('Fertilizante','Fungicida','Insecticida','Enmienda','Bioestimulante')),
    CONSTRAINT ck_insumo_cost CHECK (costo_unitario >= 0),
    CONSTRAINT ck_insumo_car  CHECK (periodo_carencia_dias IS NULL OR periodo_carencia_dias >= 0)
);

-- ------------------------------------------------------------
-- 16. APLICACION_INSUMO  (relacion ternaria Zona x Insumo x Operario)
-- ------------------------------------------------------------
CREATE TABLE Aplicacion_Insumo (
    id_parcela  INTEGER      NOT NULL,
    num_zona    SMALLINT     NOT NULL,
    id_insumo   INTEGER      NOT NULL,
    id_operario INTEGER      NOT NULL,
    fecha_hora  TIMESTAMP    NOT NULL,
    dosis       NUMERIC(8,2) NOT NULL,
    metodo      VARCHAR(20)  NOT NULL,
    CONSTRAINT pk_aplicacion      PRIMARY KEY (id_parcela, num_zona, id_insumo, id_operario, fecha_hora),
    CONSTRAINT fk_aplicacion_zona FOREIGN KEY (id_parcela, num_zona)
                                  REFERENCES Zona_Manejo(id_parcela, num_zona)
                                  ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_aplicacion_ins  FOREIGN KEY (id_insumo) REFERENCES Insumo(id_insumo)
                                  ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_aplicacion_ope  FOREIGN KEY (id_operario) REFERENCES Operario(id_operario)
                                  ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT ck_aplicacion_dos  CHECK (dosis > 0),
    CONSTRAINT ck_aplicacion_met  CHECK (metodo IN ('Fertirriego','Foliar','Al suelo','Drench'))
);

-- ------------------------------------------------------------
-- 17. MANTENIMIENTO  (relacion N:M Operario x Dispositivo)
-- ------------------------------------------------------------
CREATE TABLE Mantenimiento (
    id_dispositivo INTEGER      NOT NULL,
    id_operario    INTEGER      NOT NULL,
    fecha          DATE         NOT NULL,
    tipo           VARCHAR(15)  NOT NULL,
    observacion    VARCHAR(120),
    costo          NUMERIC(8,2),
    CONSTRAINT pk_mantenimiento      PRIMARY KEY (id_dispositivo, id_operario, fecha),
    CONSTRAINT fk_mantenimiento_disp FOREIGN KEY (id_dispositivo) REFERENCES Dispositivo(id_dispositivo)
                                     ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_mantenimiento_oper FOREIGN KEY (id_operario) REFERENCES Operario(id_operario)
                                     ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT ck_mantenimiento_tipo CHECK (tipo IN ('Preventivo','Correctivo','Calibracion')),
    CONSTRAINT ck_mantenimiento_cost CHECK (costo IS NULL OR costo >= 0)
);

-- ------------------------------------------------------------
-- 18. AUDITORIA_CAMPANIA  (bitacora alimentada por trigger)
-- ------------------------------------------------------------
CREATE TABLE Auditoria_Campania (
    id_auditoria    BIGSERIAL,
    id_campania     INTEGER     NOT NULL,
    estado_anterior VARCHAR(15),
    estado_nuevo    VARCHAR(15),
    usuario_bd      VARCHAR(40) NOT NULL DEFAULT CURRENT_USER,
    fecha_cambio    TIMESTAMP   NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_auditoria PRIMARY KEY (id_auditoria)
);
