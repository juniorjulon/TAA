# Monitor Táctico — Propuesta de Rediseño
## Rimac Group · Gestión de Portafolios · Junio 2026

---

## Pregunta 1: Rediseño de la presentación TAA — De tilts automáticos a Monitor Táctico

### Contexto

Se decidió cambiar el enfoque del entregable: en lugar de un sistema que genera desviaciones tácticas automáticas frente al benchmark (requiere backtesting complejo y calibración de muchos hiperparámetros), el output será un **"Monitor Táctico"** que produce z-scores por asset class (con etiquetas OW/Neutral/UW), sin traducirse directamente en tilts. A partir de estos z-scores, el equipo de gestión de portafolios lleva una presentación a un pseudo-comité de asignación táctica, se abre la discusión, y se cierra con una votación anónima vía QR para definir el view táctico de la empresa.

---

### Diagnóstico de la presentación actual

| Sección actual | Acción |
|---|---|
| 1. System Overview | ✅ Conservar (ajuste menor) |
| 2. Signal Engine & Transform Codes | ✅ Conservar |
| 3. The Four Pillars (F/M/S/V) | ✅ Conservar |
| 4. Composite Scoring & Conviction Mapping | ✅ Conservar parcialmente |
| 5. Conviction & Views (slide 16 — 35/65 blend) | ❌ Eliminar completo |
| 6. Hierarchy, Portfolio & Implementation | ❌ Eliminar completo |

---

## PARTE 1 — Nueva estructura de la presentación

### Nueva agenda (5 secciones)

```
1  System Overview
2  Signal Engine & Transform Codes
3  The Four Pillars (F / M / S / V)
4  Composite Scoring & Monitor Output
5  Tactical View Consensus System   ← NUEVA SECCIÓN
```

---

### Slides a conservar sin cambio
Slides 3, 5, 7, 8, 10, 11, 13 → sin modificación.

---

### Slides a modificar

**Slide 4 — Construction Table**
En Stage 5, cambiar de:
> "Views → Absolute and relative tilts"

A:
> "Monitor Output → Composite z-score + conviction label (OW / Neutral / UW) por AC"

Eliminar toda referencia a "35/65 blend", "final_tilt", y "relative cross-sectional ranking".

**Slide 15 — From composite z-score to tactical intensity**
Conservar la tabla de conviction thresholds (±0.75, ±1.50), pero el output es una **etiqueta semafórica**, no un tilt numérico:

| Z-score | Label | Señal visual |
|---|---|---|
| z ≥ +1.50 | HIGH OW | 🟢🟢 |
| +0.75 a +1.49 | MEDIUM OW | 🟢 |
| −0.75 a +0.74 | NEUTRAL | ⚪ |
| −1.50 a −0.76 | MEDIUM UW | 🔴 |
| z < −1.50 | HIGH UW | 🔴🔴 |

Eliminar la fórmula `abs_tilt = tilt_fraction × conviction_mult × MAX_TILT_PCT`.

**Slide 17 — Next Steps**
Actualizar prioridades al nuevo contexto:
1. Backtesting (hit-rate del monitor, no de tilts)
2. Calibración del sistema de votación (umbrales, horizonte)
3. Automatización del tracking y dashboard de performance

**Todos los slides de Agenda** → actualizar a las 5 nuevas secciones.

---

### Slides a eliminar

- **Slide 16** — "Absolute vs Relative Views & Final Tilt Blend" (35/65 blend)
- Referencias a `Hierarchy`, `Portfolio & Implementation` en todos los agendas

---

### Nueva Sección 5 — 5 slides nuevos

---

#### Slide N1 — El Reencuadre: De Sistema Automático a Monitor de Convicción

**Título:** *Del tilt algorítmico al juicio asistido*

| Approach anterior | Nuevo approach |
|---|---|
| El modelo decide el tilt | El modelo informa la discusión |
| Output: desviación numérica frente al benchmark | Output: z-scores + etiquetas OW/N/UW |
| Requiere calibración compleja | Requiere consenso del equipo |
| "Hedge fund algorítmico" | "Monitor táctico + comité de convicción" |

