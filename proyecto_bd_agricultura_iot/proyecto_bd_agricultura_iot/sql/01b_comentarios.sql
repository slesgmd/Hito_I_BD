-- ============================================================
-- Documentacion del esquema (fuente del diccionario de datos)
-- ============================================================
COMMENT ON TABLE Fundo IS 'Predio agrícola de la empresa, ubicado en un distrito del Perú.';
COMMENT ON COLUMN Fundo.id_fundo IS 'Identificador del fundo.';
COMMENT ON COLUMN Fundo.nombre IS 'Nombre comercial del fundo.';
COMMENT ON COLUMN Fundo.departamento IS 'Departamento donde se ubica.';
COMMENT ON COLUMN Fundo.provincia IS 'Provincia donde se ubica.';
COMMENT ON COLUMN Fundo.distrito IS 'Distrito donde se ubica.';
COMMENT ON COLUMN Fundo.area_total_ha IS 'Superficie total del predio en hectáreas.';
COMMENT ON COLUMN Fundo.latitud IS 'Latitud WGS84 del punto de referencia.';
COMMENT ON COLUMN Fundo.longitud IS 'Longitud WGS84 del punto de referencia.';
COMMENT ON COLUMN Fundo.fecha_registro IS 'Fecha en que el fundo se registró en el sistema.';

COMMENT ON TABLE Parcela IS 'Unidad productiva dentro de un fundo; es la base de cada campaña.';
COMMENT ON COLUMN Parcela.id_parcela IS 'Identificador de la parcela.';
COMMENT ON COLUMN Parcela.id_fundo IS 'Fundo al que pertenece.';
COMMENT ON COLUMN Parcela.codigo_parcela IS 'Código interno, único dentro del fundo (P-001, P-002...).';
COMMENT ON COLUMN Parcela.area_ha IS 'Área cultivable en hectáreas.';
COMMENT ON COLUMN Parcela.tipo_suelo IS 'Clase textural del suelo.';
COMMENT ON COLUMN Parcela.pendiente_pct IS 'Pendiente media del terreno en porcentaje.';
COMMENT ON COLUMN Parcela.fecha_habilitacion IS 'Fecha en que la parcela entró en producción.';

COMMENT ON TABLE Zona_Manejo IS 'Subdivisión de una parcela con manejo homogéneo de riego y nutrición (entidad débil).';
COMMENT ON COLUMN Zona_Manejo.id_parcela IS 'Parcela propietaria (parte de la clave).';
COMMENT ON COLUMN Zona_Manejo.num_zona IS 'Número correlativo de la zona dentro de la parcela (clave parcial).';
COMMENT ON COLUMN Zona_Manejo.area_ha IS 'Área de la zona en hectáreas.';
COMMENT ON COLUMN Zona_Manejo.descripcion IS 'Descripción libre de la zona.';

COMMENT ON TABLE Cultivo IS 'Catálogo de especies con sus rangos agronómicos óptimos.';
COMMENT ON COLUMN Cultivo.id_cultivo IS 'Identificador del cultivo.';
COMMENT ON COLUMN Cultivo.nombre_comun IS 'Nombre comercial de la especie o variedad.';
COMMENT ON COLUMN Cultivo.nombre_cientifico IS 'Nombre científico.';
COMMENT ON COLUMN Cultivo.ciclo_dias IS 'Duración típica de la campaña en días.';
COMMENT ON COLUMN Cultivo.humedad_optima_min IS 'Humedad volumétrica mínima recomendada (%).';
COMMENT ON COLUMN Cultivo.humedad_optima_max IS 'Humedad volumétrica máxima recomendada (%).';
COMMENT ON COLUMN Cultivo.ph_optimo_min IS 'pH mínimo recomendado.';
COMMENT ON COLUMN Cultivo.ph_optimo_max IS 'pH máximo recomendado.';
COMMENT ON COLUMN Cultivo.ce_maxima_ds_m IS 'Conductividad eléctrica máxima tolerada (dS/m).';

