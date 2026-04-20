# ================================================================
# TAA DASHBOARD — Momentum & Valuation
# Plataforma: R Shiny  |  Replicable en Power BI
# Autores: Investment Management — Lima, Peru
#
# INSTRUCCIONES:
#   install.packages(c("shiny","shinydashboard","shinyWidgets",
#     "readxl","dplyr","tidyr","plotly","DT","TTR","zoo","scales"))
#   shiny::runApp("taa_dashboard.R")
#
# NOTA POWER BI: Los cálculos están comentados con equivalentes DAX/
#   Power Query para facilitar la migración a Power BI.
# ================================================================

library(shiny)
library(shinydashboard)
library(shinyWidgets)
library(readxl)
library(dplyr)
library(tidyr)
library(plotly)
library(DT)
library(TTR)
library(zoo)
library(scales)

FILE_PATH <- "0_Dashboard_TAA.xlsx"   # ajustar si es necesario

# ── PALETA RIMAC ─────────────────────────────────────────────
R_BG      <- "#0B1220"
R_PANEL   <- "#111C2E"
R_CARD    <- "#162236"
R_BORDER  <- "#1E2E47"
R_RED     <- "#C41230"   # RIMAC primary
R_RED2    <- "#E8354A"
R_TEXT    <- "#E2E8F0"
R_MUTED   <- "#6B7A99"
R_GREEN   <- "#22C55E"
R_YELLOW  <- "#F0B429"
R_BLUE    <- "#3A7BD5"
R_TEAL    <- "#14B8A6"
R_ORANGE  <- "#F97316"

# ── LABELS ───────────────────────────────────────────────────
EQUITY_LABELS <- c(
  "NDDUWI Index"   = "MSCI World (DM)",
  "NDUEACWF Index" = "MSCI ACWI",
  "SPTRSVX Index"  = "S&P 500 Value",
  "SPXQUT Index"   = "S&P 500 Quality",
  "SPTRSGX Index"  = "S&P 500 Growth",
  "M0EFHUSD Index" = "MSCI EAFE (DM ex US)",
  "NDUEEGF Index"  = "MSCI EM",
  "M1CXBRV Index"  = "MSCI EM ex China",
  "NDEUCHF Index"  = "MSCI China",
  "S5INFT Index"   = "IT",
  "S5ENRS Index"   = "Energy",
  "S5UTIL Index"   = "Utilities",
  "S5INDU Index"   = "Industrials",
  "S5HLTH Index"   = "Health Care",
  "S5MATR Index"   = "Materials",
  "S5CONS Index"   = "Cons. Staples",
  "S5TELS Index"   = "Comm. Services",
  "S5RLST Index"   = "Real Estate",
  "S5COND Index"   = "Cons. Disc.",
  "S5FINL Index"   = "Financials"
)

OAS_LABELS <- c(
  "BAMLC0A4CBBB"         = "US Corp BBB (IG)",
  "BAMLH0A0HYM2"         = "US Corp HY",
  "BAMLEM2BRRBBBCRPIOAS" = "EM BBB",
  "BAMLEMRLCRPILAOAS"    = "LatAm EM"
)

SECTOR_TICKERS <- c("S5INFT Index","S5ENRS Index","S5UTIL Index","S5INDU Index",
                     "S5HLTH Index","S5MATR Index","S5CONS Index","S5TELS Index",
                     "S5RLST Index","S5COND Index","S5FINL Index")

# Pairs para rolling returns
PAIRS <- list(
  list(a = "NDDUWI Index",  b = "NDUEEGF Index",  label = "DM vs EM"),
  list(a = "SPTRSGX Index", b = "SPTRSVX Index",  label = "Growth vs Value"),
  list(a = "NDDUWI Index",  b = "M0EFHUSD Index", label = "World vs DM ex US"),
  list(a = "M1CXBRV Index", b = "NDEUCHF Index",  label = "EM ex China vs China")
)

# ================================================================
# 1. CARGA DE DATOS
# ================================================================
load_all <- function(path) {
  tr  <- read_excel(path, sheet = "TR Index")  %>% arrange(Date) %>% filter(!is.na(Date))
  pe  <- read_excel(path, sheet = "PE")        %>% arrange(Date) %>% filter(!is.na(Date))
  oas <- read_excel(path, sheet = "OAS")       %>% arrange(Date) %>% filter(!is.na(Date))
  cds <- read_excel(path, sheet = "CDS")       %>% arrange(Date) %>% filter(!is.na(Date))
  tsy <- read_excel(path, sheet = "TSY")       %>% arrange(Date) %>% filter(!is.na(Date))
  # Estandarizar nombre columna Treasury
  names(tsy) <- trimws(names(tsy))
  list(tr = tr, pe = pe, oas = oas, cds = cds, tsy = tsy)
}

# ================================================================
# 2. FUNCIONES DE CÁLCULO
# ================================================================

# ── Rolling Return (PBI: CALCULATE con DATESINPERIOD) ────────
rolling_ret <- function(px, lag) {
  n <- length(px)
  if (n <= lag) return(rep(NA_real_, n))
  c(rep(NA_real_, lag), (px[(lag + 1):n] / px[1:(n - lag)] - 1) * 100)
}

# ── MA distance (PBI: AVERAGEX + DATESINPERIOD) ──────────────
ma_dist <- function(px, n) {
  ma <- rollmean(px, n, fill = NA, align = "right")
  round((px / ma - 1) * 100, 2)
}

# ── RSI (PBI: custom measure con cambios positivos/negativos) ─
calc_rsi <- function(px, n) RSI(px, n = n)

# ── Compute all momentum metrics for TR tickers ──────────────
compute_momentum <- function(tr_df, oas_df) {
  tickers <- setdiff(names(tr_df), "Date")

  res <- lapply(tickers, function(tk) {
    px  <- tr_df[[tk]]
    n   <- length(px)
    lp  <- tail(px[!is.na(px)], 1)
    ma50  <- mean(tail(px[!is.na(px)], 50),  na.rm = TRUE)
    ma200 <- mean(tail(px[!is.na(px)], 200), na.rm = TRUE)

    # Returns
    safe <- function(lag) if (n > lag && !is.na(px[n-lag])) round((lp/px[n-lag]-1)*100,2) else NA_real_
    r1m  <- safe(21); r3m <- safe(63); r6m <- safe(126); r12m <- safe(min(252,n-1))

    # MA dists
    d50  <- if (n>=50)  round((lp/ma50-1)*100,2)  else NA_real_
    d200 <- if (n>=200) round((lp/ma200-1)*100,2) else NA_real_

    # Cross
    cross <- if (!is.na(d50) && !is.na(d200))
      if (ma50 > ma200) "Golden Cross" else "Death Cross" else NA_character_

    # Hi/Lo
    w3  <- if (n>=63)  tail(px[!is.na(px)],63)  else px[!is.na(px)]
    w6  <- if (n>=126) tail(px[!is.na(px)],126) else px[!is.na(px)]
    h3m <- max(w3); l3m <- min(w3)
    h6m <- max(w6); l6m <- min(w6)
    vs_h3 <- round((lp/h3m-1)*100,2); vs_l3 <- round((lp/l3m-1)*100,2)
    vs_h6 <- round((lp/h6m-1)*100,2); vs_l6 <- round((lp/l6m-1)*100,2)

    # RSI
    rsi14 <- if (n>=15) { r <- RSI(px[!is.na(px)],14); if (!all(is.na(r))) round(tail(r[!is.na(r)],1),1) else NA_real_ } else NA_real_
    rsi30 <- if (n>=31) { r <- RSI(px[!is.na(px)],30); if (!all(is.na(r))) round(tail(r[!is.na(r)],1),1) else NA_real_ } else NA_real_

    rsi_sig <- dplyr::case_when(
      is.na(rsi14) ~ NA_character_,
      rsi14 > 70   ~ "Sobrecompra",
      rsi14 < 30   ~ "Sobreventa",
      rsi14 >= 50  ~ "Alcista",
      TRUE         ~ "Bajista"
    )

    tibble(Ticker=tk, Label=EQUITY_LABELS[tk],
           Ret_1M=r1m, Ret_3M=r3m, Ret_6M=r6m, Ret_12M=r12m,
           Dist_MA50=d50, Dist_MA200=d200, Cross=cross,
           Hi_3M=h3m, Lo_3M=l3m, Hi_6M=h6m, Lo_6M=l6m,
           PctVsHi3M=vs_h3, PctVsLo3M=vs_l3, PctVsHi6M=vs_h6, PctVsLo6M=vs_l6,
           RSI_14=rsi14, RSI_30=rsi30, RSI_Signal=rsi_sig)
  })
  bind_rows(res) %>%
    mutate(
      Score = {
        cols <- c("Ret_1M","Ret_3M","Ret_6M","Ret_12M","Dist_MA50","Dist_MA200")
        apply(select(., all_of(cols)), 1, function(x) {
          if (all(is.na(x))) return(NA_real_)
          mean(rank(x, na.last="keep", ties.method="average") /
               sum(!is.na(x)), na.rm=TRUE) * 100
        }) %>% round(1)
      }
    )
}

# ── PE: Relative ratio + dynamic bands ───────────────────────
# PBI: Medida = DIVIDE(PE_A, PE_B)
# Bandas: Mean = AVERAGE(ratio sobre ventana), Std = STDEV.P(ratio sobre ventana)
pe_relative <- function(pe_df, tk_a, tk_b, lookback_rows = NULL) {
  df <- pe_df %>% select(Date, A = all_of(tk_a), B = all_of(tk_b)) %>%
    filter(!is.na(A), !is.na(B), B > 0)
  if (!is.null(lookback_rows) && nrow(df) > lookback_rows)
    df <- tail(df, lookback_rows)
  df %>% mutate(Ratio = A / B * 100)
}