> *"Systematic signals + human judgment outperform either alone."*
> — Kahneman, Sibony & Sunstein (2021), *Noise*

**Mensaje central:**
> El sistema proporciona el diagnóstico. El equipo toma la decisión.

---

#### Slide N2 — El Output del Monitor: Scorecard Semanal

**Título:** *Lo que ve el comité cada semana*

**Scorecard ejemplo:**

| Asset Class | Z_F | Z_M | Z_S | Z_V | Z_Comp | Señal |
|---|---|---|---|---|---|---|
| LT US Treasuries | −1.1 | +1.2 | +0.5 | +1.6 | +0.57 | 🟢 MEDIUM OW |
| LT US Corporate | +0.4 | +0.6 | −0.2 | −1.6 | −0.26 | ⚪ NEUTRAL |
| LT EM Fixed Income | +0.0 | +0.1 | +1.0 | −3.0 | −0.49 | ⚪ NEUTRAL |
| US Equity | +0.6 | −0.2 | +0.0 | −0.5 | −0.04 | ⚪ NEUTRAL |
| DM ex-US Equity | −2.0 | −1.7 | +0.1 | +0.8 | −0.78 | 🔴 MEDIUM UW |
| EM Equity | +0.1 | −0.4 | +1.4 | +0.9 | +0.37 | ⚪ NEUTRAL |

**Zona central:** Gráfico de ranking relativo — barras horizontales ordenadas de mayor a menor z-score compuesto.

**Nota al pie:**
> Este scorecard es el input, no el output. El output es el view del equipo.

---

#### Slide N3 — Flujo de la Reunión Táctica

**Título:** *De la señal al posicionamiento: el proceso en 5 pasos*

```
[1. MONITOR] → [2. PRESENTACIÓN] → [3. DISCUSIÓN] → [4. VOTACIÓN] → [5. POSICIÓN]
```

**① Monitor Táctico (T−0)**
- El sistema genera el scorecard semanal automáticamente
- Z-scores por pilar y AC disponibles en el dashboard
- Señales de alerta: cambios > 1σ vs. semana anterior

**② Presentación al Comité (30 min)**
- Portfolio Manager presenta el scorecard
- Foco en ACs con señal fuera del rango neutral (|z| > 0.75)
- Contexto histórico: ¿Cuántas veces el modelo ha estado en este nivel?
- Breakdown de pillars: ¿cuál está impulsando la señal?

**③ Discusión (30 min)**
- Debate abierto: ¿el equipo concuerda con la dirección del modelo?
- ¿Hay información cualitativa no capturada por el sistema?
- ¿Algún pilar contradice la señal macro del momento?
- Regla: se puede divergir del modelo, pero debe documentarse el razonamiento

**④ Votación Anónima (5 min)**
- QR code → formulario de votación
- Escala de −2 a +2 por cada AC
- Resultados en tiempo real en pantalla

**⑤ Posición Táctica (Output)**
- View oficial del equipo: OW / Neutral / UW por AC
- Documentado y archivado para tracking
- Comunicado a los PMs de portafolios

---

#### Slide N4 — Sistema de Votación: Mecánica y Reglas

**Título:** *La votación: reglas, escala y umbrales*

**La escala de votación:**

| Voto | Significado |
|---|---|
| +2 | Strong OW — convicción alta |
| +1 | Mild OW — sesgo positivo |
| 0 | Neutral |
| −1 | Mild UW — sesgo negativo |
| −2 | Strong UW — convicción alta |

**Reglas de agregación:**

Consenso = **mediana** de votos del equipo (robusta ante outliers)

| Mediana del voto | View del equipo |
|---|---|
| ≥ +1.25 | 🟢🟢 HIGH OW |
| +0.50 a +1.24 | 🟢 MEDIUM OW |
| −0.49 a +0.49 | ⚪ NEUTRAL |
| −1.24 a −0.50 | 🔴 MEDIUM UW |
| ≤ −1.25 | 🔴🔴 HIGH UW |

