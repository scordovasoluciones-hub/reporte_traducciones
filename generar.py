#!/usr/bin/env python3
"""
Generador del Reporte de Traducciones — Área de Engagement (SDS) · Compassion Perú.

Flujo: lee el CSV histórico de datos/, calcula KPIs, estacionalidad, calidad,
proyección de volumen y necesidad de traductores para el próximo año fiscal,
valida la calidad del dato, e inyecta todo en plantilla.html -> salida/index.html.

Uso:
    python generar.py                      # usa el CSV más reciente en datos/
    python generar.py datos/mi_base.csv    # usa un archivo específico
"""
import sys, json, glob, datetime as dt
import pandas as pd, numpy as np

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# ─────────────────────────── CONFIGURACIÓN ───────────────────────────
# Ajusta estos supuestos aquí; el dashboard se recalcula solo al regenerar.
PRODUCTIVIDADES   = [1000, 1500, 2000, 2500, 3000]   # traducciones/traductor/mes (escenarios)
PROD_DEFAULT      = 2000              # escenario mostrado por defecto
VOLUMEN_ANUAL_OBJ = None              # None = estimar de años completos; o fija un número
CRECIMIENTO       = 0.0               # ajuste % opcional sobre el objetivo anual
UMBRAL_ISSUES_ALTA = 2.0             # % de issues que marca una plantilla como "alta"
FYORDER = ['01.Jul','02.Ago','03.Sep','04.Oct','05.Nov','06.Dic',
           '07.Ene','08.Feb','09.Mar','10.Abr','11.May','12.Jun']

# ─────────────────────────── UTILIDADES ───────────────────────────
def fecha_cal(r):
    """MesNum es mes calendario (1-12). FY va Jul->Jun: meses 7-12 = año AñoFY-1."""
    y = r['AñoFY'] - 1 if r['MesNum'] >= 7 else r['AñoFY']
    return pd.Timestamp(int(y), int(r['MesNum']), 1)

# ─────────────────────────── CARGA ───────────────────────────
def cargar(path):
    df = pd.read_csv(path)
    req = ['VENDOR','TRANSLATOR NAME','TEMPLATE','TRANSLATION COUNT',
           'TRANSLATION CHECKS PERFORMED','RETURNED TO TRANSLATOR',
           'CONTENT ISSUES CONFIRMED','MesNum','MesFY','AñoFY']
    faltan = [c for c in req if c not in df.columns]
    if faltan:
        raise SystemExit(f"❌ Faltan columnas en el CSV: {faltan}")
    df['fecha']  = df.apply(fecha_cal, axis=1)
    df['forder'] = df['MesFY'].str[:2].astype(int)
    return df

