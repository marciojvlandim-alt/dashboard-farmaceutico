import io
from typing import Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Dashboard de Auditoria Farmacêutica",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================
# Configurações visuais
# =============================
CUSTOM_CSS = """
<style>
.block-container {
    padding-top: 1.4rem;
    padding-bottom: 1.5rem;
}
.metric-card {
    background: #ffffff;
    border: 1px solid #e9ecef;
    border-radius: 16px;
    padding: 16px 18px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.small-note {
    color: #6c757d;
    font-size: 0.9rem;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

REQUIRED_COLUMNS = {
    "CRM": "CRM",
    "Cat": "Cat",
    "Médico": "Médico",
    "PX": "PX",
    "Produto": "Produto",
    "PX Mercado": "PX Mercado",
    "Endereço": "Endereço",
    "Cidade": "Cidade",
}

COLUMN_ALIASES = {
    "crm": "CRM",
    "cat": "Cat",
    "medico": "Médico",
    "médico": "Médico",
    "px": "PX",
    "produto": "Produto",
    "px mercado": "PX Mercado",
    "px_mercado": "PX Mercado",
    "endereco": "Endereço",
    "endereço": "Endereço",
    "cidade": "Cidade",
}


# =============================
# Funções auxiliares
# =============================
def normalize_text(value: str) -> str:
    if value is None:
        return ""
    return (
        str(value)
        .strip()
        .replace("\n", " ")
        .replace("\t", " ")
    )


def normalize_column_name(col: str) -> str:
    col = normalize_text(col).lower()
    return COLUMN_ALIASES.get(col, normalize_text(col))


@st.cache_data(show_spinner=False)
def load_data(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        # tenta separadores comuns no Brasil automaticamente
        raw = uploaded_file.getvalue()
        for sep in [",", ";", "\t", "|"]:
            try:
                df_test = pd.read_csv(io.BytesIO(raw), sep=sep)
                if df_test.shape[1] > 1:
                    df = df_test.copy()
                    break
            except Exception:
                df = None
        if df is None:
            raise ValueError("Não foi possível ler o CSV. Verifique o separador do arquivo.")
    elif name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file)
    else:
        raise ValueError("Formato não suportado. Envie um arquivo CSV, XLSX ou XLS.")

    df.columns = [normalize_column_name(c) for c in df.columns]

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            "As seguintes colunas obrigatórias não foram encontradas: "
            + ", ".join(missing)
        )

    df = df[list(REQUIRED_COLUMNS.keys())].copy()

    # Tratamento de texto
    text_cols = ["CRM", "Cat", "Médico", "Produto", "Endereço", "Cidade"]
    for col in text_cols:
        df[col] = df[col].astype(str).map(normalize_text)
        df[col] = df[col].replace({"nan": pd.NA, "None": pd.NA, "": pd.NA})

    # Tratamento numérico
    for col in ["PX", "PX Mercado"]:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
            .str.replace(" ", "", regex=False)
        )
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Limpeza final
    df["Produto"] = df["Produto"].fillna("Não informado")
    df["Cidade"] = df["Cidade"].fillna("Não informado")
    df["Médico"] = df["Médico"].fillna("Não informado")
    df["CRM"] = df["CRM"].fillna("Não informado")
    df["Cat"] = df["Cat"].fillna("Não informado")
    df["Endereço"] = df["Endereço"].fillna("Não informado")

    return df


def format_number(value: float) -> str:
    return f"{value:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")


def donut_chart(
    data: pd.DataFrame,
    names_col: str,
    values_col: str,
    title: str,
    top_n: int | None = None,
    hole: float = 0.58,
):
    chart_df = data.copy()
    chart_df = chart_df[chart_df[values_col] > 0].sort_values(values_col, ascending=False)

    if chart_df.empty:
        st.info(f"Sem dados para exibir em: {title}")
        return

    if top_n is not None and len(chart_df) > top_n:
        top = chart_df.head(top_n).copy()
        other_sum = chart_df.iloc[top_n:][values_col].sum()
        if other_sum > 0:
            other_row = pd.DataFrame([{names_col: "Outros", values_col: other_sum}])
            chart_df = pd.concat([top, other_row], ignore_index=True)
        else:
            chart_df = top

    fig = px.pie(
        chart_df,
        names=names_col,
        values=values_col,
        hole=hole,
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate=f"<b>%{{label}}</b><br>{values_col}: %{{value:,.0f}}<br>Share: %{{percent}}<extra></extra>",
    )
    fig.update_layout(
        title=title,
        legend_title="",
        margin=dict(l=10, r=10, t=60, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
        height=480,
    )
    st.plotly_chart(fig, use_container_width=True)


# =============================
# Cabeçalho
# =============================
st.title("📊 Dashboard de Auditoria do Mercado Farmacêutico")
st.caption(
    "Faça o upload da sua base em CSV/XLSX, aplique filtros e acompanhe KPIs e participações por médico, cidade e produto."
)

with st.expander("Estrutura esperada da planilha", expanded=False):
    sample = pd.DataFrame(
        {
            "CRM": ["12345", "67890"],
            "Cat": ["A", "B"],
            "Médico": ["Dr. João", "Dra. Maria"],
            "PX": [120, 80],
            "Produto": ["Produto X", "Produto Y"],
            "PX Mercado": [600, 450],
            "Endereço": ["Rua 1", "Rua 2"],
            "Cidade": ["Fortaleza", "Sobral"],
        }
    )
    st.dataframe(sample, use_container_width=True, hide_index=True)

uploaded_file = st.file_uploader(
    "Envie sua planilha (.csv, .xlsx ou .xls)",
    type=["csv", "xlsx", "xls"],
)

if not uploaded_file:
    st.info("Envie um arquivo para carregar o dashboard.")
    st.stop()

try:
    df = load_data(uploaded_file)
except Exception as e:
    st.error(f"Erro ao processar o arquivo: {e}")
    st.stop()

# =============================
# Sidebar com filtros
# =============================
st.sidebar.header("Filtros")

product_options = sorted(df["Produto"].dropna().unique().tolist())
city_options = sorted(df["Cidade"].dropna().unique().tolist())

selected_products = st.sidebar.multiselect(
    "Produto",
    options=product_options,
    default=product_options,
    placeholder="Selecione um ou mais produtos",
)

selected_cities = st.sidebar.multiselect(
    "Cidade",
    options=city_options,
    default=city_options,
    placeholder="Selecione uma ou mais cidades",
)

filtered_df = df.copy()
if selected_products:
    filtered_df = filtered_df[filtered_df["Produto"].isin(selected_products)]
if selected_cities:
    filtered_df = filtered_df[filtered_df["Cidade"].isin(selected_cities)]

if filtered_df.empty:
    st.warning("Nenhum registro encontrado para os filtros selecionados.")
    st.stop()

# =============================
# KPIs
# =============================
total_px = filtered_df["PX"].sum()
total_medicos = filtered_df["CRM"].nunique()
total_px_mercado = filtered_df["PX Mercado"].sum()
share_marca = (total_px / total_px_mercado * 100) if total_px_mercado > 0 else 0

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Total de Prescrições da Marca", format_number(total_px))
with k2:
    st.metric("Total de Médicos Prescritores", format_number(total_medicos))
with k3:
    st.metric("Total de Prescrições do Mercado", format_number(total_px_mercado))
with k4:
    st.metric("Share da Marca vs. Mercado", f"{share_marca:.2f}%")

st.markdown("---")

# =============================
# Bases agregadas
# =============================
medico_df = (
    filtered_df.groupby("Médico", as_index=False)["PX"]
    .sum()
    .sort_values("PX", ascending=False)
)

cidade_df = (
    filtered_df.groupby("Cidade", as_index=False)["PX"]
    .sum()
    .sort_values("PX", ascending=False)
)

produto_df = (
    filtered_df.groupby("Produto", as_index=False)["PX"]
    .sum()
    .sort_values("PX", ascending=False)
)

# =============================
# Gráficos
# =============================
g1, g2 = st.columns(2)
with g1:
    donut_chart(
        medico_df,
        names_col="Médico",
        values_col="PX",
        title="Gráfico 1 — Participação dos Médicos",
        top_n=10,
    )
with g2:
    donut_chart(
        cidade_df,
        names_col="Cidade",
        values_col="PX",
        title="Gráfico 2 — Participação por Cidade",
        top_n=None,
    )

st.markdown("\n")
donut_chart(
    produto_df,
    names_col="Produto",
    values_col="PX",
    title="Gráfico 3 — Share de Produtos",
    top_n=None,
)

# =============================
# Tabela analítica
# =============================
st.subheader("Visão Analítica")
resumo_cols = ["CRM", "Cat", "Médico", "Produto", "PX", "PX Mercado", "Cidade", "Endereço"]
st.dataframe(
    filtered_df[resumo_cols].sort_values(["PX", "Médico"], ascending=[False, True]),
    use_container_width=True,
    hide_index=True,
)

csv_export = filtered_df.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="Baixar dados filtrados em CSV",
    data=csv_export,
    file_name="auditoria_filtrada.csv",
    mime="text/csv",
)

st.caption(
    "Dica: para melhor leitura no celular, abra o app em tela cheia e use os filtros pela barra lateral."
)
