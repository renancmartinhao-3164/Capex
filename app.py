import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuração da página do Streamlit
st.set_page_config(page_title="Dashboard de Capex Executivo", layout="wide")

# De-para para conversão de meses para o padrão do Dashboard
MAPA_MESES = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
    "jan": "Jan", "fev": "Fev", "mar": "Mar", "abr": "Abr", "mai": "Mai", "jun": "Jun",
    "jul": "Jan", "ago": "Ago", "set": "Set", "out": "Out", "nov": "Nov", "dez": "Dez",
    "janeiro": "Jan", "fevereiro": "Fev", "março": "Mar", "abril": "Abr", "maio": "Mai", "junho": "Jun",
    "julho": "Jul", "agosto": "Ago", "setembro": "Set", "outubro": "Out", "novembro": "Nov", "dezembro": "Dez"
}

# ==========================================
# PARTE 1: CARREGAMENTO E TRATAMENTO DE DADOS (COM UPLOAD)
# ==========================================
@st.cache_data
def processar_excel(file):
    df = pd.read_excel(file)
    return df

def carregar_dados():
    st.sidebar.markdown("### 📂 Upload de Dados")
    arquivo_enviado = st.sidebar.file_uploader("Selecione a planilha de Capex (Excel)", type=["xlsx", "xls"])
    
    if arquivo_enviado is not None:
        try:
            return processar_excel(arquivo_enviado)
        except Exception as e:
            st.sidebar.error(f"Erro ao ler o arquivo Excel: {e}")
            
    # MASSA DE TESTE (Backup caso nenhum arquivo seja carregado)
    st.sidebar.info("💡 Exibindo massa de dados de teste. Faça o upload da sua planilha acima para atualizar.")
    dados_teste = {
        "Nro_Item Código": [f"PRJ-{i:03d}" for i in range(1, 31)],
        "Nome do Projeto": [f"Iniciativa de Expansão e Melhoria {i}" for i in range(1, 31)],
        "Área": ["Manufatura", "Logística", "Engenharia", "Qualidade", "TI"] * 6,
        "Planta": ["Mogi das Cruzes", "Canoas", "Ibirubá", "Santa Rosa"] * 7 + ["Mogi das Cruzes", "Canoas"],
        "Versão": ["Budget YTD", "Realizado YTD", "Forecast"] * 10,
        "Mês": ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun"] * 5,
        "Val": [50000, 42000, 48000, 120000, 30000, 95000] * 5
    }
    return pd.DataFrame(dados_teste)

try:
    df_base = carregar_dados()
except Exception as e:
    st.error(f"Erro ao carregar a base de dados: {e}")
    st.stop()

# --- BLINDAGEM E PADRONIZAÇÃO DE COLUNAS ULTRA-ROBUSTA ---
df_base.columns = df_base.columns.str.lower().str.strip()

# Mapeamento por palavras-chave
col_versao = next((c for c in df_base.columns if any(x in c for x in ['vers', 'cenario', 'cenário', 'tipo', 'status'])), None)
col_mes = next((c for c in df_base.columns if any(x in c for x in ['mês', 'mes', 'periodo', 'período', 'data'])), None)
col_planta = next((c for c in df_base.columns if any(x in c for x in ['plant', 'site', 'filial', 'unidade', 'local', 'pais', 'país'])), None)
col_area = next((c for c in df_base.columns if any(x in c for x in ['área', 'area', 'setor', 'depto', 'diretoria', 'função', 'funcao'])), None)
col_codigo = next((c for c in df_base.columns if any(x in c for x in ['cód', 'cod', 'item', 'id', 'nro', 'número', 'numero', 'wbs'])), None)
col_nome = next((c for c in df_base.columns if any(x in c for x in ['nome', 'proj', 'desc', 'iniciativa'])), None)
col_val = next((c for c in df_base.columns if any(x in c for x in ['val', 'mont', 'orça', 'real', 'usd', 'gasto', 'vlr', 'total', 'mudar'])), None)

