import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import base64

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

ARQUIVO_PADRAO = "SA_CAPEX 2026_v1.xlsx"
ARQUIVO_LOGO = "logo.jpg" 

@st.cache_data
def carregar_dados_excel(file_path_or_buffer):
    return pd.read_excel(file_path_or_buffer)

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

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
# PARTE 2: PADRONIZAÇÃO E DESPIVOTEAMENTO (FIX FINAL)
# =========================================================
if df_base is not None:

    df_base.columns = df_base.columns.astype(str).str.strip()

    mapeamento_colunas = {}

    for col in df_base.columns:
        col_lower = col.lower().strip()

        if any(x in col_lower for x in ['versão', 'versao']):
            mapeamento_colunas[col] = "Versão"

        elif any(x in col_lower for x in ['planta', 'site']):
            mapeamento_colunas[col] = "Planta"

        elif any(x in col_lower for x in ['área', 'area']):
            mapeamento_colunas[col] = "Área"

        elif any(x in col_lower for x in ['codigo', 'código', 'id']):
            mapeamento_colunas[col] = "Nro_Item Código"

        elif any(x in col_lower for x in ['projeto', 'nome']):
            mapeamento_colunas[col] = "Nome do Projeto"

        elif any(x in col_lower for x in ['ano']):
            mapeamento_colunas[col] = "Ano"

        elif any(x in col_lower for x in ['responsável', 'responsavel']):
            mapeamento_colunas[col] = "Responsável"

        # NÃO mapear status aqui → vamos tratar separado

    df_base = df_base.rename(columns=mapeamento_colunas)

    # ✅ prioridade Status CER
    if "Status CER" in df_base.columns:
        df_base["Status"] = df_base["Status CER"]
    elif "Status" not in df_base.columns:
        df_base["Status"] = "Não Informado"

    # ✅ remover duplicadas (ESSENCIAL)
    df_base = df_base.loc[:, ~df_base.columns.duplicated()]

    # ✅ garantir colunas
    if "Responsável" not in df_base.columns:
        df_base["Responsável"] = "Não Informado"

    if "Planta" not in df_base.columns:
        df_base["Planta"] = "Não Informado"

    if "Área" not in df_base.columns:
        df_base["Área"] = "Não Informado"

    # ✅ limpeza
    df_base["Status"] = df_base["Status"].astype(str).str.strip().replace("", "Não Informado")

    # ===================================
    # MÊS
    # ===================================
    m_ord = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
    colunas_meses_encontradas = [m for m in m_ord if m in df_base.columns]

    colunas_identificadoras = [
        c for c in [
            "Nro_Item Código","Nome do Projeto","Área",
            "Planta","Versão","Ano","Responsável","Status"
        ] if c in df_base.columns
    ]

    if colunas_meses_encontradas:
        df_base = pd.melt(
            df_base,
            id_vars=colunas_identificadoras,
            value_vars=colunas_meses_encontradas,
            var_name="Mês",
            value_name="Val"
        )
    else:
        st.error("⚠️ Nenhuma coluna de mês detectada.")
        st.stop()

# ✅ limpeza final
df_base["Status"] = df_base["Status"].replace(["nan","None",""], "Não Informado")
df_base["Val"] = pd.to_numeric(df_base["Val"], errors='coerce').fillna(0.0)

# ==========================================
# PARTE 3: FILTROS CORPORATIVOS DINÂMICOS
# ==========================================
st.sidebar.write("---")
st.sidebar.header("🎛️ Painel de Controle Regional")

anos_disponiveis = sorted(list(df_base["Ano"].unique())) if "Ano" in df_base.columns else [2026, 2025]
if 0 in anos_disponiveis: anos_disponiveis.remove(0)
ano_s = st.sidebar.selectbox("Ano Base Orçamentário", anos_disponiveis, index=0)

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
palavras_chave_total = ['total', 'subtotal', 'soma', 'consolidado', 'summary']
df_base = df_base[
    ~df_base["Nome do Projeto"].astype(str).str.lower().str.contains('|'.join(palavras_chave_total)) &
    ~df_base["Nro_Item Código"].astype(str).str.lower().str.contains('|'.join(palavras_chave_total))
]

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

