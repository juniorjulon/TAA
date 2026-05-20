# Discurso TAA — Comité de Inversiones
**Duración estimada:** 6 minutos 30 segundos  
**Ritmo:** ~130 palabras/minuto → ~850 palabras totales  
**Guía de tiempo:** [🕐 0:00] = comienzo | ⏱ = pausa natural | Total 10 slides

---

## Slide 1 — Portada: TAA System Methodology

[🕐 0:00]

Buenos días. En los próximos siete minutos voy a presentarles el sistema de Asignación Táctica de Activos que hemos desarrollado para las cuatro carteras de Rimac. ⏱

El objetivo es simple: generar señales cuantitativas, reproducibles y explicables que nos digan, semana a semana, cuándo movernos dentro de los rangos tácticos permitidos por nuestra política de inversión. ⏱

Este no es un modelo de caja negra. Cada decisión metodológica tiene un respaldo en la literatura académica y, más importante, tiene sentido económico. Eso es lo que vamos a revisar juntos.

---

## Slide 2 — TAA System at a Glance

[🕐 0:40]

El sistema procesa **97 señales de mercado** organizadas en **diez clases de activo** y **cuatro pilares de análisis**. ⏱

El flujo es lineal: primero cargamos los datos del Excel de inputs, los normalizamos a z-scores, los combinamos en pilares, y esos pilares generan un z-score compuesto por clase de activo. Ese z-score se convierte en una convicción —alta, media o neutral— que determina el tamaño del tilt táctico. ⏱

Todo el sistema cumple dos restricciones institucionales no negociables: primero, **no posiciones cortas**, por mandato de Solvencia II. Segundo, **zero-sum**: si subimos una clase de activo, necesariamente bajamos otra dentro del mismo presupuesto de tracking error.

---

## Slide 3 — The Four Signal Pillars

[🕐 1:20]

Los cuatro pilares capturan dimensiones independientes del mercado. ⏱

**Fundamentals** responde a: ¿el entorno macro favorece esta clase de activo? PMI, revisiones de PIB, sorpresas económicas, revisiones de utilidades.

**Momentum** responde a: ¿el precio está en tendencia? Utilizamos momentum de 12 meses menos 1 mes —que es el benchmark de la literatura desde Jegadeesh y Titman de 1993— más retorno de 3 meses, cruce de medias móviles y RSI.

**Sentiment** responde a: ¿el mercado está con miedo o con euforia? VIX, MOVE, el ratio Put/Call. Y ojo: estas señales son **contrarias** —el miedo extremo es señal de compra.

**Valuation** responde a: ¿está caro o barato el activo versus su historia? Prime de riesgo de renta variable, OAS de crédito, niveles de rendimiento real.

Cada pilar tiene un peso del **25%** —ponderación igualitaria— un enfoque respaldado por DeMiguel, Garlappi y Uppal en 2009, quienes demostraron que el peso 1/N es difícil de superar fuera de muestra cuando no tenemos certeza sobre los pesos óptimos.

---

## Slide 4 — Signal Normalization Framework

[🕐 2:15]

Aquí está la pregunta que más me hicieron cuando expliqué el sistema: **¿por qué el z-score de una señal no es comparable con el de otra?** ⏱

La respuesta es que un z-score siempre dice: *"qué tan lejos está el valor de hoy de su referencia histórica, medido en unidades de su propia variabilidad."* Pero esa referencia y esa variabilidad se definen diferente para cada tipo de serie. ⏱

El PMI oscila alrededor de 50 con distribución aproximadamente normal. Se normaliza con un promedio exponencialmente ponderado —**ewma_z**— que se adapta al régimen actual.

El OAS de high yield, en cambio, es muy sesgado a la derecha: sube a 1.500 puntos en crisis y vuelve a 300 en normalidad. Si usáramos la misma fórmula, la crisis de 2020 distorsionaría todos los z-scores futuros. Por eso usamos **percentil histórico** —que no asume ninguna distribución y es robusto a colas gruesas.

Las revisiones de utilidades son distintas: lo que importa no es el nivel de EPS, sino si los analistas están revisando *más rápido o más lento que lo normal*. Eso requiere normalizar la **tasa de cambio**, no el nivel.

En resumen: cada código de transformación responde a una pregunta económica diferente sobre una serie con propiedades estadísticas diferentes. No son caprichos metodológicos —son decisiones defensibles.

---

## Slide 5 — Pillar Detail: Fundamentals & Momentum

[🕐 3:30]

No voy a entrar en cada señal, pero destaco dos elementos metodológicos clave. ⏱

En Fundamentals, las señales de crecimiento —PMI, PIB, sorpresas— tienen **signo opuesto** según la clase de activo. Para renta variable, crecimiento es alcista. Para bonos del tesoro de larga duración, crecimiento es bajista, porque implica tasas más altas y precios de bonos más bajos. El signo vive en la hoja de configuración de Excel —nunca se invierte en el código Python.

En Momentum, el z-score de precio composite pondera cuatro horizontes: el de 12 menos 1 meses tiene el 40% del peso porque es el más documentado en la literatura; los de corto plazo complementan. Ninguna señal individual determina el momentum.

---

## Slide 6 — Pillar Detail: Sentiment & Valuation

[🕐 4:05]

Dos señales de sentimiento merecen atención especial. ⏱

Primero, el **VIX**: un VIX alto no es directamente bajista para la renta variable. Es una señal **contraria**: el pánico extremo históricamente precede a rebotes. Baker y Wurgler en 2007 y Whaley en 2000 documentaron esto extensamente.

Segundo, el ratio **Put/Call de CBOE**: cuando los inversionistas compran pocas opciones de protección, están siendo complacientes. Eso también es una señal contraria de advertencia —incorporada en mayo de 2026.