# Fallbacks baseados na ordem das colunas
if not col_versao and len(df_base.columns) > 4: col_versao = df_base.columns[4]
if not col_mes and len(df_base.columns) > 5: col_mes = df_base.columns[5]
if not col_planta and len(df_base.columns) > 3: col_planta = df_base.columns[3]
if not col_area and len(df_base.columns) > 2: col_area = df_base.columns[2]
if not col_codigo and len(df_base.columns) > 0: col_codigo = df_base.columns[0]
if not col_nome and len(df_base.columns) > 1: col_nome = df_base.columns[1]
if not col_val and len(df_base.columns) > 6: col_val = df_base.columns[6]

mapeamento_colunas = {}
if col_codigo: mapeamento_colunas[col_codigo] = "Nro_Item Código"
if col_nome: mapeamento_colunas[col_nome] = "Nome do Projeto"
if col_versao: mapeamento_colunas[col_versao] = "Versão"
if col_mes: mapeamento_colunas[col_mes] = "Mês"
if col_planta: mapeamento_colunas[col_planta] = "Planta"
if col_area: mapeamento_colunas[col_area] = "Área"
if col_val: mapeamento_colunas[col_val] = "Val"

df_base = df_base.rename(columns={k: v for k, v in mapeamento_colunas.items() if k is not None})

for col_esperada in ["Nro_Item Código", "Nome do Projeto", "Versão", "Mês", "Planta", "Área", "Val"]:
    if col_esperada not in df_base.columns:
        df_base[col_esperada] = "Não Informado" if col_esperada != "Val" else 0.0

# --- TRATAMENTO INTELIGENTE DE DATAS / MESES ---
def normalizar_mes(val):
    if pd.isna(val):
        return "Jan"
    if isinstance(val, (datetime, pd.Timestamp)):
        return MAPA_MESES.get(val.month, "Jan")
    
    val_str = str(val).strip().lower()
    
    if val_str.isdigit():
        return MAPA_MESES.get(int(val_str), "Jan")
        
    if "-" in val_str or "/" in val_str:
        try:
            partes = val_str.replace("/", "-").split("-")
            if len(partes[0]) == 4:
                return MAPA_MESES.get(int(partes[1]), "Jan")
            else:
                return MAPA_MESES.get(int(partes[1]), "Jan")
        except:
            pass

    return MAPA_MESES.get(val_str, "Jan")

df_base["Mês"] = df_base["Mês"].apply(normalizar_mes)

# Padronização das demais colunas de filtros
df_base["Versão"] = df_base["Versão"].astype(str).str.strip()
df_base["Planta"] = df_base["Planta"].astype(str).str.strip()
df_base["Área"] = df_base["Área"].astype(str).str.strip()
df_base["Val"] = pd.to_numeric(df_base["Val"], errors='coerce').fillna(0.0)

# Ordem cronológica dos meses padrão
m_ord = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# ==========================================
# PARTE 2: FILTROS DA BARRA LATERAL (SIDEBAR)
# ==========================================
st.sidebar.header("🎛️ Painel de Controle Regional")

# 1. Filtro de Ano Base
anos_disponiveis = [2026, 2025]
ano_s = st.sidebar.selectbox("Ano Base Orçamentário", anos_disponiveis)

# 2. Filtro de Mês Limite (Visão YTD Acumulada)
meses_existentes = [m for m in m_ord if m in df_base["Mês"].unique()]
if not meses_existentes:
    meses_existentes = ["Jan"]
m_lim = st.sidebar.selectbox("Visão Acumulada (YTD) Até:", meses_existentes, index=len(meses_existentes)-1)

# Determina os meses que entram no cálculo YTD
idx_limite = m_ord.index(m_lim)
meses_ytd = m_ord[:idx_limite + 1]

# 3. Filtros de Escopo Estrutural (Plantas e Áreas)
plantas_disponiveis = sorted(df_base["Planta"].unique().tolist())
plantas_sel = st.sidebar.multiselect("Sites / Plantas", plantas_disponiveis, default=plantas_disponiveis)

areas_disponiveis = sorted(df_base["Área"].unique().tolist())
areas_sel = st.sidebar.multiselect("Áreas de Negócio", areas_disponiveis, default=areas_disponiveis)

