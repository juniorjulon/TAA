# Goal 1 — Los 4 Portafolios en el Sistema: Estado Actual y Propuesta de Dashboard

---

## 1. Qué genera el sistema con los 4 portafolios (estado actual)

### Pipeline actual

```
main.py
  └── portfolio.py → build_multi_portfolio_report()
        └── Lee portfolios.xlsx (4 filas: IGCON/IGMOD/IGDIN/IGEQUS)
        └── Para cada portfolio:
              - Aplica el scorecard central (mismos z-scores para todos)
              - Escala los tilts por te_budget: tilt_p = tilt_ref × (TE / 100)
              - Aplica force_zero_sum = True (ningún peso < 0%)
              - Genera: saa_weight, scaled_max_tilt, portfolio_tilt, portfolio_weight
        └── Guarda → results/RUN_*/multi_portfolio_views.xlsx (5 sheets)
```

### Qué hay en multi_portfolio_views.xlsx

Tiene 5 sheets:
- `IGCON_USD` — tilts y pesos del portafolio Conservador (TE = 50 bps)
- `IGMOD_USD` — Moderado (TE = 75 bps)
- `IGDIN_USD` — Dinámico (TE = 100 bps)
- `IGEQUS_USD` — Acciones (TE = 125 bps)
- `Tilt_Summary` — comparación side-by-side de tilts de los 4

### Ejemplo del output actual (run 2026-05-13)

| AC | IGCON tilt | IGMOD tilt | IGDIN tilt | IGEQUS tilt |
|---|---|---|---|---|
| lt_em_fi | +0.57% | +0.86% | +1.15% | +1.50% |
| us_equity | −0.02% | −0.03% | −0.05% | −1.50% |
| dm_equity | −0.52% | −0.79% | −1.05% | 0% |
| em_equity | −0.02% | −0.04% | −0.05% | 0% |

Los tilts son **proporcionales al TE budget** — la señal de casa es la misma, solo cambia la magnitud. Correcto metodológicamente (Lee 2000).

---

## 2. Qué MUESTRA el dashboard hoy

**Nada de los portafolios reales.** El dashboard solo muestra:
- `SCORECARD` — z-scores compuestos y tilts de la **vista de casa** (referencia a 100 bps TE)
- `COMPOSITES` — historia de z-scores por AC
- `CB` — chartbook de señales

El `multi_portfolio_views.xlsx` **no se inyecta en index.html**. Es un output de Python que existe en results/ pero el dashboard no lo lee.

Esto significa que cuando el IC ve el dashboard, ve los tilts del portafolio de referencia (100 bps) — no los tilts específicos de IGCON, IGMOD, etc.

---

## 3. Por qué esto es un problema de presentación

El IC gestiona **IGCON, IGMOD, IGDIN e IGEQUS** — no un portafolio abstracto de 100 bps. Lo que necesitan ver:

1. **¿Qué peso tengo hoy en EM Fixed Income en IGCON?** → SAA 30% + tilt +0.57% = **30.57%**
2. **¿Cuánto estoy desviado de mi SAA en IGMOD?** → Tilts específicos por portafolio
3. **¿Cómo varía la señal entre portafolios?** → Misma dirección, diferente magnitud por TE

Sin esta vista, el dashboard es un modelo académico, no una herramienta operacional.

---

## 4. Propuesta: Sección "Portfolio Views" en el dashboard

### Diseño sugerido

**Ubicación:** Nueva sección en el sidebar nav: `Portfolio Views` (debajo de Scorecard o en posición principal)

**Estructura visual:**

