import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# ==========================================
# PARTE 1: CONFIGURAÇÕES E DADOS DE SIMULAÇÃO
# ==========================================
st.set_page_config(layout="wide", page_title="Capex Dashboard")

st.sidebar.header("⚙️ Configurações")
uploaded_file = st.sidebar.file_uploader("Arquivo Excel", type=["xlsx", "xls"], key="uploader_capex_agco")

if uploaded_file is not None:
    data_update_txt = datetime.now().strftime("%d/%m/%Y - %H:%M")
    status_excel = f"Atualizado em: {data_update_txt} (Arquivo carregado)"
else:
    status_excel = "Atualizado em: 10/06/2026 - 17:13 (Dados de Demonstração)"

# Cabeçalho corporativo
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
    anos, vers = [2026], ["Budget 2026", "Realizado", "Fcast 2+10"]
    areas = ["Manufacturing", "Logistics", "Quality", "Engineering"]
    tipos = ["NPI", "Legal / Regulatory", "Quality", "Infrastructure", "Maintenance", "Capacity"]
    plantas = ["Mogi", "Canoas", "Ibirubá", "Santa Rosa"]
    meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    
    nomes_projetos_ficticios = [
        "Expansão da Linha de Montagem", "Adequação NR12 Prensas", "Upgrade Lab de Qualidade", 
        "Novo Sistema de Exaustão", "Automação do Almoxarifado", "Reestruturação da Pintura", 
        "Subestação de Energia Principal", "Frota de AGVs Internos", "Injetora de Plásticos Novo NPI"
    ]
    
    data = []
    for i in range(1, 81):
        item_cod = f"ITM-{1000 + i}"
        nome_proj = nomes_projetos_ficticios[i % len(nomes_projetos_ficticios)] + f" ({i})"
        a = 2026
        ar = np.random.choice(areas)
        t = np.random.choice(tipos)
        p = np.random.choice(plantas)
        
        for v in vers:
            if v == "Budget 2026":
                vals = [np.random.randint(15000, 90000) for _ in range(12)]
            elif v == "Fcast 2+10":
                vals = [np.random.randint(10000, 85000) for _ in range(12)]
            else:
                vals = [np.random.randint(1000, 40000) for _ in range(12)]
                
            data.append([item_cod, a, v, ar, t, p, "Dado_E1", "Dado_E2", nome_proj] + vals)
            
    colunas_ficticias = ["Nro_Item Código", "Ano", "Versão", "Área", "Tipo_Proj Código", "Planta", "Dummy1", "Dummy2", "Nome do Projeto"] + meses
    return pd.DataFrame(data, columns=colunas_ficticias)

df_bruto = pd.read_excel(uploaded_file) if uploaded_file is not None else dados_ficticios()
if uploaded_file is not None: st.sidebar.success("Excel carregado!")


