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

origem_dados = st.sidebar.radio(
    label="Selecione a fonte dos dados:",
    options=["Usar Última Base (Servidor)", "Fazer Upload de Novo Arquivo (.xlsx)"]
)

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
    df_base.columns = df_base.columns.astype(str).str.strip()
    
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
        elif col_lower in ['ano', 'exercício', 'exercicio', 'ano_base']:
            mapeamento_colunas[col] = "Ano"
            
    df_base = df_base.rename(columns=mapeamento_colunas)

    m_ord = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    colunas_meses_encontradas = [m for m in m_ord if m in df_base.columns]
    
    # Adiciona a coluna Ano aos identificadores se ela existir nativamente na planilha
    colunas_identificadoras = [c for c in ["Nro_Item Código", "Nome do Projeto", "Área", "Planta", "Versão", "Ano"] if c in df_base.columns]

    if colunas_meses_encontradas:
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

df_base = df_base.dropna(subset=["Versão"])

df_base["Versão"] = df_base["Versão"].astype(str).str.strip()
df_base["Mês"] = df_base["Mês"].astype(str).str.strip()
df_base["Planta"] = df_base["Planta"].astype(str).str.strip()
df_base["Área"] = df_base["Área"].astype(str).str.strip()
df_base["Val"] = pd.to_numeric(df_base["Val"], errors='coerce').fillna(0.0)

# Se a planilha tiver uma coluna de Ano, garante o tipo inteiro para a comparação
if "Ano" in df_base.columns:
    df_base["Ano"] = pd.to_numeric(df_base["Ano"], errors='coerce').fillna(0).astype(int)

# ==========================================
# PARTE 3: FILTROS CORPORATIVOS DINÂMICOS
# ==========================================
st.sidebar.write("---")
st.sidebar.header("🎛️ Painel de Controle Regional")

anos_disponiveis = [2026, 2025]
ano_s = st.sidebar.selectbox("Ano Base Orçamentário", anos_disponiveis)

meses_existentes = [m for m in m_ord if m in df_base["Mês"].unique()]
if not meses_existentes:
    meses_existentes = ["Jan"]
m_lim = st.sidebar.selectbox("Visão Acumulada (YTD) Até:", meses_existentes, index=len(meses_existentes)-1)

idx_limite = m_ord.index(m_lim)
meses_ytd = m_ord[:idx_limite + 1]

plantas_disponiveis = sorted(df_base["Planta"].unique().tolist())
plantas_sel = st.sidebar.multiselect("Sites / Plantas", plantas_disponiveis, default=plantas_disponiveis)

areas_disponiveis = sorted(df_base["Área"].unique().tolist())
areas_sel = st.sidebar.multiselect("Áreas de Negócio", areas_disponiveis, default=areas_disponiveis)

# ==========================================
# PARTE 4: PROCESSAMENTO FINANCEIRO CORE
# ==========================================

# 1. EXPURGO DE LINHAS DE TOTAIS
palavras_chave_total = ['total', 'subtotal', 'soma', 'consolidado', 'summary']
df_base = df_base[
    ~df_base["Nome do Projeto"].astype(str).str.lower().str.contains('|'.join(palavras_chave_total)) &
    ~df_base["Nro_Item Código"].astype(str).str.lower().str.contains('|'.join(palavras_chave_total))
]

# 2. FILTRAGEM DO ESCOPO SELECIONADO NA TELA (Mês YTD + Planta + Área + CORREÇÃO DO ANO)
if "Ano" in df_base.columns and df_base["Ano"].max() > 0:
    filtro_ano = (df_base["Ano"] == int(ano_s))
else:
    filtro_ano = True

df_f = df_base[
    filtro_ano &
    (df_base["Mês"].isin(meses_ytd)) &
    (df_base["Planta"].isin(plantas_sel)) &
    (df_base["Área"].isin(areas_sel))
].copy()

df_analise_base = df_base[
    filtro_ano &
    (df_base["Planta"].isin(plantas_sel)) &
    (df_base["Área"].isin(areas_sel))
].copy()

# 3. MAPEAMENTO RESTRITO POR ELIMINAÇÃO (BLINDAGEM CONTRA DUPLICAÇÃO)
v_nomes = df_f["Versão"].unique()

# A. Identifica o Budget
v_b = next((v for v in v_nomes if any(x in str(v).lower() for x in ['budget', 'orcamento', 'orçamento', 'previsto'])), None)
if not v_b:
    v_b = next((v for v in v_nomes if 'orc' in str(v).lower() or 'bud' in str(v).lower()), None)

# B. Identifica o Fcast 2+10
v_f = next((v for v in v_nomes if any(x in str(v).lower() for x in ['fcast', '2+10', 'forecast', 'fore'])), None)

# C. Identifica o Realizado por Eliminação Absoluta
v_r = next((v for v in v_nomes if v != v_b and v != v_f), None)

if not v_r:
    v_r = next((v for v in v_nomes if any(x in str(v).lower() for x in ['real', 'realizado', 'efetivado'])), None)

# Cálculo final dos KPIs macros com isolamento de ano e mês aplicados
val_budg = df_f[df_f["Versão"] == v_b]["Val"].sum() if v_b else 0.0
val_fcast = df_f[df_f["Versão"] == v_f]["Val"].sum() if v_f else 0.0
val_real = df_f[df_f["Versão"] == v_r]["Val"].sum() if v_r else 0.0

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
cor_graficos = ["#a11f1f"]

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

fig_ev = px.line
