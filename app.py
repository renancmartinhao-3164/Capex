import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# Configuração da página do Streamlit
st.set_page_config(page_title="Dashboard de Capex Executivo", layout="wide")

# ==========================================
# PARTE 1: CARREGAMENTO DOS DADOS (HÍBRIDO)
# ==========================================
st.sidebar.header("📂 Origem dos Dados de Capex")

# Opção para o usuário escolher como deseja carregar a base
origem_dados = st.sidebar.radio(
    label="Selecione a fonte dos dados:",
    options=["Usar Última Base (Servidor)", "Fazer Upload de Novo Arquivo (.xlsx)"]
)

# Nome do arquivo padrão que fica salvo no servidor/repositório
ARQUIVO_PADRAO = "seus_dados_capex.xlsx"

@st.cache_data
def carregar_dados_excel(file_path_or_buffer):
    return pd.read_excel(file_path_or_buffer)

df_base = None

if origem_dados == "Usar Última Base (Servidor)":
    if os.path.exists(ARQUIVO_PADRAO):
        try:
            df_base = carregar_dados_excel(ARQUIVO_PADRAO)
            st.sidebar.success("Base padrão carregada!")
        except Exception as e:
            st.sidebar.error(f"Erro ao ler a base padrão: {e}")
            st.stop()
    else:
        st.title("📊 Gestão Estratégica de Investimentos Capex")
        st.error(f"⚠️ O arquivo padrão `{ARQUIVO_PADRAO}` não foi encontrado no servidor.")
        st.info("Mude a opção na barra lateral para **'Fazer Upload de Novo Arquivo'** ou insira o arquivo no repositório.")
        st.stop()
else:
    arquivo_publicado = st.sidebar.file_uploader(
        label="Suba o arquivo Excel de Capex (.xlsx)",
        type=["xlsx"]
    )
    if arquivo_publicado is not None:
        try:
            df_base = carregar_dados_excel(arquivo_publicado)
            st.sidebar.success("✅ Novo arquivo processado!")
        except Exception as e:
            st.sidebar.error(f"Erro ao ler o arquivo enviado: {e}")
            st.stop()
    else:
        st.title("📊 Gestão Estratégica de Investimentos Capex")
        st.info("👋 Aguardando importação. Por favor, faça o upload do seu arquivo Excel (.xlsx) na barra lateral esquerda.")
        st.stop()

# =========================================================
# PARTE 2: PADRONIZAÇÃO E DESPIVOTEAMENTO (HORIZONTAl -> VERTICAL)
# =========================================================
if df_base is not None:
    # 1. Remove espaços invisíveis dos nomes das colunas originais
    df_base.columns = df_base.columns.astype(str).str.strip()
    
    # 2. Mapeamento inteligente de colunas fixas para tolerar variações de escrita
    mapeamento_colunas = {}
    for col in df_base.columns:
        col_lower = col.lower()
        if col_lower in ['versão', 'versao', 'cenário', 'cenario', 'tipo', 'cenarios', 'versoes']:
            mapeamento_colunas[col] = "Versão"
        elif col_lower in ['planta', 'site', 'unidade', 'filial', 'plantas', 'sites']:
            mapeamento_colunas[col] = "Planta"
        elif col_lower in ['área', 'area', 'diretoria', 'setor', 'áreas', 'areas']:
            mapeamento_colunas[col] = "Área"
        elif col_lower in ['nro_item código', 'código', 'codigo', 'id', 'item', 'wbs']:
            mapeamento_colunas[col] = "Nro_Item Código"
        elif col_lower in ['nome do projeto', 'projeto', 'nome', 'descrição', 'descricao']:
            mapeamento_colunas[col] = "Nome do Projeto"
            
    df_base = df_base.rename(columns=mapeamento_colunas)

    # Lista de meses cronológicos esperados como colunas horizontais a partir da coluna O
    m_ord = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    colunas_meses_encontradas = [m for m in m_ord if m in df_base.columns]
    colunas_identificadoras = [c for c in ["Nro_Item Código", "Nome do Projeto", "Área", "Planta", "Versão"] if c in df_base.columns]

    if colunas_meses_encontradas:
        # Transforma a estrutura horizontal (meses em colunas) em formato vertical de banco de dados
        df_base = pd.melt(
            df_base,
            id_vars=colunas_identificadoras,
            value_vars=colunas_meses_encontradas,
            var_name="Mês",
            value_name="Val"
        )
    else:
        st.title("📊 Gestão Estratégica de Investimentos Capex")
        st.error("⚠️ Nenhuma coluna de mês (Jan, Fev, Mar...) foi detectada no arquivo Excel.")
        st.stop()