COMMENT ON TABLE Operario IS 'Personal de campo que riega, aplica insumos, cosecha y mantiene equipos.';
COMMENT ON COLUMN Operario.id_operario IS 'Identificador del operario.';
COMMENT ON COLUMN Operario.dni IS 'Documento Nacional de Identidad (8 dígitos, único).';
COMMENT ON COLUMN Operario.nombre IS 'Nombres.';
COMMENT ON COLUMN Operario.apellido IS 'Apellidos.';
COMMENT ON COLUMN Operario.rol IS 'Función que desempeña en el fundo.';
COMMENT ON COLUMN Operario.telefono IS 'Celular de contacto (9 dígitos).';
COMMENT ON COLUMN Operario.id_fundo IS 'Fundo donde labora habitualmente.';
COMMENT ON COLUMN Operario.fecha_ingreso IS 'Fecha de ingreso a la empresa.';

COMMENT ON TABLE Campania IS 'Periodo de siembra de un cultivo en una parcela.';
COMMENT ON COLUMN Campania.id_campania IS 'Identificador de la campaña.';
COMMENT ON COLUMN Campania.id_parcela IS 'Parcela sembrada.';
COMMENT ON COLUMN Campania.id_cultivo IS 'Cultivo sembrado.';
COMMENT ON COLUMN Campania.fecha_siembra IS 'Fecha de siembra o inicio de campaña.';
COMMENT ON COLUMN Campania.fecha_fin_estimada IS 'Fecha estimada de término (siembra + ciclo).';
COMMENT ON COLUMN Campania.densidad_plantas_ha IS 'Plantas por hectárea.';
COMMENT ON COLUMN Campania.estado IS 'Planificada, En curso, Cerrada o Perdida.';
COMMENT ON COLUMN Campania.rendimiento_kg_ha IS 'Atributo derivado: kg cosechados / área; lo mantiene un trigger.';

COMMENT ON TABLE Sistema_Riego IS 'Infraestructura de riego instalada en una parcela.';
COMMENT ON COLUMN Sistema_Riego.id_sistema IS 'Identificador del sistema.';
COMMENT ON COLUMN Sistema_Riego.id_parcela IS 'Parcela que abastece.';
COMMENT ON COLUMN Sistema_Riego.tipo IS 'Goteo, aspersión, microaspersión o gravedad tecnificada.';
COMMENT ON COLUMN Sistema_Riego.caudal_nominal_lph IS 'Caudal de diseño en litros por hora.';
COMMENT ON COLUMN Sistema_Riego.fuente_agua IS 'Origen del agua.';
COMMENT ON COLUMN Sistema_Riego.fecha_instalacion IS 'Fecha de instalación.';
COMMENT ON COLUMN Sistema_Riego.estado IS 'Operativo, Averiado o Fuera de servicio.';

COMMENT ON TABLE Dispositivo IS 'Superclase de todo equipo IoT instalado en campo.';
COMMENT ON COLUMN Dispositivo.id_dispositivo IS 'Identificador del dispositivo (heredado por las subclases).';
COMMENT ON COLUMN Dispositivo.codigo_serie IS 'Número de serie del fabricante (único).';
COMMENT ON COLUMN Dispositivo.modelo IS 'Modelo comercial.';
COMMENT ON COLUMN Dispositivo.fabricante IS 'Fabricante.';
COMMENT ON COLUMN Dispositivo.fecha_instalacion IS 'Fecha de instalación en campo.';
COMMENT ON COLUMN Dispositivo.estado IS 'Activo, Inactivo, Mantenimiento o Baja.';
COMMENT ON COLUMN Dispositivo.id_parcela IS 'Parcela de la zona donde está instalado.';
COMMENT ON COLUMN Dispositivo.num_zona IS 'Zona de manejo donde está instalado.';

COMMENT ON TABLE Sensor IS 'Subclase de Dispositivo que mide variables del suelo.';
COMMENT ON COLUMN Sensor.id_dispositivo IS 'Clave heredada de Dispositivo.';
COMMENT ON COLUMN Sensor.tipo_sensor IS 'Humedad, Multiparametro, Conductividad, pH o Temperatura.';
COMMENT ON COLUMN Sensor.profundidad_cm IS 'Profundidad de instalación en centímetros.';
COMMENT ON COLUMN Sensor.frecuencia_min IS 'Intervalo de muestreo configurado (minutos).';
COMMENT ON COLUMN Sensor.unidad_medida IS 'Unidad principal que reporta.';
COMMENT ON COLUMN Sensor.rango_min IS 'Límite inferior de medición declarado por el fabricante.';
COMMENT ON COLUMN Sensor.rango_max IS 'Límite superior de medición declarado por el fabricante.';