# ── OAS MA metrics ───────────────────────────────────────────
oas_ma_metrics <- function(oas_df) {
  tickers <- setdiff(names(oas_df), "Date")
  lapply(tickers, function(tk) {
    px <- oas_df[[tk]]
    n  <- length(px)
    lp <- tail(px[!is.na(px)],1)
    ma50  <- mean(tail(px[!is.na(px)], 50),  na.rm=TRUE)
    ma200 <- mean(tail(px[!is.na(px)], 200), na.rm=TRUE)
    tibble(
      Ticker    = tk,
      Label     = OAS_LABELS[tk],
      Last      = round(lp, 2),
      MA50      = round(ma50, 2),
      MA200     = round(ma200, 2),
      Dist_MA50 = round((lp/ma50-1)*100, 2),
      Dist_MA200= round((lp/ma200-1)*100, 2),
      Cross     = if (ma50 > ma200) "Golden Cross" else "Death Cross"
    )
  }) %>% bind_rows()
}

# ================================================================
# 4-PILLAR TAA FRAMEWORK (Unified Scoring)
# ================================================================

# ── PILLAR 1: FUNDAMENTALS (Macro + Corporate) ────────────────
# Weight: 25% | Signals: ISM PMI (growth), inflation, leverage, defaults
compute_fundamentals <- function(data_list) {
  # Simplified: Uses current data; in production, integrate macro feeds
  tibble(
    Pillar = "Fundamentals",
    Weight = 0.25,
    Description = "Macro growth, inflation, leverage, defaults",
    Signal = 0.0,  # Placeholder; calibrate with macro data
    Direction = "Neutral"
  )
}

# ── PILLAR 2: MOMENTUM & SENTIMENT ──────────────────────────
# Weight: 30% | Signals: Price trends (12M returns), RSI, MA crosses, VIX
compute_momentum_pillar <- function(momentum_df) {
  # Aggregate momentum across tickers
  if (nrow(momentum_df) == 0) {
    return(tibble(
      Pillar = "Momentum & Sentiment",
      Weight = 0.30,
      Avg_Momentum = NA_real_,
      RSI_Avg = NA_real_,
      Signal = NA_real_
    ))
  }

  avg_momentum <- mean(momentum_df$Ret_12M, na.rm = TRUE)
  avg_rsi <- mean(momentum_df$RSI_14, na.rm = TRUE)

  # Normalized signal: RSI > 50 = bullish, < 50 = bearish
  signal <- ifelse(is.na(avg_rsi), 0,
                   if (avg_rsi > 70) -1 else if (avg_rsi > 50) 0.5 else if (avg_rsi < 30) 1 else 0)

  tibble(
    Pillar = "Momentum & Sentiment",
    Weight = 0.30,
    Avg_Momentum = round(avg_momentum, 2),
    RSI_Avg = round(avg_rsi, 1),
    Signal = signal
  )
}

# ── PILLAR 3: POSITIONING (Liquidity, Fund Flows) ────────────
# Weight: 15% | Signals: OAS spreads, fund flows, issuance, bid-ask
compute_positioning <- function(oas_df) {
  if (nrow(oas_df) == 0) {
    return(tibble(
      Pillar = "Positioning",
      Weight = 0.15,
      Avg_OAS = NA_real_,
      Spread_Signal = NA_character_,
      Signal = NA_real_
    ))
  }

  avg_oas <- mean(oas_df$Dist_MA200, na.rm = TRUE)

  # Spread interpretation: widening (negative) vs. tightening (positive)
  spread_signal <- if (is.na(avg_oas)) "Neutral"
                   else if (avg_oas > 5) "Widening (Risk-off)"
                   else if (avg_oas < -5) "Tightening (Risk-on)"
                   else "Neutral"

  signal <- if (is.na(avg_oas)) 0 else avg_oas / 10  # Scale to pillar score

  tibble(
    Pillar = "Positioning",
    Weight = 0.15,
    Avg_OAS_Dist = round(avg_oas, 2),
    Spread_Signal = spread_signal,
    Signal = signal
  )
}

# ── PILLAR 4: VALUATION ────────────────────────────────────
# Weight: 20% | Signals: P/E (absolute & relative), real yields, ERP
compute_valuation <- function(pe_df) {
  if (nrow(pe_df) == 0) {
    return(tibble(
      Pillar = "Valuation",
      Weight = 0.20,
      Avg_PE = NA_real_,
      Valuation_Signal = NA_character_,
      Signal = NA_real_
    ))
  }

  # Aggregate P/E across available tickers (exclude Date column)
  pe_values <- pe_df %>% select(-Date) %>% as.matrix() %>% as.numeric()
  pe_values <- pe_values[!is.na(pe_values)]

  avg_pe <- if (length(pe_values) > 0) mean(pe_values, na.rm = TRUE) else NA_real_

  # Valuation zones: <16x cheap, 16-22x fair, >22x expensive
  valuation_signal <- if (is.na(avg_pe)) "Neutral"
                      else if (avg_pe < 16) "Undervalued (Buy)"
                      else if (avg_pe > 22) "Overvalued (Sell)"
                      else "Fair Value (Neutral)"

  signal <- if (is.na(avg_pe)) 0 else -((avg_pe - 19) / 10)  # Centered at 19x

  tibble(
    Pillar = "Valuation",
    Weight = 0.20,
    Avg_PE = round(avg_pe, 1),
    Valuation_Signal = valuation_signal,
    Signal = signal
  )
}

# ── UNIFIED TAA SCORE (Aggregate 4 pillars) ────────────────
compute_taa_unified_score <- function(fundamentals, momentum, positioning, valuation) {
  # Weighted aggregate: each pillar contributes its weight × signal
  pillars <- list(
    list(pillar = fundamentals, weight = 0.25),
    list(pillar = momentum, weight = 0.30),
    list(pillar = positioning, weight = 0.15),
    list(pillar = valuation, weight = 0.20)
  )

  # Add Carry + Regime Overlay (10% placeholder)
  carry_regime_signal <- 0.10  # Placeholder

  # Extract signals safely
  signals <- sapply(pillars, function(x) {
    if (is.na(x$pillar$Signal[1])) 0 else x$pillar$Signal[1]
  })
  weights <- sapply(pillars, function(x) x$weight)

  composite_score <- sum(signals * weights, na.rm = TRUE) + carry_regime_signal * 0

  tibble(
    Date = Sys.Date(),
    Composite_Score = round(composite_score, 3),
    Conviction = dplyr::case_when(
      composite_score > 1.0 ~ "Very High (Strong OW)",
      composite_score > 0.5 ~ "High (OW)",
      composite_score > -0.5 ~ "Low (Neutral)",
      composite_score > -1.0 ~ "High UW (High UW)",
      TRUE ~ "Very High (Strong UW)"
    ),
    Fundamentals_Contrib = signals[1] * weights[1],
    Momentum_Contrib = signals[2] * weights[2],
    Positioning_Contrib = signals[3] * weights[3],
    Valuation_Contrib = signals[4] * weights[4]
  )
}

# ================================================================
# HELPERS PLOTLY
# ================================================================
rimac_layout <- function(p, title = NULL, xlab = "", ylab = "") {
  p %>% layout(
    title      = if (!is.null(title)) list(text=title, font=list(color=R_TEXT,size=13), x=0.01) else NULL,
    paper_bgcolor = R_CARD, plot_bgcolor = R_CARD,
    font       = list(color = R_TEXT, size = 11),
    xaxis      = list(title=xlab, gridcolor=R_BORDER, zerolinecolor=R_BORDER,
                      tickfont=list(color=R_MUTED)),
    yaxis      = list(title=ylab, gridcolor=R_BORDER, zerolinecolor=R_BORDER,
                      tickfont=list(color=R_MUTED)),
    legend     = list(bgcolor="transparent", font=list(color=R_TEXT,size=10),
                      orientation="h", y=1.08, x=0),
    hovermode  = "x unified",
    margin     = list(t=50, b=40, l=50, r=20)
  ) %>% config(displayModeBar=FALSE)
}

box_r <- function(..., title="Example", status="primary", width=12) {
  box(..., title=tags$span(style=paste0("color:",R_TEXT,"; font-weight:600;"), title),
      status=status, solidHeader=TRUE, width=width,
      style=paste0("background:",R_CARD,"; border:1px solid ",R_BORDER,
                   "; border-top:3px solid ", if(status=="primary") R_RED else if(status=="warning") R_YELLOW else R_BLUE,";"))
}