En Valuation, una aclaración importante: la **prima de riesgo de renta variable** —utilidad esperada menos rendimiento real de TIPS— es la métrica central de valoración relativa entre acciones y bonos. Actualmente está comprimida históricamente en EE.UU., lo que apunta a que la renta variable americana está cara vs bonos, aunque no necesariamente cara en términos absolutos.

---

## Slide 7 — From Signals to Composite Z-Score

[🕐 4:50]

El flujo técnico es: normalizar cada señal, combinarlas con promedio ponderado dentro del pilar, re-estandarizar el pilar —porque la correlación entre señales reduce la varianza compuesta— y combinar los cuatro pilares en el z-score final. ⏱

El z-score compuesto luego pasa por un filtro de **convicción**: necesitamos al menos tres de cuatro pilares apuntando en la misma dirección para generar un tilt máximo. Si solo uno apunta en esa dirección, el tilt es cero —no generamos ruido.

---

## Slide 8 — Conviction Framework

[🕐 5:20]

Los umbrales son: z mayor a 1.5 es HIGH Overweight, entre 0.75 y 1.5 es MEDIUM Overweight, entre -0.75 y 0.75 es Neutral. Simétrico al otro lado. ⏱

El multiplicador de convicción penaliza cuando los pilares no acuerdan: cuatro pilares alineados = 100%; tres de cuatro = 80%; dos de cuatro = 50%; uno de cuatro = 0%. Esto es lo que Wang y Kochard llamaron en 2012 la combinación de señales: la convicción cruzada es más robusta que la señal individual.

---

## Slide 9 — Absolute + Relative Views

[🕐 5:50]

El sistema combina dos perspectivas: la **vista absoluta** —¿está este activo caro o barato versus su propia historia?— y la **vista relativa** —¿cuál activo prefiero cross-sectionalmente esta semana? ⏱

El peso es 35% absoluta y 65% relativa, directamente de Wang y Kochard 2012. La vista relativa domina porque en carteras de seguros, las decisiones tácticas son principalmente de rotación, no de timing puro de mercado. ⏱

El tilt final se escala por el presupuesto de tracking error de cada cartera: IGCON con 50 puntos base recibe la mitad del tilt que IGEQUS con 125 puntos base.

---

## Slide 10 — Hierarchical Structure & Portfolio Implementation

[🕐 6:25]

El sistema opera en dos niveles jerárquicos. Nivel L1: la dirección agregada —¿más o menos renta fija o variable en general? Nivel L2: la rotación interna —dentro de renta fija, ¿preferimos tesoros, corporativos IG o deuda EM? ⏱

Las cuatro carteras reales de Rimac —IGCON, IGMOD, IGDIN e IGEQUS— reciben el mismo scorecard central, escalado por su respectivo presupuesto de riesgo. Todas tienen force_zero_sum activo: ningún peso puede ir por debajo de cero.

---

## Cierre — Next Steps (Slide final)

[🕐 6:55]

Para cerrar: el sistema está operativo y corriendo cada semana. Los próximos pasos son tres.

**Primero**, construir el backtest formal —medir el information coefficient señal por señal, el Sharpe del overlay táctico histórico y validar los pesos de pilares.

**Segundo**, ampliar el universo de señales con el CAPE de Shiller, datos del COT de la CFTC, y un índice del ciclo crediticio.

**Tercero**, automatizar la cadena completa: desde la descarga de datos hasta la generación del dashboard, para que el proceso sea reproducible y auditable sin intervención manual.

El sistema es funcional, tiene base académica y tiene lógica económica. Estamos listos para presentarlo formalmente ante el Comité de Inversiones. ⏱

Quedo abierto a preguntas. Gracias.

[🕐 7:10]

---

## Guía de Timing

| Slide | Tiempo inicio | Duración estimada |
|---|---|---|
| 1 - Portada | 0:00 | 40 seg |
| 2 - Sistema | 0:40 | 40 seg |
| 3 - Cuatro Pilares | 1:20 | 55 seg |
| 4 - Normalización | 2:15 | 75 seg |
| 5 - F & M | 3:30 | 35 seg |
| 6 - S & V | 4:05 | 45 seg |
| 7 - Composite Z | 4:50 | 30 seg |
| 8 - Convicción | 5:20 | 30 seg |
| 9 - Absoluto + Relativo | 5:50 | 35 seg |
| 10 - Jerarquía + Carteras | 6:25 | 30 seg |
| Cierre - Next Steps | 6:55 | 15 seg |
| **TOTAL** | | **~7:10 min** |

---

## Respuestas preparadas para preguntas frecuentes del IC

**"¿Por qué no usamos pesos optimizados en los pilares?"**  
Porque la optimización in-sample no sobrevive out-of-sample en combinaciones de factores —DeMiguel, Garlappi y Uppal (2009) lo demostraron. El peso 1/N es el default robusto.

**"¿Por qué EM Fixed Income tiene Overweight si los spreads están ajustados?"**  
El tilt viene del carry: los rendimientos de EM en dólares están 140 bps por encima de la media histórica (EWMA), no de la expectativa de compresión de spreads. Es una posición de carry, no de valoración de spreads.

**"¿Por qué US Equity está en Neutral si el mercado sigue subiendo?"**  
El momentum es positivo pero el sentimiento es negativo: el ratio Put/Call está muy bajo (los inversionistas son complacientes) y las condiciones financieras han endurecido. Los señales se cancelan → Neutral es la respuesta correcta.

**"¿Qué pasa si hay una crisis de mercado?"**  
El sistema tiene un override de crisis: si VIX y MOVE superan simultáneamente el percentil 80, todos los tilts se fuerzan a cero hasta que ambos bajen del percentil 70. Preservación de capital por encima de la señal táctica.