# Validação final de consistência estrutural
colunas_obrigatorias = ["Nro_Item Código", "Nome do Projeto", "Área", "Planta", "Versão", "Mês", "Val"]
df_base = df_base.dropna(subset=["Versão"])  # Elimina linhas totalmente nulas

# Tratamento seguro de tipos de dados e strings
df_base["Versão"] = df_base["Versão"].astype(str).str.strip()
df_base["Mês"] = df_base["Mês"].astype(str).str.strip()
df_base["Planta"] = df_base["Planta"].astype(str).str.strip()
df_base["Área"] = df_base["Área"].astype(str).str.strip()

# Conversão numérica forçada: células com texto ou vazias viram 0.0, prevenindo inflação nas somas
df_base["Val"] = pd.to_numeric(df_base["Val"], errors='coerce').fillna(0.0)

# ==========================================
# PARTE 3: FILTROS CORPORATIVOS DINÂMICOS
# ==========================================
st.sidebar.write("---")
st.sidebar.header("🎛️ Painel de Controle Regional")

# 1. Filtro de Ano Base
anos_disponiveis = [2026, 2025]
ano_s = st.sidebar.selectbox("Ano Base Orçamentário", anos_disponiveis)

# 2. Filtro de Mês Limite (Visão YTD Acumulada)
meses_existentes = [m for m in m_ord if m in df_base["Mês"].unique()]
if not meses_existentes:
    meses_existentes = ["Jan"]
m_lim = st.sidebar.selectbox("Visão Acumulada (YTD) Até:", meses_existentes, index=len(meses_existentes)-1)

idx_limite = m_ord.index(m_lim)
meses_ytd = m_ord[:idx_limite + 1]

# 3. Filtros de Escopo (Lidos diretamente dos dados importados)
plantas_disponiveis = sorted(df_base["Planta"].unique().tolist())
plantas_sel = st.sidebar.multiselect("Sites / Plantas", plantas_disponiveis, default=plantas_disponiveis)

areas_disponiveis = sorted(df_base["Área"].unique().tolist())
areas_sel = st.sidebar.multiselect("Áreas de Negócio", areas_disponiveis, default=areas_disponiveis)

# ==========================================
# PARTE 4: PROCESSAMENTO FINANCEIRO CORE
# ==========================================

# 1. EXPURGO CRÍTICO DE LINHAS DE TOTAIS DA PLANILHA (Previne duplicações de valores no Pandas)
palavras_chave_total = ['total', 'subtotal', 'soma', 'consolidado', 'summary']
df_base = df_base[
    ~df_base["Nome do Projeto"].astype(str).str.lower().str.contains('|'.join(palavras_chave_total)) &
    ~df_base["Nro_Item Código"].astype(str).str.lower().str.contains('|'.join(palavras_chave_total))
]

# 2. FILTRAGEM DO ESCOPO SELECIONADO NA TELA (YTD + Escopo)
df_f = df_base[
    (df_base["Mês"].isin(meses_ytd)) &
    (df_base["Planta"].isin(plantas_sel)) &
    (df_base["Área"].isin(areas_sel))
].copy()

# Base total para análises de projetos que dependem do ano cheio
df_analise_base = df_base[
    (df_base["Planta"].isin(plantas_sel)) &
    (df_base["Área"].isin(areas_sel))
].copy()

# 3. MAPEAMENTO EXATO E DE PARIDADE COM OS CENÁRIOS CORPORATIVOS
v_nomes = df_f["Versão"].unique()

# Identificação precisa baseada na sua nomenclatura real
v_b = next((v for v in v_nomes if any(x in str(v).lower() for x in ['budget', 'orcamento', 'orçamento', 'previsto'])), None)
if not v_b:
    v_b = next((v for v in v_nomes if 'orc' in str(v).lower() or 'bud' in str(v).lower()), None)

# Força o Realizado a ignorar sumariamente qualquer menção que contenha a palavra "cast" (Fcast 2+10)
v_r = next((v for v in v_nomes if any(x in str(v).lower() for x in ['real', 'realizado', 'efetivado']) and 'cast' not in str(v).lower()), None)