# ==========================================
# PARTE 2: TRATAMENTO E ENGENHARIA DE DADOS
# ==========================================
try:
    def limpa(t):
        t = str(t).lower().strip()
        for o, s in [("ã","a"),("õ","a"),("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u")]:
            t = t.replace(o, s)
        return t

    map_c = {c: limpa(c) for c in df_bruto.columns}
    
    c_ano = next((o for o, n in map_c.items() if "ano" in n), df_bruto.columns[1])
    c_ver = next((o for o, n in map_c.items() if "vers" in n or "cenar" in n), df_bruto.columns[2])
    c_item = "Nro_Item Código" if "Nro_Item Código" in df_bruto.columns else next((o for o, n in map_c.items() if "item" in n or "nro" in n), df_bruto.columns[0])
    
    # MAPEAMENTO DA COLUNA I (Índice 8) PARA O NOME DO PROJETO
    c_nome_proj = df_bruto.columns[8] if len(df_bruto.columns) >= 9 else df_bruto.columns[0]
    
    c_area = df_bruto.columns[3] if len(df_bruto.columns) >= 4 else df_bruto.columns[0]
    c_tipo = "Tipo_Proj Código" if "Tipo_Proj Código" in df_bruto.columns else next((o for o, n in map_c.items() if "tipo" in n or "proj" in n), None)
    c_planta = next((o for o, n in map_c.items() if any(x in n for x in ["planta", "filial", "unidade", "site"])), None)

    m_ord = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    m_alvo = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    c_meses = []
    for m in m_alvo:
        match = next((o for o, n in map_c.items() if n == m or n.startswith(m)), None)
        if match: c_meses.append(match)

    fixas = [c_item, c_nome_proj, c_ano, c_ver]
    for col in [c_area, c_tipo, c_planta]:
        if col and col not in fixas: fixas.append(col)

    df_l = df_bruto.melt(id_vars=fixas, value_vars=c_meses, var_name='M_Orig', value_name='Val')
    df_l = df_l.rename(columns={c_ano: 'Ano', c_ver: 'Versão', c_item: 'Nro_Item Código', c_nome_proj: 'Nome do Projeto'})
    
    map_m = dict(zip(c_meses, m_ord))
    df_l['Mês'] = df_l['M_Orig'].map(map_m)
    df_l['Área'] = df_l[c_area]
    df_l['Projeto'] = df_l[c_tipo] if c_tipo else 'Geral'
    df_l['Planta'] = df_l[c_planta] if c_planta else 'Geral'
    
    df_l['Val'] = pd.to_numeric(df_l['Val'], errors='coerce').fillna(0)
    df_l['Ano'] = df_l['Ano'].astype(str).str.replace(r'\.0$', '', regex=True)

except Exception as e:
    st.error(f"Erro no mapeamento estrutural com a Coluna I: {e}")
    st.stop()


# ==========================================
# PARTE 3: FILTROS DINÂMICOS E PAINEL DE KPIs
# ==========================================
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
    m_lim = st.selectbox("⏳ Visão YTD (Até)", m_ord, index=4)

df_f = df_l[(df_l["Ano"] == ano_s) & (df_l["Versão"].isin(ver_s)) & (df_l["Área"].isin(area_s)) & (df_l["Planta"].isin(site_s))]
df_f = df_f[df_f["Mês"].isin(m_ord[:m_ord.index(m_lim)+1])]