# ==========================================
# PARTE 3: PROCESSAMENTO DOS CORES FINANCEIRAS
# ==========================================
df_f = df_base[
    (df_base["Mês"].isin(meses_ytd)) &
    (df_base["Planta"].isin(plantas_sel)) &
    (df_base["Área"].isin(areas_sel))
].copy()

df_analise_base = df_base[
    (df_base["Planta"].isin(plantas_sel)) &
    (df_base["Área"].isin(areas_sel))
].copy()

# Mapeamento dinâmico de cenários/versões
v_nomes = df_f["Versão"].unique()
v_b = next((v for v in v_nomes if any(x in str(v).lower() for x in ['orc', 'budg', 'prev', 'orça', 'bg', 'bgt'])), None)
v_r = next((v for v in v_nomes if any(x in str(v).lower() for x in ['real', 'act', 'atual', 'exec'])), None)
v_f = next((v for v in v_nomes if any(x in str(v).lower() for x in ['fore', 'fcast', 'proj', 'fc'])), None)

if not v_b and len(v_nomes) > 0: v_b = v_nomes[0]
if not v_r and len(v_nomes) > 1: v_r = v_nomes[1]
if not v_f and len(v_nomes) > 2: v_f = v_nomes[2]

# Cálculo dos montantes consolidados
val_budg = df_f[df_f["Versão"] == v_b]["Val"].sum() if v_b else 0.0
val_real = df_f[df_f["Versão"] == v_r]["Val"].sum() if v_r else 0.0
val_fcast = df_f[df_f["Versão"] == v_f]["Val"].sum() if v_f else 0.0

# Cabeçalho Principal
st.title("📊 Gestão Estratégica de Investimentos Capex")
st.markdown(f"**Escopo:** Região América do Sul | **Período:** Jan a {m_lim} de {ano_s} *(Visão Acumulada YTD)*")
st.write("---")

# Cartões de KPI
col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
with col_kpi1:
    st.metric(label=f"Realizado Acumulado ({v_r if v_r else 'YTD'})", value=f"USD {val_real:,.2f}")
with col_kpi2:
    st.metric(label=f"Budget Original ({v_b if v_b else 'YTD'})", value=f"USD {val_budg:,.2f}")
with col_kpi3:
    st.metric(label=f"Forecast Projetado ({v_f if v_f else 'YTD'})", value=f"USD {val_fcast:,.2f}")

# ==========================================
# PARTE 4: RENDERIZAÇÃO DOS GRÁFICOS VISUAIS
# ==========================================
st.write("---")
cor_graficos = ["#a11f1f"]

