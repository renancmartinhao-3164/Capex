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

ARQUIVO_PADRAO = "seus_dados_capex.xlsx"
ARQUIVO_LOGO = "logo.jpg" # Define o nome do arquivo de logo

@st.cache_data
def carregar_dados_excel(file_path_or_buffer):
    return pd.read_excel(file_path_or_buffer)

# Função para converter imagem para base64 para embutir no HTML
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
            st.sidebar.error(f"Erro ao ler the arquivo enviado: {e}")
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
        elif col_lower in ['responsável', 'responsavel', 'owner', 'resp', 'responsáveis', 'responsaveis']:
            mapeamento_colunas[col] = "Responsável"
        elif col_lower in ['status', 'situação', 'situacao', 'estado', 'fase']:
            mapeamento_colunas[col] = "Status"
            
    df_base = df_base.rename(columns=mapeamento_colunas)

    # Cria colunas caso não existam no Excel para evitar quebras de compilação
    if "Responsável" not in df_base.columns:
        df_base["Responsável"] = "Não Informado"
    if "Status" not in df_base.columns:
        df_base["Status"] = "Não Informado"

    m_ord = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    colunas_meses_encontradas = [m for m in m_ord if m in df_base.columns]
    
    colunas_identificadoras = [c for c in ["Nro_Item Código", "Nome do Projeto", "Área", "Planta", "Versão", "Ano", "Responsável", "Status"] if c in df_base.columns]

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
df_base["Responsável"] = df_base["Responsável"].astype(str).str.strip().fillna("Não Informado")
df_base["Status"] = df_base["Status"].astype(str).str.strip().fillna("Não Informado")
df_base["Val"] = pd.to_numeric(df_base["Val"], errors='coerce').fillna(0.0)

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

col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
with col_kpi1:
    st.metric(label="Realizado Acumulado YTD", value=f"USD {val_real:,.2f}")
with col_kpi2:
    st.metric(label="Budget Original YTD", value=f"USD {val_budg:,.2f}")
with col_kpi3:
    st.metric(label="Forecast Projetado YTD", value=f"USD {val_fcast:,.2f}")

# ==========================================
# PARTE 5: VISUALIZAÇÕES GRÁFICAS STANDARD (Tudo em AZUL)
# ==========================================
st.write("---")
cor_graficos = ["#0066cc"]

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
fig_p = px.bar(df_proj_ver, x="Área", y="Val", color="Versão", barmode="group", text_auto='.2f', color_discrete_sequence=px.colors.qualitative.Plotly_r)
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