df_analise_base = df_l[(df_l["Ano"] == ano_s) & (df_l["Área"].isin(area_s)) & (df_l["Planta"].isin(site_s))]
df_analise_base = df_analise_base[df_analise_base["Mês"].isin(m_ord[:m_ord.index(m_lim)+1])]

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
# ==========================================
# PARTE 4: LAYOUT VERTICAL E ANÁLISE TOP 20 (ATUALIZADA)
# ==========================================
    st.write("---")
    
    # Cor padrão para manter a identidade visual nos gráficos e no PDF
    cor_graficos = ["#a11f1f"]  # Vermelho corporativo
    
    # 1. Comparativo Geral
    st.subheader(f"📊 Comparativo Geral Capex YTD (Jan a {m_lim}) - USD")
    fig_main = px.bar(df_f.groupby("Versão")["Val"].sum().reset_index(), x="Versão", y="Val", color_discrete_sequence=cor_graficos, text_auto='.2f')
    fig_main.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
    fig_main.update_layout(yaxis_tickformat='$', height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_main, use_container_width=True)

    st.write("---")
    
    # 2. Cenários por Tipo de Projeto
    st.subheader("📊 Cenários por Tipo de Projeto (Budget vs Fcast vs Realizado)")
    df_proj_ver = df_f.groupby(["Projeto", "Versão"])["Val"].sum().reset_index()
    fig_p = px.bar(df_proj_ver, x="Projeto", y="Val", color="Versão", barmode="group", text_auto='.2f')
    fig_p.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
    fig_p.update_layout(yaxis_tickformat='$', xaxis_title="Tipo de Projeto", legend_title="Cenário", xaxis={'categoryorder':'total descending'}, height=450, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_p, use_container_width=True)
        
    st.write("---")

    # 3. Distribuição por Site
    st.subheader("🏢 Distribuição Total por Site")
    fig_pl = px.bar(df_f.groupby("Planta")["Val"].sum().reset_index().sort_values("Val", ascending=False), x="Planta", y="Val", color_discrete_sequence=cor_graficos, text_auto='.2f')
    fig_pl.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
    fig_pl.update_layout(yaxis_tickformat='$', showlegend=False, xaxis_title="Site", height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_pl, use_container_width=True)

    st.write("---")

    # 4. Evolução Mensal Temporal
    st.subheader("📈 Evolução Mensal Temporal")
    df_ev = df_f.groupby(["Mês", "Versão"])["Val"].sum().reset_index()
    df_ev['Idx'] = df_ev['Mês'].map({m: i for i, m in enumerate(m_ord)})
    df_ev_sorted = df_ev.sort_values('Idx')
    df_ev_sorted['Label_Txt'] = df_ev_sorted['Val'].map(lambda x: f"${x:,.0f}")
    
    fig_ev = px.line(df_ev_sorted, x="Mês", y="Val", color="Versão", markers=True, text="Label_Txt")
    fig_ev.update_traces(textposition='top center')
    fig_ev.update_layout(yaxis_tickformat='$', height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_ev, use_container_width=True)


    # =========================================================
    # NOVAS PROPOSTAS ESTRATÉGICAS (MATRIZ, PREVISÃO E PARETO)
    # =========================================================
    st.write("---")
    
    # Preparação de dados cruzados para as novas visões
    v_nomes = df_analise_base["Versão"].unique()
    v_b = next((v for v in v_nomes if any(x in str(v).lower() for x in ['orc', 'budg', 'prev'])), None)
    v_r = next((v for v in v_nomes if 'real' in str(v).lower()), None)

    if v_b and v_r:
        df_cross = df_analise_base.groupby(["Nro_Item Código", "Nome do Projeto", "Área", "Planta", "Versão"])["Val"].sum().unstack(level="Versão").fillna(0).reset_index()
        df_cross["Atraso (USD)"] = df_cross[v_b] - df_cross[v_r]
        df_cross["Atingimento %"] = (df_cross[v_r] / df_cross[v_b] * 100).fillna(0).clip(0, 200)
        
        # PROPOSTA 1: Matriz de Criticidade (Scatter Plot)
        st.subheader("🎯 Proposta 1: Matriz de Criticidade (Projetos Críticos)")
        st.markdown("O quadrante **superior direito** isola de forma visual imediata as iniciativas de **alto valor e com maior desvio orçamentário**.")
        
        fig_scatter = px.scatter(
            df_cross[df_cross[v_b] > 0], 
            x=v_b, y="Atraso (USD)", 
            size=v_b, color="Área",
            hover_name="Nome do Projeto",
            labels={v_b: "Orçamento Planejado (USD)", "Atraso (USD)": "Desvio / Atraso Cumulativo (USD)"},
            height=450
        )
        fig_scatter.update_layout(plot_bgcolor='#f8f9fa', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_scatter, use_container_width=True)
        st.write("---")

        # PROPOSTA 2: Tendência de Fechamento (Run Rate Projeção)
        st.subheader("🔮 Proposta 2: Análise Preditiva de Tendência (Run Rate)")
        n_meses_ytd = m_ord.index(m_lim) + 1
        gasto_medio_mensal = val_real / n_meses_ytd
        proj_fim_ano = val_real + (gasto_medio_mensal * (12 - n_meses_ytd))
        
        df_runrate = pd.DataFrame({
            "Métrica": ["Realizado YTD", "Projeção Final de Ano (Run Rate)", "Budget Anual Total"],
            "Valor": [val_real, proj_fim_ano, val_budg]
        })
        fig_run = px.bar(df_runrate, x="Métrica", y="Valor", text_auto='.2f', color="Métrica", color_discrete_sequence=["#ff2a2a", "#3b7aae", "#343a40"])
        fig_run.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
        fig_run.update_layout(yaxis_tickformat='$', showlegend=False, height=400, plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_run, use_container_width=True)
        st.write("---")

        # PROPOSTA 3: Princípio de Pareto (Concentração do Orçamento)
        st.subheader("📊 Proposta 3: Curva de Pareto de Projetos")
        st.markdown("Identificação visual dos grandes blocos de investimento (Regra dos 80/20).")
        
        df_pareto = df_cross.groupby("Nome do Projeto")[v_b].sum().reset_index().sort_values(by=v_b, ascending=False)
        df_pareto["% Acumulado"] = (df_pareto[v_b].cumsum() / df_pareto[v_b].sum() * 100)
        
        fig_pareto = px.bar(df_pareto.head(15), x="Nome do Projeto", y=v_b, text_auto='.2f', color_discrete_sequence=cor_graficos)
        fig_pareto.update_traces(texttemplate='$%{y:,.0f}', textposition='outside')
        fig_pareto.update_layout(yaxis_tickformat='$', height=450, xaxis_tickangle=-45, plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pareto, use_container_width=True)
    else:
        fig_scatter, fig_run, fig_pareto = None, None, None