COMMENT ON TABLE Controlador IS 'Subclase de Dispositivo que abre y cierra válvulas de un sistema de riego.';
COMMENT ON COLUMN Controlador.id_dispositivo IS 'Clave heredada de Dispositivo.';
COMMENT ON COLUMN Controlador.id_sistema IS 'Sistema de riego que acciona.';
COMMENT ON COLUMN Controlador.caudal_max_lps IS 'Caudal máximo que admite la válvula (L/s).';
COMMENT ON COLUMN Controlador.tipo_valvula IS 'Solenoide, hidráulica o manual motorizada.';

COMMENT ON TABLE Lectura_Suelo IS 'Medición enviada por un sensor en un instante (entidad débil).';
COMMENT ON COLUMN Lectura_Suelo.id_dispositivo IS 'Sensor que reporta (parte de la clave).';
COMMENT ON COLUMN Lectura_Suelo.fecha_hora IS 'Instante de la medición, truncado al minuto (clave parcial).';
COMMENT ON COLUMN Lectura_Suelo.humedad_pct IS 'Humedad volumétrica del suelo (%). Nulo si el sensor no la mide.';
COMMENT ON COLUMN Lectura_Suelo.temperatura_c IS 'Temperatura del suelo (°C).';
COMMENT ON COLUMN Lectura_Suelo.ph IS 'pH del suelo. Nulo si el sensor no lo mide.';
COMMENT ON COLUMN Lectura_Suelo.conductividad_ds_m IS 'Conductividad eléctrica (dS/m). Nulo si el sensor no la mide.';
COMMENT ON COLUMN Lectura_Suelo.bateria_pct IS 'Carga de batería del equipo al enviar (%).';

COMMENT ON TABLE Evento_Riego IS 'Riego ejecutado sobre una zona por un sistema.';
COMMENT ON COLUMN Evento_Riego.id_evento IS 'Identificador del evento.';
COMMENT ON COLUMN Evento_Riego.id_sistema IS 'Sistema de riego utilizado.';
COMMENT ON COLUMN Evento_Riego.id_parcela IS 'Parcela de la zona regada.';
COMMENT ON COLUMN Evento_Riego.num_zona IS 'Zona regada.';
COMMENT ON COLUMN Evento_Riego.id_operario IS 'Operario que lo ejecutó o supervisó (nulo si fue automático sin supervisión).';
COMMENT ON COLUMN Evento_Riego.fecha_hora_inicio IS 'Inicio del riego.';
COMMENT ON COLUMN Evento_Riego.duracion_min IS 'Duración en minutos (máximo 720).';
COMMENT ON COLUMN Evento_Riego.volumen_litros IS 'Volumen aplicado; si no se reporta, lo calcula un trigger.';
COMMENT ON COLUMN Evento_Riego.modo IS 'Automatico, Manual o Programado.';

COMMENT ON TABLE Alerta IS 'Aviso generado a partir de una lectura fuera de rango.';
COMMENT ON COLUMN Alerta.id_alerta IS 'Identificador de la alerta.';
COMMENT ON COLUMN Alerta.id_dispositivo IS 'Sensor de la lectura que originó la alerta.';
COMMENT ON COLUMN Alerta.fecha_hora IS 'Instante de la lectura que originó la alerta.';
COMMENT ON COLUMN Alerta.tipo IS 'Humedad baja, Humedad alta, pH fuera de rango, Salinidad alta o Bateria baja.';
COMMENT ON COLUMN Alerta.severidad IS 'Baja, Media, Alta o Critica.';
COMMENT ON COLUMN Alerta.valor_registrado IS 'Valor que disparó la alerta.';
COMMENT ON COLUMN Alerta.atendida IS 'Indica si la alerta fue atendida.';
COMMENT ON COLUMN Alerta.fecha_atencion IS 'Momento de atención; obligatorio si atendida es verdadero.';
COMMENT ON COLUMN Alerta.id_operario IS 'Operario que la atendió.';