```
[ IGCON ] [ IGMOD ] [ IGDIN ] [ IGEQUS ]    ← Tab switcher

Tab activo: IGCON — IG Conservador USD | TE Budget: 50 bps

┌──────────────────────────────────────────────────────────────────────┐
│ PORTFOLIO WEIGHTS (SAA + Tilt = Current Weight)                      │
│                                                                      │
│  LT EM Fixed Income    SAA: 30.0%  Tilt: +0.57% → Current: 30.57%  │
│                        ████████████████████████░░░░░░░░░░  OW       │
│                                                                      │
│  US Equity             SAA: 19.2%  Tilt: −0.02% → Current: 19.18%  │
│                        ██████████████████████████░░░░░░░░  NEUTRAL   │
│                                                                      │
│  DM ex-US              SAA:  7.5%  Tilt: −0.52% → Current:  6.98%  │
│                        █████████████████░░░░░░░░░░░░░░░░░  UW       │
│  ...                                                                 │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ TILT COMPARISON — All 4 portfolios                                   │
│                                                                      │
│             IGCON    IGMOD    IGDIN   IGEQUS                         │
│ lt_em_fi   +0.57%   +0.86%   +1.15%  +1.50%  ↑ OW                  │
│ dm_equity  −0.52%   −0.79%   −1.05%   0.00%  ↓ UW                  │
│ us_equity  −0.02%   −0.03%   −0.05%  −1.50%  ↓ slight              │
└──────────────────────────────────────────────────────────────────────┘
```

### Datos a inyectar

Necesitas que `generate_dashboard.py` lea `multi_portfolio_views.xlsx` y genere:

```javascript
const PORTFOLIOS = {
  meta: {
    portfolios: ["IGCON_USD", "IGMOD_USD", "IGDIN_USD", "IGEQUS_USD"],
    labels:     ["IG Conservador", "IG Moderado", "IG Dinámico", "IG Acciones"],
    te_budgets: [50, 75, 100, 125],
  },
  IGCON_USD: [
    {ac:"lt_em_fi", label:"LT EM Fixed Income", saa:30.0,
     tilt:0.57, weight:30.57, conviction:"MEDIUM OW"},
    {ac:"us_equity", label:"US Equity", saa:19.2,
     tilt:-0.02, weight:19.18, conviction:"NEUTRAL"},
    ...
  ],
  IGMOD_USD: [...],
  IGDIN_USD: [...],
  IGEQUS_USD: [...],
  tilt_summary: {
    lt_em_fi:  [0.57, 0.86, 1.15, 1.50],
    us_equity: [-0.02, -0.03, -0.05, -1.50],
    ...
  }
};
```

### Pasos de implementación

1. **`generate_dashboard.py`**: Agregar función `_load_portfolio_views()` que lee `multi_portfolio_views.xlsx` y lo convierte a `PORTFOLIOS` JS const
2. **`index.html`**: Agregar `const PORTFOLIOS = {};` (placeholder para inyección) y la nueva sección HTML con tab switcher
3. **JS**: Función `buildPortfolioView(portfolioId)` que rellena la tabla con SAA, tilt, peso actual, barra de progreso y color por convicción
4. **`build_dashboard.py`**: Agregar `const PORTFOLIOS` a los marcadores de inyección

### Beneficio operacional

Con esta vista, el IC puede:
- Confirmar en tiempo real cuál es el peso exacto de cada activo en su portafolio específico
- Verificar que los tilts suman cero (zero-sum enforcement)
- Comparar cómo una misma señal se manifiesta con diferente intensidad en carteras conservadoras vs agresivas
- Detectar automáticamente cuándo un tilt choca con el floor de cero (por Solvencia II)

---

## 5. Alternativa más simple: inyectar el Tilt Summary en el Scorecard actual

Si no quieres una sección separada, la opción mínima es agregar columnas al scorecard existente:

| AC | Z_composite | Conv | Abs Tilt (ref) | **IGCON** | **IGMOD** | **IGDIN** | **IGEQUS** |
|---|---|---|---|---|---|---|---|
| lt_em_fi | +1.38 | MEDIUM OW | +1.15% | +0.57% | +0.86% | +1.15% | +1.50% |

Esto requiere solo: leer el Tilt_Summary sheet e inyectarlo como columnas adicionales en `SCORECARD`.