**Regla de divergencia:** Si la desviación estándar de los votos > 1.0 → **alta dispersión** → se requiere segunda ronda de discusión antes de decidir.

**Balance de portafolio — el rol de MM y STFI:**
> Un OW neto en los 6 ACs activos se financia implícitamente con una reducción en MM y/o STFI. El comité debe visualizar esta consecuencia antes de cerrar la votación. La restricción real no es suma cero entre los 6 ACs, sino el **piso mínimo de MM** (~3%) en cada portafolio.

---

#### Slide N5 — Posición Relativa & Tracking de Performance

**Título:** *¿Quién prefiero sobre quién? Tracking de aciertos*

**Ranking relativo (cross-asset):**

```
MÁXIMO OW →  EM Equity    ← mediana: +1.5
             LT Tsy       ← +0.8
NEUTRAL →    US Equity    ← 0.0
             LT EM FI     ← −0.3
             LT Corp      ← −0.7
MÁXIMO UW →  DM Equity    ← −1.5
```

Pares implícitos: EM > DM (diferencial: +3.0) · UST > LT Corp (diferencial: +1.5)

**Tabla de tracking:**

| Fecha | AC | Z_comp | View equipo | Modelo concordaba | Retorno 4W | Retorno 8W | Acierto 4W | Acierto 8W |
|---|---|---|---|---|---|---|---|---|
| 2026-05-07 | DM Equity | −0.78 | UW | ✅ | −2.3% | −4.1% | ✅ | ✅ |
| 2026-05-07 | LT Tsy | +0.57 | OW | ✅ | +1.8% | +2.2% | ✅ | ✅ |

**Métricas de calibración:**

| Métrica | Definición | Target mínimo |
|---|---|---|
| Hit rate | % views correctos en dirección | > 52% (n ≥ 20) |
| IC (equipo) | Corr(voto mediana, retorno 4W) | > 0.05 |
| Override premium | Hit rate cuando equipo diverge del modelo | Comparar vs. cuando sigue |
| Calibración por convicción | ¿Los HIGH OW outperforman los MEDIUM OW? | Confirmación de escala |
| Consistencia modelo | Hit rate del z_comp sin voto humano | Benchmark de comparación |

---

## PARTE 2 — Diseño completo del sistema de votación

### Herramienta recomendada

| Opción | Herramienta | Pros | Contras |
|---|---|---|---|
| A (Inmediato) | Google Forms + Google Sheets | Gratis, anónimo, tracking automático | Visualización básica, no tiempo real |
| B (Mejor) | Mentimeter | Tiempo real, anónimo, visual | Costo mensual, no integrado |
| C (Ideal) | Módulo en `index.html` del dashboard TAA | Totalmente integrado, histórico automático | Requiere desarrollo (~2-3 días) |

**Recomendación:** empezar con A mientras se desarrolla C.

---

### Formulario de votación

**Header:**
```
COMITÉ TÁCTICO — [Fecha]
Sistema de Gestión de Portafolios — RIMAC
Votación anónima · Duración: 5 minutos
```

**Por cada AC:**
```
LT US Treasuries — Z_comp actual: +0.57 (🟢 MEDIUM OW)
¿Cuál es tu view táctico para las próximas 4-8 semanas?
  ○ +2  Strong Overweight
  ○ +1  Mild Overweight
  ○  0  Neutral
  ○ -1  Mild Underweight
  ○ -2  Strong Underweight
```

---

### Tracking en Google Sheets — Estructura

**Pestaña 1: `Votes_Raw`**
| Timestamp | AC | Vote | Session_ID |

**Pestaña 2: `Session_Summary`**
| Session | Date | AC | Z_comp | Median_Vote | Std_Vote | High_Dispersion | View_Official | Model_Agrees |

**Pestaña 3: `Performance_Tracking`** *(actualizar 4W y 8W después)*
| Session | Date | AC | View | Return_4W | Return_8W | Hit_4W | Hit_8W | Override |