# ─────────────────────────── VALIDACIÓN DE CALIDAD ───────────────────────────
def validar(df):
    """Devuelve una lista de alertas de calidad del dato para mostrar en el reporte."""
    alertas = []
    # 1. Outliers mensuales de volumen (>2.5 desviaciones sobre la mediana robusta)
    mv = df.groupby('fecha')['TRANSLATION COUNT'].sum()
    med, mad = mv.median(), (mv - mv.median()).abs().median() or 1
    out = mv[(mv - med).abs() / (1.4826 * mad) > 3.5]
    for f, v in out.items():
        alertas.append(f"Volumen atípico en {f.strftime('%b %Y')}: {int(v):,} "
                       f"(mediana ~{int(med):,}). Excluido del perfil estacional.")
    # 2. Meses faltantes en el rango
    rango = pd.period_range(mv.index.min(), mv.index.max(), freq='M')
    faltan = [p.strftime('%b %Y') for p in rango if p.to_timestamp() not in mv.index]
    if faltan:
        alertas.append(f"Meses sin datos en el rango: {', '.join(faltan)}.")
    # 3. Caída anómala de traductores activos (afecta la productividad aparente)
    act = df[df['TRANSLATION COUNT'] > 0].groupby('fecha')['TRANSLATOR NAME'].nunique()
    base = act.iloc[:len(act)//2].median()
    recientes = act.iloc[-3:]
    if base and (recientes.median() < base * 0.6):
        alertas.append(
            f"La cuenta de traductores activos cae de ~{int(base)} a ~{int(recientes.median())} "
            f"en meses recientes: probable cambio de registro, no mejora real de productividad. "
            f"La proyección usa una productividad estable ({PROD_DEFAULT}/mes), no la reciente.")
    # 4. Consistencia de niveles entre columnas
    inc = ((df['CONTENT ISSUES CONFIRMED'] > 0) & (df['TRANSLATION CHECKS PERFORMED'] == 0)).sum()
    if inc:
        alertas.append(
            f"{inc:,} filas tienen issues confirmados con 0 revisiones: las columnas de "
            f"revisión, issues y devolución se registran a distinto nivel (revisor vs. traductor). "
            f"Los ratios son válidos en agregado, no fila por fila.")
    return alertas, out.index

# ─────────────────────────── CÁLCULOS ───────────────────────────
# NOTA: aquí solo se exportan los datos GRANULARES (agrupados a nivel
# mes+vendor+traductor+plantilla) más la configuración. Todos los KPIs,
# la estacionalidad, la proyección, etc. se calculan en el navegador
# (ver el motor de cálculo en <script> de plantilla.html), para que el
# mismo código sirva tanto para los filtros como para la vista previa
# de un Excel nuevo cargado por el usuario.
def construir(df, outlier_fechas):
    g = (df.groupby(['fecha', 'AñoFY', 'MesFY', 'VENDOR', 'TRANSLATOR NAME', 'TEMPLATE'], as_index=False)
           .agg(v=('TRANSLATION COUNT', 'sum'), c=('TRANSLATION CHECKS PERFORMED', 'sum'),
                r=('RETURNED TO TRANSLATOR', 'sum'), i=('CONTENT ISSUES CONFIRMED', 'sum')))

    vendors = sorted(df['VENDOR'].unique().tolist())
    trads   = sorted(df['TRANSLATOR NAME'].unique().tolist())
    temps   = sorted(df['TEMPLATE'].unique().tolist())
    fechas_dt = sorted(g['fecha'].unique())
    v_idx = {x: i for i, x in enumerate(vendors)}
    t_idx = {x: i for i, x in enumerate(trads)}
    p_idx = {x: i for i, x in enumerate(temps)}
    f_idx = {x: i for i, x in enumerate(fechas_dt)}

    fy_por_fecha    = dict(zip(g['fecha'], g['AñoFY']))
    mesfy_por_fecha = dict(zip(g['fecha'], g['MesFY']))
    outlier_set = set(outlier_fechas)

    D = {}
    D['raw'] = dict(
        f=[f_idx[x] for x in g['fecha']],
        ve=[v_idx[x] for x in g['VENDOR']],
        tr=[t_idx[x] for x in g['TRANSLATOR NAME']],
        te=[p_idx[x] for x in g['TEMPLATE']],
        v=[int(x) for x in g['v']], c=[int(x) for x in g['c']],
        r=[int(x) for x in g['r']], i=[int(x) for x in g['i']],
    )
    D['lookup'] = dict(
        vendors=vendors, traductores=trads, templates=temps,
        fechas=[x.strftime('%b %y') for x in fechas_dt],
        fy=[int(fy_por_fecha[x]) for x in fechas_dt],
        mesfy=[mesfy_por_fecha[x] for x in fechas_dt],
        outlier=[bool(x in outlier_set) for x in fechas_dt],
    )
    D['meta'] = dict(
        prod_default=PROD_DEFAULT, productividades=PRODUCTIVIDADES,
        umbral_issues=UMBRAL_ISSUES_ALTA, volumen_anual_obj=VOLUMEN_ANUAL_OBJ,
        crecimiento=CRECIMIENTO, fyorder=FYORDER,
        rango=f"{min(fechas_dt).strftime('%b %Y')} → {max(fechas_dt).strftime('%b %Y')}",
        fy_min=f"FY{min(fy_por_fecha.values())}", fy_max=f"FY{max(fy_por_fecha.values())}",
        actualizado=dt.date.today().strftime('%d %b %Y'))
    return D

# ─────────────────────────── PRESUPUESTO (hoja aparte) ───────────────────────────
# Fuente independiente: pagos/licencias/budget por mes fiscal y Tipo Traductor.
# No se cruza con el CSV de traducciones (usan convenciones de FY distintas);
# se filtra y agrega en el navegador igual que la data principal.
BUDGET_COLS = ['fy', 'mes', 'cod_mes', 'cod_my', 'tipo', 'budget', 'q_lic',
               'costo_lic_unit', 'costo_lic_total', 'lic_adicional',
               'pago_cartas', 'pago_total', 'q_cartas', 'costo_carta']

def cargar_budget(path):
    df = pd.read_excel(path, sheet_name=0)
    if len(df.columns) < len(BUDGET_COLS):
        raise SystemExit(f"❌ El Excel de presupuesto tiene {len(df.columns)} columnas, "
                          f"se esperaban {len(BUDGET_COLS)}.")
    df = df.iloc[:, :len(BUDGET_COLS)].copy()
    df.columns = BUDGET_COLS
    df['mesfy'] = df['cod_mes'].str.replace('_', '.', regex=False)  # '01_Jul' -> '01.Jul'
    # Cod_MY tipo '25Jul' o '25_Jul' (año 2 dígitos + separador opcional + mes abreviado)
    # -> etiqueta 'Jul 25' para las gráficas.
    m = df['cod_my'].astype(str).str.extract(r'^(\d{2})[_\s]?([A-Za-zÀ-ÿ]+)$')
    df['label'] = (m[1].fillna('') + ' ' + m[0].fillna('')).str.strip()
    df.loc[df['label'] == '', 'label'] = df['cod_my'].astype(str)
    return df

def construir_budget(df):
    tipos = sorted(df['tipo'].dropna().unique().tolist())
    fys = sorted(int(x) for x in df['fy'].dropna().unique())
    t_idx = {x: i for i, x in enumerate(tipos)}
    num = lambda col: [float(x) if pd.notna(x) else None for x in df[col]]
    raw = dict(
        fy=[int(x) for x in df['fy']], mesfy=df['mesfy'].tolist(), label=df['label'].tolist(),
        tipo=[t_idx[x] for x in df['tipo']],
        budget=num('budget'), costo_lic_total=num('costo_lic_total'),
        lic_adicional=num('lic_adicional'), pago_cartas=num('pago_cartas'),
        pago_total=num('pago_total'), q_cartas=num('q_cartas'), q_lic=num('q_lic'))
    return dict(raw=raw, lookup=dict(tipos=tipos, fys=fys))

# ─────────────────────────── RENDER ───────────────────────────
def render(D, alertas):
    D['alertas'] = alertas
    tpl = open('plantilla.html', encoding='utf-8').read()
    html = tpl.replace('__DATA__', json.dumps(D, ensure_ascii=False))
    import os; os.makedirs('salida', exist_ok=True)
    open('salida/index.html', 'w', encoding='utf-8').write(html)
    json.dump(D, open('salida/datos.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if args:
        path = args[0]
    else:
        cands = sorted(glob.glob('datos/*.csv') + glob.glob('datos/*.CSV'),
                       key=lambda p: __import__('os').path.getmtime(p))
        if not cands:
            raise SystemExit("❌ No hay CSV en datos/. Coloca la base ahí o pásala como argumento.")
        path = cands[-1]
    print(f"📄 Fuente: {path}")
    df = cargar(path)
    alertas, out_fechas = validar(df)
    D = construir(df, out_fechas)

    bpath_cands = sorted(glob.glob('datos/*.xlsx') + glob.glob('datos/*.xls'),
                          key=lambda p: __import__('os').path.getmtime(p))
    if bpath_cands:
        bpath = bpath_cands[-1]
        print(f"📄 Fuente presupuesto: {bpath}")
        D['budget'] = construir_budget(cargar_budget(bpath))
    else:
        print("ℹ  No hay Excel de presupuesto en datos/ — se omite la pestaña Presupuesto.")
        D['budget'] = None

    render(D, alertas)
    total = int(sum(D['raw']['v']))
    print(f"✅ salida/index.html generado — {total:,} traducciones, "
          f"{len(D['lookup']['fechas'])} meses, {len(D['raw']['v']):,} filas granulares.")
    if D['budget']:
        print(f"✅ Presupuesto incluido — {len(D['budget']['raw']['fy'])} filas, "
              f"tipos: {', '.join(D['budget']['lookup']['tipos'])}.")
    if alertas:
        print("⚠  Alertas de calidad del dato:")
        for a in alertas: print("   -", a)

if __name__ == '__main__':
    main()