v_nomes = df_f["Versão"].unique()

v_b = next((v for v in v_nomes if any(x in str(v).lower() for x in ['budget', 'orcamento', 'orçamento', 'previsto'])), None)
if not v_b:
    v_b = next((v for v in v_nomes if 'orc' in str(v).lower() or 'bud' in str(v).lower()), None)

v_f = next((v for v in v_nomes if any(x in str(v).lower() for x in ['fcast', '2+10', 'forecast', 'fore'])), None)

v_r = next((v for v in v_nomes if v != v_b and v != v_f), None)
if not v_r:
    v_r = next((v for v in v_nomes if any(x in str(v).lower() for x in ['real', 'realizado', 'efetivado'])), None)

val_budg = df_f[df_f["Versão"] == v_b]["Val"].sum() if v_b else 0.0
val_fcast = df_f[df_f["Versão"] == v_f]["Val"].sum() if v_f else 0.0
val_real = df_f[df_f["Versão"] == v_r]["Val"].sum() if v_r else 0.0

# --- CÁLCULO DAS VARIAÇÕES ---
var_budg_usd = val_real - val_budg
pct_budg = (var_budg_usd / val_budg * 100) if val_budg > 0 else 0.0

var_fcast_usd = val_real - val_fcast
pct_fcast = (var_fcast_usd / val_fcast * 100) if val_fcast > 0 else 0.0

# --- NOVO SISTEMA DINÂMICO DE CORES EXECUTIVAS ---
CINZA_BUDGET = "#808080"
PRETO_FORECAST = "#000000"
VERDE_REALIZADO = "#056608"  # Verde Escuro (Acima do Forecast)
VERMELHO_REALIZADO = "#8B0000"  # Vermelho Escuro (Abaixo do Forecast)

# Mapeamento estático inicial para Budget e Forecast
MAPA_CORES_CENARIO = {}
if v_b: MAPA_CORES_CENARIO[v_b] = CINZA_BUDGET
if v_f: MAPA_CORES_CENARIO[v_f] = PRETO_FORECAST

# Determinação da cor do realizado global baseado nas métricas acumuladas totais
cor_realizado_global = VERDE_REALIZADO if val_real >= val_fcast else VERMELHO_REALIZADO
if v_r: MAPA_CORES_CENARIO[v_r] = cor_realizado_global

# Configuração dos cards executivos
if var_budg_usd < 0:
    bg_card_b = "#fce8e6"      
    cor_texto_b = "#dc3545"    
    seta_b = "↓"               
else:
    bg_card_b = "#e6f4ea"      
    cor_texto_b = "#28a745"    
    seta_b = "↑"               

if var_fcast_usd < 0:
    bg_card_f = "#fce8e6"      
    cor_texto_f = "#dc3545"    
    seta_f = "↓"               
else:
    bg_card_f = "#e6f4ea"      
    cor_texto_f = "#28a745"    
    seta_f = "↑"               

col_logo_header, col_title_header = st.columns([1, 6])
with col_logo_header:
    if os.path.exists(ARQUIVO_LOGO):
        st.image(ARQUIVO_LOGO, width=120)
    else:
        st.warning("⚠️ Logo ausente.")

with col_title_header:
    st.title("📊 Gestão Estratégica de Investimentos Capex")
    st.markdown(f"**Escopo:** Região América do Sul | **Período:** Jan a {m_lim} de {ano_s} *(Visão Acumulada YTD)*")

st.write("---")

# --- CARTOES DE MÉTRICAS EXECUTIVOS ---
col_kpi1, col_kpi2, col_kpi3 = st.columns(3)