**Pestaña 4: `Metrics_Dashboard`**
- Hit rate total, por AC, por conviction level
- Override premium · IC · Gráfico de barras de hit rates

---

### Índices de retorno para tracking

| AC | Índice |
|---|---|
| LT US Treasuries | LT03TRUU (lt03_price) |
| LT US Corporate | I13282US (i132_price) |
| LT EM Fixed Income | BSGVTRUU (bsgv_price) |
| US Equity | SPXT (sp500_tr) |
| DM ex-US Equity | NDDUEAFE (eafe_tr) |
| EM Equity | NDUEEGF (msci_em_tr) |

Acierto: `sign(view) == sign(retorno_4W)`

---

### Resumen de acción

| Acción | Slides afectados | Tiempo estimado |
|---|---|---|
| ❌ Eliminar slide 16 (35/65 blend) | 1 slide | Inmediato |
| ✏️ Modificar agenda (5 secciones) | 3 slides de agenda | 30 min |
| ✏️ Ajustar slide 4 (pipeline stage 5) | 1 slide | 15 min |
| ✏️ Ajustar slide 15 (output = label, no tilt) | 1 slide | 15 min |
| ➕ Agregar 5 slides nuevos (Sección 5) | 5 slides nuevos | 2-3 horas |
| 🗂️ Configurar Google Forms + Sheets | — | 1-2 horas |

---

---

## Pregunta 2: Zero-sum y traducción de views a portafolios

### 2.1 El zero-sum no aplica entre los 6 ACs activos — aplica al portafolio completo

La restricción `force_zero_sum = True` **no** exige que los 6 ACs activos sumen cero entre sí. Exige que el portafolio completo (los 10 ACs, incluyendo MM y STFI) sume cero en tilts netos.

```
Suma de tilts de los 6 ACs activos  →  residual absorbido por MM y STFI
```

**Colchón de absorción por portafolio:**

| Portafolio | SAA MM | SAA STFI | Colchón total | Límite práctico |
|---|---|---|---|---|
| IGCON | 15% | 25% | **40%** | Alto margen |
| IGMOD | 10% | 15% | **25%** | Moderado |
| IGDIN | 5% | 10% | **15%** | Ajustado |
| IGEQUS | 5% | 0% | **5%** | Casi nulo |

**Lo que debe mostrarse en tiempo real durante la votación:**

```
─────────────────────────────────────────────────
  Suma neta de views (6 ACs activos):   +1.8
  ────────────────────────────────────────────────
  Implicación en MM/STFI:             −1.8

  ⚠️  IGEQUS: esto deja MM en 3.2% (mínimo recomendado: 3%)
     IGDIN:  MM queda en 3.1%  ← límite inminente
     IGCON:  sin restricción
─────────────────────────────────────────────────
```

**La restricción práctica no es suma cero — es el piso de MM (~3%).**

**Reformulación del bloque en la presentación:**
> *Money Market y Renta Fija de Corto Plazo son los amortiguadores estructurales del sistema. Un OW neto en los 6 ACs activos se financia implícitamente con una reducción en MM y/o STFI. El comité debe visualizar esta consecuencia antes de cerrar la votación.*

---

### 2.2 Traducción de views a cada portafolio

**El principio:** El view del comité es **único y direccional** (un solo scorecard OW/N/UW para los 6 ACs). Lo que varía por portafolio es el **tamaño del tilt**, escalado por el presupuesto de TE.

```
View del comité     →  Dirección + Convicción (igual para todos)
TE budget           →  Determina el tamaño del tilt
SAA del portafolio  →  Punto de partida de los pesos
```

---

#### Paso 1 — El comité genera el view unificado

| AC | Mediana voto | View oficial |
|---|---|---|
| LT US Tsy | +1.0 | MEDIUM OW |
| LT US Corp | −0.3 | NEUTRAL |
| LT EM FI | −1.3 | MEDIUM UW |
| US Equity | +0.0 | NEUTRAL |
| DM Equity | −1.5 | HIGH UW |
| EM Equity | +1.3 | MEDIUM OW |

