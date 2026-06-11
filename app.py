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
# PARTE 4: LAYOUT VERTICAL E ANÁLISE TOP 20
# ==========================================
    st.write("---")
    
    # Cor padrão para manter a identidade visual nos gráficos e no PDF
    cor_graficos = ["#a11f1f"]  # Vermelho corporativo (ou troque por "#0066cc" para azul)
    
    # 1. Comparativo Geral
    st.subheader(f"📊 Comparativo Geral Capex YTD (Jan a {m_lim}) - USD")
    fig_main = px.bar(df_f.groupby("Versão")["Val"].sum().reset_index(), x="Versão", y="Val", color_discrete_sequence=cor_graficos, text_auto='.2f')
    fig_main.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
    fig_main.update_layout(yaxis_tickformat='$', height=450, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_main, use_container_width=True)

    st.write("---")
    
    # 2. Cenários por Tipo de Projeto
    st.subheader("📊 Cenários por Tipo de Projeto (Budget vs Fcast vs Realizado)")
    df_proj_ver = df_f.groupby(["Projeto", "Versão"])["Val"].sum().reset_index()
    fig_p = px.bar(df_proj_ver, x="Projeto", y="Val", color="Versão", barmode="group", text_auto='.2f')
    fig_p.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
    fig_p.update_layout(yaxis_tickformat='$', xaxis_title="Tipo de Projeto", legend_title="Cenário", xaxis={'categoryorder':'total descending'}, height=480, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_p, use_container_width=True)
        
    st.write("---")

    # 3. Distribuição por Site
    st.subheader("🏢 Distribuição Total por Site")
    fig_pl = px.bar(df_f.groupby("Planta")["Val"].sum().reset_index().sort_values("Val", ascending=False), x="Planta", y="Val", color_discrete_sequence=cor_graficos, text_auto='.2f')
    fig_pl.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
    fig_pl.update_layout(yaxis_tickformat='$', showlegend=False, xaxis_title="Site", height=450, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
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
    fig_ev.update_layout(yaxis_tickformat='$', height=450, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_ev, use_container_width=True)

    # 5. TABELA ANALÍTICA DE ATRASOS
    st.write("---")
    st.subheader(f"⚠️ Análise de Desvios: TOP 20 Projetos em Atraso no Desembolso YTD (Até {m_lim})")
    st.markdown("A tabela abaixo rastreia os desvios utilizando a chave **Nro_Item Código** combinada com o **Nome do Projeto (Coluna I)**.")

    v_nomes = df_analise_base["Versão"].unique()
    v_b = next((v for v in v_nomes if any(x in str(v).lower() for x in ['orc', 'budg', 'prev'])), None)
    v_r = next((v for v in v_nomes if 'real' in str(v).lower()), None)

    if not v_b or not v_r:
        st.info("ℹ️ Certifique-se de possuir dados de 'Budget' e 'Realizado' para calcular os desvios.")
    else:
        df_pivot_itens = df_analise_base.groupby(["Nro_Item Código", "Nome do Projeto", "Área", "Planta", "Versão"])["Val"].sum().unstack(level="Versão").fillna(0).reset_index()
        
        if v_b in df_pivot_itens.columns and v_r in df_pivot_itens.columns:
            df_pivot_itens["Atraso (USD)"] = df_pivot_itens[v_b] - df_pivot_itens[v_r]
            df_atrasados = df_pivot_itens[df_pivot_itens["Atraso (USD)"] > 0].copy()
            
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
                    "Nro_Item Código": "TOTAL DO TOP 20",
                    "Nome do Projeto": "---",
                    "Área": "---",
                    "Planta": "---",
                    "Budget YTD": total_b,
                    "Realizado YTD": total_r,
                    "Atraso (USD)": total_a
                }])
                
                df_exibicao_com_total = pd.concat([df_exibicao, linha_total], ignore_index=True)
                
                for col in ["Budget YTD", "Realizado YTD", "Atraso (USD)"]:
                    df_exibicao_com_total[col] = df_exibicao_com_total[col].map(lambda x: f"$ {x:,.2f}")
                
                st.dataframe(df_exibicao_com_total, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ Colunas de cenários insuficientes para o cruzamento de dados.")


# ==========================================
# PARTE COMPLEMENTAR: EXPORTAÇÃO EXECUTIVA CORRIGIDA
# ==========================================
st.write("---")
st.subheader("🖨️ Exportação Completa para Diretoria")
st.markdown("Clique no botão abaixo para gerar a versão oficial consolidada com **KPIs, Gráficos Coloridos e Tabelas**.")

try:
    # Forçar a renderização com cores explícitas antes de converter para o HTML de exportação
    fig_main.update_layout(colorway=cor_graficos)
    fig_pl.update_layout(colorway=cor_graficos)
    
    chart_main_html = fig_main.to_html(full_html=False, include_plotlyjs='cdn')
    chart_p_html = fig_p.to_html(full_html=False, include_plotlyjs='cdn')
    chart_pl_html = fig_pl.to_html(full_html=False, include_plotlyjs='cdn')
    chart_ev_html = fig_ev.to_html(full_html=False, include_plotlyjs='cdn')

    html_report = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Relatório de Investimentos Capex</title>
        <style>
            /* IMPORTANTE: Forçar o navegador a imprimir cores de fundo e gráficos */
            * {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
            @media print {{
                .no-print {{ display: none; }}
                body {{ background: #fff; color: #000; padding: 0; }}
                .report-wrapper {{ border: none !important; box-shadow: none !important; padding: 0 !important; max-width: 100% !important; }}
            }}
            @page {{
                size: A4;
                margin: 20mm 15mm 20mm 15mm;
            }}
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                color: #2b2b2b;
                margin: 0;
                padding: 20px;
                line-height: 1.4;
                background-color: #fafafa;
            }}
            .report-wrapper {{
                max-width: 900px;
                margin: 0 auto;
                background: #fff;
                padding: 40px;
                border: 1px solid #e0e0e0;
                box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            }}
            .header {{
                border-bottom: 3px solid #a11f1f;
                padding-bottom: 12px;
                margin-bottom: 25px;
            }}
            .title {{ font-size: 20pt; font-weight: bold; color: #a11f1f; text-transform: uppercase; letter-spacing: 0.5px; }}
            .subtitle {{ font-size: 11pt; color: #555; margin-top: 5px; font-weight: 500; }}
            .meta-date {{ font-size: 9pt; color: #888; font-style: italic; margin-top: 2px; }}
            
            h2 {{
                font-size: 13pt;
                color: #1a1a1a;
                margin: 35px 0 15px 0;
                padding-left: 8px;
                border-left: 4px solid #a11f1f;
                text-transform: uppercase;
                page-break-after: avoid;
            }}
            
            p {{ margin: 0 0 12px 0; color: #444; text-align: justify; font-size: 10pt; }}
            
            table.kpi-table {{ width: 100%; border-collapse: separate; border-spacing: 12px 0; margin: 15px -12px; }}
            td.kpi-card {{ width: 33.33%; background-color: #f8f9fa !important; border: 1px solid #e9ecef; border-radius: 6px; padding: 14px; vertical-align: top; border-left: 4px solid #a11f1f !important; }}
            .kpi-label {{ font-size: 8pt; color: #6c757d; font-weight: bold; text-transform: uppercase; }}
            .kpi-value {{ font-size: 15pt; font-weight: bold; color: #1a1a1a; margin-top: 4px; }}
            
            .chart-box {{
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 15px;
                margin-bottom: 30px;
                page-break-inside: avoid;
            }}
            
            table.data-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 20px; page-break-inside: avoid; }}
            table.data-table th {{ background-color: #343a40 !important; color: white !important; font-weight: bold; text-align: left; padding: 9px 10px; font-size: 9pt; border: 1px solid #343a40; text-transform: uppercase; }}
            table.data-table td {{ padding: 8px 10px; border: 1px solid #dee2e6; font-size: 9pt; }}
            table.data-table tr:nth-child(even) {{ background-color: #f8f9fa !important; }}
            table.data-table tr.total-row {{ background-color: #e9ecef !important; font-weight: bold; }}
            table.data-table tr.total-row td {{ border-top: 2px solid #495057; border-bottom: 2px solid #495057; color: #000; }}
            .numeric {{ text-align: right; }}
            .negative {{ color: #c9302c; font-weight: bold; }}
            
            .footer-notice {{ margin-top: 40px; font-size: 8pt; color: #999; text-align: center; border-top: 1px solid #eee; padding-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="report-wrapper">
            <div class="header">
                <div class="title">Capex - Evolução do Investimento</div>
                <div class="subtitle">Relatório Executivo Regional — Manufatura América do Sul</div>
                <div class="meta-date">Filtros Aplicados: Ano Base {ano_s} | Visão YTD Acumulada até {m_lim}</div>
            </div>
            
            <p>Este report consolidado reflete o status oficial de investimentos da região, sumarizando a performance financeira corporativa e os desvios de desembolsos mapeados no período.</p>

            <table class="kpi-table">
                <tr>
                    <td class="kpi-card">
                        <div class="kpi-label">Realizado Cumulativo YTD</div>
                        <div class="kpi-value">$ {val_real:,.2f}</div>
                    </td>
                    <td class="kpi-card" style="border-left-color: #0066cc !important;">
                        <div class="kpi-label">Budget Original YTD</div>
                        <div class="kpi-value">$ {val_budg:,.2f}</div>
                    </td>
                    <td class="kpi-card" style="border-left-color: #3b7aae !important;">
                        <div class="kpi-label">Forecast Projetado (2+10)</div>
                        <div class="kpi-value">$ {val_fcast:,.2f}</div>
                    </td>
                </tr>
            </table>

            <h2>1. Comparativo Geral Capex YTD - Visão Consolidada</h2>
            <div class="chart-box">{chart_main_html}</div>

            <h2>2. Cenários por Tipo de Categoria de Projeto</h2>
            <div class="chart-box">{chart_p_html}</div>

            <h2>3. Distribuição Total de Recursos por Site (Plantas)</h2>
            <div class="chart-box">{chart_pl_html}</div>

            <h2>4. Evolução Temporal Mensal dos Desembolsos</h2>
            <div class="chart-box">{chart_ev_html}</div>

            <h2>5. Análise de Desvios Críticos: TOP 20 Projetos em Atraso YTD</h2>
            <p>Iniciativas que registram maior diferimento físico-financeiro acumulado em relação às metas originais estabelecidas no Budget.</p>
            
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Item Código</th>
                        <th>Nome do Projeto</th>
                        <th>Área</th>
                        <th>Planta</th>
                        <th class="numeric">Budget YTD</th>
                        <th class="numeric">Realizado YTD</th>
                        <th class="numeric">Atraso (USD)</th>
                    </tr>
                </thead>
                <tbody>
    """

    if 'df_top_20' in locals() and not df_top_20.empty:
        for _, r in df_top_20.iterrows():
            html_report += f"""
                <tr>
                    <td>{r['Nro_Item Código']}</td>
                    <td>{r['Nome do Projeto']}</td>
                    <td>{r['Área']}</td>
                    <td>{r['Planta']}</td>
                    <td class="numeric">$ {r['Budget YTD']:,.2f}</td>
                    <td class="numeric">$ {r['Realizado YTD']:,.2f}</td>
                    <td class="numeric negative">$ {r['Atraso (USD)']:,.2f}</td>
                </tr>
            """
        html_report += f"""
                <tr class="total-row">
                    <td>TOTAL TOP 20</td>
                    <td>---</td>
                    <td>---</td>
                    <td>---</td>
                    <td class="numeric">$ {total_b:,.2f}</td>
                    <td class="numeric">$ {total_r:,.2f}</td>
                    <td class="numeric negative">$ {total_a:,.2f}</td>
                </tr>
        """
    else:
        html_report += """<tr><td colspan="7" style="text-align:center;">Nenhum desvio crítico registrado para o período.</td></tr>"""

    html_report += f"""
                </tbody>
            </table>
            
            <div class="footer-notice">
                AGCO SA — Sistema de Relatórios de Manufatura SA — Gerado em {datetime.now().strftime("%d/%m/%Y")} — Altamente Confidencial
            </div>
        </div>
    </body>
    </html>
    """

    st.download_button(
        label="📥 Baixar Relatório Executivo Completo (Com Gráficos)",
        data=html_report,
        file_name=f"Relatorio_Diretoria_Capex_{m_lim}_{ano_s}.html",
        mime="text/html",
        help="Baixa o book completo formatado. Abra o arquivo e use Ctrl+P para Salvar como PDF perfeito."
    )
except Exception as err_pdf:
    st.sidebar.error(f"Erro ao estruturar gráficos no report: {err_pdf}")

# EXPANDER DE SEGURANÇA (DADOS BRUTOS)
with st.expander("🔍 Ver Tabela de Dados Brutos"):
    if 'df_f' in locals() and not df_f.empty:
        df_view = df_f.copy()
        df_view['Val'] = df_view['Val'].map(lambda x: f"$ {x:,.2f}")
        st.dataframe(df_view, use_container_width=True)
    else:
        st.info("Nenhum dado bruto encontrado