# Captura o cenário de Projeções (Fcast 2+10) com precisão
v_f = next((v for v in v_nomes if any(x in str(v).lower() for x in ['fcast', 'fore', 'forecast', 'proj'])), None)

# Cálculo final limpo dos KPIs macros exibidos na tela (sem sobreposição)
val_budg = df_f[df_f["Versão"] == v_b]["Val"].sum() if v_b else 0.0
val_real = df_f[df_f["Versão"] == v_r]["Val"].sum() if v_r else 0.0
val_fcast = df_f[df_f["Versão"] == v_f]["Val"].sum() if v_f else 0.0

# Renderização do cabeçalho principal do painel
st.title("📊 Gestão Estratégica de Investimentos Capex")
st.markdown(f"**Escopo:** Região América do Sul | **Período:** Jan a {m_lim} de {ano_s} *(Visão Acumulada YTD)*")
st.write("---")

# Exibição dos Cartões de KPI de Alto Nível
col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
with col_kpi1:
    st.metric(label="Realizado Acumulado YTD", value=f"USD {val_real:,.2f}")
with col_kpi2:
    st.metric(label="Budget Original YTD", value=f"USD {val_budg:,.2f}")
with col_kpi3:
    st.metric(label="Forecast Projetado YTD", value=f"USD {val_fcast:,.2f}")

# ==========================================
# PARTE 5: VISUALIZAÇÕES GRÁFICAS STANDARD
# ==========================================
st.write("---")
cor_graficos = ["#a11f1f"]  # Tom vermelho corporativo