---

#### Paso 2 — Tilt máximo de referencia por AC (a 100 bps TE)

| AC | MAX_TILT_REF |
|---|---|
| LT US Tsy | ±4% |
| LT US Corp | ±3% |
| LT EM FI | ±3% |
| US Equity | ±5% |
| DM Equity | ±4% |
| EM Equity | ±4% |

---

#### Paso 3 — Escalar por TE budget

```
Tilt_portafolio = fracción × MAX_TILT_REF × (TE_portafolio / 100 bps)
```

| AC | View | Fracción | IGCON (×0.50) | IGMOD (×0.75) | IGDIN (×1.00) | IGEQUS (×1.25) |
|---|---|---|---|---|---|---|
| LT US Tsy | MED OW | +0.5 | +2.0% | +3.0% | +4.0% | +5.0% |
| LT Corp | NEUTRAL | 0 | 0% | 0% | 0% | 0% |
| LT EM FI | MED UW | −0.5 | −1.5% | −2.3% | −3.0% | n/a |
| US Equity | NEUTRAL | 0 | 0% | 0% | 0% | 0% |
| DM Equity | HIGH UW | −1.0 | −2.0% | −3.0% | −4.0% | n/a |
| EM Equity | MED OW | +0.5 | +2.0% | +3.0% | +4.0% | n/a |
| **Suma neta activos** | | | +0.5% | +0.7% | +1.0% | +5.0% |
| **Absorción MM/STFI** | | | −0.5% | −0.7% | −1.0% | −5.0%* |

*IGEQUS: MM baja de 5% a 0% — requiere aprobación explícita del comité.

*IGEQUS solo traduce el view de US Equity (único AC con SAA relevante).*

---

#### Paso 4 — Pesos tácticos finales (ejemplo IGMOD)

| AC | SAA | Tilt | Peso táctico |
|---|---|---|---|
| Money Market | 10.0% | −0.7% | **9.3%** |
| Short-Term FI | 15.0% | 0% | **15.0%** |
| LT US Tsy | 0% | +3.0% | **3.0%** |
| LT US Corp | 0% | 0% | **0%** |
| LT EM FI | 25.0% | −2.3% | **22.7%** |
| US Equity | 32.0% | 0% | **32.0%** |
| DM Equity | 12.5% | −3.0% | **9.5%** |
| EM Equity | 5.5% | +3.0% | **8.5%** |
| **Total** | **100%** | **0%** | **100%** ✅ |

---

#### Vista consolidada de los 4 portafolios

```
              IGCON        IGMOD        IGDIN        IGEQUS
              SAA  Táct    SAA  Táct    SAA  Táct    SAA  Táct
MM             15  14.5    10   9.3     5    4.0     5    0.0*
STFI           25  25.0    15  15.0    10   10.0     0    0.0
LT Tsy          0   2.0     0   3.0     0    4.0     0    5.0
LT Corp         0   0.0     0   0.0     0    0.0     0    0.0
LT EM FI       30  28.5    25  22.7    15   12.0     0    0.0
US Equity      19  19.0    32  32.0    45   45.0    95   90.0
DM Equity       8   6.0    13  10.0    18   14.0     0    0.0
EM Equity       3   5.0     6   8.0     7   11.0     0    0.0

* Requiere aprobación explícita del comité
```

---

### Resumen de los dos puntos

| Pregunta | Respuesta |
|---|---|
| ¿El comité necesita votar suma cero? | **No.** El exceso neto lo absorbe MM/STFI. La restricción real es el **piso de MM (~3%)**. Mostrar la implicación en MM en tiempo real durante la votación. |
| ¿Cómo se traduce a cada portafolio? | **Un solo view del comité, cuatro tamaños de tilt.** Fórmula: `Tilt = fracción × MAX_TILT_REF × (TE / 100 bps)`. Para IGEQUS, solo aplica el view de US Equity. |

---

*Documento generado: Junio 2026 · Rimac Group — Gestión de Portafolios*