COMMENT ON TABLE Cosecha IS 'Registro de un pase de cosecha de una campaña.';
COMMENT ON COLUMN Cosecha.id_cosecha IS 'Identificador del registro.';
COMMENT ON COLUMN Cosecha.id_campania IS 'Campaña cosechada.';
COMMENT ON COLUMN Cosecha.id_operario IS 'Responsable del registro en campo.';
COMMENT ON COLUMN Cosecha.fecha IS 'Fecha de cosecha.';
COMMENT ON COLUMN Cosecha.cantidad_kg IS 'Peso cosechado en kilogramos.';
COMMENT ON COLUMN Cosecha.categoria IS 'Calidad comercial: Primera, Segunda, Tercera o Descarte.';
COMMENT ON COLUMN Cosecha.humedad_producto_pct IS 'Humedad del producto cosechado (%).';
COMMENT ON COLUMN Cosecha.precio_kg_soles IS 'Precio de venta estimado por kilogramo (S/).';

COMMENT ON TABLE Insumo IS 'Catálogo de fertilizantes, enmiendas y productos fitosanitarios.';
COMMENT ON COLUMN Insumo.id_insumo IS 'Identificador del insumo.';
COMMENT ON COLUMN Insumo.nombre IS 'Nombre comercial y concentración.';
COMMENT ON COLUMN Insumo.tipo IS 'Fertilizante, Fungicida, Insecticida, Enmienda o Bioestimulante.';
COMMENT ON COLUMN Insumo.unidad IS 'Unidad de dosificación (kg o L).';
COMMENT ON COLUMN Insumo.costo_unitario IS 'Costo por unidad (S/).';
COMMENT ON COLUMN Insumo.periodo_carencia_dias IS 'Días mínimos entre la aplicación y la cosecha.';

COMMENT ON TABLE Aplicacion_Insumo IS 'Relación ternaria: un operario aplica un insumo en una zona de manejo.';
COMMENT ON COLUMN Aplicacion_Insumo.id_parcela IS 'Parcela de la zona tratada.';
COMMENT ON COLUMN Aplicacion_Insumo.num_zona IS 'Zona tratada.';
COMMENT ON COLUMN Aplicacion_Insumo.id_insumo IS 'Insumo aplicado.';
COMMENT ON COLUMN Aplicacion_Insumo.id_operario IS 'Operario que aplicó.';
COMMENT ON COLUMN Aplicacion_Insumo.fecha_hora IS 'Momento de la aplicación.';
COMMENT ON COLUMN Aplicacion_Insumo.dosis IS 'Cantidad aplicada en la unidad del insumo.';
COMMENT ON COLUMN Aplicacion_Insumo.metodo IS 'Fertirriego, Foliar, Al suelo o Drench.';

COMMENT ON TABLE Mantenimiento IS 'Relación N:M entre operarios y dispositivos que atienden.';
COMMENT ON COLUMN Mantenimiento.id_dispositivo IS 'Equipo intervenido.';
COMMENT ON COLUMN Mantenimiento.id_operario IS 'Técnico que realizó el trabajo.';
COMMENT ON COLUMN Mantenimiento.fecha IS 'Fecha de la intervención.';
COMMENT ON COLUMN Mantenimiento.tipo IS 'Preventivo, Correctivo o Calibracion.';
COMMENT ON COLUMN Mantenimiento.observacion IS 'Detalle del trabajo realizado.';
COMMENT ON COLUMN Mantenimiento.costo IS 'Costo de la intervención (S/).';

COMMENT ON TABLE Auditoria_Campania IS 'Bitácora técnica de cambios de estado de campañas (no forma parte del modelo conceptual).';
COMMENT ON COLUMN Auditoria_Campania.id_auditoria IS 'Identificador del registro de auditoría.';
COMMENT ON COLUMN Auditoria_Campania.id_campania IS 'Campaña modificada.';
COMMENT ON COLUMN Auditoria_Campania.estado_anterior IS 'Estado previo al cambio.';
COMMENT ON COLUMN Auditoria_Campania.estado_nuevo IS 'Estado posterior al cambio.';
COMMENT ON COLUMN Auditoria_Campania.usuario_bd IS 'Usuario de base de datos que hizo el cambio.';
COMMENT ON COLUMN Auditoria_Campania.fecha_cambio IS 'Momento del cambio.';
