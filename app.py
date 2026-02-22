import streamlit as st
import pandas as pd
import datetime

st.set_page_config(
    page_title="Dashboard KPI — SAP PM",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── estilos ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #F1F5F9; }
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    .kpi-box {
        background: #1e3a5f; color: white; border-radius: 10px;
        padding: 16px 20px; text-align: center; box-shadow: 0 3px 14px rgba(0,0,0,0.13);
    }
    .kpi-value { font-size: 2.2rem; font-weight: 800; line-height: 1; }
    .kpi-label { font-size: 0.7rem; font-weight: 600; text-transform: uppercase;
                 letter-spacing: 0.8px; opacity: 0.75; margin-top: 4px; }
    .section-title {
        background: #1e3a5f; color: white; font-weight: 700; font-size: 0.8rem;
        letter-spacing: 1.2px; text-transform: uppercase; padding: 7px 14px;
        border-radius: 7px; margin: 18px 0 10px 0;
    }
    div[data-testid="stMetricValue"] { font-size: 2rem !important; font-weight: 800 !important; }
    .stTabs [data-baseweb="tab"] { font-weight: 600; font-size: 0.85rem; }
    .stTabs [aria-selected="true"] { color: #1e3a5f !important; }
</style>
""", unsafe_allow_html=True)

# ── helpers ───────────────────────────────────────────────────────────────────
EMPRESA_MAP = {
    "H":"3001-ALTER",    "L":"5001-SOLIN",     "F":"2002-ALIM.SELEC",
    "K":"4002-MAGNO",    "D":"1004-CEDISA",    "J":"4001-RECOR",
    "E":"2001-Z.FERTIL", "S":"3006-ELEC.SERV", "O":"1005-NORDPHARMA",
    "G":"2003-CAFE.SELEC","Q":"3003-US.GEOTHER","R":"3005-ELEC.POW",
    "N":"2004-TIPSA",    "M":"6000-YR",        "A":"1001-JICOH",
    "B":"1002-JICOHSA",
}

def get_tipo(clase):
    if pd.isna(clase): return "Otro"
    c = str(clase)
    if c.startswith(("ZMC","ZCI","ZOCH")): return "Correctivo"
    if c.startswith(("ZMP","ZOPH","ZPI")): return "Preventivo"
    if c.startswith(("ZMT","ZOTH")):       return "Ubic.Técnica"
    return "Otro"

def get_empresa(clase):
    if pd.isna(clase) or len(str(clase)) < 4: return "N/A"
    return EMPRESA_MAP.get(str(clase)[3], str(clase))

def get_sub_ubi(empresa, ubi):
    if empresa != "2002-ALIM.SELEC": return None
    if pd.isna(ubi): return "Sin Ubic."
    p = str(ubi)[:4]
    if p == "2201": return "Planta 2201"
    if p == "2202": return "Planta 2202"
    return "Otras"

def simplify_status(s):
    if pd.isna(s): return "Otro"
    s = str(s)
    if "CERR" in s: return "Cerrada"
    if "CTEC" in s: return "Concluida"
    if "LIB." in s: return "Liberada"
    if "ABIE" in s: return "Abierta"
    return "Otro"

def simplify_aviso(s):
    if pd.isna(s): return "Otro"
    s = str(s)
    if "MECE" in s: return "Concluido"
    if "MEAB" in s: return "Abierto"
    if "METR" in s: return "En Tratamiento"
    return "Otro"

def pct_color(p):
    if p >= 80: return "🟢"
    if p >= 60: return "🟡"
    return "🔴"

def days_diff(fecha):
    if pd.isna(fecha): return None
    try:
        d = pd.to_datetime(fecha)
        return (datetime.datetime.today() - d).days
    except: return None

STATUS_COLORS = {
    "Abierta":   "🔴",
    "Liberada":  "🟡",
    "Concluida": "🟢",
    "Cerrada":   "⚫",
    "Otro":      "⚪",
}

# ── load & process ────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def process_ordenes(file):
    df = pd.read_excel(file, dtype=str)
    df.columns = df.columns.str.strip()
    df["Tipo"]    = df["Clase de orden"].apply(get_tipo)
    df["Empresa"] = df["Clase de orden"].apply(get_empresa)
    df["Status"]  = df["Status sistema"].apply(simplify_status)
    df["Ubi"]     = df.get("Ubicac.técnica", pd.Series(dtype=str))
    df["SubUbi"]  = df.apply(lambda r: get_sub_ubi(r["Empresa"], r.get("Ubi","")), axis=1)
    df["Fecha"]   = pd.to_datetime(df.get("Fe.inic.extrema",""), errors="coerce")
    df["Dias"]    = df.apply(lambda r: days_diff(r["Fecha"]) if r["Status"] in ("Abierta","Liberada") else None, axis=1)
    return df

@st.cache_data(show_spinner=False)
def process_avisos(file):
    df = pd.read_excel(file, dtype=str)
    df.columns = df.columns.str.strip()
    df["StatusSimple"] = df["Status sistema"].apply(simplify_aviso)
    return df

@st.cache_data(show_spinner=False)
def process_ip24(file):
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip()
    df["ConOrden"] = df["Orden"].apply(
        lambda x: bool(x) and str(x).strip() not in ["","nan","0","NaN"])
    df["Fecha"]    = pd.to_datetime(df.get("Fe.inic.progr.",""), errors="coerce")
    df["DiasVenc"] = df["Fecha"].apply(days_diff)
    return df

@st.cache_data(show_spinner=False)
def process_ip16(file):
    df = pd.read_excel(file, dtype=str)
    df.columns = df.columns.str.strip()
    return df

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📁 Cargar Archivos SAP")
    st.markdown("---")

    f_ord = st.file_uploader("🔧 Órdenes (IW38)", type=["xlsx","xls"], key="ord")
    f_av  = st.file_uploader("🔔 Avisos (IW29)",  type=["xlsx","xls"], key="av")
    f_16  = st.file_uploader("📋 Planes (IP16)",  type=["xlsx","xls"], key="ip16")
    f_24  = st.file_uploader("📅 Posiciones (IP24)", type=["xlsx","xls"], key="ip24")

    st.markdown("---")
    st.markdown(f"📅 **{datetime.datetime.today().strftime('%d/%m/%Y %H:%M')}**")

    if f_ord or f_av:
        st.success("✅ Datos cargados — dashboard activo")
    else:
        st.info("⬆️ Sube los archivos para activar el dashboard")

    st.markdown("---")
    st.markdown("#### 📌 Filtros")
    emp_filter  = ""
    sub_filter  = ""

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='background:linear-gradient(135deg,#0f2443,#1e3a5f,#1a4f7a);
     padding:20px 28px;border-radius:12px;margin-bottom:20px;
     box-shadow:0 4px 20px rgba(0,0,0,0.2)'>
  <div style='font-size:10px;color:rgba(255,255,255,0.4);letter-spacing:3px;text-transform:uppercase'>SAP Plant Maintenance</div>
  <h1 style='margin:4px 0 0;color:white;font-size:1.6rem;font-weight:800'>📋 Dashboard KPI — Mantenimiento</h1>
  <div style='font-size:12px;color:rgba(255,255,255,0.5);margin-top:4px'>Sube los archivos exportados de SAP en el panel izquierdo para activar el dashboard</div>
</div>
""", unsafe_allow_html=True)

if not f_ord and not f_av:
    st.markdown("""
    <div style='text-align:center;padding:60px 20px;color:#64748B'>
        <div style='font-size:64px'>📊</div>
        <h2 style='color:#1e3a5f;margin-top:12px'>Esperando archivos SAP...</h2>
        <p style='max-width:500px;margin:8px auto;line-height:1.6'>
            Usa el panel lateral izquierdo para subir los reportes exportados de SAP.
            El dashboard se generará automáticamente.
        </p>
        <div style='display:flex;justify-content:center;gap:24px;margin-top:24px;flex-wrap:wrap'>
            <div style='background:#F8FAFC;border:2px dashed #CBD5E1;border-radius:12px;padding:16px 24px;min-width:140px'>
                <div style='font-size:28px'>🔧</div><div style='font-weight:600;margin-top:4px'>Órdenes</div><div style='font-size:12px;color:#94A3B8'>IW38</div>
            </div>
            <div style='background:#F8FAFC;border:2px dashed #CBD5E1;border-radius:12px;padding:16px 24px;min-width:140px'>
                <div style='font-size:28px'>🔔</div><div style='font-weight:600;margin-top:4px'>Avisos</div><div style='font-size:12px;color:#94A3B8'>IW29</div>
            </div>
            <div style='background:#F8FAFC;border:2px dashed #CBD5E1;border-radius:12px;padding:16px 24px;min-width:140px'>
                <div style='font-size:28px'>📋</div><div style='font-weight:600;margin-top:4px'>Planes</div><div style='font-size:12px;color:#94A3B8'>IP16</div>
            </div>
            <div style='background:#F8FAFC;border:2px dashed #CBD5E1;border-radius:12px;padding:16px 24px;min-width:140px'>
                <div style='font-size:28px'>📅</div><div style='font-weight:600;margin-top:4px'>Posiciones</div><div style='font-size:12px;color:#94A3B8'>IP24</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── PROCESS DATA ──────────────────────────────────────────────────────────────
df_ord = process_ordenes(f_ord) if f_ord else pd.DataFrame()
df_av  = process_avisos(f_av)   if f_av  else pd.DataFrame()
df_ip16= process_ip16(f_16)     if f_16  else pd.DataFrame()
df_ip24= process_ip24(f_24)     if f_24  else pd.DataFrame()

# ── FILTROS EN SIDEBAR ────────────────────────────────────────────────────────
if not df_ord.empty:
    with st.sidebar:
        empresas = sorted([e for e in df_ord["Empresa"].unique() if e and e != "N/A"])
        emp_opts = ["Todas"] + empresas
        emp_sel  = st.selectbox("🏢 Empresa", emp_opts)
        emp_filter = "" if emp_sel == "Todas" else emp_sel

        if emp_filter == "2002-ALIM.SELEC":
            sub_opts = ["Todas", "Planta 2201", "Planta 2202", "Otras"]
            sub_sel  = st.selectbox("📍 Locación ALIM.SELEC", sub_opts)
            sub_filter = "" if sub_sel == "Todas" else sub_sel

# Aplicar filtros
df_f = df_ord.copy()
if emp_filter:
    df_f = df_f[df_f["Empresa"] == emp_filter]
if sub_filter and emp_filter == "2002-ALIM.SELEC":
    df_f = df_f[df_f["SubUbi"] == sub_filter]

lbl = emp_filter if emp_filter else "Todas las empresas"
if sub_filter: lbl += f" · {sub_filter}"

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Resumen", "🔔 Avisos", "🔧 Órdenes",
    "🟢 Preventivo", "🔴 Correctivo", "📅 Planes PM"
])

# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — RESUMEN
# ════════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown(f"#### 📍 Filtrando: **{lbl}**")

    # AVISOS
    if not df_av.empty:
        st.markdown('<div class="section-title">🔔 Avisos de Mantenimiento</div>', unsafe_allow_html=True)
        av_t  = len(df_av)
        av_ab = len(df_av[df_av["StatusSimple"]=="Abierto"])
        av_tr = len(df_av[df_av["StatusSimple"]=="En Tratamiento"])
        av_co = len(df_av[df_av["StatusSimple"]=="Concluido"])
        av_pct= av_co/av_t*100 if av_t else 0

        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("📋 Total Avisos",    av_t)
        c2.metric("🔴 Abiertos",        av_ab)
        c3.metric("🟡 En Tratamiento",  av_tr)
        c4.metric("✅ Concluidos",      av_co)
        c5.metric(f"{pct_color(av_pct)} % Conclusión", f"{av_pct:.1f}%")

    # ÓRDENES
    if not df_f.empty:
        st.markdown('<div class="section-title">🔧 Órdenes de Mantenimiento</div>', unsafe_allow_html=True)
        o_t  = len(df_f)
        o_ab = len(df_f[df_f["Status"]=="Abierta"])
        o_lb = len(df_f[df_f["Status"]=="Liberada"])
        o_ct = len(df_f[df_f["Status"]=="Concluida"])
        o_ce = len(df_f[df_f["Status"]=="Cerrada"])

        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("📋 Total Órdenes", o_t)
        c2.metric("🔴 Abiertas",      o_ab)
        c3.metric("🟡 Liberadas",     o_lb)
        c4.metric("✅ Concluidas",    o_ct)
        c5.metric("⚫ Cerradas",      o_ce)

        # Sub-ubicación ALIM.SELEC
        if emp_filter == "2002-ALIM.SELEC" and not sub_filter:
            st.markdown('<div class="section-title" style="background:#b45309">📍 ALIM. SELEC — Por Locación</div>', unsafe_allow_html=True)
            sub_grupos = df_ord[df_ord["Empresa"]=="2002-ALIM.SELEC"].groupby("SubUbi")
            cols_sub = st.columns(len(sub_grupos))
            for i,(ubi,grp) in enumerate(sub_grupos):
                ej = len(grp[grp["Status"].isin(["Concluida","Cerrada"])])
                p  = ej/len(grp)*100 if len(grp) else 0
                with cols_sub[i]:
                    st.markdown(f"**📍 {ubi}**")
                    st.metric("Total", len(grp))
                    st.metric("Correctivo", len(grp[grp["Tipo"]=="Correctivo"]))
                    st.metric("Preventivo", len(grp[grp["Tipo"]=="Preventivo"]))
                    st.metric("Abiertas", len(grp[grp["Status"]=="Abierta"]))
                    st.progress(min(p/100,1.0))
                    st.caption(f"Ejecución: {p:.1f}%")

        # PREVENTIVO vs CORRECTIVO
        st.markdown('<div class="section-title" style="background:#374151">📊 Preventivo · Correctivo · Ubic. Técnica</div>', unsafe_allow_html=True)
        c1,c2,c3 = st.columns(3)
        for col, tipo, color_emoji in [(c1,"Correctivo","🔴"),(c2,"Preventivo","🟢"),(c3,"Ubic.Técnica","🟣")]:
            sub = df_f[df_f["Tipo"]==tipo]
            t   = len(sub)
            ej  = len(sub[sub["Status"].isin(["Concluida","Cerrada"])])
            p   = ej/t*100 if t else 0
            with col:
                st.markdown(f"**{color_emoji} {tipo}**")
                cc1,cc2 = st.columns(2)
                cc1.metric("Total",    t)
                cc2.metric("Ejecutadas", ej)
                cc3,cc4 = st.columns(2)
                cc3.metric("Abiertas",  len(sub[sub["Status"]=="Abierta"]))
                cc4.metric("Liberadas", len(sub[sub["Status"]=="Liberada"]))
                st.progress(min(p/100,1.0))
                st.caption(f"{pct_color(p)} Ejecución: **{p:.1f}%**")
                st.markdown("---")

        # ANTIGÜEDAD
        st.markdown('<div class="section-title">⏳ Antigüedad Órdenes Pendientes</div>', unsafe_allow_html=True)
        pend = df_f[df_f["Status"].isin(["Abierta","Liberada"])].copy()
        pend["Dias"] = pd.to_numeric(pend["Dias"], errors="coerce")
        c1,c2,c3,c4 = st.columns(4)
        for col,(lbl2,mn,mx,ico) in zip([c1,c2,c3,c4],[
            ("0–30 días",0,30,"🟢"),("31–60 días",31,60,"🟡"),
            ("61–90 días",61,90,"🟠"),("+90 días",91,9999,"🔴")]):
            sub = pend[pend["Dias"].between(mn,mx)]
            col.metric(f"{ico} {lbl2}", len(sub))
            col.caption(f"C:{len(sub[sub['Tipo']=='Correctivo'])} · P:{len(sub[sub['Tipo']=='Preventivo'])} · U:{len(sub[sub['Tipo']=='Ubic.Técnica'])}")

    # PLANES
    if not df_ip16.empty and not df_ip24.empty:
        st.markdown('<div class="section-title" style="background:#4C1D95">📅 Planes de Mantenimiento Preventivo</div>', unsafe_allow_html=True)
        pl_t  = len(df_ip16)
        po_t  = len(df_ip24)
        po_con= len(df_ip24[df_ip24["ConOrden"]==True])
        po_sin= po_t - po_con
        po_v30= len(df_ip24[df_ip24["DiasVenc"]>30])
        po_pct= po_con/po_t*100 if po_t else 0

        c1,c2,c3,c4,c5,c6 = st.columns(6)
        c1.metric("📋 Planes",      pl_t)
        c2.metric("📌 Posiciones",  po_t)
        c3.metric("✅ Con Orden",   po_con)
        c4.metric("⚠️ Sin Orden",   po_sin)
        c5.metric("🚨 Venc. +30d",  po_v30)
        c6.metric(f"{pct_color(po_pct)} % Cobertura", f"{po_pct:.1f}%")

    # TABLA POR EMPRESA
    if not df_ord.empty:
        st.markdown('<div class="section-title">🏢 Resumen por Empresa</div>', unsafe_allow_html=True)
        emp_summary = []
        for emp in sorted(df_ord["Empresa"].unique()):
            sub = df_ord[df_ord["Empresa"]==emp]
            t   = len(sub)
            ej  = len(sub[sub["Status"].isin(["Concluida","Cerrada"])])
            p   = ej/t*100 if t else 0
            emp_summary.append({
                "Empresa": emp, "Total": t,
                "Correctivo": len(sub[sub["Tipo"]=="Correctivo"]),
                "Preventivo": len(sub[sub["Tipo"]=="Preventivo"]),
                "Ubic.Téc.":  len(sub[sub["Tipo"]=="Ubic.Técnica"]),
                "Abiertas":   len(sub[sub["Status"]=="Abierta"]),
                "Liberadas":  len(sub[sub["Status"]=="Liberada"]),
                "Ejecutadas": ej,
                "% Ejec.":    f"{pct_color(p)} {p:.1f}%",
            })
        st.dataframe(pd.DataFrame(emp_summary), use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — AVISOS
# ════════════════════════════════════════════════════════════════════════════════
with tab2:
    if df_av.empty:
        st.info("Sube el archivo de Avisos (IW29) para ver esta sección.")
    else:
        av_t=len(df_av); av_ab=len(df_av[df_av["StatusSimple"]=="Abierto"])
        av_tr=len(df_av[df_av["StatusSimple"]=="En Tratamiento"]); av_co=len(df_av[df_av["StatusSimple"]=="Concluido"])
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("📋 Total",          av_t)
        c2.metric("🔴 Abiertos",       av_ab)
        c3.metric("🟡 En Tratamiento", av_tr)
        c4.metric("✅ Concluidos",     av_co)
        st.markdown("---")
        cols_show = [c for c in ["Notificación","Fecha de aviso","Clase de aviso","StatusSimple","Equipo","Ubicac.técnica","Descripción"] if c in df_av.columns]
        df_show = df_av[cols_show].rename(columns={"StatusSimple":"Status","Ubicac.técnica":"Ubicación"})
        st.dataframe(df_show, use_container_width=True, hide_index=True, height=520)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — ÓRDENES
# ════════════════════════════════════════════════════════════════════════════════
with tab3:
    if df_f.empty:
        st.info("Sube el archivo de Órdenes (IW38) para ver esta sección.")
    else:
        o_t=len(df_f); o_ab=len(df_f[df_f["Status"]=="Abierta"])
        o_lb=len(df_f[df_f["Status"]=="Liberada"]); o_ct=len(df_f[df_f["Status"]=="Concluida"]); o_ce=len(df_f[df_f["Status"]=="Cerrada"])
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("📋 Total",    o_t)
        c2.metric("🔴 Abiertas", o_ab)
        c3.metric("🟡 Liberadas",o_lb)
        c4.metric("✅ Concluidas",o_ct)
        c5.metric("⚫ Cerradas", o_ce)
        st.caption(f"📍 Filtrando: **{lbl}**")
        st.markdown("---")
        cols_ord = [c for c in ["Orden","Clase de orden","Tipo","Empresa","SubUbi","Status","Fecha","Dias","Equipo","Texto breve"] if c in df_f.columns]
        df_show = df_f[cols_ord].rename(columns={"SubUbi":"Locación","Dias":"Días"}).copy()
        if "Fecha" in df_show.columns:
            df_show["Fecha"] = pd.to_datetime(df_show["Fecha"],errors="coerce").dt.strftime("%d/%m/%Y").fillna("")
        st.dataframe(df_show, use_container_width=True, hide_index=True, height=520)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — PREVENTIVO
# ════════════════════════════════════════════════════════════════════════════════
with tab4:
    if df_f.empty:
        st.info("Sube el archivo de Órdenes (IW38) para ver esta sección.")
    else:
        prev = df_f[df_f["Tipo"]=="Preventivo"]
        pr_t=len(prev); pr_ej=len(prev[prev["Status"].isin(["Concluida","Cerrada"])])
        pr_pct=pr_ej/pr_t*100 if pr_t else 0

        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("📋 Total",     pr_t)
        c2.metric("🔴 Abiertas",  len(prev[prev["Status"]=="Abierta"]))
        c3.metric("🟡 Liberadas", len(prev[prev["Status"]=="Liberada"]))
        c4.metric("✅ Ejecutadas",pr_ej)
        c5.metric(f"{pct_color(pr_pct)} % Ejecución", f"{pr_pct:.1f}%")

        st.progress(min(pr_pct/100,1.0))
        st.caption(f"Nivel de ejecución global: **{pr_pct:.1f}%**")
        st.markdown("---")

        if not emp_filter:
            st.markdown("**Por Empresa**")
            rows=[]
            for emp in sorted(df_ord["Empresa"].unique()):
                sub=df_ord[(df_ord["Empresa"]==emp)&(df_ord["Tipo"]=="Preventivo")]
                if not len(sub): continue
                ej=len(sub[sub["Status"].isin(["Concluida","Cerrada"])]); p=ej/len(sub)*100
                rows.append({"Empresa":emp,"Total":len(sub),"Abiertas":len(sub[sub["Status"]=="Abierta"]),"Liberadas":len(sub[sub["Status"]=="Liberada"]),"Concluidas":len(sub[sub["Status"]=="Concluida"]),"Cerradas":len(sub[sub["Status"]=="Cerrada"]),"Ejecutadas":ej,"% Ejec.":f"{pct_color(p)} {p:.1f}%"})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        elif emp_filter=="2002-ALIM.SELEC":
            st.markdown("**Por Locación — ALIM. SELEC**")
            rows=[]
            for ubi in df_ord[df_ord["Empresa"]=="2002-ALIM.SELEC"]["SubUbi"].dropna().unique():
                sub=df_ord[(df_ord["Empresa"]=="2002-ALIM.SELEC")&(df_ord["Tipo"]=="Preventivo")&(df_ord["SubUbi"]==ubi)]
                if not len(sub): continue
                ej=len(sub[sub["Status"].isin(["Concluida","Cerrada"])]); p=ej/len(sub)*100
                rows.append({"Locación":ubi,"Total":len(sub),"Abiertas":len(sub[sub["Status"]=="Abierta"]),"Liberadas":len(sub[sub["Status"]=="Liberada"]),"Ejecutadas":ej,"% Ejec.":f"{pct_color(p)} {p:.1f}%"})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 5 — CORRECTIVO
# ════════════════════════════════════════════════════════════════════════════════
with tab5:
    if df_f.empty:
        st.info("Sube el archivo de Órdenes (IW38) para ver esta sección.")
    else:
        corr=df_f[df_f["Tipo"]=="Correctivo"]
        co_t=len(corr); co_ej=len(corr[corr["Status"].isin(["Concluida","Cerrada"])])
        co_pct=co_ej/co_t*100 if co_t else 0

        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("📋 Total",     co_t)
        c2.metric("🔴 Abiertas",  len(corr[corr["Status"]=="Abierta"]))
        c3.metric("🟡 Liberadas", len(corr[corr["Status"]=="Liberada"]))
        c4.metric("✅ Ejecutadas",co_ej)
        c5.metric(f"{pct_color(co_pct)} % Cierre", f"{co_pct:.1f}%")

        st.progress(min(co_pct/100,1.0))
        st.caption(f"Nivel de cierre global: **{co_pct:.1f}%**")
        st.markdown("---")

        if not emp_filter:
            st.markdown("**Por Empresa**")
            rows=[]
            for emp in sorted(df_ord["Empresa"].unique()):
                sub=df_ord[(df_ord["Empresa"]==emp)&(df_ord["Tipo"]=="Correctivo")]
                if not len(sub): continue
                ej=len(sub[sub["Status"].isin(["Concluida","Cerrada"])]); p=ej/len(sub)*100
                rows.append({"Empresa":emp,"Total":len(sub),"Abiertas":len(sub[sub["Status"]=="Abierta"]),"Liberadas":len(sub[sub["Status"]=="Liberada"]),"Concluidas":len(sub[sub["Status"]=="Concluida"]),"Cerradas":len(sub[sub["Status"]=="Cerrada"]),"Ejecutadas":ej,"% Cierre":f"{pct_color(p)} {p:.1f}%"})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        elif emp_filter=="2002-ALIM.SELEC":
            st.markdown("**Por Locación — ALIM. SELEC**")
            rows=[]
            for ubi in df_ord[df_ord["Empresa"]=="2002-ALIM.SELEC"]["SubUbi"].dropna().unique():
                sub=df_ord[(df_ord["Empresa"]=="2002-ALIM.SELEC")&(df_ord["Tipo"]=="Correctivo")&(df_ord["SubUbi"]==ubi)]
                if not len(sub): continue
                ej=len(sub[sub["Status"].isin(["Concluida","Cerrada"])]); p=ej/len(sub)*100
                rows.append({"Locación":ubi,"Total":len(sub),"Abiertas":len(sub[sub["Status"]=="Abierta"]),"Liberadas":len(sub[sub["Status"]=="Liberada"]),"Ejecutadas":ej,"% Cierre":f"{pct_color(p)} {p:.1f}%"})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 6 — PLANES PM
# ════════════════════════════════════════════════════════════════════════════════
with tab6:
    if df_ip16.empty or df_ip24.empty:
        st.info("Sube los archivos IP16 e IP24 para ver esta sección.")
    else:
        pl_t=len(df_ip16); po_t=len(df_ip24)
        po_con=len(df_ip24[df_ip24["ConOrden"]==True]); po_sin=po_t-po_con
        po_v30=len(df_ip24[df_ip24["DiasVenc"]>30]); po_pct=po_con/po_t*100 if po_t else 0

        c1,c2,c3,c4,c5,c6=st.columns(6)
        c1.metric("📋 Planes",     pl_t)
        c2.metric("📌 Posiciones", po_t)
        c3.metric("✅ Con Orden",  po_con)
        c4.metric("⚠️ Sin Orden",  po_sin)
        c5.metric("🚨 Venc.+30d", po_v30)
        c6.metric(f"{pct_color(po_pct)} % Cobertura", f"{po_pct:.1f}%")

        st.progress(min(po_pct/100,1.0))
        st.caption(f"Cobertura de órdenes generadas: **{po_pct:.1f}%**")
        st.markdown("---")

        st.markdown("#### 🚨 Posiciones Sin Orden — ordenadas por urgencia")
        df_sin = df_ip24[df_ip24["ConOrden"]==False].copy()
        df_sin = df_sin.sort_values("DiasVenc", ascending=False)
        cols_24 = [c for c in ["Plan mant.preventivo","Descripción posición de mantenimiento","Estrategia mantenim.","Nº toma mant.","Fecha","DiasVenc"] if c in df_sin.columns]
        df_show24 = df_sin[cols_24].rename(columns={"Plan mant.preventivo":"Plan","Descripción posición de mantenimiento":"Descripción","Estrategia mantenim.":"Estrategia","Nº toma mant.":"Toma","DiasVenc":"Días Vencido"})
        if "Fecha" in df_show24.columns:
            df_show24["Fecha"] = pd.to_datetime(df_show24["Fecha"],errors="coerce").dt.strftime("%d/%m/%Y").fillna("")
        st.dataframe(df_show24, use_container_width=True, hide_index=True, height=500)
