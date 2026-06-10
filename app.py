import streamlit as st
import pandas as pd
import plotly.express as px
import os

# 1. CONFIGURAÇÃO DA PÁGINA E CABEÇALHO
st.set_page_config(layout="wide", page_title="Capex Dashboard")

# Layout do Topo (Logo + Título)
col_logo, col_tit = st.columns([1, 5])
with col_logo:
    logo_path = next((f for f in ["Logo AGCO.jpg", "logo.jpg"] if os.path.exists(f)), None)
    if logo_path:
        st.image(logo_path, width=180)
    else:
        st.write("📌 [Logo]")

with col_tit:
    st.markdown("<h1 style='margin-bottom:0;'>Capex - Evolução do Investimento</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='margin-top:0; color: #555;'>Manufatura SA</h3>", unsafe_allow_html=True)

# 2. BARRA LATERAL - UPLOAD
st.sidebar.header("⚙️ Configurações")
uploaded_file = st.sidebar.file_uploader("Arquivo Excel", type=["xlsx", "xls"], key="uploader_capex_agco")

@st.cache_data
def dados_ficticios():
    import numpy as np
    anos, vers = [2024, 2025, 2026], ["Budget 2026", "Realizado", "Fcast 2+10"]
    areas = ["Manufacturing", "Logistics", "Quality", "Engineering"]
    tipos = ["Capacidade", "Manutenção", "Segurança", "Inovação"]
    plantas = ["Mogi", "Canoas", "Ibirubá", "Santa Rosa"]
    meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    data = []
    for a in anos:
        for v in vers:
            for ar in areas:
                for t in tipos:
                    for p in plantas:
                        vals = [np.random.randint(5000, 50000) for _ in range(12)]
                        data.append([a, v, ar, t, p] + vals)
    return pd.DataFrame(data, columns=["Ano", "Versão", "Área", "Tipo_Proj Código", "Planta"] + meses)

df_bruto = pd.read_excel(uploaded_file) if uploaded_file is not None else dados_ficticios()
if uploaded_file is not None: st.sidebar.success("Excel carregado!")
    # --- 3. TRATAMENTO DOS DADOS ---
try:
    def limpa(t):
        t = str(t).lower().strip()
        for o, s in [("ã","a"),("õ","a"),("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u")]:
            t = t.replace(o, s)
        return t

    map_c = {c: limpa(c) for c in df_bruto.columns}
    
    # Identifica colunas-chave (Área forçada estritamente na Coluna D do Excel, índice 3)
    c_ano = next((o for o, n in map_c.items() if "ano" in n), df_bruto.columns[0])
    c_ver = next((o for o, n in map_c.items() if "vers" in n or "cenar" in n), df_bruto.columns[1])
    
    # Forçando explicitamente a Coluna D (índice 3 do DataFrame)
    c_area = df_bruto.columns[3] if len(df_bruto.columns) >= 4 else df_bruto.columns[0]
    
    c_tipo = "Tipo_Proj Código" if "Tipo_Proj Código" in df_bruto.columns else next((o for o, n in map_c.items() if "tipo" in n or "proj" in n), None)
    c_planta = next((o for o, n in map_c.items() if any(x in n for x in ["planta", "filial", "unidade", "site"])), None)

    # Identifica meses
    m_ord = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    m_alvo = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    c_meses = []
    for m in m_alvo:
        match = next((o for o, n in map_c.items() if n == m or n.startswith(m)), None)
        if match: c_meses.append(match)

    fixas = [c_ano, c_ver]
    for col in [c_area, c_tipo, c_planta]:
        if col and col not in fixas: fixas.append(col)

    # Reestruturação (Wide to Long)
    df_l = df_bruto.melt(id_vars=fixas, value_vars=c_meses, var_name='M_Orig', value_name='Val')
    df_l = df_l.rename(columns={c_ano: 'Ano', c_ver: 'Versão'})
    
    map_m = dict(zip(c_meses, m_ord))
    df_l['Mês'] = df_l['M_Orig'].map(map_m)
    df_l['Área'] = df_l[c_area]
    df_l['Projeto'] = df_l[c_tipo] if c_tipo else 'Geral'
    df_l['Planta'] = df_l[c_planta] if c_planta else 'Geral'
    
    df_l['Val'] = pd.to_numeric(df_l['Val'], errors='coerce').fillna(0)
    df_l['Ano'] = df_l['Ano'].astype(str).str.replace(r'\.0$', '', regex=True)

except Exception as e:
    st.error(f"Erro no mapeamento: {e}")
    st.stop()
    # --- 4. FILTROS ---
st.write("---")
f1, f2, f2_site, f3, f4 = st.columns(5)
with f1: 
    ano_s = st.selectbox("📅 Ano", sorted(df_l["Ano"].unique(), reverse=True))
with f2: 
    area_s = st.multiselect("📂 Área", sorted(df_l["Área"].unique()), default=df_l["Área"].unique())
with f2_site: 
    site_s = st.multiselect("🏢 Site", sorted(df_l["Planta"].unique()), default=df_l["Planta"].unique())
with f3:
    v_list = list(df_l["Versão"].unique())
    v_def = [v for v in v_list if any(x in str(v).lower() for x in ['real', 'orc', 'budg'])]
    ver_s = st.multiselect("🔄 Versão", v_list, default=v_def if v_def else [v_list[0]] if v_list else [])
with f4: 
    m_lim = st.selectbox("⏳ Visão YTD (Até)", m_ord, index=4)  # Padrão em Maio

# Aplicação dos Filtros
df_f = df_l[(df_l["Ano"] == ano_s) & (df_l["Versão"].isin(ver_s)) & (df_l["Área"].isin(area_s)) & (df_l["Planta"].isin(site_s))]
df_f = df_f[df_f["Mês"].isin(m_ord[:m_ord.index(m_lim)+1])]