# ================================================================
# 3. UI
# ================================================================
ui <- dashboardPage(
  skin = "black", title = "TAA Dashboard",

  dashboardHeader(
    title = tags$span(
      tags$b(style=paste0("color:",R_RED,"; font-size:15px; letter-spacing:1px;"), "RIMAC"),
      tags$span(style=paste0("color:",R_MUTED,"; font-size:13px; margin-left:6px;"), "TAA Dashboard")
    ),
    titleWidth = 240
  ),

  dashboardSidebar(
    width = 210,
    sidebarMenu(
      id = "main_nav",
      tags$li(style=paste0("padding:10px 16px 4px; color:",R_RED,"; font-size:11px; letter-spacing:2px;"), "TAA FRAMEWORK"),
      menuSubItem("4-Pillar Unified", tabName = "taa_unified", icon = icon("chart-area")),
      tags$hr(style=paste0("border-color:",R_BORDER,";")),
      tags$li(style=paste0("padding:10px 16px 4px; color:",R_MUTED,"; font-size:10px; letter-spacing:2px;"), "I. MOMENTUM"),
      menuSubItem("Rolling Returns",   tabName = "roll_ret",   icon = icon("chart-line")),
      menuSubItem("Moving Averages",   tabName = "mov_avg",    icon = icon("wave-square")),
      menuSubItem("Breakouts",         tabName = "breakouts",  icon = icon("arrow-trend-up")),
      menuSubItem("RSI",               tabName = "rsi_tab",    icon = icon("gauge-high")),
      tags$hr(style=paste0("border-color:",R_BORDER,";")),
      tags$li(style=paste0("padding:6px 16px 4px; color:",R_MUTED,"; font-size:10px; letter-spacing:2px;"), "II. VALUATION"),
      menuSubItem("P/E Absolute",      tabName = "pe_abs",     icon = icon("dollar-sign")),
      menuSubItem("P/E Relative",      tabName = "pe_rel",     icon = icon("scale-balanced")),
      menuSubItem("OAS",               tabName = "oas_tab",    icon = icon("credit-card")),
      menuSubItem("CDS",               tabName = "cds_tab",    icon = icon("shield-halved")),
      menuSubItem("Yield Curve",       tabName = "yld_tab",    icon = icon("bezier-curve"))
    ),
    tags$div(
      style=paste0("position:absolute;bottom:14px;left:0;right:0;text-align:center;",
                   "font-size:10px;color:",R_MUTED,";"),
      icon("circle-dot", style=paste0("color:",R_RED,";")),
      " Investment Management"
    )
  ),

  dashboardBody(
    tags$head(tags$style(HTML(paste0("
      body,.wrapper,.content-wrapper{background:",R_BG,"!important}
      .skin-black .main-sidebar{background:",R_PANEL,";}
      .skin-black .sidebar-menu>li>a{color:",R_TEXT,"; font-size:13px;}
      .skin-black .sidebar-menu>li.active>a,.skin-black .sidebar-menu>li>a:hover{
        background:",R_BORDER,"!important; color:",R_TEXT,"!important;}
      .skin-black .sidebar-menu>li>a>.fa{color:",R_RED,";}
      .main-header .navbar,.main-header .logo{background:",R_PANEL,"!important;
        border-bottom:1px solid ",R_BORDER,"!important;}
      .box{background:",R_CARD,"!important;border-color:",R_BORDER,"!important;color:",R_TEXT,"!important;}
      .box-header .box-title{color:",R_TEXT,"!important; font-size:13px;}
      .nav-tabs-custom>.tab-content{background:",R_CARD,";}
      .select2-container--default .select2-selection--single,
      .select2-container--default .select2-selection--multiple{
        background:",R_BORDER,"; border-color:",R_BORDER,"; color:",R_TEXT,";}
      .select2-container--default .select2-results__option{background:",R_PANEL,";color:",R_TEXT,";}
      .select2-container--default .select2-results__option--highlighted{background:",R_BORDER,"!important;}
      .form-control{background:",R_BORDER,"; color:",R_TEXT,"; border-color:",R_BORDER,";}
      .irs--shiny .irs-bar{background:",R_RED,";border-color:",R_RED,";}
      .irs--shiny .irs-handle{background:",R_RED,";}
      .irs--shiny .irs-single,.irs--shiny .irs-to,.irs--shiny .irs-from{background:",R_RED,";}
      .dataTables_wrapper,.dataTables_filter input{color:",R_TEXT,";}
      table.dataTable{background:",R_CARD,"!important;color:",R_TEXT,"!important;}
      table.dataTable thead th{background:#1E2E47!important;color:",R_TEXT,"!important;border-bottom:1px solid ",R_BORDER,";}
      .small-box{background:",R_CARD,"!important;border:1px solid ",R_BORDER,"!important;}
      .small-box .icon{color:",R_BORDER,"!important;}
      .shiny-notification{background:",R_PANEL,";color:",R_TEXT,";}
      .nav-pills>li>a{color:",R_TEXT,"!important; background:",R_PANEL,"!important;}
      .nav-pills>li.active>a,.nav-pills>li>a:hover{background:",R_RED,"!important; color:white!important;}
    ")))),

    tabItems(

      # ── 0. TAA UNIFIED 4-PILLAR SCORECARD ───────────────────
      tabItem("taa_unified",
        fluidRow(
          column(12, h2(style=paste0("color:",R_TEXT,"; font-weight:700;"),
            icon("compass"), " TAA Framework: 4-Pillar Unified Score"))
        ),
        fluidRow(
          box_r(DTOutput("tbl_taa_pillars"),
            title="Pillar Analysis (25% / 30% / 15% / 20% weights)", width=12)
        ),
        fluidRow(
          box_r(
            column(4, uiOutput("vb_composite_score")),
            column(4, uiOutput("vb_conviction")),
            column(4, uiOutput("vb_pillar_consensus")),
            width=12
          )
        ),
        fluidRow(
          box_r(plotlyOutput("plt_pillar_waterfall", height="360px"),
            title="Pillar Contribution to Composite Score (Waterfall)", width=6),
          box_r(plotlyOutput("plt_pillar_radar", height="360px"),
            title="Pillar Strength Profile (Radar)", width=6)
        ),
        fluidRow(
          box_r(
            fluidRow(
              column(6, h4("Interpretation Guide")),
              column(6, tags$small(style="color:#999;", "Based on z-score normalization"))
            ),
            fluidRow(
              column(3, tags$div(
                style=paste0("padding:10px; background:",R_CARD,"; border-left:3px solid ",R_GREEN,";"),
                tags$b("Very High (>+1.5)"), br(),
                "Strong overweight signal"
              )),
              column(3, tags$div(
                style=paste0("padding:10px; background:",R_CARD,"; border-left:3px solid ",R_BLUE,";"),
                tags$b("High (+0.5 to +1.5)"), br(),
                "Moderate overweight"
              )),
              column(3, tags$div(
                style=paste0("padding:10px; background:",R_CARD,"; border-left:3px solid ",R_YELLOW,";"),
                tags$b("Low (-0.5 to +0.5)"), br(),
                "Neutral; stay at benchmark"
              )),
              column(3, tags$div(
                style=paste0("padding:10px; background:",R_CARD,"; border-left:3px solid ",R_RED,";"),
                tags$b("Underweight (<-0.5)"), br(),
                "Defensive positioning"
              ))
            ),
            title="Signal Levels & Portfolio Actions", width=12, status="primary"
          )
        )
      ),

      # ── I-1. ROLLING RETURNS ────────────────────────────────
      tabItem("roll_ret",
        fluidRow(
          column(3,
            pickerInput("roll_period", "Período de retorno:",
              choices=c("1M (~21d)"="21","3M (~63d)"="63","6M (~126d)"="126","12M (~252d)"="252"),
              selected="63", options=pickerOptions(style="btn-dark")),
            sliderInput("roll_lookback","Ventana histórica (días):",
              min=60, max=261, value=200, step=10, ticks=FALSE)
          ),
          column(9,
            tags$div(style=paste0("color:",R_MUTED,"; font-size:11px; padding:8px 0;"),
              icon("circle-info"), " Rolling return = retorno acumulado en la ventana seleccionada, calculado día a día.")
          )
        ),
        fluidRow(
          box_r(plotlyOutput("plt_pair1", height="220px"), title="DM vs EM", width=6),
          box_r(plotlyOutput("plt_pair2", height="220px"), title="Growth vs Value", width=6)
        ),
        fluidRow(
          box_r(plotlyOutput("plt_pair3", height="220px"), title="World vs DM ex US", width=6),
          box_r(plotlyOutput("plt_pair4", height="220px"), title="EM ex China vs China", width=6)
        ),
        fluidRow(
          box_r(
            fluidRow(
              column(5,
                pickerInput("roll_free_sel","Seleccionar activos:",
                  choices = setNames(names(EQUITY_LABELS), EQUITY_LABELS),
                  selected = c("NDDUWI Index","SPTRSGX Index","NDUEEGF Index","NDEUCHF Index"),
                  multiple=TRUE, options=pickerOptions(actionsBox=TRUE, style="btn-dark",
                  selectedTextFormat="count > 2", liveSearch=TRUE))
              )
            ),
            plotlyOutput("plt_roll_free", height="280px"),
            title="Comparador libre — Todos los activos", width=12
          )
        )
      ),

      # ── I-2. MOVING AVERAGES ────────────────────────────────
      tabItem("mov_avg",
        fluidRow(
          box_r(
            DTOutput("tbl_ma_equity"),
            title="Equity — Distancia a MA 50/200d", width=8,
            tags$p(style=paste0("font-size:10px;color:",R_MUTED,";margin-top:8px;"),
              "Dist % = (Precio / MAn − 1) × 100. Verde = sobre la MA. PBI: MEASURE Dist_MA50 = DIVIDE([Last],[MA50],0)−1")
          ),
          box_r(
            plotlyOutput("plt_ma_bar",  height="400px"),
            title="Heatmap Δ MA200", width=4
          )
        ),
        fluidRow(
          box_r(
            plotlyOutput("plt_oas_ma", height="360px"),
            title="OAS — Evolución + MA 50/200d (datos históricos largos)", width=12,
            fluidRow(
              column(4, pickerInput("oas_ma_sel","Serie OAS:",
                choices=setNames(names(OAS_LABELS),OAS_LABELS), selected="BAMLH0A0HYM2",
                options=pickerOptions(style="btn-dark"))),
              column(4, sliderInput("oas_lb","Ventana histórica (años):",
                min=2, max=26, value=10, step=1, ticks=FALSE))
            )
          )
        )
      ),

      # ── I-3. BREAKOUTS ──────────────────────────────────────
      tabItem("breakouts",
        fluidRow(
          box_r(DTOutput("tbl_breakouts"), title="Breakouts activos 3M / 6M + Golden/Death Cross", width=12)
        ),
        fluidRow(
          box_r(plotlyOutput("plt_cross_chart", height="380px"),
            title="Visualización: MA50 vs MA200 (activo seleccionado)", width=8,
            pickerInput("cross_sel","Activo:",
              choices=setNames(names(EQUITY_LABELS),EQUITY_LABELS),
              selected="NDDUWI Index", options=pickerOptions(style="btn-dark"))),
          box_r(plotlyOutput("plt_hilow", height="380px"),
            title="% vs High/Low — Todos los activos", width=4)
        )
      ),

      # ── I-4. RSI ────────────────────────────────────────────
      tabItem("rsi_tab",
        fluidRow(
          valueBoxOutput("vb_overbought", width=3),
          valueBoxOutput("vb_oversold",   width=3),
          valueBoxOutput("vb_bullish",    width=3),
          valueBoxOutput("vb_bearish",    width=3)
        ),
        fluidRow(
          box_r(plotlyOutput("plt_rsi_bars", height="380px"),
            title="RSI 14d / 30d — Todos los activos", width=7),
          box_r(plotlyOutput("plt_rsi_ts",   height="380px"),
            title="Serie RSI histórica", width=5,
            pickerInput("rsi_tk","Activo:",
              choices=setNames(names(EQUITY_LABELS),EQUITY_LABELS),
              selected="SPTRSGX Index", options=pickerOptions(style="btn-dark")))
        )
      ),

      # ── II-1. P/E ABSOLUTE ──────────────────────────────────
      tabItem("pe_abs",
        fluidRow(
          box_r(plotlyOutput("plt_pe_global",  height="320px"),
            title="Global / Regional P/E Forward", width=6),
          box_r(plotlyOutput("plt_pe_sectors", height="320px"),
            title="S&P 500 Sectores — P/E Forward", width=6)
        ),
        fluidRow(
          box_r(DTOutput("tbl_pe_current"), title="P/E actual — Todos los activos", width=12)
        )
      ),

      # ── II-2. P/E RELATIVE ──────────────────────────────────
      tabItem("pe_rel",
        fluidRow(
          column(3,
            pickerInput("pe_rel_a", "Numerador (A):",
              choices = setNames(names(EQUITY_LABELS),EQUITY_LABELS),
              selected = "S5INFT Index", options = pickerOptions(style="btn-dark",liveSearch=TRUE)),
            pickerInput("pe_rel_b", "Denominador (B) — Mercado:",
              choices = setNames(names(EQUITY_LABELS),EQUITY_LABELS),
              selected = "NDUEACWF Index", options = pickerOptions(style="btn-dark",liveSearch=TRUE)),
            sliderInput("pe_rel_lb","Ventana histórica (días):",
              min=60, max=261, value=200, step=10, ticks=FALSE),
            tags$div(style=paste0("color:",R_MUTED,";font-size:10px;margin-top:8px;"),
              "Ratio = P/E(A) / P/E(B) × 100",tags$br(),
              "Banda media = promedio histórico (ventana seleccionada)",tags$br(),
              "Bandas ±1σ = ±1 desviación estándar",tags$br(),tags$br(),
              icon("lightbulb")," PBI DAX:",tags$br(),
              "Mean = AVERAGE(ratio [ALL DATES en ventana])",tags$br(),
              "Std = STDEV.P(ratio [ALL DATES en ventana])")
          ),
          column(9,
            box_r(plotlyOutput("plt_pe_rel", height="440px"),
              title="P/E Relativo con Bandas Dinámicas", width=12)
          )
        ),
        fluidRow(
          box_r(plotlyOutput("plt_pe_rel_heatmap", height="360px"),
            title="Heatmap P/E Relativo — Sectores S&P 500 vs US Market (All US Sectors)", width=12)
        )
      ),

      # ── II-3. OAS ───────────────────────────────────────────
      tabItem("oas_tab",
        fluidRow(
          column(3,
            sliderInput("oas_hist_lb","Ventana histórica (años):",
              min=2, max=26, value=10, step=1, ticks=FALSE)
          ),
          column(9, tags$div(style=paste0("color:",R_MUTED,";font-size:11px;padding:8px 0;"),
            "OAS = Option-Adjusted Spread vs Treasury. Fuente: ICE BofA / FRED."))
        ),
        fluidRow(
          box_r(plotlyOutput("plt_oas_ig_hy", height="320px"),
            title="US Corp: IG (BBB) vs HY — OAS histórico", width=6),
          box_r(plotlyOutput("plt_oas_em",    height="320px"),
            title="EM BBB vs LatAm EM — OAS histórico", width=6)
        ),
        fluidRow(
          box_r(plotlyOutput("plt_oas_all_bands", height="340px"),
            title="OAS con Bandas ±1σ (ventana seleccionada)", width=12,
            pickerInput("oas_band_sel","Serie:",
              choices=setNames(names(OAS_LABELS),OAS_LABELS),
              selected="BAMLH0A0HYM2", options=pickerOptions(style="btn-dark")))
        )
      ),

      # ── II-4. CDS ───────────────────────────────────────────
      tabItem("cds_tab",
        fluidRow(
          column(3,
            sliderInput("cds_lb","Ventana histórica (años):",
              min=2, max=15, value=8, step=1, ticks=FALSE)
          )
        ),
        fluidRow(
          box_r(plotlyOutput("plt_cds_ts",    height="340px"),
            title="CDS 5Y — US IG vs US HY (bps)", width=8),
          box_r(plotlyOutput("plt_cds_stats", height="340px"),
            title="CDS actual vs histórico (percentil)", width=4)
        ),
        fluidRow(
          box_r(DTOutput("tbl_cds_summary"), title="CDS — Resumen estadístico", width=12)
        )
      ),

      # ── II-5. YIELD CURVE ────────────────────────────────────
      tabItem("yld_tab",
        fluidRow(
          valueBoxOutput("vb_10y",    width=3),
          valueBoxOutput("vb_2y",     width=3),
          valueBoxOutput("vb_spread", width=3),
          valueBoxOutput("vb_curve_signal", width=3)
        ),
        fluidRow(
          box_r(plotlyOutput("plt_yield_spread", height="360px"),
            title="US Yield Curve — Spread 10Y − 2Y (bps)", width=8,
            column(12, sliderInput("tsy_lb","Ventana histórica (años):",
              min=2, max=26, value=8, step=1, ticks=FALSE))),
          box_r(plotlyOutput("plt_yield_levels", height="360px"),
            title="Niveles — Treasury 10Y vs 2Y", width=4)
        ),
        fluidRow(
          box_r(plotlyOutput("plt_yield_dist", height="260px"),
            title="Distribución histórica del spread (ventana seleccionada)", width=6,
            status="warning"),
          box_r(DTOutput("tbl_yield_stats"), title="Estadísticas Yield Curve", width=6)
        )
      )
    )
  )
)

# ================================================================
# 4. SERVER
# ================================================================
server <- function(input, output, session) {

  # ── DATOS ────────────────────────────────────────────────────
  D <- reactive({ withProgress(message="Cargando datos...",{load_all(FILE_PATH)}) })

  momentum <- reactive({
    withProgress(message="Calculando momentum...",{
      compute_momentum(D()$tr, D()$oas)
    })
  })

  # ── 4-PILLAR TAA FRAMEWORK ──────────────────────────────────
  fundamentals_pillar <- reactive({
    withProgress(message="Calculando Pillar 1: Fundamentals...",{
      compute_fundamentals(list(macro = NULL, corp = NULL))
    })
  })

  momentum_pillar <- reactive({
    withProgress(message="Calculando Pillar 2: Momentum...",{
      compute_momentum_pillar(momentum())
    })
  })

  positioning_pillar <- reactive({
    withProgress(message="Calculando Pillar 3: Positioning...",{
      oas_metrics <- oas_ma_metrics(D()$oas)
      compute_positioning(oas_metrics)
    })
  })

  valuation_pillar <- reactive({
    withProgress(message="Calculando Pillar 4: Valuation...",{
      compute_valuation(D()$pe)
    })
  })

  # ── UNIFIED TAA COMPOSITE SCORE ────────────────────────────
  taa_composite <- reactive({
    withProgress(message="Unificando 4 Pilares...",{
      compute_taa_unified_score(
        fundamentals_pillar(),
        momentum_pillar(),
        positioning_pillar(),
        valuation_pillar()
      )
    })
  })

  # ── HELPER: retornos rolling para un ticker ──────────────────
  get_rolling <- function(tk, lag) {
    df <- D()$tr %>% select(Date, px = all_of(tk)) %>% filter(!is.na(px))
    n  <- nrow(df)
    actual_lag <- min(lag, n-1)
    df %>% mutate(ret = rolling_ret(px, actual_lag)) %>% filter(!is.na(ret))
  }

  # ── HELPER: pair rolling chart ───────────────────────────────
  pair_chart <- function(tk_a, tk_b, label_a, label_b, lag, lookback) {
    da <- get_rolling(tk_a, lag) %>% tail(lookback)
    db <- get_rolling(tk_b, lag) %>% tail(lookback)

    plot_ly() %>%
      add_lines(data=da, x=~Date, y=~ret, name=label_a,
                line=list(color=R_BLUE, width=2)) %>%
      add_lines(data=db, x=~Date, y=~ret, name=label_b,
                line=list(color=R_RED2, width=2, dash="dash")) %>%
      add_lines(data=da, x=~Date, y=rep(0,nrow(da)), showlegend=FALSE,
                line=list(color=R_MUTED, width=1, dash="dot")) %>%
      rimac_layout(ylab="Retorno %")
  }

  lag_val <- reactive({ as.integer(input$roll_period) })

  # ── TAA UNIFIED OUTPUTS ─────────────────────────────────────
  output$tbl_taa_pillars <- renderDT({
    taa_pillars <- bind_rows(
      fundamentals_pillar(),
      momentum_pillar(),
      positioning_pillar(),
      valuation_pillar()
    )

    dt_tbl <- taa_pillars %>%
      select(Pillar, Weight, Signal) %>%
      mutate(
        Weight = paste0(round(Weight * 100), "%"),
        Signal = round(Signal, 3)
      )

    datatable(dt_tbl, rownames = FALSE,
      options = list(dom = 'fti', pageLength = 4, ordering = FALSE)) %>%
      formatStyle(
        'Signal',
        backgroundColor = styleInterval(
          c(-1, -0.5, 0, 0.5, 1),
          c('#C41230', '#F97316', '#F0B429', '#3A7BD5', '#22C55E')
        ),
        color = R_TEXT
      )
  })

  output$vb_composite_score <- renderUI({
    score <- taa_composite()$Composite_Score[1]
    score_color <- if (score > 0.5) R_GREEN else if (score < -0.5) R_RED else R_YELLOW

    valueBox(
      value = tags$span(style = paste0("color:", score_color, "; font-size:24px; font-weight:700;"),
                        sprintf("%.3f", score)),
      subtitle = "Composite Z-Score",
      icon = icon("compass"),
      color = "black",
      width = 12
    )
  })

  output$vb_conviction <- renderUI({
    conv <- taa_composite()$Conviction[1]
    conv_color <- if (grepl("Very High|Strong", conv)) R_RED else if (grepl("High", conv)) R_ORANGE else R_YELLOW

    valueBox(
      value = tags$span(style = paste0("color:", conv_color, ";"), conv),
      subtitle = "Signal Conviction Level",
      icon = icon("star"),
      color = "black",
      width = 12
    )
  })

  output$vb_pillar_consensus <- renderUI({
    signals <- c(
      taa_composite()$Fundamentals_Contrib[1],
      taa_composite()$Momentum_Contrib[1],
      taa_composite()$Positioning_Contrib[1],
      taa_composite()$Valuation_Contrib[1]
    )
    consensus <- mean(signals[!is.na(signals)])
    agreement <- sum(sign(signals) == sign(consensus), na.rm = TRUE) / length(signals[!is.na(signals)])

    valueBox(
      value = tags$span(style = paste0("color:", R_TEAL, ";"),
                        sprintf("%.1f%%", agreement * 100)),
      subtitle = "Pillar Agreement Rate",
      icon = icon("handshake"),
      color = "black",
      width = 12
    )
  })

  output$plt_pillar_waterfall <- renderPlotly({
    composite <- taa_composite()

    pillars_names <- c("Fundamentals", "Momentum", "Positioning", "Valuation", "Composite")
    pillars_contrib <- c(
      composite$Fundamentals_Contrib[1],
      composite$Momentum_Contrib[1],
      composite$Positioning_Contrib[1],
      composite$Valuation_Contrib[1],
      composite$Composite_Score[1]
    )

    colors <- c(R_BLUE, R_TEAL, R_ORANGE, R_GREEN, R_RED)

    plot_ly(x = pillars_names, y = pillars_contrib, type = "bar",
            marker = list(color = colors, opacity = 0.85),
            text = round(pillars_contrib, 3), textposition = "outside") %>%
      rimac_layout(title = "Pillar Contributions", ylab = "Z-Score") %>%
      layout(margin = list(b = 50))
  })

  output$plt_pillar_radar <- renderPlotly({
    composite <- taa_composite()

    signals <- c(
      composite$Fundamentals_Contrib[1],
      composite$Momentum_Contrib[1],
      composite$Positioning_Contrib[1],
      composite$Valuation_Contrib[1]
    )

    r <- signals / max(abs(signals), na.rm = TRUE)

    plot_ly(
      type = "scatterpolar",
      r = c(r[1], r[2], r[3], r[4], r[1]),
      theta = c("Fundamentals", "Momentum", "Positioning", "Valuation", "Fundamentals"),
      fill = "toself",
      line = list(color = R_RED),
      fillcolor = "rgba(196, 18, 48, 0.3)",
      name = "Pillar Strength"
    ) %>%
      layout(
        polar = list(
          bgcolor = R_CARD,
          radialaxis = list(
            visible = TRUE,
            range = c(-1, 1),
            tickfont = list(color = R_MUTED, size = 9),
            gridcolor = R_BORDER,
            zeroline = TRUE
          ),
          angularaxis = list(tickfont = list(color = R_TEXT, size = 11))
        ),
        paper_bgcolor = R_CARD,
        font = list(color = R_TEXT),
        showlegend = FALSE,
        margin = list(t = 40, b = 40, l = 40, r = 40)
      )
  })

  output$plt_pair1 <- renderPlotly({
    pair_chart("NDDUWI Index","NDUEEGF Index","MSCI World (DM)","MSCI EM",
               lag_val(), input$roll_lookback)
  })
  output$plt_pair2 <- renderPlotly({
    pair_chart("SPTRSGX Index","SPTRSVX Index","S&P 500 Growth","S&P 500 Value",
               lag_val(), input$roll_lookback)
  })
  output$plt_pair3 <- renderPlotly({
    pair_chart("NDDUWI Index","M0EFHUSD Index","MSCI World","MSCI EAFE (ex US)",
               lag_val(), input$roll_lookback)
  })
  output$plt_pair4 <- renderPlotly({
    pair_chart("M1CXBRV Index","NDEUCHF Index","MSCI EM ex China","MSCI China",
               lag_val(), input$roll_lookback)
  })

  output$plt_roll_free <- renderPlotly({
    req(input$roll_free_sel)
    colors <- colorRampPalette(c(R_BLUE,R_TEAL,R_YELLOW,R_RED2,R_ORANGE,R_GREEN))(length(input$roll_free_sel))
    p <- plot_ly()
    for (i in seq_along(input$roll_free_sel)) {
      tk <- input$roll_free_sel[i]
      df <- get_rolling(tk, lag_val()) %>% tail(input$roll_lookback)
      lbl <- EQUITY_LABELS[tk]
      p <- add_lines(p, data=df, x=~Date, y=~ret, name=lbl,
                     line=list(color=colors[i], width=1.8))
    }
    p %>% add_lines(x=range(D()$tr$Date), y=c(0,0), showlegend=FALSE,
                    line=list(color=R_MUTED,width=1,dash="dot")) %>%
      rimac_layout(ylab="Retorno %")
  })

  # ── MOVING AVERAGES TABLE ────────────────────────────────────
  output$tbl_ma_equity <- renderDT({
    m <- momentum() %>%
      transmute(
        Activo    = Label,
        `Ret 1M%` = Ret_1M,
        `Ret 3M%` = Ret_3M,
        `Δ MA50%`  = Dist_MA50,
        `Δ MA200%` = Dist_MA200,
        Cross      = Cross,
        `RSI 14`   = RSI_14
      )
    datatable(m, rownames=FALSE,
      options=list(pageLength=20, dom='frti', scrollX=TRUE,
                   columnDefs=list(list(className='dt-center',targets=1:6)))) %>%
      formatRound(c("Ret 1M%","Ret 3M%","Δ MA50%","Δ MA200%","RSI 14"), 2) %>%
      formatStyle(c("Δ MA50%","Δ MA200%"),
        backgroundColor=styleInterval(c(-3,0,3),c("#EF444440","#EF444425","#22222220","#22C55E25","#22C55E40")),
        color=R_TEXT) %>%
      formatStyle("RSI 14",
        backgroundColor=styleInterval(c(30,50,70),c("#EF444440","#EF444420","#22C55E20","#F0B42940")),
        color=R_TEXT) %>%
      formatStyle("Cross",
        backgroundColor=styleEqual(c("Golden Cross","Death Cross"),c("#22C55E30","#EF444430")),
        color=R_TEXT)
  })

  output$plt_ma_bar <- renderPlotly({
    m <- momentum() %>% filter(!is.na(Dist_MA200)) %>% arrange(Dist_MA200)
    bar_col <- ifelse(m$Dist_MA200 >= 0, R_GREEN, R_RED)
    plot_ly(m, x=~Dist_MA200, y=~Label, type="bar", orientation="h",
            text=~round(Dist_MA200,1), textposition="outside",
            marker=list(color=bar_col, opacity=0.85)) %>%
      rimac_layout(title="Dist. MA 200d (%)", xlab="%") %>%
      layout(yaxis=list(tickfont=list(size=9), automargin=TRUE),
             margin=list(l=110,r=40))
  })

  output$plt_oas_ma <- renderPlotly({
    req(input$oas_ma_sel, input$oas_lb)
    tk  <- input$oas_ma_sel
    lbl <- OAS_LABELS[tk]
    lb_rows <- input$oas_lb * 252
    df <- D()$oas %>% select(Date, px=all_of(tk)) %>% filter(!is.na(px)) %>%
      tail(lb_rows) %>%
      mutate(MA50  = rollmean(px, 50,  fill=NA, align="right"),
             MA200 = rollmean(px, 200, fill=NA, align="right"))

    plot_ly(df, x=~Date) %>%
      add_lines(y=~px,   name=lbl,    line=list(color=R_TEAL, width=2)) %>%
      add_lines(y=~MA50, name="MA 50",line=list(color=R_YELLOW,width=1.5,dash="dot")) %>%
      add_lines(y=~MA200,name="MA 200",line=list(color=R_RED2,  width=1.5,dash="dash")) %>%
      rimac_layout(ylab="OAS (%)") %>%
      layout(legend=list(orientation="h",y=1.06,x=0))
  })

  # ── BREAKOUTS ────────────────────────────────────────────────
  output$tbl_breakouts <- renderDT({
    m <- momentum() %>%
      transmute(
        Activo = Label,
        Cross  = Cross,
        `vs Máx 3M%` = PctVsHi3M,
        `vs Mín 3M%` = PctVsLo3M,
        `vs Máx 6M%` = PctVsHi6M,
        `vs Mín 6M%` = PctVsLo6M,
        `Breakout 3M` = dplyr::case_when(
          abs(PctVsHi3M) < 1 ~ "▲ New High 3M",
          abs(PctVsLo3M) < 1 ~ "▼ New Low 3M",
          TRUE ~ "—"),
        `Breakout 6M` = dplyr::case_when(
          abs(PctVsHi6M) < 1 ~ "▲ New High 6M",
          abs(PctVsLo6M) < 1 ~ "▼ New Low 6M",
          TRUE ~ "—")
      )
    datatable(m, rownames=FALSE, escape=FALSE,
      options=list(pageLength=20, dom='frti', scrollX=TRUE)) %>%
      formatRound(c("vs Máx 3M%","vs Mín 3M%","vs Máx 6M%","vs Mín 6M%"), 2) %>%
      formatStyle("Cross",
        backgroundColor=styleEqual(c("Golden Cross","Death Cross"),c("#22C55E30","#EF444430")),
        color=R_TEXT) %>%
      formatStyle(c("Breakout 3M","Breakout 6M"),
        backgroundColor=styleEqual(
          c("▲ New High 3M","▼ New Low 3M","▲ New High 6M","▼ New Low 6M","—"),
          c("#22C55E50","#EF444450","#22C55E50","#EF444450","transparent")),
        color=R_TEXT)
  })

  output$plt_cross_chart <- renderPlotly({
    req(input$cross_sel)
    tk <- input$cross_sel
    df <- D()$tr %>% select(Date, px=all_of(tk)) %>% filter(!is.na(px)) %>%
      mutate(MA50  = rollmean(px, 50,  fill=NA, align="right"),
             MA200 = rollmean(px, 200, fill=NA, align="right"))

    plot_ly(df, x=~Date) %>%
      add_lines(y=~px,   name=EQUITY_LABELS[tk], line=list(color=R_BLUE,  width=2)) %>%
      add_lines(y=~MA50, name="MA 50",            line=list(color=R_YELLOW,width=1.5,dash="dot")) %>%
      add_lines(y=~MA200,name="MA 200",           line=list(color=R_RED2,  width=1.5,dash="dash")) %>%
      rimac_layout(ylab="Índice") %>%
      layout(legend=list(orientation="h",y=1.06,x=0))
  })

  output$plt_hilow <- renderPlotly({
    m <- momentum() %>% filter(!is.na(PctVsHi3M)) %>% arrange(PctVsHi3M)
    plot_ly(m, x=~PctVsHi3M, y=~Label, type="bar", orientation="h",
            name="vs Máx 3M", text=~round(PctVsHi3M,1), textposition="outside",
            marker=list(color=ifelse(m$PctVsHi3M>=0,R_GREEN,R_RED), opacity=0.8)) %>%
      rimac_layout(title="% vs Máx 3M", xlab="%") %>%
      layout(yaxis=list(tickfont=list(size=9),automargin=TRUE), margin=list(l=110,r=40))
  })

  # ── RSI VALUE BOXES ──────────────────────────────────────────
  output$vb_overbought <- renderValueBox({
    n <- sum(momentum()$RSI_14 > 70, na.rm=TRUE)
    valueBox(n, "RSI > 70 — Sobrecompra", icon=icon("arrow-trend-up"),
             color="red")
  })
  output$vb_oversold <- renderValueBox({
    n <- sum(momentum()$RSI_14 < 30, na.rm=TRUE)
    valueBox(n, "RSI < 30 — Sobreventa", icon=icon("arrow-trend-down"),
             color="orange")
  })
  output$vb_bullish <- renderValueBox({
    n <- sum(momentum()$RSI_14 >= 50 & momentum()$RSI_14 <= 70, na.rm=TRUE)
    valueBox(n, "RSI 50–70 — Alcista", icon=icon("circle-arrow-up"),
             color="green")
  })
  output$vb_bearish <- renderValueBox({
    n <- sum(momentum()$RSI_14 < 50 & momentum()$RSI_14 >= 30, na.rm=TRUE)
    valueBox(n, "RSI 30–50 — Bajista", icon=icon("circle-arrow-down"),
             color="blue")
  })

  output$plt_rsi_bars <- renderPlotly({
    m <- momentum() %>% filter(!is.na(RSI_14)) %>% arrange(RSI_14)
    cols <- dplyr::case_when(
      m$RSI_14 > 70 ~ R_RED2, m$RSI_14 < 30 ~ R_ORANGE,
      m$RSI_14 >= 50 ~ R_GREEN, TRUE ~ R_MUTED)

    plot_ly(m) %>%
      add_bars(x=~RSI_14, y=~Label, orientation="h", name="RSI 14d",
               text=~round(RSI_14,1), textposition="outside",
               marker=list(color=cols, opacity=0.85)) %>%
      add_bars(x=~RSI_30, y=~Label, orientation="h", name="RSI 30d",
               text=~round(RSI_30,1), textposition="outside",
               marker=list(color=R_BLUE, opacity=0.5)) %>%
      add_lines(x=c(70,70), y=c(-0.5,nrow(m)-0.5), showlegend=FALSE,
                line=list(color=R_RED2, dash="dash", width=1)) %>%
      add_lines(x=c(30,30), y=c(-0.5,nrow(m)-0.5), showlegend=FALSE,
                line=list(color=R_ORANGE, dash="dash", width=1)) %>%
      add_lines(x=c(50,50), y=c(-0.5,nrow(m)-0.5), showlegend=FALSE,
                line=list(color=R_MUTED, dash="dot", width=1)) %>%
      rimac_layout(xlab="RSI") %>%
      layout(barmode="group",
             xaxis=list(range=c(0,108)),
             yaxis=list(tickfont=list(size=9),automargin=TRUE),
             margin=list(l=110,r=20))
  })

  output$plt_rsi_ts <- renderPlotly({
    req(input$rsi_tk)
    tk <- input$rsi_tk
    df <- D()$tr %>% select(Date, px=all_of(tk)) %>% filter(!is.na(px)) %>%
      mutate(RSI14 = RSI(px, 14), RSI30 = RSI(px, 30))

    plot_ly(df, x=~Date) %>%
      add_lines(y=~RSI14, name="RSI 14d", line=list(color=R_YELLOW, width=2)) %>%
      add_lines(y=~RSI30, name="RSI 30d", line=list(color=R_TEAL,   width=1.5, dash="dash")) %>%
      add_lines(y=rep(70,nrow(df)), showlegend=FALSE,
                line=list(color=R_RED2,  width=1, dash="dash")) %>%
      add_lines(y=rep(30,nrow(df)), showlegend=FALSE,
                line=list(color=R_ORANGE,width=1, dash="dash")) %>%
      add_ribbons(ymin=~pmax(RSI14,70,na.rm=TRUE), ymax=rep(100,nrow(df)),
                  fillcolor=paste0(R_RED2,"25"), line=list(width=0), showlegend=FALSE) %>%
      add_ribbons(ymin=rep(0,nrow(df)), ymax=~pmin(RSI14,30,na.rm=TRUE),
                  fillcolor=paste0(R_ORANGE,"25"), line=list(width=0), showlegend=FALSE) %>%
      rimac_layout(ylab="RSI") %>%
      layout(yaxis=list(range=c(0,100), tickvals=c(0,30,50,70,100)),
             legend=list(orientation="h",y=1.06,x=0))
  })

  # ── PE ABSOLUTE ──────────────────────────────────────────────
  pe_long <- reactive({
    pe_df <- D()$pe
    tickers <- setdiff(names(pe_df), "Date")
    pe_df %>%
      pivot_longer(-Date, names_to="Ticker", values_to="PE") %>%
      filter(!is.na(PE)) %>%
      mutate(Label = EQUITY_LABELS[Ticker])
  })

  output$plt_pe_global <- renderPlotly({
    global_tks <- c("NDDUWI Index","NDUEACWF Index","M0EFHUSD Index",
                    "NDUEEGF Index","M1CXBRV Index","NDEUCHF Index",
                    "SPTRSVX Index","SPTRSGX Index","SPXQUT Index")
    df <- pe_long() %>% filter(Ticker %in% global_tks)
    cols <- colorRampPalette(c(R_BLUE,R_TEAL,R_GREEN,R_YELLOW,R_ORANGE,R_RED2))(length(global_tks))

    p <- plot_ly()
    for (i in seq_along(global_tks)) {
      tk <- global_tks[i]
      sub <- df %>% filter(Ticker == tk)
      p <- add_lines(p, data=sub, x=~Date, y=~PE, name=EQUITY_LABELS[tk],
                     line=list(color=cols[i], width=1.8))
    }
    p %>% rimac_layout(ylab="P/E Forward") %>%
      layout(legend=list(orientation="h",y=1.12,x=0,font=list(size=9)))
  })

  output$plt_pe_sectors <- renderPlotly({
    df <- pe_long() %>% filter(Ticker %in% SECTOR_TICKERS)
    cols <- colorRampPalette(c(R_BLUE,R_TEAL,R_GREEN,R_YELLOW,R_ORANGE,R_RED2))(length(SECTOR_TICKERS))

    p <- plot_ly()
    for (i in seq_along(SECTOR_TICKERS)) {
      tk <- SECTOR_TICKERS[i]
      sub <- df %>% filter(Ticker==tk)
      p <- add_lines(p, data=sub, x=~Date, y=~PE, name=EQUITY_LABELS[tk],
                     line=list(color=cols[i], width=1.8))
    }
    p %>% rimac_layout(ylab="P/E Forward") %>%
      layout(legend=list(orientation="h",y=1.12,x=0,font=list(size=9)))
  })

  output$tbl_pe_current <- renderDT({
    latest <- D()$pe %>%
      filter(Date == max(Date, na.rm=TRUE)) %>%
      pivot_longer(-Date, names_to="Ticker", values_to="PE") %>%
      filter(!is.na(PE)) %>%
      mutate(Label=EQUITY_LABELS[Ticker]) %>%
      select(Activo=Label, `P/E Forward`=PE) %>%
      arrange(`P/E Forward`)

    datatable(latest, rownames=FALSE,
      options=list(pageLength=20, dom='frti')) %>%
      formatRound("P/E Forward", 2) %>%
      formatStyle("P/E Forward",
        background=styleColorBar(c(0,40), R_BLUE),
        backgroundSize='98% 60%', backgroundRepeat='no-repeat', backgroundPosition='center',
        color=R_TEXT)
  })

  # ── PE RELATIVE (con bandas dinámicas) ───────────────────────
  pe_rel_data <- reactive({
    req(input$pe_rel_a, input$pe_rel_b, input$pe_rel_lb)
    pe_relative(D()$pe, input$pe_rel_a, input$pe_rel_b, input$pe_rel_lb)
  })

  output$plt_pe_rel <- renderPlotly({
    df     <- pe_rel_data()
    mu     <- mean(df$Ratio, na.rm=TRUE)
    sigma  <- sd(df$Ratio, na.rm=TRUE)
    last_r <- tail(df$Ratio, 1)
    la     <- EQUITY_LABELS[input$pe_rel_a]
    lb     <- EQUITY_LABELS[input$pe_rel_b]

    annotation_txt <- sprintf("Actual: %.1f%%  |  Media: %.1f%%  |  +1σ: %.1f%%  |  −1σ: %.1f%%",
                               last_r, mu, mu+sigma, mu-sigma)

    plot_ly(df, x=~Date) %>%
      # Zona entre bandas
      add_ribbons(ymin=mu-sigma, ymax=mu+sigma,
                  fillcolor=paste0(R_MUTED,"20"), line=list(width=0),
                  name="±1σ zona", showlegend=FALSE) %>%
      # Línea ratio
      add_lines(y=~Ratio, name=paste0(la," / ",lb),
                line=list(color=R_BLUE, width=2.5)) %>%
      # Bandas
      add_lines(y=rep(mu, nrow(df)), name="Media",
                line=list(color=R_YELLOW, width=2)) %>%
      add_lines(y=rep(mu+sigma, nrow(df)), name="+1σ",
                line=list(color=R_MUTED, width=1.5, dash="dash")) %>%
      add_lines(y=rep(mu-sigma, nrow(df)), name="−1σ",
                line=list(color=R_MUTED, width=1.5, dash="dash")) %>%
      # Punto actual
      add_markers(x=tail(df$Date,1), y=last_r, name="Actual",
                  marker=list(color=R_RED, size=10, symbol="circle")) %>%
      layout(
        annotations=list(list(
          x=tail(df$Date,1), y=last_r,
          text=paste0("<b>",round(last_r,1),"%</b>"),
          showarrow=TRUE, arrowhead=2, arrowcolor=R_RED,
          font=list(color=R_RED, size=12), bgcolor=paste0(R_RED,"30"),
          bordercolor=R_RED, borderwidth=1, xshift=30
        )),
        paper_bgcolor=R_CARD, plot_bgcolor=R_CARD,
        font=list(color=R_TEXT, size=11),
        title=list(text=annotation_txt, font=list(color=R_MUTED,size=10), x=0.01),
        xaxis=list(title="", gridcolor=R_BORDER),
        yaxis=list(title=paste0("P/E(A) / P/E(B) × 100"), gridcolor=R_BORDER,
                   zerolinecolor=R_BORDER),
        legend=list(orientation="h",y=1.08,x=0,bgcolor="transparent",
                    font=list(color=R_TEXT,size=10)),
        hovermode="x unified", margin=list(t=50,b=40)
      ) %>% config(displayModeBar=FALSE)
  })

  output$plt_pe_rel_heatmap <- renderPlotly({
    # Sectores S&P 500 vs "US Market" = promedio PE de los 11 sectores
    pe_df <- D()$pe
    latest <- pe_df %>% filter(Date==max(Date,na.rm=TRUE))

    # Calcular US Market PE como promedio de sectores
    sec_vals <- unlist(latest[1, SECTOR_TICKERS])
    us_mkt_pe <- mean(sec_vals, na.rm=TRUE)

    # Calcular ratios para toda la historia
    ticks <- SECTOR_TICKERS
    df_out <- lapply(ticks, function(tk) {
      pe_df %>%
        select(Date, A=all_of(tk)) %>%
        filter(!is.na(A)) %>%
        rowwise() %>%
        mutate(
          B   = mean(as.numeric(pe_df[pe_df$Date==Date, SECTOR_TICKERS]), na.rm=TRUE),
          Rat = A/B*100,
          Ticker = tk
        ) %>% ungroup()
    }) %>% bind_rows()

    # Para heatmap: usar último valor y percentil histórico
    summary_df <- df_out %>%
      group_by(Ticker) %>%
      summarise(
        Current    = last(Rat, na_rm=TRUE),
        Mean       = mean(Rat, na.rm=TRUE),
        Sigma      = sd(Rat, na.rm=TRUE),
        Pct_Z      = (last(Rat, na_rm=TRUE) - mean(Rat, na.rm=TRUE)) / sd(Rat, na.rm=TRUE),
        .groups="drop"
      ) %>%
      mutate(Label = EQUITY_LABELS[Ticker]) %>%
      arrange(Pct_Z)

    plot_ly(summary_df, x=~Label,
            y=~round(Current,1), type="bar",
            text=~paste0(round(Current,1),"%<br>Z-score: ",round(Pct_Z,2)),
            hoverinfo="text",
            marker=list(
              color=~Pct_Z,
              colorscale=list(c(0,R_RED),c(0.5,R_PANEL),c(1,R_GREEN)),
              cmin=-2.5, cmax=2.5,
              colorbar=list(title="Z-score",thickness=10,
                            bgcolor=R_CARD, tickfont=list(color=R_TEXT))
            )) %>%
      add_lines(x=summary_df$Label, y=rep(100,nrow(summary_df)),
                showlegend=FALSE, line=list(color=R_YELLOW,width=1.5,dash="dash")) %>%
      rimac_layout(ylab="P/E Sector / P/E US Market × 100") %>%
      layout(xaxis=list(tickangle=-35,tickfont=list(size=10)))
  })

  # ── OAS ──────────────────────────────────────────────────────
  oas_filtered <- reactive({
    req(input$oas_hist_lb)
    lb <- input$oas_hist_lb * 252
    D()$oas %>% tail(lb)
  })

  output$plt_oas_ig_hy <- renderPlotly({
    df <- oas_filtered()
    plot_ly(df, x=~Date) %>%
      add_lines(y=~BAMLC0A4CBBB,   name="US Corp BBB (IG)",
                line=list(color=R_BLUE, width=2)) %>%
      add_lines(y=~BAMLH0A0HYM2,   name="US Corp HY",
                line=list(color=R_RED2, width=2)) %>%
      rimac_layout(ylab="OAS (%)") %>%
      layout(legend=list(orientation="h",y=1.06,x=0))
  })

  output$plt_oas_em <- renderPlotly({
    df <- oas_filtered()
    plot_ly(df, x=~Date) %>%
      add_lines(y=~BAMLEM2BRRBBBCRPIOAS, name="EM BBB",
                line=list(color=R_TEAL, width=2)) %>%
      add_lines(y=~BAMLEMRLCRPILAOAS,   name="LatAm EM",
                line=list(color=R_ORANGE, width=2)) %>%
      rimac_layout(ylab="OAS (%)") %>%
      layout(legend=list(orientation="h",y=1.06,x=0))
  })

  output$plt_oas_all_bands <- renderPlotly({
    req(input$oas_band_sel)
    tk  <- input$oas_band_sel
    lbl <- OAS_LABELS[tk]
    df  <- oas_filtered() %>% select(Date, px=all_of(tk)) %>% filter(!is.na(px))
    mu    <- mean(df$px, na.rm=TRUE)
    sigma <- sd(df$px, na.rm=TRUE)
    last_v <- tail(df$px, 1)

    plot_ly(df, x=~Date) %>%
      add_ribbons(ymin=mu-sigma, ymax=mu+sigma,
                  fillcolor=paste0(R_MUTED,"20"), line=list(width=0),
                  name="±1σ zona", showlegend=FALSE) %>%
      add_lines(y=~px, name=lbl, line=list(color=R_TEAL, width=2)) %>%
      add_lines(y=rep(mu,nrow(df)), name="Media",
                line=list(color=R_YELLOW, width=2)) %>%
      add_lines(y=rep(mu+sigma,nrow(df)), name="+1σ",
                line=list(color=R_MUTED,width=1.5,dash="dash")) %>%
      add_lines(y=rep(mu-sigma,nrow(df)), name="−1σ",
                line=list(color=R_MUTED,width=1.5,dash="dash")) %>%
      add_markers(x=tail(df$Date,1), y=last_v, name="Actual",
                  marker=list(color=R_RED,size=10)) %>%
      rimac_layout(ylab="OAS (%)") %>%
      layout(
        annotations=list(list(
          x=tail(df$Date,1), y=last_v,
          text=paste0("<b>",round(last_v,2)," %</b>"),
          showarrow=TRUE, arrowcolor=R_RED, arrowhead=2,
          font=list(color=R_RED,size=12), xshift=30
        )),
        legend=list(orientation="h",y=1.06,x=0)
      )
  })

  # ── CDS ──────────────────────────────────────────────────────
  cds_filtered <- reactive({
    req(input$cds_lb)
    lb <- input$cds_lb * 252
    D()$cds %>% tail(lb)
  })

  output$plt_cds_ts <- renderPlotly({
    df <- cds_filtered()
    plot_ly(df, x=~Date) %>%
      add_lines(y=~`IBOXUMAE Index`, name="CDS US IG 5Y",
                line=list(color=R_BLUE,  width=2)) %>%
      add_lines(y=~`IBOXHYAE Index`, name="CDS US HY 5Y",
                line=list(color=R_RED2,  width=2)) %>%
      rimac_layout(ylab="Spread (bps)") %>%
      layout(legend=list(orientation="h",y=1.06,x=0))
  })

  output$plt_cds_stats <- renderPlotly({
    df <- cds_filtered()
    tks <- c("IBOXUMAE Index","IBOXHYAE Index")
    lbls <- c("US IG","US HY")
    stats <- lapply(seq_along(tks), function(i) {
      px <- df[[tks[i]]]
      lp <- tail(px[!is.na(px)],1)
      tibble(
        Label = lbls[i],
        Actual = lp,
        Min    = min(px,na.rm=TRUE),
        Max    = max(px,na.rm=TRUE),
        Pct    = round((lp - min(px,na.rm=TRUE)) / (max(px,na.rm=TRUE)-min(px,na.rm=TRUE))*100,1)
      )
    }) %>% bind_rows()

    plot_ly(stats, x=~Pct, y=~Label, type="bar", orientation="h",
            text=~paste0(round(Actual,1)," bps  |  Pct ",Pct,"%"),
            textposition="outside",
            marker=list(
              color=~Pct,
              colorscale=list(c(0,"#22C55E"),c(0.5,R_YELLOW),c(1,R_RED2)),
              cmin=0, cmax=100,
              colorbar=list(title="Pct hist.",thickness=10,
                            bgcolor=R_CARD,tickfont=list(color=R_TEXT))
            )) %>%
      rimac_layout(title="Percentil histórico", xlab="Percentil (%)") %>%
      layout(xaxis=list(range=c(0,130)),
             yaxis=list(automargin=TRUE))
  })

  output$tbl_cds_summary <- renderDT({
    df <- cds_filtered()
    tks <- c("IBOXUMAE Index","IBOXHYAE Index")
    lbls <- c("CDX US IG 5Y","CDX US HY 5Y")
    sm <- lapply(seq_along(tks), function(i) {
      px <- df[[tks[i]]]
      lp <- tail(px[!is.na(px)],1)
      tibble(
        Instrumento = lbls[i],
        Actual      = round(lp,1),
        Mínimo      = round(min(px,na.rm=TRUE),1),
        Máximo      = round(max(px,na.rm=TRUE),1),
        Media       = round(mean(px,na.rm=TRUE),1),
        `Mediana`   = round(median(px,na.rm=TRUE),1),
        `+1σ`       = round(mean(px,na.rm=TRUE)+sd(px,na.rm=TRUE),1),
        `Percentil` = round((lp-min(px,na.rm=TRUE))/(max(px,na.rm=TRUE)-min(px,na.rm=TRUE))*100,1)
      )
    }) %>% bind_rows()

    datatable(sm, rownames=FALSE,
      options=list(dom='t')) %>%
      formatStyle("Percentil",
        background=styleColorBar(c(0,100), R_BLUE),
        backgroundSize='98% 60%', backgroundRepeat='no-repeat',
        backgroundPosition='center', color=R_TEXT)
  })

  # ── YIELD CURVE ──────────────────────────────────────────────
  tsy_filtered <- reactive({
    req(input$tsy_lb)
    lb <- input$tsy_lb * 252
    df <- D()$tsy
    names(df) <- c("Date","Y10","Y2")
    df %>% filter(!is.na(Y10),!is.na(Y2)) %>% tail(lb) %>%
      mutate(Spread = (Y10 - Y2) * 100)   # bps
  })

  output$vb_10y <- renderValueBox({
    lv <- tail(tsy_filtered()$Y10, 1)
    valueBox(paste0(round(lv,3),"%"), "Treasury 10Y", icon=icon("arrow-up"), color="blue")
  })
  output$vb_2y <- renderValueBox({
    lv <- tail(tsy_filtered()$Y2, 1)
    valueBox(paste0(round(lv,3),"%"), "Treasury 2Y", icon=icon("arrows-up-down"), color="light-blue")
  })
  output$vb_spread <- renderValueBox({
    lv <- tail(tsy_filtered()$Spread, 1)
    valueBox(paste0(round(lv,1)," bps"), "Spread 10Y − 2Y",
             icon=icon("chart-simple"), color=if(lv>=0) "green" else "red")
  })
  output$vb_curve_signal <- renderValueBox({
    lv <- tail(tsy_filtered()$Spread, 1)
    sig <- if (lv > 50) "Empinada (Bullish)" else if (lv >= 0) "Plana" else "Invertida (Warning)"
    valueBox(sig, "Señal Yield Curve", icon=icon("bezier-curve"),
             color=if(lv>50)"green" else if(lv>=0)"yellow" else "red")
  })

  output$plt_yield_spread <- renderPlotly({
    df <- tsy_filtered()
    col_area <- ifelse(df$Spread >= 0, paste0(R_GREEN,"60"), paste0(R_RED2,"60"))

    plot_ly(df, x=~Date) %>%
      add_lines(y=~Spread, name="Spread 10Y−2Y (bps)",
                line=list(color=R_BLUE, width=2)) %>%
      add_lines(y=rep(0,nrow(df)), showlegend=FALSE,
                line=list(color=R_MUTED, width=1, dash="dot")) %>%
      add_ribbons(ymin=~pmin(Spread,0), ymax=rep(0,nrow(df)),
                  fillcolor=paste0(R_RED2,"30"), line=list(width=0),
                  name="Inversión", showlegend=FALSE) %>%
      add_ribbons(ymin=rep(0,nrow(df)), ymax=~pmax(Spread,0),
                  fillcolor=paste0(R_GREEN,"20"), line=list(width=0),
                  name="Positivo", showlegend=FALSE) %>%
      rimac_layout(ylab="bps") %>%
      layout(legend=list(orientation="h",y=1.06,x=0))
  })

  output$plt_yield_levels <- renderPlotly({
    df <- tsy_filtered()
    plot_ly(df, x=~Date) %>%
      add_lines(y=~Y10, name="10Y", line=list(color=R_BLUE,   width=2)) %>%
      add_lines(y=~Y2,  name="2Y",  line=list(color=R_YELLOW, width=2, dash="dash")) %>%
      rimac_layout(ylab="Yield (%)") %>%
      layout(legend=list(orientation="h",y=1.06,x=0))
  })

  output$plt_yield_dist <- renderPlotly({
    df <- tsy_filtered()
    last_s <- tail(df$Spread,1)
    mu     <- mean(df$Spread, na.rm=TRUE)
    sigma  <- sd(df$Spread,   na.rm=TRUE)

    plot_ly(df, x=~Spread, type="histogram", nbinsx=50,
            marker=list(color=R_BLUE, opacity=0.7)) %>%
      add_lines(x=c(mu,mu), y=c(0,80), name="Media",
                line=list(color=R_YELLOW,width=2)) %>%
      add_lines(x=c(last_s,last_s), y=c(0,80), name="Actual",
                line=list(color=R_RED,width=2.5)) %>%
      add_lines(x=c(0,0), y=c(0,80), name="Cero",
                line=list(color=R_MUTED,width=1,dash="dot")) %>%
      rimac_layout(xlab="Spread (bps)", ylab="Frecuencia") %>%
      layout(legend=list(orientation="h",y=1.06,x=0))
  })

  output$tbl_yield_stats <- renderDT({
    df <- tsy_filtered()
    last_s <- tail(df$Spread,1)
    stats <- tibble(
      Métrica = c("Actual","Mínimo","Máximo","Media","Mediana","+1σ","−1σ","% obs. invertidas"),
      `10Y−2Y (bps)` = c(
        round(last_s,1),
        round(min(df$Spread,na.rm=TRUE),1),
        round(max(df$Spread,na.rm=TRUE),1),
        round(mean(df$Spread,na.rm=TRUE),1),
        round(median(df$Spread,na.rm=TRUE),1),
        round(mean(df$Spread,na.rm=TRUE)+sd(df$Spread,na.rm=TRUE),1),
        round(mean(df$Spread,na.rm=TRUE)-sd(df$Spread,na.rm=TRUE),1),
        round(mean(df$Spread<0,na.rm=TRUE)*100,1)
      )
    )
    datatable(stats, rownames=FALSE,
      options=list(dom='t')) %>%
      formatStyle("`10Y−2Y (bps)`",
        color=styleInterval(0, c(R_RED2, R_GREEN)))
  })
}

# ================================================================
# 5. LANZAR
# ================================================================
shinyApp(ui, server)
