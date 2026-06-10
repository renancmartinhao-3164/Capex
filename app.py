import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# 1. CONFIGURAÇÃO DA PÁGINA E CABEÇALHO
st.set_page_config(layout="wide", page_title="Capex Dashboard")

# 2. BARRA LATERAL - UPLOAD
st.sidebar.header("⚙️ Configurações")
uploaded_file = st.sidebar.file_uploader("Arquivo Excel", type=["xlsx", "xls"], key="uploader_capex_agco")

# Lógica de Metadados do Upload
if uploaded_file is not None:
    data_update_txt = datetime.now().strftime("%d/%m/%Y - %H:%M")
    status_excel = f"Atualizado em: {data_update_txt} (Arquivo carregado)"
else:
    status_excel = "Atualizado em: 10/06/2026 - 16:37 (Dados de Demonstração)"

# Layout do Topo (Logo + Título + Data de Update)
col_logo, col_tit = st.columns([1, 5])
with col_logo:
    logo_path = next((f for f in ["Logo AGCO.jpg", "logo.jpg"] if os.path.exists(f)), None)
    if logo_path:
        st.image(logo_path, width=180)
    else:
        st.write("📌 [Logo]")

with col_tit:
    st.markdown("<h1 style='margin-bottom:0;'>Capex - Evolução do Investimento</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='margin-top:0; color: #555; margin-bottom:5px;'>Manufatura SA</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='margin-top:0; color: #888; font-size: 14px; font-style: italic;'>📅 {status_excel}</p>", unsafe_allow_html=True)

@st.cache_data
def dados_ficticios():
    import numpy as np
    anos, vers = [2024, 2025, 2026], ["Budget 2026", "Realizado", "Fcast 2+10"]
    areas = ["Manufacturing", "Logistics", "Quality", "Engineering"]
    tipos = ["NPI", "Legal / Regulatory", "Quality", "Infrastructure", "Maintenance", "Capacity"]
    plantas = ["Mogi", "Canoas", "Ibirubá", "Santa Rosa"]
    meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    data = []
    
    # Gerando 80 itens únicos fixos com Nro_Item Código para a simulação
    for i in range(1, 81):
        item_cod = f"ITM-{1000 + i}"
        a = 2026
        ar = np.random.choice(areas)
        t = np.random.choice(tipos)
        p = np.random.choice(plantas)
        
        # Cria cenários correspondentes para o mesmo item
        for v in vers:
            if v == "Budget 2026":
                vals = [np.random.randint(10000, 80000) for _ in range(12)]
            elif v == "Fcast 2+10":
                vals = [np.random.randint(9000, 75000) for _ in range(12)]
            else: # Realizado com valores menores simulando atraso proposital
                vals = [np.random.randint(2000, 45000) for _ in range(12)]
            data.append([item_cod, a, v, ar, t, p] + vals)
            
    return pd.DataFrame(data, columns=["Nro_Item Código", "Ano", "Versão", "Área", "Tipo_Proj Código", "Planta"] + meses)

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
    
    c_ano = next((o for o, n in map_c.items() if "ano" in n), df_bruto.columns[1])
    c_ver = next((o for o, n in map_c.items() if "vers" in n or "cenar" in n), df_bruto.columns[2])
    
    # Mapeamento do Identificador Estável solicitado
    c_item = "Nro_Item Código" if "Nro_Item Código" in df_bruto.columns else next((o for o, n in map_c.items() if "item" in n or "nro" in n), df_bruto.columns[0])
    
    # Forçando leitura da Coluna D para a variável Área
    c_area = df_bruto.columns[3] if len(df_bruto.columns) >= 4 else df_bruto.columns[0]
    c_tipo = "Tipo_Proj Código" if "Tipo_Proj Código" in df_bruto.columns else next((o for o, n in map_c.items() if "tipo" in n or "proj" in n), None)
    c_planta = next((o for o, n in map_c.items() if any(x in n for x in ["planta", "filial", "unidade", "site"])), None)

    m_ord = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    m_alvo = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    c_meses = []
    for m in m_alvo:
        match = next((o for o, n in map_c.items() if n == m or n.startswith(m)), None)
        if match: c_meses.append(match)

    fixas = [c_item, c_ano, c_ver]
    for col in [c_area, c_tipo, c_planta]:
        if col and col not in fixas: fixas.append(col)

    df_l = df_bruto.melt(id_vars=fixas, value_vars=c_meses, var_name='M_Orig', value_name='Val')
    df_l = df_l.rename(columns={c_ano: 'Ano', c_ver: 'Versão', c_item: 'Nro_Item Código'})
    
    map_m = dict(zip(c_meses, m_ord))
    df_l['Mês'] = df_l['M_Orig'].map(map_m)
    df_l['Área'] = df_l[c_area]
    df_l['Projeto'] = df_l[c_tipo] if c_tipo else 'Geral'
    df_l['Planta'] = df_l[c_planta] if c_planta else 'Geral'
    
    df_l['Val'] = pd.to_numeric(df_l['Val'], errors='coerce').fillna(0)
    df_l['Ano'] = df_l['Ano'].astype(str).str.replace(r'\.0$', '', regex=True)

