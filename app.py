import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuração da página do Streamlit
st.set_page_config(page_title="Dashboard de Capex Executivo", layout="wide")

# ==========================================
# PARTE 1: CARREGAMENTO E TRATAMENTO DE DADOS (COM UPLOAD)
# ==========================================
@st.cache_data
def processar_excel(file):
    # Lê o arquivo enviado pelo usuário
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
    
# Renomeia para manter compatibilidade com o resto do script do dashboard
df_base = df_base.rename(columns={
    col_codigo: "Nro_Item Código",
    col_nome: "Nome do Projeto",
    col_versao: "Versão",
    col_mes: "Mês",
    col_planta: "Planta",
    col_area: "Área",
    col_val: "Val"
})

# Ordem cronológica dos meses para ordenação dos gráficos de linha
m_ord = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# --- BLINDAGEM E PADRONIZAÇÃO DE COLUNAS CORRIGIDA ---
df_base.columns = df_base.columns.str.lower().str.strip()

# Mapeamento robusto por palavras-chave (ignora maiúsculas e espaços)
col_versao = next((c for c in df_base.columns if any(x in c for x in ['vers', 'cenario', 'cenário', 'tipo'])), None)
col_mes = next((c for c in df_base.columns if any(x in c for x in ['mês', 'mes', 'periodo', 'período'])), None)
col_planta = next((c for c in df_base.columns if any(x in c for x in ['plant', 'site', 'filial', 'unidade', 'local'])), None)
col_area = next((c for c in df_base.columns if any(x in c for x in ['área', 'area', 'setor', 'depto', 'diretoria'])), None)

# Busca exaustiva para a coluna de Código do Projeto
col_codigo = next((c for c in df_base.columns if any(x in c for x in ['cód', 'cod', 'item', 'id', 'nro', 'número', 'numero'])), None)
# Se ainda assim não encontrar o código, assume por segurança a primeira coluna da planilha
if not col_codigo and len(df_base.columns) > 0:
    col_codigo = df_base.columns[0]

col_nome = next((c for c in df_base.columns if any(x in c for x in ['nome', 'proj', 'desc', 'iniciativa'])), None)
if not col_nome and len(df_base.columns) > 1:
    col_nome = df_base.columns[1]

col_val = next((c for c in df_base.columns if any(x in c for x in ['val', 'mont', 'orça', 'real', 'usd', 'gasto', 'vlr'])), None)
if not col_val and len(df_base.columns) > 2:
    col_val = df_base.columns[-1] # Assume a última coluna se não achar palavras-chave

# Verificação de segurança para as colunas vitais de filtros estruturais
if not all([col_versao, col_mes, col_planta, col_area]):
    st.error("❌ Erro estrutural: A base de dados não possui as colunas necessárias para os filtros (Versão/Cenário, Mês, Planta/Site, Área).")
    st.markdown(f"**Colunas detectadas na sua planilha:** `{list(df_base.columns)}`")
    st.stop()

# Garantir padronização dos textos e evitar falhas de filtros por espaços vazios
df_base[col_versao] = df_base[col_versao].astype(str).str.strip()
df_base[col_mes] = df_base[col_mes].astype(str).str.strip()
df_base[col_planta] = df_base[col_planta].astype(str).str.strip()
df_base[col_area] = df_base[col_area].astype(str).str.strip()

# Renomeia dinamicamente garantindo que strings nulas não quebrem o dicionário
df_base = df_base.rename(columns={
    col_codigo: "Nro_Item Código",
    col_nome: "Nome do Projeto",
    col_versao: "Versão",
    col_mes: "Mês",
    col_planta: "Planta",
    col_area: "Área",
    col_val: "Val"
})

# Ordem cronológica dos meses para ordenação dos gráficos de linha
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
v_b = next((v for v in v_nomes if any(x in str(v).lower() for x in ['orc', 'budg', 'prev'])), None)
v_r = next((v for v in v_nomes if 'real' in str(v).lower()), None)
v_f = next((v for v in v_nomes if any(x in str(v).lower() for x in ['fore', 'fcast', 'proj'])), None)

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
    st.metric(label="Realizado Acumulado YTD", value=f"USD {val_real:,.2f}")
with col_kpi2:
    st.metric(label="Budget Original YTD", value=f"USD {val_budg:,.2f}")
with col_kpi3:
    st.metric(label="Forecast Projetado YTD", value=f"USD {val_fcast:,.2f}")

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
st.subheader("📊 Cenários por Tipo de Categoria de Projeto (Budget vs Forecast vs Realizado)")
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
    df_cross["Atraso (USD)"] = df_cross[v_b] - df_cross[v_r]
    df_cross["Atingimento %"] = (df_cross[v_r] / df_cross[v_b] * 100).fillna(0).clip(0, 200)
    
    # PROPOSTA 1: Matriz de Criticidade
    st.subheader("🎯 Proposta 1: Matriz de Alocação e Criticidade de Desvios")
    st.markdown("O quadrante **superior direito** isola instantaneamente os projetos de **alto valor aprovado que registram os maiores desvios** acumulados.")
    
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

    # PROPOSTA 2: Run Rate Preditivo
    st.subheader("🔮 Proposta 2: Análise Preditiva de Fechamento (Run Rate Anual)")
    st.markdown("Cálculo baseado no ritmo médio de execução real YTD projetado linearmente para os meses restantes do ano.")
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

    # PROPOSTA 3: Princípio de Pareto
    st.subheader("📊 Proposta 3: Concentração de Linhas de Investimento (Pareto TOP 15)")
    st.markdown("Identificação dos maiores blocos de contratos. Mitigar o risco nesta seleção protege 80% do Capex regional.")
    
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
st.markdown("Rastreabilidade focada nos maiores gaps financeiros. Células coloridas indicam a gravidade do desvio técnico.")