fig_ev = px.line(df_ev_sorted, x="Mês", y="Val", color="Versão", markers=True, text="Label_Txt", color_discrete_sequence=px.colors.qualitative.Plotly_r)
fig_ev.update_traces(textposition='top center')
fig_ev.update_layout(yaxis_tickformat='$', height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
st.plotly_chart(fig_ev, use_container_width=True)

# =========================================================
# PARTE 6: GRÁFICOS AVANÇADOS (MATRIZ, PREVISÃO, PARETO)
# =========================================================
st.write("---")

if v_b and v_r:
    df_cross = df_f.groupby(["Nro_Item Código", "Nome do Projeto", "Área", "Planta", "Responsável", "Status", "Versão"])["Val"].sum().unstack(level="Versão").fillna(0).reset_index()
    
    if v_b in df_cross.columns and v_r in df_cross.columns:
        df_cross["Atraso (USD)"] = df_cross[v_b] - df_cross[v_r]
        df_cross["Atingimento %"] = (df_cross[v_r] / df_cross[v_b] * 100).fillna(0).clip(0, 200)
        
        st.subheader("🎯 Matriz de Alocação e Criticidade de Desvios")
        fig_scatter = px.scatter(
            df_cross[df_cross[v_b] > 0], x=v_b, y="Atraso (USD)", size=v_b, color="Área", hover_name="Nome do Projeto",
            labels={v_b: "Budget YTD Aprovado (USD)", "Atraso (USD)": "Desvio / Atraso Cumulativo YTD (USD)"}, height=450,
            color_discrete_sequence=px.colors.qualitative.Pastel_r
        )
        fig_scatter.update_layout(plot_bgcolor='#f8f9fa', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_scatter, use_container_width=True)
        st.write("---")

        st.subheader("🔮 Análise Preditiva de Fechamento (Run Rate Anual)")
        n_meses_ytd = m_ord.index(m_lim) + 1
        gasto_medio_mensal = val_real / n_meses_ytd
        proj_fim_ano = val_real + (gasto_medio_mensal * (12 - n_meses_ytd))
        
        val_budg_anual = df_analise_base[df_analise_base["Versão"] == v_b]["Val"].sum() if v_b else 0.0
        
        df_runrate = pd.DataFrame({
            "Métrica de Fechamento": ["Realizado YTD", "Projeção Final de Ano (Run Rate)", "Budget Anual Planejado"],
            "Valor (USD)": [val_real, proj_fim_ano, val_budg_anual]
        })
        fig_run = px.bar(df_runrate, x="Métrica de Fechamento", y="Valor (USD)", text_auto='.2f', color="Métrica de Fechamento", color_discrete_sequence=["#336699", "#6699CC", "#343a40"])
        fig_run.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
        fig_run.update_layout(yaxis_tickformat='$', showlegend=False, height=400, plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_run, use_container_width=True)
        st.write("---")

        st.subheader("📊 Concentração de Linhas de Investimento (Pareto TOP 15)")
        df_pareto = df_cross.groupby("Nome do Projeto")[v_b].sum().reset_index().sort_values(by=v_b, ascending=False)
        df_pareto["% Acumulado"] = (df_pareto[v_b].cumsum() / df_pareto[v_b].sum() * 100)
        
        fig_pareto = px.bar(df_pareto.head(15), x="Nome do Projeto", y=v_b, text_auto='.2f', color_discrete_sequence=cor_graficos)
        fig_pareto.update_traces(texttemplate='$%{y:,.0f}', textposition='outside')
        fig_pareto.update_layout(yaxis_tickformat='$', height=450, xaxis_tickangle=-45, plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pareto, use_container_width=True)
    else:
        fig_scatter, fig_run, fig_pareto = None, None, None
else:
    fig_scatter, fig_run, fig_pareto = None, None, None

# =========================================================
# PARTE 7: TABELAS ANALÍTICAS DE ATRASOS (TOP 20)
# =========================================================
st.write("---")

# Definição de placeholders para injeção HTML estruturada
table_html_snippet_budget = "<p>Sem dados de desvios de Budget para o cenário atual.</p>"
table_html_snippet_forecast = "<p>Sem dados de desvios de Forecast para o cenário atual.</p>"

if v_b and v_r and 'df_cross' in locals() and v_b in df_cross.columns and v_r in df_cross.columns:
    # --- TABELA 1: TOP 20 VS BUDGET ---
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
        for col in ["Budget YTD", "Realizado YTD", "Atraso (USD)"]:
            df_exibicao_com_total_b[col] = df_exibicao_com_total_b[col].map(lambda x: f"$ {x:,.2f}")
        
        table_html_snippet_budget = df_exibicao_com_total_b.to_html(index=False, classes='data-table')
        st.dataframe(df_exibicao_com_total_b, use_container_width=True, hide_index=True)

if v_f and v_r and 'df_cross' in locals() and v_f in df_cross.columns and v_r in df_cross.columns:
    # --- TABELA 2: TOP 20 VS FORECAST ---
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
        for col in ["Forecast YTD", "Realizado YTD", "Atraso vs Fcast (USD)"]:
            df_exibicao_com_total_f[col] = df_exibicao_com_total_f[col].map(lambda x: f"$ {x:,.2f}")
        
        table_html_snippet_forecast = df_exibicao_com_total_f.to_html(index=False, classes='data-table')
        st.dataframe(df_exibicao_com_total_f, use_container_width=True, hide_index=True)

# ==========================================
# PARTE 8: EXPORTAÇÃO EXECUTIVA (HTML) com LOGO e Paleta Azul
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
            td.kpi-card {{ width: 33.33%; background-color: #f8f9fa !important; border: 1px solid #e9ecef; border-radius: 6px; padding: 14px; border-left: 4px solid #336699 !important; }}
            .chart-box {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 15px; margin-bottom: 30px; overflow-x: auto; }}
            
            /* Estilização Executiva para as Tabelas */
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
                    <td class="kpi-card"><div>REALIZADO YTD</div><div style="font-size:14pt;font-weight:bold;">$ {val_real:,.2f}</div></td>
                    <td class="kpi-card" style="border-left-color: #0066cc !important;"><div>BUDGET YTD</div><div style="font-size:14pt;font-weight:bold;">$ {val_budg:,.2f}</div></td>
                    <td class="kpi-card" style="border-left-color: #3b7aae !important;"><div>FORECAST (2+10)</div><div style="font-size:14pt;font-weight:bold;">$ {val_fcast:,.2f}</div></td>
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
            <div class="chart-box">
                {table_html_snippet_budget}
            </div>

            <h2>4. Análise de Desvios Críticos: TOP 20 Projetos em Atraso YTD vs. Fcast 2+10</h2>
            <div class="chart-box">
                {table_html_snippet_forecast}
            </div>
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
        st.write("**Filtros ativos:**", f"Ano Orçamentário: {ano_s} | Período: Jan a {m_lim}")
        df_view = df_f.copy()
        df_view['Val'] = df_view['Val'].map(lambda x: f"$ {x:,.2f}")
        st.dataframe(df_view, use_container_width=True)
        