# =========================================================
    # 5. TABELA ANALÍTICA COM SEMÁFORO E JUSTIFICATIVAS (CORRIGIDA)
    # =========================================================
    st.write("---")
    st.subheader(f"⚠️ Análise de Desvios: TOP 20 Projetos em Atraso no Desembolso YTD (Até {m_lim})")
    st.markdown("Abaixo estão listados os maiores desvios. A tabela utiliza **alertas visuais** para identificar a criticidade do atraso.")

    if v_b and v_r and v_b in df_cross.columns:
        df_atrasados = df_cross[df_cross["Atraso (USD)"] > 0].copy()
        df_atrasados = df_atrasados.rename(columns={v_b: "Budget YTD", v_r: "Realizado YTD"})
        df_top_20 = df_atrasados.sort_values(by="Atraso (USD)", ascending=False).head(20)
        
        if df_top_20.empty:
            st.success("✅ Nenhum projeto apresenta desembolso atrasado em relação ao Budget para os filtros aplicados.")
        else:
            # Preparação do DataFrame de Exibição
            df_exibicao = df_top_20[["Nro_Item Código", "Nome do Projeto", "Área", "Planta", "Budget YTD", "Realizado YTD", "Atraso (USD)"]].copy()
            
            # --- CAMPO 1: SINALIZADOR VISUAL (SEMÁFORO) ---
            def colorir_semaforo(val):
                if isinstance(val, (int, float)):
                    if val > 100000:    # Crítico: Vermelho
                        return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
                    elif val > 30000:   # Atenção: Amarelo
                        return 'background-color: #fff3cd; color: #856404;'
                    else:               # Tolerável: Verde
                        return 'background-color: #d4edda; color: #155724;'
                return ''

            st.dataframe(
                df_exibicao.style.applymap(colorir_semaforo, subset=["Atraso (USD)"])
                .format({"Budget YTD": "$ {:,.2f}", "Realizado YTD": "$ {:,.2f}", "Atraso (USD)": "$ {:,.2f}"}),
                use_container_width=True,
                hide_index=True
            )
            
            # --- CAMPO 2: CAMPO DE JUSTIFICATIVA EXECUTIVA DINÂMICA ---
            st.write("")
            st.markdown("### 💬 Detalhamento e Justificativa por Iniciativa")
            
            lista_projetos_justificativa = df_exibicao.apply(lambda r: f"{r['Nro_Item Código']} - {r['Nome do Projeto']}", axis=1).tolist()
            projeto_selecionado = st.selectbox("Selecione um projeto crítico para avaliar a justificativa do Site:", lista_projetos_justificativa)
            
            if projeto_selecionado:
                # Extrai o código do projeto selecionado para buscar os dados da linha
                cod_sel = projeto_selecionado.split(" - ")[0]
                row_sel = df_exibicao[df_exibicao["Nro_Item Código"] == cod_sel].iloc[0]
                
                # Definição de uma justificativa inteligente/simulada com base na planta e valor
                # Se sua base do Excel tiver uma coluna de comentários real, substitua essa lógica por: justificativa_real = row_sel['Sua_Coluna']
                atraso_val = row_sel["Atraso (USD)"]
                planta_sel = row_sel["Planta"]
                
                if atraso_val > 100000:
                    status_crit = "🔴 CRÍTICO (Desvio Estr
                    
