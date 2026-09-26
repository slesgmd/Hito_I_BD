-- Consulta 5 reescrita: el EXISTS correlacionado se evalua una sola vez por
-- alerta y el resultado se reutiliza en las dos agregaciones.
WITH evaluadas AS (
    SELECT f.nombre AS fundo,
           EXISTS (
               SELECT 1
               FROM Evento_Riego er
               WHERE er.id_parcela = d.id_parcela
                 AND er.num_zona   = d.num_zona
                 AND er.fecha_hora_inicio >  a.fecha_hora
                 AND er.fecha_hora_inicio <= a.fecha_hora + INTERVAL '6 hours'
           ) AS con_riego
    FROM Alerta       a
    JOIN Dispositivo  d ON d.id_dispositivo = a.id_dispositivo
    JOIN Parcela      p ON p.id_parcela = d.id_parcela
    JOIN Fundo        f ON f.id_fundo   = p.id_fundo
    WHERE a.tipo = 'Humedad baja'
      AND a.severidad IN ('Alta','Critica')
)
SELECT fundo,
       COUNT(*)                                                    AS alertas,
       COUNT(*) FILTER (WHERE con_riego)                           AS atendidas_con_riego,
       ROUND(100.0 * COUNT(*) FILTER (WHERE con_riego) / COUNT(*), 2) AS pct_respuesta
FROM evaluadas
GROUP BY fundo
HAVING COUNT(*) > 3
ORDER BY pct_respuesta ASC;
