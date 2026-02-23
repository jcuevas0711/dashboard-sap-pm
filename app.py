import streamlit as st
import pandas as pd
import datetime
import requests
import io
import base64

st.set_page_config(
    page_title="Dashboard KPI — SAP PM",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main { background-color: #F1F5F9; }
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    .section-title {
        background: #1e3a5f; color: white; font-weight: 700; font-size: 0.8rem;
        letter-spacing: 1.2px; text-transform: uppercase; padding: 7px 14px;
        border-radius: 7px; margin: 18px 0 10px 0;
    }
    .stTabs [data-baseweb="tab"] { font-weight: 600; font-size: 0.85rem; }
    .stTabs [aria-selected="true"] { color: #1e3a5f !important; }
</style>
""", unsafe_allow_html=True)

# ── helpers ───────────────────────────────────────────────────────────────────
EMPRESA_MAP = {
    "H":"3001-ALTER",     "L":"5001-SOLIN",     "F":"2002-ALIM.SELEC",
    "K":"4002-MAGNO",     "D":"1004-CEDISA",    "J":"4001-RECOR",
    "E":"2001-Z.FERTIL",  "S":"3006-ELEC.SERV", "O":"1005-NORDPHARMA",
    "G":"2003-CAFE.SELEC","Q":"3003-US.GEOTHER","R":"3005-ELEC.POW",
    "N":"2004-TIPSA",     "M":"6000-YR",        "A":"1001-JICOH",
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

def pct_icon(p):
    if p >= 80: return "🟢"
    if p >= 60: return "🟡"
    return "🔴"

def days_diff(fecha):
    if pd.isna(fecha): return None
    try:
        return (datetime.datetime.today() - pd.to_datetime(fecha)).days
    except:
        return None

def sharepoint_to_direct(share_url):
    """Convierte link de SharePoint/OneDrive a URL de descarga directa."""
    share_url = str(share_url).strip()
    # Método 1: usar la API de OneDrive shares
    encoded = base64.b64encode(share_url.encode()).decode()
    encoded = encoded.rstrip("=").replace("/", "_").replace("+", "-")
    return f"https://api.onedrive.com/v1.0/shares/u!{encoded}/root/content"

@st.cache_data(ttl=300, show_spinner=False)
def fetch_excel(url: str, label: str):
    """Descarga Excel desde URL directa de OneDrive."""
    if not url or not url.strip():
        return None
    try:
        direct = sharepoint_to_direct(url)
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(direct, headers=headers, timeout=30, allow_redirects=True)
        if r.status_code == 200:
            return pd.read_excel(io.BytesIO(r.content), dtype=str)
        else:
            st.warning(f"⚠️ {label}: HTTP {r.status_code}")
            return None
    except Exception as e:
        st.warning(f"⚠️ Error cargando {label}: {str(e)[:100]}")
        return None

def process_ordenes(df):
    df = df.copy(); df.columns = df.columns.str.strip()
    df["Tipo"]    = df["Clase de orden"].apply(get_tipo)
    df["Empresa"] = df["Clase de orden"].apply(get_empresa)
    df["Status"]  = df["Status sistema"].apply(simplify_status)
    df["Ubi"]     = df.get("Ubicac.técnica", pd.Series([""] * len(df)))
    df["SubUbi"]  = df.apply(lambda r: get_sub_ubi(r["Empresa"], r.get("Ubi", "")), axis=1)
    df["Fecha"]   = pd.to_datetime(df.get("Fe.inic.extrema", ""), errors="coerce")
    df["Dias"]    = df.apply(
        lambda r: days_diff(r["Fecha"]) if r["Status"] in ("Abierta","Liberada") else None, axis=1)
    return df

def process_avisos(df):
    df = df.copy(); df.columns = df.columns.str.strip()
    df["StatusSimple"] = df["Status sistema"].apply(simplify_aviso)
    return df

def process_ip24(df):
    df = df.copy(); df.columns = df.columns.str.strip()
    df["ConOrden"] = df["Orden"].apply(
        lambda x: bool(x) and str(x).strip() not in ["","nan","0","NaN"])
    df["Fecha"]    = pd.to_datetime(df.get("Fe.inic.progr.", ""), errors="coerce")
    df["DiasVenc"] = df["Fecha"].apply(days_diff)
    return df

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuración")
    st.markdown("---")
    st.markdown("### 🔗 Links de OneDrive")
    st.markdown("""Para cada archivo: clic derecho → **Compartir** → 
    **Cualquier persona con vínculo** → Copiar""")

    url_av  = st.text_input("🔔 Avisos.xlsx",   placeholder="https://jicohen0-my.sharepoint.com/...")
    url_ord = st.text_input("🔧 Ordenes.xlsx",  placeholder="https://jicohen0-my.sharepoint.com/...")
    url_16  = st.text_input("📋 IP16.xlsx",     placeholder="https://jicohen0-my.sharepoint.com/...")
    url_24  = st.text_input("📅 IP24.xlsx",     placeholder="https://jicohen0-my.sharepoint.com/...")

    cargar = st.button("🔄 Cargar / Actualizar", type="primary", use_container_width=True)
    if cargar:
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.caption(f"📅 {datetime.datetime.today().strftime('%d/%m/%Y %H:%M')}")
    st.caption("Cache: 5 minutos")

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='background:linear-gradient(135deg,#0f2443,#1e3a5f,#1a4f7a);
     padding:20px 28px;border-radius:12px;margin-bottom:20px;
     box-shadow:0 4px 20px rgba(0,0,0,0.2)'>
  <div style='font-size:10px;color:rgba(255,255,255,0.4);letter-spacing:3px;
       text-transform:uppercase'>SAP Plant Maintenance</div>
  <h1 style='margin:4px 0 0;color:white;font-size:1.6rem;font-weight:800'>
    📋 Dashboard KPI — Mantenimiento
  </h1>
  <div style='font-size:12px;color:rgba(255,255,255,0.5);margin-top:4px'>
    Datos desde OneDrive · Se actualiza automáticamente cada 5 minutos
  </div>
</div>
""", unsafe_allow_html=True)

# ── CARGAR ────────────────────────────────────────────────────────────────────
any_url = any([url_av, url_ord, url_16, url_24])

if not any_url:
    st.markdown("""
    <div style='text-align:center;padding:60px 20px;color:#64748B'>
        <div style='font-size:64px'>📊</div>
        <h2 style='color:#1e3a5f;margin-top:12px'>Configura los links de OneDrive</h2>
        <p style='max-width:520px;margin:8px auto;line-height:1.6'>
            En el panel lateral izquierdo, pega los links compartidos de cada 
            archivo Excel. El dashboard se genera automáticamente.
        </p>
        <div style='background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;
             padding:16px 24px;max-width:480px;margin:20px auto;text-align:left;font-family:monospace'>
            📁 Dashboard-SAP-PM/<br>
            ├── Avisos.xlsx &nbsp;&nbsp;&nbsp;← IW29<br>
            ├── Ordenes.xlsx ← IW38<br>
            ├── IP16.xlsx &nbsp;&nbsp;&nbsp;← IP16<br>
            └── IP24.xlsx &nbsp;&nbsp;&nbsp;← IP24
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Cargar archivos
with st.spinner("⏳ Cargando datos desde OneDrive..."):
    raw_av  = fetch_excel(url_av,  "Avisos")  if url_av  else None
    raw_ord = fetch_excel(url_ord, "Ordenes") if url_ord else None
    raw_16  = fetch_excel(url_16,  "IP16")    if url_16  else None
    raw_24  = fetch_excel(url_24,  "IP24")    if url_24  else None

df_ord  = process_ordenes(raw_ord) if raw_ord is not None else pd.DataFrame()
df_av   = process_avisos(raw_av)   if raw_av  is not None else pd.DataFrame()
df_ip16 = raw_16 if raw_16 is not None else pd.DataFrame()
df_ip24 = process_ip24(raw_24)     if raw_24  is not None else pd.DataFrame()

# Status sidebar
with st.sidebar:
    st.markdown("---")
    st.markdown("#### 📊 Estado")
    for lbl2, df2 in [("🔧 Órdenes",df_ord),("🔔 Avisos",df_av),("📋 IP16",df_ip16),("📅 IP24",df_ip24)]:
        if not df2.empty:
            st.success(f"{lbl2}: {len(df2):,}")
        elif any_url:
            st.error(f"{lbl2}: error")

if df_ord.empty and df_av.empty:
    st.error("❌ No se cargó ningún archivo. Verifica que los links estén compartidos como 'Cualquier persona con el vínculo'.")
    st.stop()

# ── FILTROS ───────────────────────────────────────────────────────────────────
emp_filter = ""
sub_filter = ""

if not df_ord.empty:
    with st.sidebar:
        st.markdown("---")
        st.markdown("#### 📌 Filtros")
        empresas   = sorted([e for e in df_ord["Empresa"].unique() if e and e != "N/A"])
        emp_sel    = st.selectbox("🏢 Empresa", ["Todas"] + empresas)
        emp_filter = "" if emp_sel == "Todas" else emp_sel
        if emp_filter == "2002-ALIM.SELEC":
            sub_sel    = st.selectbox("📍 Locación", ["Todas","Planta 2201","Planta 2202","Otras"])
            sub_filter = "" if sub_sel == "Todas" else sub_sel

df_f = df_ord.copy()
if emp_filter:
    df_f = df_f[df_f["Empresa"] == emp_filter]
if sub_filter and emp_filter == "2002-ALIM.SELEC":
    df_f = df_f[df_f["SubUbi"] == sub_filter]

lbl = emp_filter if emp_filter else "Todas las empresas"
if sub_filter: lbl += f" · {sub_filter}"

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1,tab2,tab3,tab4,tab5,tab6 = st.tabs([
    "📊 Resumen","🔔 Avisos","🔧 Órdenes",
    "🟢 Preventivo","🔴 Correctivo","📅 Planes PM"
])

# ════════ TAB 1: RESUMEN ════════
with tab1:
    st.markdown(f"#### 📍 {lbl}")

    if not df_av.empty:
        st.markdown('<div class="section-title">🔔 Avisos de Mantenimiento</div>', unsafe_allow_html=True)
        av_t=len(df_av); av_ab=len(df_av[df_av["StatusSimple"]=="Abierto"])
        av_tr=len(df_av[df_av["StatusSimple"]=="En Tratamiento"]); av_co=len(df_av[df_av["StatusSimple"]=="Concluido"])
        av_pct=av_co/av_t*100 if av_t else 0
        c1,c2,c3,c4,c5=st.columns(5)
        c1.metric("📋 Total",av_t); c2.metric("🔴 Abiertos",av_ab)
        c3.metric("🟡 En Tratamiento",av_tr); c4.metric("✅ Concluidos",av_co)
        c5.metric(f"{pct_icon(av_pct)} % Conclusión",f"{av_pct:.1f}%")

    if not df_f.empty:
        st.markdown('<div class="section-title">🔧 Órdenes de Mantenimiento</div>', unsafe_allow_html=True)
        o_t=len(df_f); o_ab=len(df_f[df_f["Status"]=="Abierta"])
        o_lb=len(df_f[df_f["Status"]=="Liberada"]); o_ct=len(df_f[df_f["Status"]=="Concluida"]); o_ce=len(df_f[df_f["Status"]=="Cerrada"])
        c1,c2,c3,c4,c5=st.columns(5)
        c1.metric("📋 Total",o_t); c2.metric("🔴 Abiertas",o_ab)
        c3.metric("🟡 Liberadas",o_lb); c4.metric("✅ Concluidas",o_ct); c5.metric("⚫ Cerradas",o_ce)

        if emp_filter=="2002-ALIM.SELEC" and not sub_filter:
            st.markdown('<div class="section-title" style="background:#b45309">📍 ALIM. SELEC — Por Locación</div>', unsafe_allow_html=True)
            sub_g=df_ord[df_ord["Empresa"]=="2002-ALIM.SELEC"].groupby("SubUbi")
            cols_s=st.columns(max(len(sub_g),1))
            for i,(ubi,grp) in enumerate(sub_g):
                ej=len(grp[grp["Status"].isin(["Concluida","Cerrada"])]); p=ej/len(grp)*100 if len(grp) else 0
                with cols_s[i]:
                    st.markdown(f"**📍 {ubi}**")
                    ca,cb=st.columns(2); ca.metric("Total",len(grp)); cb.metric("Abiertas",len(grp[grp["Status"]=="Abierta"]))
                    cc,cd=st.columns(2); cc.metric("Correc.",len(grp[grp["Tipo"]=="Correctivo"])); cd.metric("Prev.",len(grp[grp["Tipo"]=="Preventivo"]))
                    st.progress(min(p/100,1.0)); st.caption(f"Ejecución: {p:.1f}%")

        st.markdown('<div class="section-title" style="background:#374151">📊 Preventivo · Correctivo · Ubic. Técnica</div>', unsafe_allow_html=True)
        c1,c2,c3=st.columns(3)
        for col,tipo,ico in [(c1,"Correctivo","🔴"),(c2,"Preventivo","🟢"),(c3,"Ubic.Técnica","🟣")]:
            sub=df_f[df_f["Tipo"]==tipo]; t=len(sub)
            ej=len(sub[sub["Status"].isin(["Concluida","Cerrada"])]); p=ej/t*100 if t else 0
            with col:
                st.markdown(f"**{ico} {tipo}**")
                ca,cb=st.columns(2); ca.metric("Total",t); cb.metric("Ejecutadas",ej)
                cc,cd=st.columns(2); cc.metric("Abiertas",len(sub[sub["Status"]=="Abierta"])); cd.metric("Liberadas",len(sub[sub["Status"]=="Liberada"]))
                st.progress(min(p/100,1.0)); st.caption(f"{pct_icon(p)} Ejecución: **{p:.1f}%**"); st.markdown("---")

        st.markdown('<div class="section-title">⏳ Antigüedad Órdenes Pendientes</div>', unsafe_allow_html=True)
        pend=df_f[df_f["Status"].isin(["Abierta","Liberada"])].copy()
        pend["Dias"]=pd.to_numeric(pend["Dias"],errors="coerce")
        c1,c2,c3,c4=st.columns(4)
        for col,(l2,mn,mx,ico) in zip([c1,c2,c3,c4],[("0–30 días",0,30,"🟢"),("31–60 días",31,60,"🟡"),("61–90 días",61,90,"🟠"),("+90 días",91,9999,"🔴")]):
            sub=pend[pend["Dias"].between(mn,mx)]
            col.metric(f"{ico} {l2}",len(sub))
            col.caption(f"C:{len(sub[sub['Tipo']=='Correctivo'])} · P:{len(sub[sub['Tipo']=='Preventivo'])} · U:{len(sub[sub['Tipo']=='Ubic.Técnica'])}")

    if not df_ip16.empty and not df_ip24.empty:
        st.markdown('<div class="section-title" style="background:#4C1D95">📅 Planes de Mantenimiento</div>', unsafe_allow_html=True)
        pl_t=len(df_ip16); po_t=len(df_ip24)
        po_con=len(df_ip24[df_ip24["ConOrden"]==True]); po_sin=po_t-po_con
        po_v30=len(df_ip24[df_ip24["DiasVenc"]>30]); po_pct=po_con/po_t*100 if po_t else 0
        c1,c2,c3,c4,c5,c6=st.columns(6)
        c1.metric("📋 Planes",pl_t); c2.metric("📌 Posiciones",po_t)
        c3.metric("✅ Con Orden",po_con); c4.metric("⚠️ Sin Orden",po_sin)
        c5.metric("🚨 Venc.+30d",po_v30); c6.metric(f"{pct_icon(po_pct)} % Cobertura",f"{po_pct:.1f}%")

    if not df_ord.empty:
        st.markdown('<div class="section-title">🏢 Resumen por Empresa</div>', unsafe_allow_html=True)
        rows=[]
        for emp in sorted(df_ord["Empresa"].unique()):
            sub=df_ord[df_ord["Empresa"]==emp]; t=len(sub)
            ej=len(sub[sub["Status"].isin(["Concluida","Cerrada"])]); p=ej/t*100 if t else 0
            rows.append({"Empresa":emp,"Total":t,"Correctivo":len(sub[sub["Tipo"]=="Correctivo"]),"Preventivo":len(sub[sub["Tipo"]=="Preventivo"]),"Ubic.Téc.":len(sub[sub["Tipo"]=="Ubic.Técnica"]),"Abiertas":len(sub[sub["Status"]=="Abierta"]),"Liberadas":len(sub[sub["Status"]=="Liberada"]),"Ejecutadas":ej,"% Ejec.":f"{pct_icon(p)} {p:.1f}%"})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

# ════════ TAB 2: AVISOS ════════
with tab2:
    if df_av.empty:
        st.info("Configura el link de Avisos.xlsx en el panel lateral.")
    else:
        av_t=len(df_av); av_ab=len(df_av[df_av["StatusSimple"]=="Abierto"])
        av_tr=len(df_av[df_av["StatusSimple"]=="En Tratamiento"]); av_co=len(df_av[df_av["StatusSimple"]=="Concluido"])
        c1,c2,c3,c4=st.columns(4)
        c1.metric("📋 Total",av_t); c2.metric("🔴 Abiertos",av_ab)
        c3.metric("🟡 En Tratamiento",av_tr); c4.metric("✅ Concluidos",av_co)
        st.markdown("---")
        cols_s=[c for c in ["Notificación","Fecha de aviso","Clase de aviso","StatusSimple","Equipo","Ubicac.técnica","Descripción"] if c in df_av.columns]
        st.dataframe(df_av[cols_s].rename(columns={"StatusSimple":"Status","Ubicac.técnica":"Ubicación"}),use_container_width=True,hide_index=True,height=520)

# ════════ TAB 3: ÓRDENES ════════
with tab3:
    if df_f.empty:
        st.info("Configura el link de Ordenes.xlsx en el panel lateral.")
    else:
        o_t=len(df_f); o_ab=len(df_f[df_f["Status"]=="Abierta"]); o_lb=len(df_f[df_f["Status"]=="Liberada"])
        o_ct=len(df_f[df_f["Status"]=="Concluida"]); o_ce=len(df_f[df_f["Status"]=="Cerrada"])
        c1,c2,c3,c4,c5=st.columns(5)
        c1.metric("📋 Total",o_t); c2.metric("🔴 Abiertas",o_ab); c3.metric("🟡 Liberadas",o_lb)
        c4.metric("✅ Concluidas",o_ct); c5.metric("⚫ Cerradas",o_ce)
        st.caption(f"📍 {lbl}"); st.markdown("---")
        cols_o=[c for c in ["Orden","Clase de orden","Tipo","Empresa","SubUbi","Status","Fecha","Dias","Equipo","Texto breve"] if c in df_f.columns]
        df_s=df_f[cols_o].rename(columns={"SubUbi":"Locación","Dias":"Días"}).copy()
        if "Fecha" in df_s.columns:
            df_s["Fecha"]=pd.to_datetime(df_s["Fecha"],errors="coerce").dt.strftime("%d/%m/%Y").fillna("")
        st.dataframe(df_s,use_container_width=True,hide_index=True,height=520)

# ════════ TAB 4: PREVENTIVO ════════
with tab4:
    if df_f.empty:
        st.info("Configura el link de Ordenes.xlsx en el panel lateral.")
    else:
        prev=df_f[df_f["Tipo"]=="Preventivo"]; pr_t=len(prev)
        pr_ej=len(prev[prev["Status"].isin(["Concluida","Cerrada"])]); pr_pct=pr_ej/pr_t*100 if pr_t else 0
        c1,c2,c3,c4,c5=st.columns(5)
        c1.metric("📋 Total",pr_t); c2.metric("🔴 Abiertas",len(prev[prev["Status"]=="Abierta"]))
        c3.metric("🟡 Liberadas",len(prev[prev["Status"]=="Liberada"])); c4.metric("✅ Ejecutadas",pr_ej)
        c5.metric(f"{pct_icon(pr_pct)} % Ejecución",f"{pr_pct:.1f}%")
        st.progress(min(pr_pct/100,1.0)); st.caption(f"Nivel de ejecución: **{pr_pct:.1f}%**"); st.markdown("---")
        if not emp_filter:
            rows=[]
            for emp in sorted(df_ord["Empresa"].unique()):
                sub=df_ord[(df_ord["Empresa"]==emp)&(df_ord["Tipo"]=="Preventivo")]
                if not len(sub): continue
                ej=len(sub[sub["Status"].isin(["Concluida","Cerrada"])]); p=ej/len(sub)*100
                rows.append({"Empresa":emp,"Total":len(sub),"Abiertas":len(sub[sub["Status"]=="Abierta"]),"Liberadas":len(sub[sub["Status"]=="Liberada"]),"Concluidas":len(sub[sub["Status"]=="Concluida"]),"Cerradas":len(sub[sub["Status"]=="Cerrada"]),"Ejecutadas":ej,"% Ejec.":f"{pct_icon(p)} {p:.1f}%"})
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        elif emp_filter=="2002-ALIM.SELEC":
            rows=[]
            for ubi in df_ord[df_ord["Empresa"]=="2002-ALIM.SELEC"]["SubUbi"].dropna().unique():
                sub=df_ord[(df_ord["Empresa"]=="2002-ALIM.SELEC")&(df_ord["Tipo"]=="Preventivo")&(df_ord["SubUbi"]==ubi)]
                if not len(sub): continue
                ej=len(sub[sub["Status"].isin(["Concluida","Cerrada"])]); p=ej/len(sub)*100
                rows.append({"Locación":ubi,"Total":len(sub),"Abiertas":len(sub[sub["Status"]=="Abierta"]),"Liberadas":len(sub[sub["Status"]=="Liberada"]),"Ejecutadas":ej,"% Ejec.":f"{pct_icon(p)} {p:.1f}%"})
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

# ════════ TAB 5: CORRECTIVO ════════
with tab5:
    if df_f.empty:
        st.info("Configura el link de Ordenes.xlsx en el panel lateral.")
    else:
        corr=df_f[df_f["Tipo"]=="Correctivo"]; co_t=len(corr)
        co_ej=len(corr[corr["Status"].isin(["Concluida","Cerrada"])]); co_pct=co_ej/co_t*100 if co_t else 0
        c1,c2,c3,c4,c5=st.columns(5)
        c1.metric("📋 Total",co_t); c2.metric("🔴 Abiertas",len(corr[corr["Status"]=="Abierta"]))
        c3.metric("🟡 Liberadas",len(corr[corr["Status"]=="Liberada"])); c4.metric("✅ Ejecutadas",co_ej)
        c5.metric(f"{pct_icon(co_pct)} % Cierre",f"{co_pct:.1f}%")
        st.progress(min(co_pct/100,1.0)); st.caption(f"Nivel de cierre: **{co_pct:.1f}%**"); st.markdown("---")
        if not emp_filter:
            rows=[]
            for emp in sorted(df_ord["Empresa"].unique()):
                sub=df_ord[(df_ord["Empresa"]==emp)&(df_ord["Tipo"]=="Correctivo")]
                if not len(sub): continue
                ej=len(sub[sub["Status"].isin(["Concluida","Cerrada"])]); p=ej/len(sub)*100
                rows.append({"Empresa":emp,"Total":len(sub),"Abiertas":len(sub[sub["Status"]=="Abierta"]),"Liberadas":len(sub[sub["Status"]=="Liberada"]),"Concluidas":len(sub[sub["Status"]=="Concluida"]),"Cerradas":len(sub[sub["Status"]=="Cerrada"]),"Ejecutadas":ej,"% Cierre":f"{pct_icon(p)} {p:.1f}%"})
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        elif emp_filter=="2002-ALIM.SELEC":
            rows=[]
            for ubi in df_ord[df_ord["Empresa"]=="2002-ALIM.SELEC"]["SubUbi"].dropna().unique():
                sub=df_ord[(df_ord["Empresa"]=="2002-ALIM.SELEC")&(df_ord["Tipo"]=="Correctivo")&(df_ord["SubUbi"]==ubi)]
                if not len(sub): continue
                ej=len(sub[sub["Status"].isin(["Concluida","Cerrada"])]); p=ej/len(sub)*100
                rows.append({"Locación":ubi,"Total":len(sub),"Abiertas":len(sub[sub["Status"]=="Abierta"]),"Liberadas":len(sub[sub["Status"]=="Liberada"]),"Ejecutadas":ej,"% Cierre":f"{pct_icon(p)} {p:.1f}%"})
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

# ════════ TAB 6: PLANES PM ════════
with tab6:
    if df_ip16.empty or df_ip24.empty:
        st.info("Configura los links de IP16.xlsx e IP24.xlsx en el panel lateral.")
    else:
        pl_t=len(df_ip16); po_t=len(df_ip24)
        po_con=len(df_ip24[df_ip24["ConOrden"]==True]); po_sin=po_t-po_con
        po_v30=len(df_ip24[df_ip24["DiasVenc"]>30]); po_pct=po_con/po_t*100 if po_t else 0
        c1,c2,c3,c4,c5,c6=st.columns(6)
        c1.metric("📋 Planes",pl_t); c2.metric("📌 Posiciones",po_t)
        c3.metric("✅ Con Orden",po_con); c4.metric("⚠️ Sin Orden",po_sin)
        c5.metric("🚨 Venc.+30d",po_v30); c6.metric(f"{pct_icon(po_pct)} % Cobertura",f"{po_pct:.1f}%")
        st.progress(min(po_pct/100,1.0)); st.caption(f"Cobertura: **{po_pct:.1f}%**"); st.markdown("---")
        st.markdown("#### 🚨 Posiciones Sin Orden — ordenadas por urgencia")
        df_sin=df_ip24[df_ip24["ConOrden"]==False].sort_values("DiasVenc",ascending=False)
        cols_24=[c for c in ["Plan mant.preventivo","Descripción posición de mantenimiento","Estrategia mantenim.","Nº toma mant.","Fecha","DiasVenc"] if c in df_sin.columns]
        df_s24=df_sin[cols_24].rename(columns={"Plan mant.preventivo":"Plan","Descripción posición de mantenimiento":"Descripción","Estrategia mantenim.":"Estrategia","Nº toma mant.":"Toma","DiasVenc":"Días Vencido"}).copy()
        if "Fecha" in df_s24.columns:
            df_s24["Fecha"]=pd.to_datetime(df_s24["Fecha"],errors="coerce").dt.strftime("%d/%m/%Y").fillna("")
        st.dataframe(df_s24,use_container_width=True,hide_index=True,height=500)