except Exception as e:
    st.error(f"Erro no mapeamento estrutural: {e}")
    st.stop()
    # --- 4. FILTROS SUPERIORES ---
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
    m_lim = st.selectbox("⏳ Visão YTD (Até)", m_ord, index=4)  # Padrão: Maio

# Aplicação matemática dos filtros no DataFrame Geral
df_f = df_l[(df_l["Ano"] == ano_s) & (df_l["Versão"].isin(ver_s)) & (df_l["Área"].isin(area_s)) & (df_l["Planta"].isin(site_s))]
df_f = df_f[df_f["Mês"].isin(m_ord[:m_ord.index(m_lim)+1])]

# Base expandida para cálculo interno de atrasos (precisa do Budget e Realizado simultaneamente para a tabela analítica)
df_analise_base = df_l[(df_l["Ano"] == ano_s) & (df_l["Área"].isin(area_s)) & (df_l["Planta"].isin(site_s))]
df_analise_base = df_analise_base[df_analise_base["Mês"].isin(m_ord[:m_ord.index(m_lim)+1])]

# --- 5. VISUALIZAÇÕES E CARTÕES ---
if df_f.empty:
    st.warning("⚠️ Sem dados para os filtros selecionados.")
else:
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
        st.markdown(f"<div style='background-color:#f8f9fa; padding:15px; border-radius:10px; border-left:5px solid #ff2a2a;'><p style='margin:0; font-size:14px; color:#555; font-weight:bold;'>Realizado YTD (Jan a {m_lim})</p><h2 style='margin:5px 0 0 0; color:#222;'>$ {val_real:,.2f}</h2></div>", unsafe_allow_html=True)
    with kpi2:
        txt_delta_b = f"{pct_vs_budg:.1f}% do Budget" if val_budg > 0 else "Budget não selecionado"
        st.markdown(f"<div style='background-color:#f8f9fa; padding:15px; border-radius:10px; border-left:5px solid #0066cc;'><p style='margin:0; font-size:14px; color:#555; font-weight:bold;'>Realizado vs Budget</p><h2 style='margin:5px 0 0 0; color:#0066cc;'>{txt_delta_b}</h2><p style='margin:0; font-size:12px; color:#777;'>Total original: $ {val_budg:,.2f}</p></div>", unsafe_allow_html=True)
    with kpi3:
        txt_delta_f = f"{pct_vs_fcast:.1f}% do Forecast" if val_fcast > 0 else "Forecast não selecionado"
        st.markdown(f"<div style='background-color:#f8f9fa; padding:15px; border-radius:10px; border-left:5px solid #7cb9e8;'><p style='margin:0; font-size:14px; color:#555; font-weight:bold;'>Realizado vs Forecast</p><h2 style='margin:5px 0 0 0; color:#3b7aae;'>{txt_delta_f}</h2><p style='margin:0; font-size:12px; color:#777;'>Total original: $ {val_fcast:,.2f}</p></div>", unsafe_allow_html=True)
        # --- GRÁFICOS COM RÓTULOS ATIVADOS ---
    st.write("---")
    st.subheader(f"📊 Comparativo Geral Capex YTD (Jan a {m_lim}) - USD")
    
    fig_main = px.bar(df_f.groupby("Versão")["Val"].sum().reset_index(), x="Versão", y="Val", color="Versão", text_auto='.2f')
    fig_main.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
    fig_main.update_layout(yaxis_tickformat='$')
    st.plotly_chart(fig_main, use_container_width=True)

    st.write("---")
    g1, g2 = st.columns(2)
    
    with g1:
        st.subheader("📊 Cenários por Tipo de Projeto (Budget vs Fcast vs Realizado)")
        df_proj_ver = df_f.groupby(["Projeto", "Versão"])["Val"].sum().reset_index()
        
        fig_p = px.bar(
            df_proj_ver, 
            x="Projeto", 
            y="Val", 
            color="Versão", 
            barmode="group",
            text_auto='.2f'
        )
        fig_p.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
        fig_p.update_layout(yaxis_tickformat='$', xaxis_title="Tipo de Projeto", legend_title="Cenário", xaxis={'categoryorder':'total descending'})
        st.plotly_chart(fig_p, use_container_width=True)
        
    with g2:
        st.subheader("🏢 Distribuição Total por Site")
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

    # --- NOVA SEÇÃO: ANÁLISE COMPLEMENTAR DE PROJETOS EM ATRASO (PÓS-LINHA TEMPORAL) ---
    st.write("---")
    st.subheader(f"⚠️ Análise de Desvios: TOP 10 Projetos em Atraso no Desembolso YTD (Até {m_lim})")
    st.markdown("A tabela abaixo rastreia os projetos utilizando o **Nro_Item Código** estável. O cálculo aponta onde o montante executado (*Realizado*) está mais distante da meta original planejada (*Budget*).")

    # Identifica dinamicamente os nomes dos cenários na base
    v_nomes = df_analise_base["Versão"].unique()
    v_b = next((v for v in v_nomes if any(x in str(v).lower() for x in ['orc', 'budg', 'prev'])), None)
    v_r = next((v for v in v_nomes if 'real' in str(v).lower()), None)

    if not v_b or not v_r:
        st.info("ℹ️ Para calcular o atraso de projetos individuais, certifique-se de possuir dados de 'Budget' e 'Realizado' mapeados na coluna de Versão.")
    else:
        # Agrupa os valores acumulados YTD por Item e Versão
        df_pivot_itens = df_analise_base.groupby(["Nro_Item Código", "Projeto", "Área", "Planta", "Versão"])["Val"].sum().unstack(level="Versão").fillna(0).reset_index()
        
        if v_b in df_pivot_itens.columns and v_r in df_pivot_itens.columns:
            # Atraso = Budget acumulado - Realizado acumulado
            df_pivot_itens["Atraso (USD)"] = df_pivot_itens[v_b] - df_pivot_itens[v_r]
            
            # Filtra apenas o que de fato está atrasado (Budget > Realizado)
            df_atrasados = df_pivot_itens[df_pivot_itens["Atraso (USD)"] > 0].copy()
            
            # Se houver filtro de versão específico na tela, mantém a coerência visual das colunas informadas
            df_atrasados = df_atrasados.rename(columns={v_b: "Budget YTD", v_r: "Realizado YTD"})
            
            # Ordena do maior atraso monetário para o menor e pega os TOP 10
            df_top_10 = df_atrasados.sort_values(by="Atraso (USD)", ascending=False).head(10)
            
            if df_top_10.empty:
                st.success("✅ Excelente! Nenhum projeto mapeado apresenta desembolso atrasado em relação ao planejado no período selecionado.")
            else:
                # Formata os valores monetários para exibição na tabela corporativa
                df_exibicao = df_top_10[["Nro_Item Código", "Projeto", "Área", "Planta", "Budget YTD", "Realizado YTD", "Atraso (USD)"]].copy()
                
                # Respeita o filtro superior de Versões para ocultar colunas não selecionadas pelo usuário, se necessário
                for col in ["Budget YTD", "Realizado YTD", "Atraso (USD)"]:
                    df_exibicao[col] = df_exibicao[col].map(lambda x: f"$ {x:,.2f}")
                
                # Exibe a tabela formatada com largura total
                st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ Não foi possível localizar colunas de cenários equivalentes para calcular o desvio.")

with st.expander("🔍 Ver Tabela de Dados Brutos"):
    df_view = df_f.copy()
    df_view['Val'] = df_view['Val'].map(lambda x: f"$ {x:,.2f}")
    st.dataframe(df_view, use_container_width=True)
    