# 1. Comparativo Geral de Versões
st.subheader(f"📊 Comparativo Geral Capex YTD (Jan a {m_lim}) - USD")
fig_main = px.bar(df_f.groupby("Versão")["Val"].sum().reset_index(), x="Versão", y="Val", color_discrete_sequence=cor_graficos, text_auto='.2f')
fig_main.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
fig_main.update_layout(yaxis_tickformat='$', height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
st.plotly_chart(fig_main, use_container_width=True)

st.write("---")

# 2. Cenários Agrupados por Área de Projeto
st.subheader("📊 Cenários por Tipo de Categoria de Projeto (Budget vs Forecast vs Realizado)")
df_proj_ver = df_f.groupby(["Área", "Versão"])["Val"].sum().reset_index()
fig_p = px.bar(df_proj_ver, x="Área", y="Val", color="Versão", barmode="group", text_auto='.2f')
fig_p.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
fig_p.update_layout(yaxis_tickformat='$', xaxis_title="Tipo / Área de Projeto", legend_title="Cenário", xaxis={'categoryorder':'total descending'}, height=450, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
st.plotly_chart(fig_p, use_container_width=True)
    
st.write("---")

# 3. Distribuição Volumétrica por Planta
st.subheader("🏢 Distribuição Total de Recursos por Site (Plantas)")
fig_pl = px.bar(df_f.groupby("Planta")["Val"].sum().reset_index().sort_values("Val", ascending=False), x="Planta", y="Val", color_discrete_sequence=cor_graficos, text_auto='.2f')
fig_pl.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
fig_pl.update_layout(yaxis_tickformat='$', showlegend=False, xaxis_title="Site Planta", height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
st.plotly_chart(fig_pl, use_container_width=True)

st.write("---")

# 4. Evolução Temporal Mensal
st.subheader("📈 Evolução Mensal Temporal dos Desembolsos")
df_ev = df_f.groupby(["Mês", "Versão"])["Val"].sum().reset_index()
df_ev['Idx'] = df_ev['Mês'].map({m: i for i, m in enumerate(m_ord)})
df_ev_sorted = df_ev.sort_values('Idx')
df_ev_sorted['Label_Txt'] = df_ev_sorted['Val'].map(lambda x: f"${x:,.0f}")

fig_ev = px.line(df_ev_sorted, x="Mês", y="Val", color="Versão", markers=True, text="Label_Txt")
fig_ev.update_traces(textposition='top center')
fig_ev.update_layout(yaxis_tickformat='$', height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
st.plotly_chart(fig_ev, use_container_width=True)

# =========================================================
# PARTE 6: GRÁFICOS AVANÇADOS (MATRIZ, PREVISÃO, PARETO)
# =========================================================
st.write("---")

if v_b and v_r:
    df_cross = df_analise_base.groupby(["Nro_Item Código", "Nome do Projeto", "Área", "Planta", "Versão"])["Val"].sum().unstack(level="Versão").fillna(0).reset_index()
    df_cross["Atraso (USD)"] = df_cross[v_b] - df_cross[v_r]
    df_cross["Atingimento %"] = (df_cross[v_r] / df_cross[v_b] * 100).fillna(0).clip(0, 200)
    
    # 1. Matriz de Criticidade (Scatter Plot)
    st.subheader("🎯 Matriz de Alocação e Criticidade de Desvios")
    st.markdown("O quadrante **superior direito** isola os projetos de alto valor com maiores desvios.")
    fig_scatter = px.scatter(
        df_cross[df_cross[v_b] > 0], x=v_b, y="Atraso (USD)", size=v_b, color="Área", hover_name="Nome do Projeto",
        labels={v_b: "Budget Original Aprovado (USD)", "Atraso (USD)": "Desvio / Atraso Cumulativo (USD)"}, height=450
    )
    fig_scatter.update_layout(plot_bgcolor='#f8f9fa', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_scatter, use_container_width=True)
    st.write("---")

    # 2. Tendência de Fechamento (Run Rate Preditivo)
    st.subheader("🔮 Análise Preditiva de Fechamento (Run Rate Anual)")
    n_meses_ytd = m_ord.index(m_lim) + 1
    gasto_medio_mensal = val_real / n_meses_ytd
    proj_fim_ano = val_real + (gasto_medio_mensal * (12 - n_meses_ytd))
    
    df_runrate = pd.DataFrame({
        "Métrica de Fechamento": ["Realizado YTD", "Projeção Final de Ano (Run Rate)", "Budget Anual Planejado"],
        "Valor (USD)": [val_real, proj_fim_ano, val_budg]
    })
    fig_run = px.bar(df_runrate, x="Métrica de Fechamento", y="Valor (USD)", text_auto='.2f', color="Métrica de Fechamento", color_discrete_sequence=["#ff2a2a", "#3b7aae", "#343a40"])
    fig_run.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
    fig_run.update_layout(yaxis_tickformat='$', showlegend=False, height=400, plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_run, use_container_width=True)
    st.write("---")

    # 3. Princípio de Pareto (Concentração do Orçamento)
    st.subheader("📊 Concentração de Linhas de Investimento (Pareto TOP 15)")
    df_pareto = df_cross.groupby("Nome do Projeto")[v_b].sum().reset_index().sort_values(by=v_b, ascending=False)
    df_pareto["% Acumulado"] = (df_pareto[v_b].cumsum() / df_pareto[v_b].sum() * 100)
    
    fig_pareto = px.bar(df_pareto.head(15), x="Nome do Projeto", y=v_b, text_auto='.2f', color_discrete_sequence=cor_graficos)
    fig_pareto.update_traces(texttemplate='$%{y:,.0f}', textposition='outside')
    fig_pareto.update_layout(yaxis_tickformat='$', height=450, xaxis_tickangle=-45, plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_pareto, use_container_width=True)
else:
    fig_scatter, fig_run, fig_pareto = None, None, None

# =========================================================
# PARTE 7: TABELA ANALÍTICA DE ATRASOS (TOP 20)
# =========================================================
st.write("---")
st.subheader(f"⚠️ Análise de Desvios Críticos: TOP 20 Projetos em Atraso YTD (Até {m_lim})")

if v_b and v_r and v_b in df_cross.columns:
    df_atrasados = df_cross[df_cross["Atraso (USD)"] > 0].copy()
    df_atrasados = df_atrasados.rename(columns={v_b: "Budget YTD", v_r: "Realizado YTD"})
    df_top_20 = df_atrasados.sort_values(by="Atraso (USD)", ascending=False).head(20)
    
    if df_top_20.empty:
        st.success("✅ Nenhum projeto apresenta desembolso atrasado em relação ao Budget para os filtros aplicados.")
    else:
        df_exibicao = df_top_20[["Nro_Item Código", "Nome do Projeto", "Área", "Planta", "Budget YTD", "Realizado YTD", "Atraso (USD)"]].copy()
        total_b = df_top_20["Budget YTD"].sum()
        total_r = df_top_20["Realizado YTD"].sum()
        total_a = df_top_20["Atraso (USD)"].sum()
        
        linha_total = pd.DataFrame([{
            "Nro_Item Código": "TOTAL DO TOP 20", "Nome do Projeto": "---", "Área": "---", "Planta": "---",
            "Budget YTD": total_b, "Realizado YTD": total_r, "Atraso (USD)": total_a
        }])
        
        df_exibicao_com_total = pd.concat([df_exibicao, linha_total], ignore_index=True)
        for col in ["Budget YTD", "Realizado YTD", "Atraso (USD)"]:
            df_exibicao_com_total[col] = df_exibicao_com_total[col].map(lambda x: f"$ {x:,.2f}")
        
        st.dataframe(df_exibicao_com_total, use_container_width=True, hide_index=True)

# ==========================================
# PARTE 8: EXPORTAÇÃO EXECUTIVA (PDF/HTML)
# ==========================================
st.write("---")
st.subheader("🖨️ Exportação Completa para Diretoria")
st.markdown("Clique no botão abaixo para gerar o report consolidado completo contendo todas as visões.")

try:
    chart_main_html = fig_main.to_html(full_html=False, include_plotlyjs='cdn')
    chart_p_html = fig_p.to_html(full_html=False, include_plotlyjs='cdn')
    chart_pl_html = fig_pl.to_html(full_html=False, include_plotlyjs='cdn')
    chart_ev_html = fig_ev.to_html(full_html=False, include_plotlyjs='cdn')
    
    chart_scatter_html = fig_scatter.to_html(full_html=False, include_plotlyjs='cdn') if fig_scatter else ""
    chart_run_html = fig_run.to_html(full_html=False, include_plotlyjs='cdn') if fig_run else ""
    chart_pareto_html = fig_pareto.to_html(full_html=False, include_plotlyjs='cdn') if fig_pareto else ""

    html_report = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Report Executivo de Capex</title>
        <style>
            * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
            @media print {{ body {{ background: #fff; }} .report-wrapper {{ border: none !important; box-shadow: none !important; padding: 0 !important; max-width: 100% !important; }} }}
            @page {{ size: A4; margin: 20mm 15mm 20mm 15mm; }}
            body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #2b2b2b; margin: 0; padding: 20px; background-color: #fafafa; }}
            .report-wrapper {{ max-width: 900px; margin: 0 auto; background: #fff; padding: 40px; border: 1px solid #e0e0e0; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
            .header {{ border-bottom: 3px solid #a11f1f; padding-bottom: 12px; margin-bottom: 25px; }}
            .title {{ font-size: 20pt; font-weight: bold; color: #a11f1f; text-transform: uppercase; letter-spacing: 0.5px; }}
            .subtitle {{ font-size: 11pt; color: #555; margin-top: 5px; font-weight: 500; }}
            h2 {{ font-size: 13pt; color: #1a1a1a; margin: 35px 0 15px 0; padding-left: 8px; border-left: 4px solid #a11f1f; text-transform: uppercase; page-break-after: avoid; }}
            p {{ font-size: 10pt; color: #444; margin-bottom: 12px; text-align: justify; }}
            table.kpi-table {{ width: 100%; border-collapse: separate; border-spacing: 12px 0; margin: 15px -12px; }}
            td.kpi-card {{ width: 33.33%; background-color: #f8f9fa !important; border: 1px solid #e9ecef; border-radius: 6px; padding: 14px; vertical-align: top; border-left: 4px solid #a11f1f !important; }}
            .chart-box {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 15px; margin-bottom: 30px; page-break-inside: avoid; }}
            table.data-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; page-break-inside: avoid; }}
            table.data-table th {{ background-color: #343a40 !important; color: white !important; padding: 10px; font-size: 9pt; text-transform: uppercase; border: 1px solid #343a40; }}
            table.data-table td {{ padding: 8px 10px; border: 1px solid #dee2e6; font-size: 9pt; }}
            table.data-table tr:nth-child(even) {{ background-color: #f8f9fa !important; }}
            table.data-table tr.total-row {{ background-color: #e9ecef !important; font-weight: bold; }}
            .numeric {{ text-align: right; }}
            .negative {{ color: #c9302c; font-weight: bold; }}
            .footer-notice {{ margin-top: 40px; font-size: 8pt; color: #999; text-align: center; border-top: 1px solid #eee; padding-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="report-wrapper">
            <div class="header">
                <div class="title">Capex - Status Corporativo Global</div>
                <div class="subtitle">Book Executivo Consolidado — América do Sul — Ano Base {ano_s} (YTD até {m_lim})</div>
            </div>

            <p>Este relatório oficial reflete a compilação de investimentos de ativos imobilizados das plantas de manufatura da região, detalhando os desvios e horizontes preditivos.</p>

            <table class="kpi-table">
                <tr>
                    <td class="kpi-card"><div style="font-size:8pt;color:#6c757d;font-weight:bold;text-transform:uppercase;">REALIZADO YTD</div><div style="font-size:14pt;font-weight:bold;margin-top:4px;">$ {val_real:,.2f}</div></td>
                    <td class="kpi-card" style="border-left-color: #0066cc !important;"><div style="font-size:8pt;color:#6c757d;font-weight:bold;text-transform:uppercase;">BUDGET YTD</div><div style="font-size:14pt;font-weight:bold;margin-top:4px;">$ {val_budg:,.2f}</div></td>
                    <td class="kpi-card" style="border-left-color: #3b7aae !important;"><div style="font-size:8pt;color:#6c757d;font-weight:bold;text-transform:uppercase;">FORECAST (2+10)</div><div style="font-size:14pt;font-weight:bold;margin-top:4px;">$ {val_fcast:,.2f}</div></td>
                </tr>
            </table>

            <h2>1. Evolução e Sumário por Estruturas e Sites</h2>
            <div class="chart-box">{chart_main_html}</div>
            <div class="chart-box">{chart_p_html}</div>
            <div class="chart-box">{chart_pl_html}</div>
            <div class="chart-box">{chart_ev_html}</div>

            <h2>2. Matriz de Alocação e Criticidade de Desvios</h2>
            <div class="chart-box">{chart_scatter_html}</div>

            <h2>3. Análise Preditiva de Fechamento (Run Rate Anual)</h2>
            <div class="chart-box">{chart_run_html}</div>

            <h2>4. Concentração de Linhas de Investimento (Pareto Top 15)</h2>
            <div class="chart-box">{chart_pareto_html}</div>

            <h2>5. Análise Mapeada de Desvios Críticos: TOP 20 Projetos</h2>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Item</th><th>Nome do Projeto</th><th>Área</th><th>Planta</th>
                        <th class="numeric">Budget YTD</th><th class="numeric">Realizado YTD</th><th class="numeric">Atraso</th>
                    </tr>
                </thead>
                <tbody>
    """

    if 'df_top_20' in locals() and not df_top_20.empty:
        for _, r in df_top_20.iterrows():
            html_report += f"""
                <tr>
                    <td>{r['Nro_Item Código']}</td><td>{r['Nome do Projeto']}</td><td>{r['Área']}</td><td>{r['Planta']}</td>
                    <td class="numeric">$ {r['Budget YTD']:,.2f}</td><td class="numeric">$ {r['Realizado YTD']:,.2f}</td>
                    <td class="numeric negative">$ {r['Atraso (USD)']:,.2f}</td>
                </tr>
            """
        html_report += f"""
                <tr class="total-row">
                    <td>TOTAL TOP 20</td><td>---</td><td>---</td><td>---</td>
                    <td class="numeric">$ {total_b:,.2f}</td><td class="numeric">$ {total_r:,.2f}</td>
                    <td class="numeric negative">$ {total_a:,.2f}</td>
                </tr>
        """
    else:
        html_report += """<tr><td colspan="7" style="text-align:center;">Nenhum desvio crítico registrado para o período.</td></tr>"""

    html_report += f"""
                </tbody>
            </table>
            <div class="footer-notice">
                Sistema de Relatórios de Manufatura — Gerado em {datetime.now().strftime("%d/%m/%Y")} — Altamente Confidencial
            </div>
        </div>
    </body>
    </html>
    """

    st.download_button(
        label="📥 Baixar Livro Executivo Ampliado (PDF/HTML)",
        data=html_report,
        file_name=f"Book_Executivo_Capex_{m_lim}_{ano_s}.html",
        mime="text/html"
    )
except Exception as err_pdf:
    st.sidebar.error(f"Erro ao injetar gráficos na exportação: {err_pdf}")

# EXPANDER DE SEGURANÇA (DADOS BRUTOS VERTICALIZADOS)
with st.expander("🔍 Ver Tabela de Dados Brutos"):
    if 'df_f' in locals() and not df_f.empty:
        df_view = df_f.copy()
        df_view['Val'] = df_view['Val'].map(lambda x: f"$ {x:,.2f}")
        st.dataframe(df_view, use_container_width=True)
    else:
        st.info("Nenhum dado bruto encontrado para os filtros selecionados.")
        