with col_kpi1:
    st.markdown(f"""
        <div style="background-color: #f8f9fa; border: 1px solid #e9ecef; border-left: 5px solid {cor_realizado_global}; border-radius: 6px; padding: 16px; min-height: 100px;">
            <div style="font-size: 10pt; color: #555555; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;">Realizado Acumulado YTD</div>
            <div style="font-size: 18pt; font-weight: bold; color: {cor_realizado_global}; margin-top: 6px;">USD {val_real:,.2f}</div>
            <div style="font-size: 9.5pt; color: #777777; margin-top: 4px;">Execução com base nas metas de Forecast</div>
        </div>
    """, unsafe_allow_html=True)

with col_kpi2:
    st.markdown(f"""
        <div style="background-color: {bg_card_b}; border: 1px solid #e9ecef; border-left: 5px solid {cor_texto_b}; border-radius: 6px; padding: 16px; min-height: 100px;">
            <div style="font-size: 10pt; color: #555555; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;">Budget Original YTD</div>
            <div style="font-size: 18pt; font-weight: bold; color: #1a1a1a; margin-top: 6px;">USD {val_budg:,.2f}</div>
            <div style="font-size: 10pt; font-weight: bold; color: {cor_texto_b}; margin-top: 4px; display: flex; align-items: center;">
                <span style="font-size: 12pt; margin-right: 4px;">{seta_b}</span> Var: USD {var_budg_usd:,.2f} ({pct_budg:+.2f}%)
            </div>
        </div>
    """, unsafe_allow_html=True)