# --- 5. VISUALIZAÇÕES E GRÁFICOS ---
if df_f.empty:
    st.warning("⚠️ Sem dados para os filtros selecionados.")
else:
    # --- SEÇÃO DE CARTÕES DE DESTAQUE ---
    st.write("---")
    df_kpi = df_f.groupby("Versão")["Val"].sum().to_dict()
    
    v_real = next((v for v in df_kpi if 'real' in str(v).lower()), None)
    v_budg = next((v for v in df_kpi if any(x in str(v).lower() for x in ['orc', 'budg', 'prev'])), None)
    v_fcast = next((v for v in df_kpi if 'fcast' in str(v).lower() or 'fore' in str(v).lower()), None)
    
    val_real = df_kpi.get(v_real, 0) if v_real else 0
    val_budg = df_kpi.get(v_budg, 0) if v_budg else 0
    val_fcast = df_kpi.get(v_fcast, 0) if v_fcast else 0
    
    pct_vs_budg = (val_real / val_budg * 100) if val_budg > 0 else 0
    pct_vs_fcast = (val_real / val_fcast * 100) if val_fcast > 0 else 0

    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.markdown(
            f"<div style='background-color:#f8f9fa; padding:15px; border-radius:10px; border-left:5px solid #ff2a2a;'>"
            f"<p style='margin:0; font-size:14px; color:#555; font-weight:bold;'>Realizado YTD (Jan a {m_lim})</p>"
            f"<h2 style='margin:5px 0 0 0; color:#222;'>$ {val_real:,.2f}</h2>"
            f"</div>", unsafe_allow_html=True
        )
    with kpi2:
        txt_delta_b = f"{pct_vs_budg:.1f}% do Budget" if val_budg > 0 else "Budget não selecionado"
        st.markdown(
            f"<div style='background-color:#f8f9fa; padding:15px; border-radius:10px; border-left:5px solid #0066cc;'>"
            f"<p style='margin:0; font-size:14px; color:#555; font-weight:bold;'>Realizado vs Budget 2026</p>"
            f"<h2 style='margin:5px 0 0 0; color:#0066cc;'>{txt_delta_b}</h2>"
            f"<p style='margin:0; font-size:12px; color:#777;'>Total original: $ {val_budg:,.2f}</p>"
            f"</div>", unsafe_allow_html=True
        )
    with kpi3:
        txt_delta_f = f"{pct_vs_fcast:.1f}% do Forecast" if val_fcast > 0 else "Forecast não selecionado"
        st.markdown(
            f"<div style='background-color:#f8f9fa; padding:15px; border-radius:10px; border-left:5px solid #7cb9e8;'>"
            f"<p style='margin:0; font-size:14px; color:#555; font-weight:bold;'>Realizado vs Forecast</p>"
            f"<h2 style='margin:5px 0 0 0; color:#3b7aae;'>{txt_delta_f}</h2>"
            f"<p style='margin:0; font-size:12px; color:#777;'>Total original: $ {val_fcast:,.2f}</p>"
            f"</div>", unsafe_allow_html=True
        )
        # --- GRÁFICOS COM RÓTULOS ATIVADOS ---
    st.write("---")
    st.subheader(f"📊 Comparativo Capex YTD (Jan a {m_lim}) - USD")
    
    # 1. Barra Principal
    fig_main = px.bar(df_f.groupby("Versão")["Val"].sum().reset_index(), x="Versão", y="Val", color="Versão", text_auto='.2f')
    fig_main.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
    fig_main.update_layout(yaxis_tickformat='$')
    st.plotly_chart(fig_main, use_container_width=True)

    st.write("---")
    g1, g2 = st.columns(2)
    with g1:
        st.subheader("🍕 Por Tipo de Projeto")
        fig_p = px.pie(df_f.groupby("Projeto")["Val"].sum().reset_index(), values="Val", names="Projeto", hole=0.4)
        fig_p.update_traces(
            textinfo='percent+label',
            texttemplate='%{label}<br>%{percent:.1%}<br>$%{value:,.2f}',
            textposition='outside'
        )
        st.plotly_chart(fig_p, use_container_width=True)
    with g2:
        st.subheader("🏢 Por Site")
        fig_pl = px.bar(df_f.groupby("Planta")["Val"].sum().reset_index().sort_values("Val", ascending=False), x="Planta", y="Val", color="Planta", text_auto='.2f')
        fig_pl.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
        fig_pl.update_layout(yaxis_tickformat='$', showlegend=False, xaxis_title="Site")
        st.plotly_chart(fig_pl, use_container_width=True)

    # 3. Gráfico de Evolução Temporal Mensal
    st.write("---")
    st.subheader("📈 Evolução Mensal Temporal")
    df_ev = df_f.groupby(["Mês", "Versão"])["Val"].sum().reset_index()
    df_ev['Idx'] = df_ev['Mês'].map({m: i for i, m in enumerate(m_ord)})
    
    df_ev_sorted = df_ev.sort_values('Idx')
    df_ev_sorted['Label_Txt'] = df_ev_sorted['Val'].map(lambda x: f"${x:,.0f}")
    
    fig_ev = px.line(df_ev_sorted, x="Mês", y="Val", color="Versão", markers=True, text="Label_Txt")
    fig_ev.update_traces(textposition='top center')
    fig_ev.update_layout(yaxis_tickformat='$')
    st.plotly_chart(fig_ev, use_container_width=True)

with st.expander("🔍 Ver Tabela de Dados"):
    df_view = df_f.copy()
    df_view['Val'] = df_view['Val'].map(lambda x: f"$ {x:,.2f}")
    st.dataframe(df_view, use_container_width=True)
    