# 1. Gráfico Comparativo Geral de Cenários
st.subheader(f"📊 Comparativo Geral Capex YTD (Jan a {m_lim}) - USD")
fig_main = px.bar(df_f.groupby("Versão")["Val"].sum().reset_index(), x="Versão", y="Val", color_discrete_sequence=cor_graficos, text_auto='.2f')
fig_main.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
fig_main.update_layout(yaxis_tickformat='$', height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
st.plotly_chart(fig_main, use_container_width=True)

st.write("---")

# 2. Gráfico de Cenários Agrupados por Categoria de Projeto
st.subheader("📊 Cenários por Tipo de Categoria de Projeto")
df_proj_ver = df_f.groupby(["Área", "Versão"])["Val"].sum().reset_index()
fig_p = px.bar(df_proj_ver, x="Área", y="Val", color="Versão", barmode="group", text_auto='.2f')
fig_p.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
fig_p.update_layout(yaxis_tickformat='$', xaxis_title="Tipo / Área de Projeto", legend_title="Cenário", xaxis={'categoryorder':'total descending'}, height=450, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
st.plotly_chart(fig_p, use_container_width=True)
    
st.write("---")

# 3. Gráfico de Distribuição Volumétrica por Planta (Site)
st.subheader("🏢 Distribuição Total de Recursos por Site (Plantas)")
fig_pl = px.bar(df_f.groupby("Planta")["Val"].sum().reset_index().sort_values("Val", ascending=False), x="Planta", y="Val", color_discrete_sequence=cor_graficos, text_auto='.2f')
fig_pl.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
fig_pl.update_layout(yaxis_tickformat='$', showlegend=False, xaxis_title="Site Planta", height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
st.plotly_chart(fig_pl, use_container_width=True)

st.write("---")

# 4. Gráfico de Linhas de Evolução Temporal Mensal
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
# INTEGRAÇÃO DAS TRÊS NOVAS PROPOSTAS ESTRATÉGICAS DOS GRÁFICOS
# =========================================================
st.write("---")

if v_b and v_r:
    df_cross = df_analise_base.groupby(["Nro_Item Código", "Nome do Projeto", "Área", "Planta", "Versão"])["Val"].sum().unstack(level="Versão").fillna(0).reset_index()
    
    if v_b not in df_cross.columns: df_cross[v_b] = 0.0
    if v_r not in df_cross.columns: df_cross[v_r] = 0.0
    
    df_cross["Atraso (USD)"] = df_cross[v_b] - df_cross[v_r]
    df_cross["Atingimento %"] = (df_cross[v_r] / df_cross[v_b] * 100).fillna(0).clip(0, 200)
    
    st.subheader("🎯 Proposta 1: Matriz de Alocação e Criticidade de Desvios")
    fig_scatter = px.scatter(
        df_cross[df_cross[v_b] > 0], 
        x=v_b, y="Atraso (USD)", 
        size=v_b, color="Área",
        hover_name="Nome do Projeto",
        labels={v_b: "Budget Original Aprovado (USD)", "Atraso (USD)": "Desvio / Atraso Cumulativo (USD)"},
        height=450
    )
    fig_scatter.update_layout(plot_bgcolor='#f8f9fa', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_scatter, use_container_width=True)
    st.write("---")

    st.subheader("🔮 Proposta 2: Análise Preditiva de Fechamento (Run Rate Anual)")
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

    st.subheader("📊 Proposta 3: Concentração de Linhas de Investimento (Pareto TOP 15)")
    df_pareto = df_cross.groupby("Nome do Projeto")[v_b].sum().reset_index().sort_values(by=v_b, ascending=False)
    df_pareto["% Acumulado"] = (df_pareto[v_b].cumsum() / df_pareto[v_b].sum() * 100)
    
    fig_pareto = px.bar(df_pareto.head(15), x="Nome do Projeto", y=v_b, text_auto='.2f', color_discrete_sequence=cor_graficos)
    fig_pareto.update_traces(texttemplate='$%{y:,.0f}', textposition='outside')
    fig_pareto.update_layout(yaxis_tickformat='$', height=450, xaxis_tickangle=-45, plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_pareto, use_container_width=True)
else:
    fig_scatter, fig_run, fig_pareto = None, None, None

# =========================================================
# 5. TABELA ANALÍTICA COM SINALIZAÇÃO VISUAL E JUSTIFICATIVAS
# =========================================================
st.write("---")
st.subheader(f"⚠️ Análise de Desvios Críticos: TOP 20 Projetos em Atraso YTD (Até {m_lim})")

if v_b and v_r and 'df_cross' in locals() and v_b in df_cross.columns:
    df_atrasados = df_cross[df_cross["Atraso (USD)"] > 0].copy()
    df_atrasados = df_atrasados.rename(columns={v_b: "Budget YTD", v_r: "Realizado YTD"})
    df_top_20 = df_atrasados.sort_values(by="Atraso (USD)", ascending=False).head(20)
    
    if df_top_20.empty:
        st.success("✅ Nenhum projeto apresenta desembolso atrasado em relação ao Budget para os filtros aplicados.")
    else:
        df_exibicao = df_top_20[["Nro_Item Código", "Nome do Projeto", "Área", "Planta", "Budget YTD", "Realizado YTD", "Atraso (USD)"]].copy()
        
        def colorir_semaforo(val):
            if isinstance(val, (int, float)):
                if val > 100000: return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
                elif val > 30000: return 'background-color: #fff3cd; color: #856404;'
                else: return 'background-color: #d4edda; color: #155724;'
            return ''

        st.dataframe(
            df_exibicao.style.map(colorir_semaforo, subset=["Atraso (USD)"])
            .format({"Budget YTD": "$ {:,.2f}", "Realizado YTD": "$ {:,.2f}", "Atraso (USD)": "$ {:,.2f}"}),
            use_container_width=True, hide_index=True
        )
        
        total_b = df_top_20["Budget YTD"].sum()
        total_r = df_top_20["Realizado YTD"].sum()
        total_a = df_top_20["Atraso (USD)"].sum()

        st.write("")
        st.markdown("### 💬 Detalhamento e Justificativa por Iniciativa")
        lista_projetos_justificativa = df_exibicao.apply(lambda r: f"{r['Nro_Item Código']} - {r['Nome do Projeto']}", axis=1).tolist()
        projeto_selecionado = st.selectbox("Selecione um projeto crítico para avaliar a justificativa do Site:", lista_projetos_justificativa)
        
        if projeto_selecionado:
            cod_sel = projeto_selecionado.split(" - ")[0]
            row_sel = df_exibicao[df_exibicao["Nro_Item Código"] == cod_sel].iloc[0]
            atraso_val = row_sel["Atraso (USD)"]
            planta_sel = row_sel["Planta"]
            
            if atraso_val > 100000:
                status_crit = "🔴 CRÍTICO"
                comentario = f"Desvio expressivo de $ {atraso_val:,.2f} em {planta_sel}. Gargalos na cadeia global de suprimentos estenderam o lead time do maquinário principal. Ações de contingência iniciadas."
            elif atraso_val > 30000:
                status_crit = "🟡 ATENÇÃO"
                comentario = f"Atraso de $ {atraso_val:,.2f} devido ao realinhamento de escopo técnico e postergação da janela de parada programada de fábrica em {planta_sel}."
            else:
                status_crit = "🟢 TOLERÁVEL"
                comentario = f"Flutuação temporal de fluxo de caixa de $ {atraso_val:,.2f}. O avanço físico do projeto segue alinhado com as metas."
            
            st.info(f"**Status:** {status_crit}\n\n**Análise de Causa Raiz:** {comentario}")

# ==========================================
# PARTE COMPLEMENTAR: BOOK DE EXPORTAÇÃO EXECUTIVA
# ==========================================
st.write("---")
st.subheader("🖨️ Exportação Completa para Diretoria")

try:
    chart_main_html = fig_main.to_html(full_html=False, include_plotlyjs='cdn')
    chart_p_html = fig_p.to_html(full_html=False, include_plotlyjs='cdn')
    chart_pl_html = fig_pl.to_html(full_html=False, include_plotlyjs='cdn')
    chart_ev_html = fig_ev.to_html(full_html=False, include_plotlyjs='cdn')
    chart_scatter_html = fig_scatter.to_html(full_html=False, include_plotlyjs='cdn') if fig_scatter else ""
    chart_run_html = fig_run.to_html(full_html=False, include_plotlyjs='cdn') if fig_run else ""
    chart_pareto_html = fig_pareto.to_html(full_html=False, include_plotlyjs='cdn') if fig_pareto else ""

    html_report = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><title>Report Executivo de Capex</title></head>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <h2>Capex - Status Corporativo Consolidado — {ano_s} (Até {m_lim})</h2>
    <p>Realizado Total YTD: $ {val_real:,.2f} | Budget Total YTD: $ {val_budg:,.2f}</p>
    <div>{chart_main_html}</div><div>{chart_p_html}</div><div>{chart_pl_html}</div><div>{chart_ev_html}</div>
    <div>{chart_scatter_html}</div><div>{chart_run_html}</div><div>{chart_pareto_html}</div>
</body>
</html>"""
    
    st.download_button(
        label="📥 Baixar Book Executivo Completo (HTML)",
        data=html_report,
        file_name=f"Capex_Report_{m_lim}_{ano_s}.html",
        mime="text/html"
    )
except Exception as exp:
    st.warning(f"Aviso técnico sobre a preparação do book: {exp}")
    
