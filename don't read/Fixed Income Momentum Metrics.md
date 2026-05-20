# Métricas de Momentum y Valoración en Renta Fija de Crédito
## Informe de Investigación Académico-Institucional para Gestores de Portafolios

---

## Resumen Ejecutivo

La literatura académica e institucional converge en una conclusión central que debe servir de marco a cualquier proceso sistemático en renta fija privada: **los indicadores técnicos diseñados para acciones (RSI, medias móviles simples sobre el precio sucio, MACD) son inadecuados o engañosos en bonos**, porque la serie de precios incorpora componentes mecánicos —pull-to-par, devengo de cupón, rolldown— que contaminan cualquier señal de tendencia. La metodología institucionalmente robusta consiste en construir señales sobre (i) **retornos en exceso** sobre treasuries de duración equivalente, o sobre (ii) la **dinámica del OAS (Option-Adjusted Spread)**, escalada por **DTS (Duration Times Spread)** para hacer comparables instrumentos de distintos vencimientos y calidades crediticias.

**Hallazgos clave por horizonte y clase de activo:**

| Activo | Horizonte | Métrica de momentum más robusta | Métrica de valoración más robusta |
|---|---|---|---|
| US IG (índice) | 1–4 sem | Z-score 20–60d del OAS; cambio del OAS frente a su MA60 | Percentil del OAS a 5–10 años; spread/DTS |
| US IG (rating/sector) | 1–3 m | Excess return 3–6m relativo al peer-group; momentum residual de la equity asociada (Haesen-Houweling-van Zundert 2017) | Spread vs. fair-value regresión multifactorial (apalancamiento, cobertura, margen) |
| US HY | 1–4 sem | Excess return 1–3m (Jostova et al. 2013): el momentum en HY es persistente, ~190 bp/mes en winners–losers | Spread/DTS, OAS percentil, default-adjusted spread (Moody's FVS) |
| US HY | 1–3 m | Total return momentum 6–12m con skip-month; momentum spillover desde equities residuales | Distance-to-default (Merton/EDF) vs. spread |
| EM Corp | 1–4 sem | Cambio del CEMBI-spread Z-score; momentum del soberano (EMBI) como leading indicator | CEMBI vs. CEMBI ajustado por rating-duración, spread differential vs. EMBI |
| EM Corp | 1–3 m | Excess return cross-sectional 3–6m (Dekker-Houweling-Muskens 2021); momentum de FX y commodities como overlay | Spread por país relativo a fundamentales (CDS soberano + premio corporativo) |

**Recomendaciones principales:**
1. **No usar series de precio limpio para momentum**: usar Total Return Index o Excess Return Index sobre treasuries duración-emparejados.
2. **Escalar siempre por DTS**: el cambio relativo (en %) del spread es una variable más estacionaria que el cambio absoluto (en bp), conforme al hallazgo de Ben Dor et al. (2007).
3. **El momentum funciona empíricamente mejor en High Yield y EM Corp que en IG puro**: en IG la literatura encuentra reversión o momentum estadísticamente débil (Khang-King 2004; Gebhardt-Hvidkjaer-Swaminathan 2005; Jostova et al. 2013). En IG, el spillover desde equity (Gebhardt et al. 2005; Haesen-Houweling-van Zundert 2017) y el carry/value dominan.
4. **Combinar momentum con value**: la correlación de los factores Value-Momentum-Carry-Defensive en crédito es baja a negativa (Israel-Palhares-Richardson 2018; Houweling-van Zundert 2017), lo cual genera diversificación de signal.
5. **Atención al sesgo de réplica reciente**: trabajos como "The Corporate Bond Factor Replication Crisis" (2024–2026) muestran que parte del alfa documentado en momentum 6–12m desaparece tras corregir por errores de medición y filtros ex-post; los gestores deben validar señales con winsorización ex-ante.

---

## PARTE I — MÉTRICAS DE MOMENTUM EN RENTA FIJA DE CRÉDITO

### 1. Por qué RSI, SMA y técnicos de equity son subóptimos en bonos

La crítica metodológica es estructural y no meramente empírica:

**(a) Pull-to-par.** Como recuerda Wikipedia y AXA IM, el precio de un bono converge mecánicamente a su valor nominal a medida que se acerca el vencimiento, independientemente del crédito subyacente. Un bono *premium* exhibirá una caída de precio *sin* deterioro de crédito; un bono *discount*, una apreciación *sin* mejora de fundamentales. Una media móvil sobre el precio sucio confunde este efecto determinista con momentum genuino.

**(b) Cupón devengado y "fechas de cupón".** El precio sucio salta a la baja en la fecha ex-cupón; el precio limpio elimina ese salto pero pierde información sobre el retorno realizado. Solo un **Total Return Index** (precio + cupón devengado + cupones pagados reinvertidos) es la base correcta para construir momentum.

**(c) Rolldown y carry.** El paso del tiempo, en una curva positiva, genera una apreciación por *roll* aún si el spread permanece constante. Un momentum 6–12m sobre total return mezcla tres componentes: (i) cambio en el risk-free rate, (ii) cambio en el spread, (iii) carry+rolldown. Las metodologías institucionales modernas (AQR, Robeco) descomponen y aíslan: el momentum más informativo es el del **componente de spread o el excess return sobre tasa**, no del retorno total.

**(d) Drift de duración.** Comparar momentum entre tramos de distinta duración es engañoso si no se ajusta por DTS. El cambio en bp de un spread de 80 bp en un bond AA tiene un significado distinto al mismo cambio en un bond B con spread de 600 bp: el segundo está mucho más cerca de su volatilidad de equilibrio. Robeco/Lehman (Ben Dor, Dynkin, Hyman, Houweling, van Leeuwen, Penninga, *Journal of Portfolio Management* 2007) demostraron que **la volatilidad del exceso de retorno es proporcional a DTS = duración × spread**, no a la duración sola, y que el cambio del spread en términos *relativos* (porcentual) es lo que es estacionario.

**(e) Liquidez, no-trading y precios stale.** En crédito OTC, muchos bonos no se cruzan diariamente; los precios "matrix-priced" generan auto-correlación espuria a 1–5 días que hace que el RSI corto plazo sea parásito. Jostova et al. (2013) muestran que los profits del momentum *no* desaparecen en datos TRACE post-transparencia, pero documentan también que los retornos de muy corto plazo en HY contienen reversión por liquidez (cf. Bali-Subrahmanyam-Wen sobre short-term reversals).

**(f) Conclusión metodológica institucional.** AQR (Brooks-Katz-Moskowitz 2016, "Style Investing in Fixed Income") explicita que las señales de momentum en crédito se computan sobre retornos en exceso o cambios de spread, *nunca* sobre price-only series, y AQR-Israel-Palhares-Richardson construyen el factor "momentum" como retorno en exceso 6 meses con skip de un mes para mitigar reversal de corto plazo.

### 2. Métricas de momentum basadas en spreads

#### 2.A. Cambio absoluto y rate-of-change del OAS

- **ΔOAS 1M, 3M, 6M**: Δ_OAS(t,h) = OAS(t) − OAS(t−h). Útil como medida directa de tightening/widening, pero sufre del problema de heteroscedasticidad: una caída de 30 bp en 2008 (de 600 a 570) y una caída de 30 bp en 2024 (de 110 a 80) son señales completamente distintas.
- **Cambio relativo** (preferido por Robeco): Δ%OAS(t,h) = (OAS(t) − OAS(t−h)) / OAS(t−h). Esta es la transformación coherente con la propiedad lognormal del spread documentada en Ben Dor et al. (2007).

#### 2.B. Z-score del OAS

Z(t,N) = (OAS(t) − μ_N) / σ_N, donde μ y σ se estiman sobre una ventana móvil de N días.
- Ventanas estándar: 60d, 120d, 252d (1 año), 750d (3 años).
- Lectura: |Z| > 2 indica spread > 2 desviaciones estándar respecto de su régimen reciente; en momentum, un Z creciente y positivo (widening anómalo) actúa como señal corto-plazo *contraria* (mean reversion) o *pro-cíclica* (continuación) según el régimen, lo cual debe testearse.

#### 2.C. Trend del spread vs. su MA-N

Spread sobre/bajo su media móvil 60–200 días. **Diferencia con equity**: en equity, el precio sobre la MA200 es típicamente "alcista" (continuación). En crédito, **el spread por encima de su MA largo es típicamente bearish para el bono** porque indica widening en curso; pero la lectura sobre el *total return index* invierte el signo. Este es el origen del confuso debate sobre si el "trend" en crédito es momentum o reversión: depende de si la señal es sobre el spread o sobre el retorno.

#### 2.D. Percentile rank del OAS

Percentil del OAS actual contra su distribución a 3y/5y/10y. Es la base estándar de los *cross-asset dashboards* de J.P. Morgan, Morgan Stanley IM (BEAT report) y Goldman Sachs FICC. Por ejemplo, Morgan Stanley IM (Sep 2025) reporta percentiles a 10 años por sub-asset (US IG, US HY, CEMBI, CMBS, ABS, CLO BB) como insumo de la decisión Overweight/Underweight. Lectura institucional: percentiles < 20% (spread tight) → reduce risk; percentiles > 80% (spread wide) → add risk.

### 3. Momentum basado en retornos

#### 3.A. Total return vs. excess return: ¿cuál es señal?

- **Total Return** = ΔPrecio + cupón devengado + reinversión. Contiene movimiento de tasas + crédito + carry.
- **Excess Return sobre treasury duración-emparejado** = TR_bond − TR_duration_matched_treasury. Aísla el componente de crédito, eliminando la contaminación del rate beta.
- **Conclusión institucional (AQR Israel-Palhares-Richardson 2018; Robeco Houweling-van Zundert 2017)**: el momentum sobre **excess return** es marginalmente superior al de total return en términos de Sharpe ratio del long-short factor portfolio. La razón: separa la decisión de duration de la decisión de credit selection.

#### 3.B. Momentum ajustado por carry (Koijen et al. 2018 aplicado a crédito)

Koijen, Moskowitz, Pedersen y Vrugt (*Journal of Financial Economics* 2018) definen carry como "el retorno si el precio no cambia" y demuestran que el carry per se predice retornos en US Treasuries y crédito. El momentum *neto de carry* — definido como el retorno realizado en exceso del carry esperado al inicio del período — es un mejor estimador del cambio en valoración fundamental que el retorno total. Operativamente:

Momentum_carry-neutral(t,h) = ER(t−h, t) − Carry_ex_ante(t−h) × h

donde Carry ≈ OAS + rolldown del crédito (estrictamente, "yield-take" Koijen-style: OAS + (∂OAS/∂maturity) × (h/12) × −1).

#### 3.C. Momentum ajustado por riesgo

Risk-adjusted momentum = ER(t−h, t) / σ_ER(t−h, t)

donde σ_ER se computa sobre ventana 30–60 días. Es la implementación AQR del "risk-parity momentum"; protege contra falsas señales en bonos de alta volatilidad cuyo retorno es ruidoso. En la práctica también se utiliza la división por **DTS** como sustituto ex-ante de σ.

### 4. Momentum cross-sectional en crédito

#### 4.A. Ranking por excess return trailing — el factor "MOM" institucional

El factor canónico construido por:
- **Robeco (Houweling-van Zundert 2017, Financial Analysts Journal)**: ordena bonos individuales por **excess return de los últimos 6 meses** (con skip de 1 mes para evitar reversal), forma decil-portfolios, long top decil – short bottom decil. Hallazgo: alpha estadísticamente significativo en IG y HY tras controlar por duración, rating y sector.
- **AQR (Israel-Palhares-Richardson 2018)**: usa retornos de los **últimos 6 meses con skip 1m**, weighted-by-DTS para neutralizar exposición a riesgo crédito. Encuentra que el momentum tiene retornos económicamente significativos pero es la *menos* persistente de las cuatro características (carry, defensive, momentum, value), con evidencia "consistente con mispricing" (overreaction).
- **Jostova-Nikolova-Philipov-Stahel (Review of Financial Studies 2013)**: documenta el resultado seminal: ~59 bp/mes en sample completo, ~192 bp/mes solo en HY, ~282 bp/mes en HY de empresas privadas. **El momentum en IG puro es estadísticamente insignificante**.
- **Pospisil-Zhang (Journal of Fixed Income 2010)**: confirma momentum en HY y reversal en IG; muestra adicionalmente que el momentum varía con el ciclo de crédito (más fuerte tras periodos de widening).

#### 4.B. Factor momentum (momentum del factor mismo)

Trabajo más reciente (Gupta-Kelly 2019 sobre equity; aplicaciones en crédito por Robeco) muestra que los factores carry, value, defensive y momentum exhiben *factor momentum* — un factor que ha rendido bien en el último año tiende a continuar rindiendo bien. En crédito, esto se aplica como overlay sobre la asignación de pesos del multi-factor portfolio.

#### 4.C. Momentum por rating (upgrades/downgrades)

- **Información de rating drift**: las acciones de las agencias generan momentum de 1–3 meses, pero gran parte de la información ya está incorporada en el spread por anticipación (Jorion-Zhang 2007).
- **Crossover signals**: el momentum más explotado institucionalmente es el de **fallen angels** (downgrade IG → HY) y **rising stars** (upgrade HY → IG). Investigación de Barclays/Lehman (Dynkin et al.) muestra reversión post-downgrade en bonos forced-sold por mandatos, generando un retorno de ~1.5–2.5% sobre el índice HY al ser reincorporados.

### 5. Síntesis de la investigación de gestoras y bancos

#### 5.A. Robeco — el banco de pruebas más profundo en factor investing en crédito

Robeco Quantitative Credits (Houweling, van Zundert, Haesen, Dekker, Muskens) ha publicado la serie más coherente:

1. **Houweling & van Zundert (2017, FAJ)** — Factor Investing in the Corporate Bond Market. Define cuatro factores: Size (market value de bonds emitidos por la empresa), Low-Risk (bonos de corta maturity y rating alto), Value (spread alto vs. spread implícito de un modelo basado en rating-maturity), Momentum (retorno pasado 6m con skip 1m). El multi-factor portfolio, por baja correlación entre factores, alcanza Information Ratio superior a cualquier factor individual.

2. **Haesen-Houweling-van Zundert (2017, JBF)** — Momentum Spillover from Stocks to Corporate Bonds. **Hallazgo crítico**: el spillover tradicional (rank por equity return total) tiene *exposición estructural y time-varying al riesgo de default* que reduce drásticamente el Sharpe. Reemplazar el equity return total por el **residual equity return** (residuo de regresión sobre el mercado) reduce la volatilidad a la mitad, **dobla el Sharpe ratio** y reduce el drawdown de −80% a −25%. Este es probablemente el resultado *más importante* en momentum aplicado a IG: dado que el momentum directo en bonos IG es débil (Jostova), el canal eficaz es el spillover residual desde equity.

3. **Dekker-Houweling-Muskens (2021, Journal of Index Investing)** — Factor Investing in Emerging Market Credits. Replica los cuatro factores en CEMBI hard currency 2001–2018: tamaño, low-risk, value y momentum **todos** generan alpha significativo, robusto a controles por país, sector, rating y maturity. El alpha del momentum sobrevive tras controlar por exposiciones a factores DM. Robustez: persiste dentro de subsamples líquidos.

4. **Ben Dor et al. (2007)** — DTS (Duration Times Spread). La volatilidad del exceso de retorno es proporcional a DTS, no a duración sola.

#### 5.B. AQR — framework "value, momentum, carry, defensive" cross-asset

- **Israel-Palhares-Richardson (2018, JoIM)** — Common Factors in Corporate Bond Returns. Las cuatro características explican porción significativa de la variación cross-sectional de excess returns; retornos no se explican por exposiciones macro; **evidencia de mispricing especialmente en momentum**.
- **Asness-Moskowitz-Pedersen (2013, JoF)** — Value and Momentum Everywhere. Confirma que value y momentum funcionan como factores comunes a todas las asset classes incluido crédito, con baja correlación entre sí.
- **Brooks-Katz-Moskowitz (2016)** y AQR Style Investing in Fixed Income (Brooks-Palhares 2016) — operacionaliza value (spread real), momentum (price-based 6m+1m skip), carry (yield-to-worst), defensive (quality) en gobierno y crédito.

#### 5.C. JPMorgan — JULI Fair Value Model

J.P. Morgan publica desde mid-2000s un fair value model para US HG (alto grado) que regresa el spread sobre cuatro determinantes:
**Spread_HG = 35.4 + 2.81 × tasa de downgrade HG 12m + 6.22 × stddev del spread HG 12m − 1.31 × retorno S&P 500 12m + 1.0 × 10y swap spread**
(R² ajustado 85% sobre 1990–2005, desviación estándar de error 17 bp, half-life del residuo 3 meses)

El residuo (spread real − fair value) es la señal de valoración: 0.5σ de desalineación sirve como umbral de trade. JPMorgan también es el creador de los índices CEMBI Broad Diversified, EMBI Global Diversified que son benchmarks para EM Corp.

#### 5.D. BlackRock — factor lens

BlackRock implementa, vía su iShares y BlackRock Systematic Fixed Income, los factores carry, value, quality, low-vol; usa el framework BSF (BlackRock Systematic Fixed Income) para tilts factoriales. Las publicaciones más relevantes son las "Factor Box" notes y el "BlackRock Investment Institute" que combinan momentum (ER 6m), value (spread vs. modelo) y quality (ratios fundamentales).

#### 5.E. Barclays / BAML / Bloomberg Index research

El sucesor del Lehman group en Barclays (Dynkin, Hyman, Ben Dor, Polbennikov) publicó "A Decade of Duration Times Spread" (2016) y mantiene la práctica de ejes de risk attribution sobre DTS en lugar de duración + market weight. ICE/BAML provee los OAS por rating y por sector que son inputs estándar.

#### 5.F. State Street / SSGA

SSGA's "Smart Beta in Fixed Income" framework usa carry, value y quality; momentum es operado más como overlay tactic que como factor estratégico, en línea con la evidencia de mayor decay del Sharpe del momentum vs. carry.

### 6. Momentum en crédito EM corporativo

#### 6.A. Diferencias estructurales con DM

El paper de Dekker-Houweling-Muskens (2021) muestra que los cuatro factores funcionan en EM Corp, pero con cuidados específicos:
- Mayor peso del riesgo país: descomponer spread en *country premium* (sovereign + transfer risk) + *issuer-specific premium* es esencial. Algunos managers (Robeco, Pictet, Ashmore) sustraen el spread soberano del spread corporativo para construir un "corporate-only excess spread".
- Heterogeneidad regional: el momentum en Asia EM Corp ha sido más persistente que en LatAm; en EMEA está más contaminado por shocks idiosincráticos (Rusia 2014, 2022; Turquía 2018).
- Liquidez: bid/ask spreads en EM Corp son 2–4× mayores que IG DM; el "skip-month" en el momentum debe ser de al menos 1 mes y los costos de transacción deben restarse del backtest (Dekker et al. lo hacen y los factores sobreviven).

#### 6.B. Soberano EM como leading indicator del corporativo EM

EMBI Global Diversified spread se mueve antes que el CEMBI en episodios de stress (~2–5 días de lead). Un widening del soberano de un país no compensado por widening del corporativo del mismo país suele resolverse con widening del corporativo en 1–4 semanas. Esta relación es explotable como señal cross-sectional intra-país.

#### 6.C. FX y commodities como overlays

Documentado por J.P. Morgan EM Strategy y Barclays EM Credit:
- **DXY momentum**: dólar fuerte (DXY tendencia alcista 4–8 semanas) precede typically 1–3 meses de widening del CEMBI. Coeficiente histórico ~3–6 bp de widening por cada +1% de DXY en HY EM Corp.
- **Brent / WTI**: petróleo a la baja arrastra spreads de soberanos exportadores (Pemex, Petrobras, Ecopetrol, Sonatrach) y sus corporates con beta de 0.4–0.7 al precio.
- **Cobre y metales**: análoga relación con soberanos chilenos, peruanos, sudafricanos.
- **PMI manufacturero China**: lead 2–4 meses para EM Corp Asia y commodities-linked LatAm/EMEA.

---

## PARTE II — MÉTRICAS DE VALORACIÓN EN RENTA FIJA DE CRÉDITO

### 1. Frameworks basados en spread

#### 1.A. OAS percentile rank — la métrica institucional canónica

Rank percentil del OAS actual sobre histórico 3y/5y/10y. Calibración estándar:
- < 10%: extremadamente caro (spread muy comprimido)
- 10–25%: caro
- 25–75%: rango neutral
- 75–90%: barato
- > 90%: extremadamente barato

A abril 2026, los spreads IG y HY en US se encuentran cerca de mínimos de varias décadas (ICE BAMLC0A0CM en torno a niveles tights vs. percentil 10y ≈ 5–10%, según FRED y dashboards de Morgan Stanley IM y JPMAM 2025), justificando el underweight táctico de muchas casas (Morgan Stanley BEAT Sep 2025: "Investment Grade U/W: With spreads near all-time tights, IG has poor convexity").

#### 1.B. Z-spread vs. OAS

- **Z-spread**: spread constante sobre la curva swap/treasury que iguala el precio del bono a la suma descontada de sus cash flows contractuales.
- **OAS**: Z-spread ajustado por el valor de las opciones embebidas (call, put, sinking fund). Para bonos non-callable IG, Z-spread ≈ OAS. Para bonds callable HY, OAS < Z-spread; usar Z-spread inflaría artificialmente la valoración.
- **Cuándo usar cada uno**: OAS para comparaciones cross-sectional dentro del mismo segmento callable; Z-spread para análisis de relative value en universos con opcionalidad heterogénea limitada.

#### 1.C. Spread/Duration ratio (carry per unit of risk) y breakeven analysis

Ratio = OAS (bp) / Spread Duration (años). Mide el "carry por unidad de riesgo de spread". Calibración histórica IG: típicamente 25–50 bp/año; HY: 80–250 bp/año.

**Breakeven (1 año)**: ¿cuántos bp puede ampliarse el spread antes de que el carry se erosione? BE_widening(1y) ≈ OAS / SpreadDuration. Si IG ofrece 90 bp con SD=7y, BE ≈ 13 bp; un widening superior a 13 bp en 12 meses produce retorno en exceso negativo. GMO (2025) usa esta lógica para mostrar que en spreads tight, **estructuras de menor SD ofrecen mayor margen de seguridad**.

#### 1.D. Spread/DTS ratio

DTS-normalized valuation: OAS / DTS_target. Una versión más sofisticada del breakeven que incorpora la propiedad lognormal del spread.

### 2. Modelos de fair value fundamental

#### 2.A. Modelo estructural de Merton

Spread implícito = f(asset volatility, leverage, risk-free rate). Usa la firma vista como call option sobre activos. Implementación práctica: **Moody's KMV EDF (Expected Default Frequency)** y **Moody's Fair Value Spread (FVS)** — calibrado vía LGD sectorial para que en promedio modeled spreads coincidan con observed spreads. La señal: market spread − FVS. Spread > FVS por más de 1σ histórica = barato por estructural; spread < FVS = caro.

#### 2.B. Modelos de regresión multifactorial

Regresión cross-sectional (a nivel emisor) o time-series (a nivel índice/rating) del OAS sobre fundamentales:
- Apalancamiento (Debt/EBITDA, Debt/Capital)
- Cobertura de intereses (EBIT/Interest)
- Margen operativo y volatilidad de margen
- Tamaño (log market cap o log assets)
- Sector dummies
- Maturity / duration

JULI fair value model de JPM (Sec. 5.C) es el ejemplo institucional emblemático para el agregado HG. A nivel emisor, gestoras usan modelos multilineales calibrados que en US IG explican 60–75% de la varianza cross-sectional del OAS.

#### 2.C. Rating-implied spread

Regresar OAS = α + β₁·Rating_dummy + β₂·Duration + β_sector + ε; el residuo ε es el "valor relativo": positivo (spread > implied) → barato vs. peer-rating; negativo → caro. Esta es la formulación de "Value" en Houweling-van Zundert (2017): el factor value del paper Robeco compara el spread observado con el spread implícito por un modelo basado en rating y maturity.

### 3. Frameworks de valor relativo

#### 3.A. Cross-currency (USD vs. EUR IG, post-hedging)

USD IG OAS − EUR IG OAS − cross-currency basis (CCY hedge cost). Cuando este "FX-adjusted spread differential" se desvía > 30 bp de su media de 5 años, hay valor relativo. Usuarios institucionales: tesoros corporativos globales, ALM aseguradoras europeas que arbitran reverse Yankees vs. USD bonds.

#### 3.B. IG vs. HY ratio

Spread ratio HY/IG: típicamente 4–6x en regímenes normales, 8–10x en stress. Ratios bajos (~3.5x o menos) indican IG relativamente barato vs. HY (HY caro); ratios altos indican lo contrario.

#### 3.C. IG vs. EM Corp

Relative value rating-, duration-, y sector-ajustado. EM Corp BBB vs. US IG BBB: differential típicamente 50–150 bp como prima de "EM premium". Cuando comprime < 30 bp → EM Corp caro; cuando > 200 bp → EM Corp barato. Morgan Stanley IM (Oct 2025) sostiene EM Corp Hard Currency O/W argumentando "default prospects appear lower than in corporate credit while quality-adjusted spreads remain higher".

#### 3.D. Relative value sectorial

Spread sectorial vs. mediana sectorial 5y; spread financials vs. non-financials; spread energy vs. utilities (ajustado por leverage); etc. Cada sector tiene su propio "fair spread" condicional al rating-duración promedio del sector.

#### 3.E. Within-rating-bucket valuation

BBB tight vs. A: cuando el ratio BBB/A < 1.3x, los inversores no son adecuadamente compensados por descender un escalón de rating; argumento usado típicamente para subir en calidad. Análogo en HY: BB/B ratio.

### 4. Yields reales y all-in yields

#### 4.A. Yield-to-worst (YTW) percentile rank

Análogo al OAS percentile pero sobre el yield total. Útil para inversores con benchmark absoluto (insurers, retirement income).

#### 4.B. Real yield

YTW − inflation breakeven 5y/10y. En 2026, US IG real yields se encuentran cerca de máximos del ciclo post-2008, soportando la asignación a IG aún con spreads tights — la "yield story" sustituye la "spread story" como tesis de valor (J.P. Morgan LTCMA 2026: US IG return forecast 5.2%).

#### 4.C. Breakeven analysis (ver 1.C)

### 5. Valoración EM Corp específica

#### 5.A. CEMBI vs. fundamentales

Modelos institucionales (FMI, BIS, J.P. Morgan EM Strategy) regresan CEMBI spread sobre:
- EM GDP growth differential vs. DM
- EM aggregate current account / GDP
- EM FX reserves / short-term external debt
- VIX, MOVE (factor de risk-on/off global)
- DXY level
- EMBI sovereign spread
- US HY spread (común factor riesgo crédito global)

#### 5.B. Premium EM Corp sobre soberano EM

CEMBI spread − EMBI sovereign spread (mismo país, ajustado por duración). Cuando este "corporate excess over sovereign" comprime cerca de 0 o se vuelve negativo (EM Corp más tight que su soberano), suele ser un signal de saturación técnica del segmento corporativo y precede typically 2–4 semanas de under-performance del corporativo. Cuando es ampliamente positivo (>200 bp), oportunidad de relative value long corporate / short sovereign.

#### 5.C. Hard currency vs. local currency

Trade-off: HC elimina FX risk pero captura riesgo soberano y corporativo en USD; LC añade FX risk pero permite participar en compresión de tasas locales. Comparación de rendimientos esperados ajustados por hedge.

---

## PARTE III — MÉTRICAS CROSS-ASSET

### 1. Crédito vs. Tasas

#### 1.A. Treasury yield momentum y crédito

El componente rate del retorno total del crédito puede dominar en horizontes cortos. Pero estructuralmente, **el spread del crédito tiende a estrecharse cuando suben las yields por crecimiento**, y a ampliarse cuando suben por inflación o riesgo. Por eso el ER (excess return) sobre treasury duration-matched es la unidad correcta: aísla el componente de crédito.

#### 1.B. MOVE Index como modificador de momentum crediticio

El MOVE (volatilidad implícita de US Treasuries) es leading indicator de stress crediticio. Choi et al. (2022, citado en research macro) encuentra que el bond variance risk premium es leading indicator de equity distress, por extensión también de credit distress. Reglas operativas: cuando MOVE > 130 con widening de spreads, no fadeear el move; cuando MOVE retrocede de niveles altos a < 100, momentum de tightening de crédito típicamente persiste 2–4 semanas.

#### 1.C. Pendiente de curva de tesoro como signal de duración crediticia

Curva 2s10s o 5s30s como leading de actividad económica (bull-steepening = expectativa de cuts en recesión = widening crédito; bear-steepening = expectativa de inflación = en general benigno para crédito a plazos cortos pero negativo a plazos largos por incremento de all-in yield).

#### 1.D. Correlación rates-credit

En regímenes "crecimiento" (post-2010 hasta 2019), correlación negativa entre yields y spreads (subida de yields acompaña tightening de spreads). En regímenes "inflación" (2022) la correlación cambia de signo: yields up + spreads up. Reconocer el régimen es clave para evitar señal cruzada.

### 2. Crédito vs. Equities

#### 2.A. Equity momentum como leading indicator de spreads

Documentación seminal: **Gebhardt, Hvidkjaer & Swaminathan (2005, JFE)** "Stock and Bond Market Interaction: Does Momentum Spill Over?" — ganadores del equity 12m son ganadores en bond market posteriormente; especialmente fuerte en IG. **Haesen-Houweling-van Zundert (2017)** mejora la señal usando *equity returns residuales* (idiosincráticos) sobre el mercado, eliminando el beta de mercado y reduciendo dramáticamente exposiciones de cola.

#### 2.B. VIX vs. spreads — ¿quién lidera?

Empíricamente y estructuralmente, **VIX y CDX/IG-OAS están altamente correlacionados** (rho ≈ 0.7–0.8 a nivel daily change). El CFA Institute (Jul 2025) encontró que el VIX *predice* movimientos del MOVE pero no al revés a frecuencia diaria. En regímenes calmados, los spreads de crédito a veces lideran el VIX (los bonos digieren información de balance antes que las acciones); en regímenes de stress, el VIX lidera (impulso de risk-off que después se transmite a crédito).

#### 2.C. EDF (Moody's) vs. market spreads

Convergencia/divergencia EDF (probabilidad de default a 1 año derivada del modelo Merton-KMV) vs. spread observado:
- Spread > FVS implícito por EDF → barato (mispricing al alza del riesgo)
- Spread < FVS → caro (mercado complacent vs. fundamentales).

Útil especialmente como filter en HY single-name selection.

#### 2.D. CDS-cash basis

Basis = CDS spread − asset swap spread del bono cash equivalente. Negative basis (CDS < cash) = el bono cash es barato vs. la protección sintética; positive basis = caro. Históricamente la basis IG es ligeramente negativa (-5 a -15 bp). Movimientos extremos (>30 bp en valor absoluto) son señales de relative value entre cash y synthetic.

#### 2.E. Equity factor signals (quality, profitability) como predictores

Quality (ROIC alto, baja volatilidad de earnings, leverage modesto) en equity → outperformance del bono del mismo emisor. Es el "defensive" / "quality" factor de Frazzini-Pedersen y AQR aplicado a crédito.

#### 2.F. Collin-Dufresne, Goldstein y Martin (2001 JoF)

"The Determinants of Credit Spread Changes" — solo ~25% de la varianza de los cambios de spread se explica por variables structural (leverage, vol, slope, level). El resto es un "common factor" que afecta a todos los créditos simultáneamente, lo que justifica el uso de signal exogena (equity, VIX, MOVE) como input para predicción de spreads.

### 3. EM cross-asset

#### 3.A. EM FX momentum como leading de EM Corp

EMFX index (J.P. Morgan ELMI o GBI-EM FX-only) momentum 1–3 meses tiene correlación 0.5–0.7 con cambios de CEMBI spread (signo invertido: FX appreciation → spread tightening). El EMFX es leading 2–6 semanas en episodios típicos.

#### 3.B. Commodities → EM Corp

- **Oil**: Brent momentum 1–3m → spreads de soberanos y corporates exportadores.
- **Cobre, hierro**: → LatAm (Chile, Perú, Brasil), Sudáfrica, Australia.
- **CRB Index** como proxy macro general.

#### 3.C. DXY → EM Corp

Como en 6.C de Parte I: dólar fuerte = stress en EM Corp via canal de financial conditions y dollar liquidity.

#### 3.D. China activity (PMI, Caixin, data crediticia)

PMI manufacturero China lead 2–4 meses para EM Corp Asia, commodities y por extensión LatAm y EMEA exportadores. Nuevos préstamos en RMB y TSF (Total Social Financing) como leading de demanda agregada EM.

---

## TABLA CONSOLIDADA DE IMPLEMENTACIÓN DE MÉTRICAS

| Métrica | Cálculo | Fuente de datos (Bloomberg / FRED) | Clase de activo | Horizonte | Referencia académica/institucional |
|---|---|---|---|---|---|
| ΔOAS 1M / 3M / 6M | OAS(t) − OAS(t−h) | LUACOAS, LF98OAS, BAMLC0A0CM (FRED) | IG, HY índice/sector | 1–4 sem / 1–3 m | Israel-Palhares-Richardson 2018 |
| Δ%OAS relativo | [OAS(t)/OAS(t−h)] − 1 | Idem | IG, HY, EM Corp | 1–4 sem / 1–3 m | Ben Dor et al. 2007 |
| Z-score OAS 60d/252d | (OAS − μ)/σ ventana móvil | Bloomberg PORT, LUACOAS | Todos | 1–4 sem | Práctica institucional estándar |
| Percentil OAS 5y/10y | rank percentil sobre ventana | FRED BAMLC0A0CM, BAMLH0A0HYM2, BAMLEMCBPIOAS | Todos | 1–3 m | Morgan Stanley BEAT, JPMorgan Cross-Asset |
| Spread/DTS ratio | OAS / (Spread Duration × OAS) = 1/SD | Bloomberg PORT, MSCI RiskMetrics | Todos | 1–3 m | Robeco / Ben Dor et al. 2007 |
| Excess return 6m skip 1m | TR_bond − TR_treasury_dur_matched, 6m con lag 1m | Bloomberg, ICE indices | IG, HY, EM Corp | 1–3 m | Houweling-van Zundert 2017; Israel et al. 2018 |
| Carry-neutral momentum | ER realizado − Carry ex ante | Bloomberg + cálculo | Todos | 1–3 m | Koijen et al. 2018 |
| Risk-adj momentum | ER / σ(ER, 30–60d) | Bloomberg | Todos | 1–4 sem / 1–3 m | AQR Brooks et al. 2016 |
| Residual equity momentum spillover | Rank por ε_i de regresión equity ret on market | CRSP/Bloomberg + cálculo | IG, HY, single-name | 1–3 m | Haesen-Houweling-van Zundert 2017 |
| Rating-implied fair spread | Residuo ε de regresión OAS = f(rating, dur, sector) | Bloomberg + Compustat | IG, HY, EM Corp | 1–3 m | Houweling-van Zundert 2017 (Value) |
| JULI HG fair value | 35.4 + 2.81·HG_DG_rate + 6.22·OAS_stddev − 1.31·SPX_12m_ret + 1.0·10y_swap | JPM JULI, Bloomberg | US IG | 1–3 m | JPMorgan US Bond Strategy |
| Moody's EDF / FVS | Modelo estructural Merton-KMV calibrado por LGD sectorial | Moody's Analytics | IG, HY single-name | 1–3 m | Moody's KMV |
| Spread/Duration breakeven (1y) | OAS / SpreadDuration | Bloomberg PORT | Todos | 1–3 m | GMO; práctica estándar buy-side |
| Real yield IG/HY | YTW − Breakeven 5y/10y | FRED T5YIE, Bloomberg | IG, HY | 1–3 m | Newfound Research (Hoffstein) |
| HY/IG ratio | OAS_HY / OAS_IG | FRED | US Corp | 1–3 m | Estándar institucional |
| EM Corp - Sovereign (mismo país) | CEMBI_country − EMBI_country, dur-adj | Bloomberg JPMorgan indices | EM Corp | 1–3 m | JPMorgan EM Strategy |
| MOVE Z-score | (MOVE − μ)/σ 252d | Bloomberg MOVE Index | Crédito (modificador) | 1–4 sem | BIS, CFA Institute 2025 |
| VIX Z-score | (VIX − μ)/σ 252d | Bloomberg VIX | Crédito (modificador) | 1–4 sem | Choi et al. 2022 |
| Equity residual momentum 12m | ε de equity ret single-name on market 12m | CRSP/Bloomberg | IG single-name | 1–3 m | Haesen-Houweling-van Zundert 2017 |
| CDS-cash basis | CDS spread − ASW spread | Bloomberg, Markit | IG, HY single-name | 1–4 sem | Práctica institucional |
| Distance-to-Default | (V_assets − Default_threshold)/(σ_V × V_assets) | Moody's KMV, Compustat | HY single-name | 1–3 m | Merton 1974; Moody's 2010 |
| EM FX momentum | Tendencia EMFX index 1–3m | Bloomberg JEM ELMI+ | EM Corp (overlay) | 1–3 m | JPMorgan EM Strategy |
| DXY momentum | Tendencia DXY 4–8 sem | Bloomberg DXY | EM Corp (overlay) | 1–4 sem | MacroMicro, BIS QR |
| Brent / commodity momentum | Tendencia Brent 1–3m | Bloomberg CO1 | EM Corp comm-linked | 1–3 m | Práctica EM Strategy buy-side |
| China PMI / Caixin | Nivel y cambio | Bloomberg CPMINDX, ECPMNICA | EM Corp Asia, commodities | 1–3 m | BIS, JPMorgan EM Strategy |

---

## REFERENCIAS ACADÉMICAS E INSTITUCIONALES PRINCIPALES

**Papers académicos seminales**

- Jostova, G., Nikolova, S., Philipov, A. & Stahel, C. W. (2013). "Momentum in Corporate Bond Returns". *Review of Financial Studies* 26(7), 1649–1693.
- Gebhardt, W. R., Hvidkjaer, S. & Swaminathan, B. (2005). "The Cross-Section of Expected Corporate Bond Returns: Betas or Characteristics?" *Journal of Financial Economics* 75(1), 85–114.
- Gebhardt, W. R., Hvidkjaer, S. & Swaminathan, B. (2005). "Stock and Bond Market Interaction: Does Momentum Spill Over?" *Journal of Financial Economics* 75(3), 651–690.
- Pospisil, L. & Zhang, J. (2010). "Momentum and Reversal Effects in Corporate Bond Prices and Credit Cycles". *Journal of Fixed Income* 20(2), 101–115.
- Khang, K. & King, T. D. (2004). "Return Reversals in the Bond Market: Evidence and Causes". *Journal of Banking & Finance* 28(3), 569–593.
- Asness, C., Moskowitz, T. & Pedersen, L. H. (2013). "Value and Momentum Everywhere". *Journal of Finance* 68(3), 929–985.
- Koijen, R., Moskowitz, T., Pedersen, L. H. & Vrugt, E. (2018). "Carry". *Journal of Financial Economics* 127(2), 197–225.
- Frazzini, A. & Pedersen, L. H. (2014). "Betting Against Beta" / Quality Minus Junk (AQR).
- Collin-Dufresne, P., Goldstein, R. S. & Martin, J. S. (2001). "The Determinants of Credit Spread Changes". *Journal of Finance* 56(6), 2177–2207.
- Bali, T., Subrahmanyam, A. & Wen, Q. — series sobre downside risk y reversals en corporate bonds.
- Kelly, B., Palhares, D. & Pruitt, S. (2023). "Modeling Corporate Bond Returns". *Journal of Finance*.

**Investigación institucional clave**

- Houweling, P. & van Zundert, J. (2017). "Factor Investing in the Corporate Bond Market". *Financial Analysts Journal* 73(2), 100–115. (Robeco)
- Haesen, D., Houweling, P. & van Zundert, J. (2017). "Momentum Spillover from Stocks to Corporate Bonds". *Journal of Banking & Finance* 79, 28–41. (Robeco)
- Dekker, L., Houweling, P. & Muskens, F. (2021). "Factor Investing in Emerging Market Credits". *Journal of Index Investing* 12(2), 28. (Robeco)
- Israel, R., Palhares, D. & Richardson, S. A. (2018). "Common Factors in Corporate Bond Returns". *Journal of Investment Management* 16(2), 17–46. (AQR)
- Brooks, J., Katz, M. & Moskowitz, T. (2016). "Style Investing in Fixed Income". (AQR Working Paper)
- Ben Dor, A., Dynkin, L., Hyman, J., Houweling, P., van Leeuwen, E. & Penninga, O. (2007). "DTS℠ (Duration Times Spread)". *Journal of Portfolio Management* 33(2), 77–100.
- Dynkin, L. et al. (2016). "A Decade of Duration Times Spread (DTS)". (Barclays Research)
- J.P. Morgan US Fixed Income Strategy. "JULI Fair Value Model". (Capítulo en "Fair Value Model for US Bonds, Credit, and Equities").
- Moody's Analytics (2010, actualizado 2.0). "EDF-based Bond Valuation Model" / Fair Value Spread methodology.
- J.P. Morgan Asset Management. *Long-Term Capital Market Assumptions* 2025 y 2026.
- Morgan Stanley Investment Management. *The BEAT* (publicación mensual de tactical asset allocation con percentile dashboards de spreads).
- BIS Quarterly Review (Dec 2025). "Volatility challenges risk-taking" — análisis de credit spreads, VIX y MOVE.
- Robeco (2024). "Duration Times Spread: measuring credit risk" y "Seizing opportunities in emerging markets credits".
- CFA Institute (2025). "Volatility Signals: Do Equities Forecast Bonds?" Enterprising Investor.

**Advertencia metodológica reciente**

Trabajos publicados en 2024–2026 (e.g., "The Corporate Bond Factor Replication Crisis", arxiv) advierten que parte de los premios documentados de momentum 6m–12m provienen de winsorización ex-post y filtros que introducen sesgo; los gestores institucionales deben validar señales con winsorización ex-ante y FDR-correction antes de asignar capital. Concretamente, el trabajo encuentra que el premio mensual del momentum 6m de 0.30% es enteramente atribuible a winsorización ex-post asimétrica, y para el momentum 12m la prima base es negativa antes de filtrar. Este es el riesgo central del momentum como factor stand-alone en IG: su robustez metodológica es inferior al value spread-based, que sobrevive las correcciones FDR y de error de medición. La conclusión práctica es **combinar momentum con value, carry y defensive en multi-factor portfolios** (la recomendación común a Robeco, AQR e Israel et al.) en lugar de operar momentum aislado.