with col_kpi3:
    st.markdown(f"""
        <div style="background-color: {bg_card_f}; border: 1px solid #e9ecef; border-left: 5px solid {cor_texto_f}; border-radius: 6px; padding: 16px; min-height: 100px;">
            <div style="font-size: 10pt; color: #555555; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;">Forecast Projetado YTD (2+10)</div>
            <div style="font-size: 18pt; font-weight: bold; color: #1a1a1a; margin-top: 6px;">USD {val_fcast:,.2f}</div>
            <div style="font-size: 10pt; font-weight: bold; color: {cor_texto_f}; margin-top: 4px; display: flex; align-items: center;">
                <span style="font-size: 12pt; margin-right: 4px;">{seta_f}</span> Var: USD {var_fcast_usd:,.2f} ({pct_fcast:+.2f}%)
            </div>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# PARTE 5: VISUALIZAÇÕES GRÁFICAS STANDARD
# ==========================================
st.write("---")

st.subheader(f"📊 Comparativo Geral Capex YTD (Jan a {m_lim}) - USD")
fig_main = px.bar(
    df_f.groupby("Versão")["Val"].sum().reset_index(), 
    x="Versão", 
    y="Val", 
    color="Versão", 
    color_discrete_map=MAPA_CORES_CENARIO, 
    text_auto='.2f'
)
fig_main.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
fig_main.update_layout(yaxis_tickformat='$', showlegend=False, height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
st.plotly_chart(fig_main, use_container_width=True)

st.write("---")

# --- PROCESSAMENTO DE CORES CONDICIONAIS DINÂMICAS PARA GRÁFICOS QUEBRADOS ---
# Para os gráficos agrupados por Área e Planta, calculamos a relação Realizado vs Forecast de cada categoria para aplicar a cor cirurgicamente.
st.subheader("📊 Cenários por Tipo de Categoria de Projeto (Budget vs Forecast vs Realizado)")
df_proj_ver = df_f.groupby(["Área", "Versão"])["Val"].sum().unstack(level="Versão").fillna(0).reset_index()

df_proj_melted = pd.melt(df_proj_ver, id_vars=["Área"], value_vars=[v for v in [v_b, v_f, v_r] if v in df_proj_ver.columns], var_name="Versão", value_name="Val")

# Injeção da coluna de cor dinâmica por linha
def calcular_cor_dinamica_area(row):
    ver = row["Versão"]
    area = row["Área"]
    if ver == v_b: return CINZA_BUDGET
    if ver == v_f: return PRETO_FORECAST
    if ver == v_r:
        val_f_local = df_proj_ver[df_proj_ver["Área"] == area][v_f].values[0] if v_f in df_proj_ver.columns else 0.0
        return VERDE_REALIZADO if row["Val"] >= val_f_local else VERMELHO_REALIZADO
    return "#CCCCCC"

df_proj_melted["Cor_Chave"] = df_proj_melted.apply(calcular_cor_dinamica_area, axis=1)

fig_p = px.bar(
    df_proj_melted, 
    x="Área", 
    y="Val", 
    color="Cor_Chave", 
    barmode="group", 
    text_auto='.2f',
    hover_data=["Versão"],
    color_discrete_sequence=df_proj_melted["Cor_Chave"].unique()
)
# Forçamos o mapeamento direto no plot do Plotly para evitar desalinhamento de legenda
for idx, v_name in enumerate(df_proj_melted["Versão"].unique()):
    fig_p.data[idx].name = v_name
    fig_p.data[idx].marker.color = df_proj_melted[df_proj_melted["Versão"] == v_name]["Cor_Chave"].iloc[0]

fig_p.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
fig_p.update_layout(yaxis_tickformat='$', xaxis_title="Tipo / Área de Projeto", legend_title="Cenário", xaxis={'categoryorder':'total descending'}, height=450, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
st.plotly_chart(fig_p, use_container_width=True)
    
st.write("---")

# --- GRÁFICO DE SITES PADRONIZADO (LADO A LADO E CORES DINÂMICAS) ---
st.subheader("🏢 Distribuição de Recursos por Site / Planta (Budget vs Forecast vs Realizado)")
df_planta_wide = df_f.groupby(["Planta", "Versão"])["Val"].sum().unstack(level="Versão").fillna(0).reset_index()
df_planta_melted = pd.melt(df_planta_wide, id_vars=["Planta"], value_vars=[v for v in [v_b, v_f, v_r] if v in df_planta_wide.columns], var_name="Versão", value_name="Val")

def calcular_cor_dinamica_planta(row):
    ver = row["Versão"]
    planta = row["Planta"]
    if ver == v_b: return CINZA_BUDGET
    if ver == v_f: return PRETO_FORECAST
    if ver == v_r:
        val_f_local = df_planta_wide[df_planta_wide["Planta"] == planta][v_f].values[0] if v_f in df_planta_wide.columns else 0.0
        return VERDE_REALIZADO if row["Val"] >= val_f_local else VERMELHO_REALIZADO
    return "#CCCCCC"

df_planta_melted["Cor_Chave"] = df_planta_melted.apply(calcular_cor_dinamica_planta, axis=1)

fig_pl = px.bar(
    df_planta_melted, 
    x="Planta", 
    y="Val", 
    color="Cor_Chave", 
    barmode="group", 
    text_auto='.2f',
    hover_data=["Versão"]
)
for idx, v_name in enumerate(df_planta_melted["Versão"].unique()):
    fig_pl.data[idx].name = v_name
    fig_pl.data[idx].marker.color = df_planta_melted[df_planta_melted["Versão"] == v_name]["Cor_Chave"].iloc[0]

fig_pl.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
fig_pl.update_layout(yaxis_tickformat='$', xaxis_title="Site Planta", legend_title="Cenário", xaxis={'categoryorder':'total descending'}, height=450, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
st.plotly_chart(fig_pl, use_container_width=True)

st.write("---")

st.subheader("📈 Evolução Mensal Temporal dos Desembolsos")
df_ev = df_f.groupby(["Mês", "Versão"])["Val"].sum().reset_index()
df_ev['Idx'] = df_ev['Mês'].map({m: i for i, m in enumerate(m_ord)})
df_ev_sorted = df_ev.sort_values('Idx')

df_ev_wide = df_ev_sorted.groupby(["Mês", "Versão"])["Val"].sum().unstack(level="Versão").fillna(0).reset_index()
df_ev_melted = pd.melt(df_ev_wide, id_vars=["Mês"], value_vars=[v for v in [v_b, v_f, v_r] if v in df_ev_wide.columns], var_name="Versão", value_name="Val")
df_ev_melted['Idx'] = df_ev_melted['Mês'].map({m: i for i, m in enumerate(m_ord)})
df_ev_melted = df_ev_melted.sort_values('Idx')
df_ev_melted['Label_Txt'] = df_ev_melted['Val'].map(lambda x: f"${x:,.0f}")

def calcular_cor_dinamica_mensal(row):
    ver = row["Versão"]
    mes = row["Mês"]
    if ver == v_b: return CINZA_BUDGET
    if ver == v_f: return PRETO_FORECAST
    if ver == v_r:
        val_f_local = df_ev_wide[df_ev_wide["Mês"] == mes][v_f].values[0] if v_f in df_ev_wide.columns else 0.0
        return VERDE_REALIZADO if row["Val"] >= val_f_local else VERMELHO_REALIZADO
    return "#CCCCCC"

df_ev_melted["Cor_Chave"] = df_ev_melted.apply(calcular_cor_dinamica_mensal, axis=1)

fig_ev = px.line(
    df_ev_melted, 
    x="Mês", 
    y="Val", 
    color="Versão", 
    markers=True, 
    text="Label_Txt", 
    color_discrete_map=MAPA_CORES_CENARIO
)
fig_ev.update_traces(textposition='top center')
fig_ev.update_layout(yaxis_tickformat='$', height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
st.plotly_chart(fig_ev, use_container_width=True)

# =========================================================
# PARTE 6: GRÁFICOS AVANÇADOS (CORRIGIDO)
# =========================================================
st.write("---")

fig_scatter, fig_run, fig_pareto = None, None, None

# ✅ NOVA FORMA ROBUSTA DE IDENTIFICAR CATEGORIAS
def classificar_versao(v):
    v = str(v).lower()
    if any(x in v for x in ['budget','orc']):
        return "Budget"
    elif any(x in v for x in ['fcast','forecast']):
        return "Forecast"
    elif any(x in v for x in ['real','realizado']):
        return "Realizado"
    else:
        return "Outros"

# ✅ aplicar classificação
df_f["Categoria"] = df_f["Versão"].apply(classificar_versao)
df_analise_base["Categoria"] = df_analise_base["Versão"].apply(classificar_versao)

# ✅ construir base cruzada corretamente
df_cross = df_f.groupby([
    "Nro_Item Código",
    "Nome do Projeto",
    "Área",
    "Planta",
    "Responsável",
    "Status",
    "Categoria"
])["Val"].sum().unstack(level="Categoria").fillna(0).reset_index()

# ✅ garantir colunas
if "Budget" not in df_cross.columns:
    df_cross["Budget"] = 0

if "Forecast" not in df_cross.columns:
    df_cross["Forecast"] = 0

if "Realizado" not in df_cross.columns:
    df_cross["Realizado"] = 0

# ✅ cálculos
df_cross["Atraso vs Budget"] = df_cross["Budget"] - df_cross["Realizado"]
df_cross["Atraso vs Forecast"] = df_cross["Forecast"] - df_cross["Realizado"]

# =========================================================
# ✅ TABELA TOP 20 FORECAST (GARANTE QUE SEMPRE APARECE)
# =========================================================
st.subheader(f"⚠️ Análise de Desvios Críticos: TOP 20 Projetos em Atraso YTD vs. Fcast")

df_atrasados_f = df_cross[df_cross["Atraso vs Forecast"] > 0].copy()

if df_atrasados_f.empty:
    st.success("✅ Nenhum projeto apresenta atraso vs Forecast.")
else:
    df_top_20_f = df_atrasados_f.sort_values(by="Atraso vs Forecast", ascending=False).head(20)

    df_exibicao = df_top_20_f[[
        "Nro_Item Código",
        "Nome do Projeto",
        "Área",
        "Planta",
        "Responsável",
        "Status",
        "Forecast",
        "Realizado",
        "Atraso vs Forecast"
    ]].copy()

    # ✅ formatar valores
    for col in ["Forecast","Realizado","Atraso vs Forecast"]:
        df_exibicao[col] = df_exibicao[col].map(lambda x: f"$ {x:,.2f}")

    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

# =========================================================
# PARTE 7: TABELAS ANALÍTICAS DE ATRASOS (TOP 20)
# =========================================================
st.write("---")

table_html_snippet_budget = "<p>Sem dados de desvios de Budget para o cenário atual.</p>"
table_html_snippet_forecast = "<p>Sem dados de desvios de Forecast para o cenário atual.</p>"

if v_b and v_r and 'df_cross' in locals() and v_b in df_cross.columns and v_r in df_cross.columns:
    df_atrasados_b = df_cross[df_cross[v_b] - df_cross[v_r] > 0].copy()
    df_atrasados_b["Atraso (USD)"] = df_atrasados_b[v_b] - df_atrasados_b[v_r]
    df_atrasados_b = df_atrasados_b.rename(columns={v_b: "Budget YTD", v_r: "Realizado YTD"})
    df_top_20_b = df_atrasados_b.sort_values(by="Atraso (USD)", ascending=False).head(20)
    
    st.subheader(f"⚠️ Análise de Desvios Críticos: TOP 20 Projetos em Atraso YTD vs. Budget (Até {m_lim})")
    if df_top_20_b.empty:
        st.success("✅ Nenhum projeto apresenta desembolso atrasado em relação ao Budget.")
        table_html_snippet_budget = "<p style='color: green; font-weight: bold;'>✅ Nenhum projeto apresenta desembolso atrasado em relação ao Budget.</p>"
    else:
        df_exibicao_b = df_top_20_b[["Nro_Item Código", "Nome do Projeto", "Área", "Planta", "Responsável", "Status", "Budget YTD", "Realizado YTD", "Atraso (USD)"]].copy()
        total_b = df_top_20_b["Budget YTD"].sum()
        total_r = df_top_20_b["Realizado YTD"].sum()
        total_a = df_top_20_b["Atraso (USD)"].sum()
        
        linha_total_b = pd.DataFrame([{
            "Nro_Item Código": "TOTAL DO TOP 20", "Nome do Projeto": "---", "Área": "---", "Planta": "---", "Responsável": "---", "Status": "---",
            "Budget YTD": total_b, "Realizado YTD": total_r, "Atraso (USD)": total_a
        }])
        
        df_exibicao_com_total_b = pd.concat([df_exibicao_b, linha_total_b], ignore_index=True)
        table_html_snippet_budget = df_exibicao_com_total_b.to_html(index=False, classes='data-table')
        
        for col in ["Budget YTD", "Realizado YTD", "Atraso (USD)"]:
            df_exibicao_com_total_b[col] = df_exibicao_com_total_b[col].map(lambda x: f"$ {x:,.2f}")
        st.dataframe(df_exibicao_com_total_b, use_container_width=True, hide_index=True)

if v_f and v_r and 'df_cross' in locals() and v_f in df_cross.columns and v_r in df_cross.columns:
    df_atrasados_f = df_cross[df_cross[v_f] - df_cross[v_r] > 0].copy()
    df_atrasados_f["Atraso vs Fcast (USD)"] = df_atrasados_f[v_f] - df_atrasados_f[v_r]
    df_atrasados_f = df_atrasados_f.rename(columns={v_f: "Forecast YTD", v_r: "Realizado YTD"})
    df_top_20_f = df_atrasados_f.sort_values(by="Atraso vs Fcast (USD)", ascending=False).head(20)
    
    st.write("---")
    st.subheader(f"⚠️ Análise de Desvios Críticos: TOP 20 Projetos em Atraso YTD vs. Fcast 2+10 (Até {m_lim})")
    if df_top_20_f.empty:
        st.success("✅ Nenhum projeto apresenta desembolso atrasado em relação ao Forecast.")
        table_html_snippet_forecast = "<p style='color: green; font-weight: bold;'>✅ Nenhum projeto apresenta desembolso atrasado em relação ao Forecast.</p>"
    else:
        df_exibicao_f = df_top_20_f[["Nro_Item Código", "Nome do Projeto", "Área", "Planta", "Responsável", "Status", "Forecast YTD", "Realizado YTD", "Atraso vs Fcast (USD)"]].copy()
        total_f_b = df_top_20_f["Forecast YTD"].sum()
        total_f_r = df_top_20_f["Realizado YTD"].sum()
        total_f_a = df_top_20_f["Atraso vs Fcast (USD)"].sum()
        
        linha_total_f = pd.DataFrame([{
            "Nro_Item Código": "TOTAL DO TOP 20", "Nome do Projeto": "---", "Área": "---", "Planta": "---", "Responsável": "---", "Status": "---",
            "Forecast YTD": total_f_b, "Realizado YTD": total_f_r, "Atraso vs Fcast (USD)": total_f_a
        }])
        
        df_exibicao_com_total_f = pd.concat([df_exibicao_f, linha_total_f], ignore_index=True)
        table_html_snippet_forecast = df_exibicao_com_total_f.to_html(index=False, classes='data-table')
        
        for col in ["Forecast YTD", "Realizado YTD", "Atraso vs Fcast (USD)"]:
            df_exibicao_com_total_f[col] = df_exibicao_com_total_f[col].map(lambda x: f"$ {x:,.2f}")
        st.dataframe(df_exibicao_com_total_f, use_container_width=True, hide_index=True)

# ==========================================
# PARTE 8: EXPORTAÇÃO EXECUTIVA (HTML OTIMIZADA)
# ==========================================
st.write("---")
st.subheader("🖨️ Exportação Completa para Diretoria")

try:
    chart_main_html = fig_main.to_html(full_html=False, include_plotlyjs='cdn')
    chart_p_html = fig_p.to_html(full_html=False, include_plotlyjs=False)
    chart_pl_html = fig_pl.to_html(full_html=False, include_plotlyjs=False)
    chart_ev_html = fig_ev.to_html(full_html=False, include_plotlyjs=False)
    
    chart_scatter_html = fig_scatter.to_html(full_html=False, include_plotlyjs=False) if fig_scatter else ""
    chart_run_html = fig_run.to_html(full_html=False, include_plotlyjs=False) if fig_run else ""
    chart_pareto_html = fig_pareto.to_html(full_html=False, include_plotlyjs=False) if fig_pareto else ""

    logo_base64_html = ""
    if os.path.exists(ARQUIVO_LOGO):
        logo_base64_html = f'<img src="data:image/jpeg;base64,{get_base64_of_bin_file(ARQUIVO_LOGO)}" style="height:50px;float:left;margin-right:20px;margin-top:-10px;">'

    html_report = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Report Executivo de Capex</title>
        <style>
            * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
            body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #2b2b2b; margin: 0; padding: 20px; background-color: #fafafa; }}
            .report-wrapper {{ max-width: 950px; margin: 0 auto; background: #fff; padding: 40px; border: 1px solid #e0e0e0; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
            .header {{ border-bottom: 3px solid #0066cc; padding-bottom: 12px; margin-bottom: 25px; }}
            .title {{ font-size: 20pt; font-weight: bold; color: #0066cc; text-transform: uppercase; }}
            h2 {{ font-size: 13pt; color: #1a1a1a; margin: 35px 0 15px 0; padding-left: 8px; border-left: 4px solid #0066cc; }}
            table.kpi-table {{ width: 100%; border-collapse: separate; border-spacing: 12px 0; margin: 15px -12px; }}
            td.kpi-card {{ width: 33.33%; background-color: #f8f9fa !important; border: 1px solid #e9ecef; border-radius: 6px; padding: 14px; border-left: 5px solid #336699 !important; }}
            .chart-box {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 15px; margin-bottom: 30px; overflow-x: auto; }}
            
            table.data-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 9pt; }}
            table.data-table th, table.data-table td {{ border: 1px solid #e2e8f0; padding: 8px 10px; text-align: left; }}
            table.data-table th {{ background-color: #0066cc; color: white; font-weight: bold; text-transform: uppercase; font-size: 8pt; letter-spacing: 0.5px; }}
            table.data-table tr:nth-child(even) {{ background-color: #f8f9fa; }}
            table.data-table tr:hover {{ background-color: #f1f5f9; }}
            table.data-table tr:last-child {{ font-weight: bold; background-color: #edf2f7; border-top: 2px solid #cbd5e1; }}
        </style>
    </head>
    <body>
        <div class="report-wrapper">
            <div class="header">
                {logo_base64_html}
                <div class="title">Capex - Status Corporativo Global</div>
                <div>Book Executivo Consolidado — América do Sul — Ano Base {ano_s} (YTD até {m_lim})</div>
            </div>
            <table class="kpi-table">
                <tr>
                    <td class="kpi-card" style="border-left-color: {cor_realizado_global} !important;"><div>REALIZADO YTD</div><div style="font-size:14pt;font-weight:bold;color:{cor_realizado_global};">$ {val_real:,.2f}</div></td>
                    <td class="kpi-card" style="background-color: {bg_card_b} !important; border-left-color: {cor_texto_b} !important;">
                        <div>BUDGET YTD</div>
                        <div style="font-size:14pt;font-weight:bold;">$ {val_budg:,.2f}</div>
                        <div style="font-size:9.5pt; font-weight:bold; color:{cor_texto_b}; margin-top:4px;">{seta_b} Var: $ {var_budg_usd:,.2f} ({pct_budg:+.2f}%)</div>
                    </td>
                    <td class="kpi-card" style="background-color: {bg_card_f} !important; border-left-color: {cor_texto_f} !important;">
                        <div>FORECAST (2+10)</div>
                        <div style="font-size:14pt;font-weight:bold;">$ {val_fcast:,.2f}</div>
                        <div style="font-size:9.5pt; font-weight:bold; color:{cor_texto_f}; margin-top:4px;">{seta_f} Var: $ {var_fcast_usd:,.2f} ({pct_fcast:+.2f}%)</div>
                    </td>
                </tr>
            </table>
            <h2>1. Evolução e Sumário por Estruturas e Sites</h2>
            <div class="chart-box">{chart_main_html}</div>
            <div class="chart-box">{chart_p_html}</div>
            <div class="chart-box">{chart_pl_html}</div>
            <div class="chart-box">{chart_ev_html}</div>
            
            <h2>2. Análises Avançadas de Risco e Concentração</h2>
            <div class="chart-box">{chart_scatter_html}</div>
            <div class="chart-box">{chart_run_html}</div>
            <div class="chart-box">{chart_pareto_html}</div>
            
            <h2>3. Análise de Desvios Críticos: TOP 20 Projetos em Atraso YTD vs. Budget</h2>
            <div class="chart-box">{table_html_snippet_budget}</div>

            <h2>4. Análise de Desvios Críticos: TOP 20 Projetos em Atraso YTD vs. Fcast 2+10</h2>
            <div class="chart-box">{table_html_snippet_forecast}</div>
        </div>
    </body>
    </html>
    """

    st.download_button(
        label="📥 Baixar Livro Executivo Ampliado (HTML)",
        data=html_report,
        file_name=f"Book_Executivo_Capex_{m_lim}_{ano_s}.html",
        mime="text/html"
    )
except Exception as err_export:
    st.sidebar.error(f"Erro ao injetar gráficos na exportação: {err_export}")

with st.expander("🔍 Ver Tabela de Dados Brutos"):
    if 'df_f' in locals() and not df_f.empty:
        st.write("**Filtros activos:**", f"Ano Orçamentário: {ano_s} | Período: Jan a {m_lim}")
        df_view = df_f.copy()
        df_view['Val'] = df_view['Val'].map(lambda x: f"$ {x:,.2f}")
        st.dataframe(df_view, use_container_width=True)
        
