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
    
    # Nomes descritivos fictícios para simular a Coluna I
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
                
            # Construindo estrutura garantindo que Nome_Proj fique na posição equivalente à Coluna I (9ª coluna)
            # Estrutura base: Item(0), Ano(1), Versão(2), Área(3), Tipo(4), Planta(5), Extra1(6), Extra2(7), Nome_Proj(8) + Meses
            data.append([item_cod, a, v, ar, t, p, "Dado_E1", "Dado_E2", nome_proj] + vals)
            
    colunas_ficticias = ["Nro_Item Código", "Ano", "Versão", "Área", "Tipo_Proj Código", "Planta", "Dummy1", "Dummy2", "Nome do Projeto"] + meses
    return pd.DataFrame(data, columns=colunas_ficticias)

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
    c_item = "Nro_Item Código" if "Nro_Item Código" in df_bruto.columns else next((o for o, n in map_c.items() if "item" in n or "nro" in n), df_bruto.columns[0])
    
    # MAPEAMENTO ESTREITO DA COLUNA I (Índice 8 no Python) PARA O NOME DO PROJETO
    c_nome_proj = df_bruto.columns[8] if len(df_bruto.columns) >= 9 else df_bruto.columns[0]
    
    # Forçando leitura da Coluna D (Índice 3) para Área e Tipo de Projeto
    c_area = df_bruto.columns[3] if len(df_bruto.columns) >= 4 else df_bruto.columns[0]
    c_tipo = "Tipo_Proj Código" if "Tipo_Proj Código" in df_bruto.columns else next((o for o, n in map_c.items() if "tipo" in n or "proj" in n), None)
    c_planta = next((o for o, n in map_c.items() if any(x in n for x in ["planta", "filial", "unidade", "site"])), None)

    # Identificação dos Meses
    m_ord = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    m_alvo = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    c_meses = []
    for m in m_alvo:
        match = next((o for o, n in map_c.items() if n == m or n.startswith(m)), None)
        if match: c_meses.append(match)

    fixas = [c_item, c_nome_proj, c_ano, c_ver]
    for col in [c_area, c_tipo, c_planta]:
        if col and col not in fixas: fixas.append(col)

    # Pivotagem estruturada do formato Largo para Longo
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
    c_item = "Nro_Item Código" if "Nro_Item Código" in df_bruto.columns else next((o for o, n in map_c.items() if "item" in n or "nro" in n), df_bruto.columns[0])
    
    # MAPEAMENTO ESTREITO DA COLUNA I (Índice 8 no Python) PARA O NOME DO PROJETO
    c_nome_proj = df_bruto.columns[8] if len(df_bruto.columns) >= 9 else df_bruto.columns[0]
    
    # Forçando leitura da Coluna D (Índice 3) para Área e Tipo de Projeto
    c_area = df_bruto.columns[3] if len(df_bruto.columns) >= 4 else df_bruto.columns[0]
    c_tipo = "Tipo_Proj Código" if "Tipo_Proj Código" in df_bruto.columns else next((o for o, n in map_c.items() if "tipo" in n or "proj" in n), None)
    c_planta = next((o for o, n in map_c.items() if any(x in n for x in ["planta", "filial", "unidade", "site"])), None)

    # Identificação dos Meses
    m_ord = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    m_alvo = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    c_meses = []
    for m in m_alvo:
        match = next((o for o, n in map_c.items() if n == m or n.startswith(m)), None)
        if match: c_meses.append(match)

    fixas = [c_item, c_nome_proj, c_ano, c_ver]
    for col in [c_area, c_tipo, c_planta]:
        if col and col not in fixas: fixas.append(col)

    # Pivotagem estruturada do formato Largo para Longo
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

    # --- ANÁLISE COMPLEMENTAR DE PROJETOS EM ATRASO (TOP 20 ATUALIZADO) ---
    st.write("---")
    st.subheader(f"⚠️ Análise de Desvios: TOP 20 Projetos em Atraso no Desembolso YTD (Até {m_lim})")
    st.markdown("A tabela abaixo rastreia os desvios utilizando a chave estável **Nro_Item Código** combinada com a **Coluna I (Nome do Projeto)**. A ordenação foca nos maiores gargalos monetários cumulativos.")

    v_nomes = df_analise_base["Versão"].unique()
    v_b = next((v for v in v_nomes if any(x in str(v).lower() for x in ['orc', 'budg', 'prev'])), None)
    v_r = next((v for v in v_nomes if 'real' in str(v).lower()), None)

    if not v_b or not v_r:
        st.info("ℹ️ Certifique-se de possuir dados de 'Budget' e 'Realizado' na base para gerar o cruzamento de atrasos.")
    else:
        # Agrupamento estrito incluindo o Nome do Projeto mapeado da coluna I
        df_pivot_itens = df_analise_base.groupby(["Nro_Item Código", "Nome do Projeto", "Área", "Planta", "Versão"])["Val"].sum().unstack(level="Versão").fillna(0).reset_index()
        
        if v_b in df_pivot_itens.columns and v_r in df_pivot_itens.columns:
            # Cálculo do Atraso Monetário
            df_pivot_itens["Atraso (USD)"] = df_pivot_itens[v_b] - df_pivot_itens[v_r]
            df_atrasados = df_pivot_itens[df_pivot_itens["Atraso (USD)"] > 0].copy()
            
            df_atrasados = df_atrasados.rename(columns={v_b: "Budget YTD", v_r: "Realizado YTD"})
            
            # SELEÇÃO EXPANDIDA PARA O TOP 20
            df_top_20 = df_atrasados.sort_values(by="Atraso (USD)", ascending=False).head(20)
            
            if df_top_20.empty:
                st.success("✅ Nenhum projeto apresenta desembolso atrasado em relação ao Budget para os filtros aplicados.")
            else:
                # Extração das colunas finais de auditoria interna
                df_exibicao = df_top_20[["Nro_Item Código", "Nome do Projeto", "Área", "Planta", "Budget YTD", "Realizado YTD", "Atraso (USD)"]].copy()
                
                # CÁLCULO E INCLUSÃO DA LINHA DE TOTAL SOLICITADA
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
                
                # Anexa a linha de total na base da tabela corporativa
                df_exibicao_com_total = pd.concat([df_exibicao, linha_total], ignore_index=True)
                
                # Formatação das colunas numéricas monetárias
                for col in ["Budget YTD", "Realizado YTD", "Atraso (USD)"]:
                    df_exibicao_com_total[col] = df_exibicao_com_total[col].map(lambda x: f"$ {x:,.2f}")
                
                # Renderização da tabela limpa na interface
                st.dataframe(df_exibicao_com_total, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ Colunas de cenários insuficientes para o cruzamento de dados.")

with st.expander("🔍 Ver Tabela de Dados Brutos"):
    df_view = df_f.copy()
    df_view['Val'] = df_view['Val'].map(lambda x: f"$ {x:,.2f}")
    st.dataframe(df_view, use_container_width=True)
    