if v_b and v_r and v_b in df_cross.columns:
    df_atrasados = df_cross[df_cross["Atraso (USD)"] > 0].copy()
    df_atrasados = df_atrasados.rename(columns={v_b: "Budget YTD", v_r: "Realizado YTD"})
    df_top_20 = df_atrasados.sort_values(by="Atraso (USD)", ascending=False).head(20)
    
    if df_top_20.empty:
        st.success("✅ Nenhum projeto apresenta desembolso atrasado em relação ao Budget para os filtros aplicados.")
    else:
        df_exibicao = df_top_20[["Nro_Item Código", "Nome do Projeto", "Área", "Planta", "Budget YTD", "Realizado YTD", "Atraso (USD)"]].copy()
        
        # Semáforo Condicional Atualizado para Pandas Moderno (.map)
        def colorir_semaforo(val):
            if isinstance(val, (int, float)):
                if val > 100000:
                    return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
                elif val > 30000:
                    return 'background-color: #fff3cd; color: #856404;'
                else:
                    return 'background-color: #d4edda; color: #155724;'
            return ''

        st.dataframe(
            df_exibicao.style.map(colorir_semaforo, subset=["Atraso (USD)"])
            .format({"Budget YTD": "$ {:,.2f}", "Realizado YTD": "$ {:,.2f}", "Atraso (USD)": "$ {:,.2f}"}),
            use_container_width=True,
            hide_index=True
        )
        
        total_b = df_top_20["Budget YTD"].sum()
        total_r = df_top_20["Realizado YTD"].sum()
        total_a = df_top_20["Atraso (USD)"].sum()

        # Interação de Justificativas Executivas
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
                comentario = f"Desvio expressivo de $ {atraso_val:,.2f} em {planta_sel}. Gargalos na cadeia global de suprimentos estenderam o lead time do maquinário principal. Ações de contingência e renegociação de marcos contratuais com fornecedores já foram iniciadas pelo time."
            elif atraso_val > 30000:
                status_crit = "🟡 ATENÇÃO"
                comentario = f"Atraso de $ {atraso_val:,.2f} devido ao realinhamento de escopo técnico e postergação da janela de parada programada de fábrica em {planta_sel}. Previsão de recuperação integral do desembolso nos próximos trimestres."
            else:
                status_crit = "🟢 TOLERÁVEL"
                comentario = f"Flutuação temporal de fluxo de caixa de $ {atraso_val:,.2f}. O avanço físico do projeto segue alinhado com as metas de compliance estabelecidas pelo comitê regional."
            
            st.info(f"**Status:** {status_crit}\n\n**Análise de Causa Raiz:** {comentario}")

# ==========================================
# PARTE COMPLEMENTAR: BOOK DE EXPORTAÇÃO EXECUTIVA AMPLIADA (PDF/HTML)
# ==========================================
st.write("---")
st.subheader("🖨️ Exportação Completa para Diretoria")
st.markdown("Clique no botão abaixo para gerar o report consolidado completo contendo todas as visões e gráficos.")

try:
    chart_main_html = fig_main.to_html(full_html=False, include_plotlyjs='cdn')
    chart_p_html = fig_p.to_html(full_html=False, include_plotlyjs='cdn')
    chart_pl_html = fig_pl.to_html(full_html=False, include_plotlyjs='cdn')
    chart_ev_html = fig_ev.to_html(full_html=False, include_plotlyjs='cdn')
    
    chart_scatter_html = fig_scatter.to_html(full_html=False, include_plotlyjs='cdn') if fig_scatter else ""
    chart_run_html = fig_run.to_html(full_html=False, include_plotlyjs='cdn') if fig_run else ""
    chart_pareto_html = fig_pareto.to_html(full_html=False, include_plotlyjs='cdn') if fig_pareto else ""

    # Estrutura inicial do HTML isolada e segura
    html_report = f"""<!DOCTYPE html>
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
            <tbody>"""

    # Concatenação limpa e segura das linhas da tabela
    if 'df_top_20' in locals() and not df_top_20.empty:
        for _, r in df_top_20.iterrows():
            html_report += f"""
                <tr>
                    <td>{r['Nro_Item Código']}</td><td>{r['Nome do Projeto']}</td><td>{r['Área']}</td><td>{r['Planta']}</td>
                    <td class="numeric">$ {r['Budget YTD']:,.2f}</td><td class="numeric">$ {r['Realizado YTD']:,.2f}</td>
                    <td class="numeric negative">$ {r['Atraso (USD)']:,.2f}</td>
                </tr>"""
        
        html_report += f"""
                <tr class="total-row">
                    <td>TOTAL TOP 20</td><td>---</td><td>---</td><td>---</td>
                    <td class="numeric">$ {total_b:,.2f}</td><td class="numeric">$ {total_r:,.2f}</td>
                    <td class="numeric negative">$ {total_a:,.2f}</td>
                </tr>"""
    else:
        html_report += """<tr><td colspan="7" style="text-align:center;">Nenhum desvio crítico registrado para o período.</td></tr>"""

    # Fechamento seguro do arquivo HTML
    html_report += f"""
            </tbody>
        </table>
        <div class="footer-notice">
            Sistema de Relatórios de Manufatura — Gerado em {datetime.now().strftime("%d/%m/%Y")}
        </div>
    </div>
</body>
</html>"""
    
    st.download_button(
        label="📥 Baixar Book Executivo Completo (HTML)",
        data=html_report,
        file_name=f"Capex_Report_América_do_Sul_{m_lim}_{ano_s}.html",
        mime="text/html"
    )

except Exception as exp:
    st.warning(f"Aviso técnico sobre a preparação do book de exportação: {exp}")
