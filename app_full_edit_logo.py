
import os
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Orçamentos G&V", layout="wide")

# === Logo ===
LOGO_PATH = "61107_G&V Florestal_040722_ff-01.jpg"
with st.container():
    cols = st.columns([1,2,1])
    with cols[1]:
        try:
            st.image(LOGO_PATH, use_container_width=False, width=320)
        except Exception:
            st.markdown("## G&V FLORESTAL")

CSV_PATH = "orcamentos.csv"

ESTADOS_BR = ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG",
              "PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"]

PRODUTOS_IMPOSTO = {
    "Cavaco": 0.03,
    "Tora": 0.06,
    "Lenha": 0.03,
}

# ----------------- Utilidades -----------------
def color_for_pct(pct_value_percent: float) -> str:
    """Retorna a cor CSS conforme % (0-100)."""
    if pct_value_percent < 20:
        return "red"
    elif pct_value_percent <= 30:
        return "orange"
    return "green"

def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "data_hora",
        # Identificação
        "nome_orcamento","estado","unidade","tipo_produto",
        # Entradas originais
        "preco_bruto","custo_madeira","custo_servicos",
        "km_total","preco_km","frete_fixo_unidade",
        "comissao_compra","comissao_venda",
        # Derivados
        "imposto","transporte","custo_total","liquido","%_lucro"
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = "" if c in ["data_hora","nome_orcamento","estado","unidade","tipo_produto"] else 0.0
    # Tipos numéricos
    for num_c in ["preco_bruto","custo_madeira","custo_servicos","km_total","preco_km",
                  "frete_fixo_unidade","comissao_compra","comissao_venda",
                  "imposto","transporte","custo_total","liquido","%_lucro"]:
        df[num_c] = pd.to_numeric(df[num_c], errors="coerce").fillna(0.0)
    return df[cols]

def load_table(filepath: str) -> pd.DataFrame:
    if not os.path.exists(filepath):
        return ensure_columns(pd.DataFrame())
    df = pd.read_csv(filepath)
    return ensure_columns(df)

def save_table(df: pd.DataFrame, filepath: str) -> None:
    df.to_csv(filepath, index=False)

def calculo_transporte(km_total: float, preco_km: float, unidade: str, frete_fixo_unidade: float = 0.0) -> float:
    if frete_fixo_unidade and frete_fixo_unidade > 0:
        return float(frete_fixo_unidade)
    divisor = 30.0 if unidade == "Tonelada" else 105.0
    return (km_total * preco_km) / divisor if divisor > 0 else 0.0

def calcular(preco_bruto: float,
             custo_madeira: float,
             tipo_produto: str,
             custo_servicos: float,
             km_total: float,
             preco_km: float,
             unidade: str,
             frete_fixo_unidade: float,
             comissao_compra: float,
             comissao_venda: float) -> dict:
    imposto = PRODUTOS_IMPOSTO.get(tipo_produto, 0.0) * preco_bruto
    transporte = calculo_transporte(km_total, preco_km, unidade, frete_fixo_unidade)
    custo_total = (custo_madeira + imposto + custo_servicos +
                   transporte + comissao_compra + comissao_venda)
    liquido = preco_bruto - custo_total
    pct_frac = (liquido / preco_bruto) if preco_bruto > 0 else 0.0
    return {
        "imposto": imposto,
        "transporte": transporte,
        "custo_total": custo_total,
        "liquido": liquido,
        "pct_frac": pct_frac,  # 0-1
        "pct_percent": pct_frac * 100.0,  # 0-100
    }

def append_row(nome: str, estado: str, unidade: str, tipo_produto: str,
               preco_bruto: float, custo_madeira: float, custo_servicos: float,
               km_total: float, preco_km: float, frete_fixo_unidade: float,
               comissao_compra: float, comissao_venda: float) -> None:
    df = load_table(CSV_PATH)
    res = calcular(preco_bruto, custo_madeira, tipo_produto, custo_servicos,
                   km_total, preco_km, unidade, frete_fixo_unidade,
                   comissao_compra, comissao_venda)
    new_row = {
        "data_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "nome_orcamento": nome,
        "estado": estado,
        "unidade": unidade,
        "tipo_produto": tipo_produto,
        "preco_bruto": preco_bruto,
        "custo_madeira": custo_madeira,
        "custo_servicos": custo_servicos,
        "km_total": km_total,
        "preco_km": preco_km,
        "frete_fixo_unidade": frete_fixo_unidade,
        "comissao_compra": comissao_compra,
        "comissao_venda": comissao_venda,
        "imposto": res["imposto"],
        "transporte": res["transporte"],
        "custo_total": res["custo_total"],
        "liquido": res["liquido"],
        "%_lucro": res["pct_frac"],
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_table(df, CSV_PATH)

def delete_row(idx: int) -> None:
    df = load_table(CSV_PATH)
    if 0 <= idx < len(df):
        df = df.drop(idx).reset_index(drop=True)
        save_table(df, CSV_PATH)

# ----------------- UI -----------------
aba_novo, aba_salvos = st.tabs(["Novo Orçamento", "Orçamentos Salvos"])

with aba_novo:
    st.subheader("Novo Orçamento")

    col_info, col_transp = st.columns([1,1])

    with col_info:
        nome_orcamento = st.text_input("Nome do orçamento", value="", help="Identifique este orçamento para consultas futuras")
        estado = st.selectbox("Estado", ESTADOS_BR, index=12)  # MG default (12)
        unidade = st.radio("Unidade", ["Tonelada", "m3"], horizontal=True, index=0)
        tipo_produto = st.selectbox("Tipo de produto (define imposto)", list(PRODUTOS_IMPOSTO.keys()), index=0)

        preco_bruto = st.number_input("Preço Bruto de Venda (R$)", min_value=0.0, value=0.0, step=0.01)
        custo_madeira = st.number_input("Custo de Madeira (R$)", min_value=0.0, value=0.0, step=0.01)
        custo_servicos = st.number_input("Serviços (R$)", min_value=0.0, value=0.0, step=0.01)
        comissao_compra = st.number_input("Comissão Compra (R$)", min_value=0.0, value=0.0, step=0.01)
        comissao_venda = st.number_input("Comissão Venda (R$)", min_value=0.0, value=0.0, step=0.01)

    with col_transp:
        st.markdown("**Transporte**")
        km_total = st.number_input("Quilometragem total (km)", min_value=0.0, value=0.0, step=1.0)
        preco_km = st.number_input("Preço por km (R$/km)", min_value=0.0, value=0.0, step=0.01)
        st.caption("Cálculo: km_total × preço_km ÷ 30 (Ton) ou ÷ 105 (m³)")
        frete_fixo_unidade = st.number_input("Preço Frete Fixo (por unidade) — opcional", min_value=0.0, value=0.0, step=0.01,
                                             help="Se informado, substitui o cálculo por km.")

    # Preview do cálculo
    res_prev = calcular(preco_bruto, custo_madeira, tipo_produto, custo_servicos,
                        km_total, preco_km, unidade, frete_fixo_unidade,
                        comissao_compra, comissao_venda)

    col_res1, col_res2, col_res3, col_res4 = st.columns(4)
    col_res1.metric("Imposto (R$)", "{:.2f}".format(res_prev['imposto']))
    col_res2.metric("Transporte (R$)", "{:.2f}".format(res_prev['transporte']))
    col_res3.metric("Custo Total (R$)", "{:.2f}".format(res_prev['custo_total']))
    pct100 = res_prev["pct_percent"]
    color = color_for_pct(pct100)
    col_res4.markdown("<div style='font-weight:700;'>% de Lucro:</div>"
                      "<div style='font-size:1.6rem;color:{c};'>{v:.2f}%</div>".format(c=color, v=pct100),
                      unsafe_allow_html=True)

    st.markdown("---")
    st.metric("Líquido (R$)", "{:.2f}".format(res_prev['liquido']))

    if st.button("Salvar orçamento 📝", type="primary", use_container_width=True):
        if not nome_orcamento.strip():
            st.warning("Informe um **Nome do orçamento** antes de salvar.")
        else:
            append_row(nome_orcamento.strip(), estado, unidade, tipo_produto,
                       preco_bruto, custo_madeira, custo_servicos,
                       km_total, preco_km, frete_fixo_unidade,
                       comissao_compra, comissao_venda)
            st.success("Orçamento salvo na tabela geral.")
            st.experimental_rerun()

with aba_salvos:
    st.subheader("Orçamentos Salvos" )
    df = load_table(CSV_PATH)

    if df.empty:
        st.info("Não há orçamentos salvos ainda.")
    else:
        # Tabela para visualização
        df_view = df.copy()
        df_view["% de Lucro"] = (df_view["%_lucro"] * 100).round(2)
        df_view = df_view.rename(columns={
            "data_hora":"Data e Hora",
            "nome_orcamento":"Nome do Orçamento",
            "estado":"Estado",
            "unidade":"Unidade",
            "tipo_produto":"Produto",
            "preco_bruto":"Preço Bruto (R$)",
            "custo_madeira":"Custo Madeira (R$)",
            "custo_servicos":"Serviços (R$)",
            "km_total":"KM total",
            "preco_km":"Preço/KM (R$)",
            "frete_fixo_unidade":"Frete Fixo/Unid (R$)",
            "comissao_compra":"Comissão Compra (R$)",
            "comissao_venda":"Comissão Venda (R$)",
            "imposto":"Imposto (R$)",
            "transporte":"Transporte (R$)",
            "custo_total":"Custo Total (R$)",
            "liquido":"Líquido (R$)",
        })
        cols_order = ["Data e Hora","Nome do Orçamento","Estado","Unidade","Produto",
                      "Preço Bruto (R$)","Custo Madeira (R$)","Serviços (R$)",
                      "KM total","Preço/KM (R$)","Frete Fixo/Unid (R$)",
                      "Comissão Compra (R$)","Comissão Venda (R$)",
                      "Imposto (R$)","Transporte (R$)","Custo Total (R$)",
                      "Líquido (R$)","% de Lucro"]
        df_view = df_view[cols_order]
        st.dataframe(df_view, use_container_width=True)

        st.markdown("---")

        # Seleção por índice para excluir/editar
        options = ["[{}] {} — {} — {}".format(i, row['nome_orcamento'], row['estado'], row['data_hora']) for i, row in df.iterrows()]
        col_sel1, col_sel2 = st.columns([1,1])
        selected = col_sel1.selectbox("Selecione um orçamento", options, index=0)
        idx = int(selected.split(']')[0][1:])

        # Excluir
        if col_sel2.button("Excluir selecionado 🗑️"):
            delete_row(idx)
            st.success("Orçamento excluído.")
            st.experimental_rerun()

        st.markdown("### Editar orçamento")
        row = df.iloc[idx]

        with st.form("form_edit_full"):
            c1, c2, c3 = st.columns(3)
            with c1:
                nome_edit = st.text_input("Nome do orçamento", value=str(row["nome_orcamento"])) 
                estado_edit = st.selectbox("Estado", ESTADOS_BR, index=ESTADOS_BR.index(row["estado"]) if row["estado"] in ESTADOS_BR else 12)
                unidade_edit = st.selectbox("Unidade", ["Tonelada","m3"], index=0 if row["unidade"]=="Tonelada" else 1)
                tipo_edit = st.selectbox("Produto (imposto)", list(PRODUTOS_IMPOSTO.keys()), index=list(PRODUTOS_IMPOSTO.keys()).index(row["tipo_produto"]) if row["tipo_produto"] in PRODUTOS_IMPOSTO else 0)
            with c2:
                preco_edit = st.number_input("Preço Bruto (R$)", min_value=0.0, value=float(row["preco_bruto"]), step=0.01)
                madeira_edit = st.number_input("Custo Madeira (R$)", min_value=0.0, value=float(row["custo_madeira"]), step=0.01)
                servicos_edit = st.number_input("Serviços (R$)", min_value=0.0, value=float(row["custo_servicos"]), step=0.01)
                comp_edit = st.number_input("Comissão Compra (R$)", min_value=0.0, value=float(row["comissao_compra"]), step=0.01)
                vend_edit = st.number_input("Comissão Venda (R$)", min_value=0.0, value=float(row["comissao_venda"]), step=0.01)
            with c3:
                km_edit = st.number_input("KM total", min_value=0.0, value=float(row["km_total"]), step=1.0)
                pk_edit = st.number_input("Preço por KM (R$/km)", min_value=0.0, value=float(row["preco_km"]), step=0.01)
                frete_fix_edit = st.number_input("Frete Fixo/Unidade (R$)", min_value=0.0, value=float(row["frete_fixo_unidade"]), step=0.01)

            # Preview com novas entradas
            preview = calcular(preco_edit, madeira_edit, tipo_edit, servicos_edit,
                               km_edit, pk_edit, unidade_edit, frete_fix_edit,
                               comp_edit, vend_edit)

            st.markdown("#### Pré‑visualização calculada (não editável)")
            pr1, pr2, pr3, pr4 = st.columns(4)
            pr1.metric("Imposto (R$)", "{:.2f}".format(preview['imposto']))
            pr2.metric("Transporte (R$)", "{:.2f}".format(preview['transporte']))
            pr3.metric("Custo Total (R$)", "{:.2f}".format(preview['custo_total']))
            pr4.markdown("<div style='font-weight:700;'>% de Lucro:</div>"
                         "<div style='font-size:1.4rem;color:{c};'>{v:.2f}%</div>".format(c=color_for_pct(preview['pct_percent']), v=preview['pct_percent']),
                         unsafe_allow_html=True)
            st.metric("Líquido (R$)", "{:.2f}".format(preview['liquido']))

            col_b1, col_b2 = st.columns(2)
            submitted = col_b1.form_submit_button("Salvar alterações ✅")
            cancel = col_b2.form_submit_button("Cancelar")

        if submitted:
            # Persistimos entradas editadas e os derivados recalculados
            df.at[idx, "nome_orcamento"] = nome_edit.strip()
            df.at[idx, "estado"] = estado_edit
            df.at[idx, "unidade"] = unidade_edit
            df.at[idx, "tipo_produto"] = tipo_edit
            df.at[idx, "preco_bruto"] = float(preco_edit)
            df.at[idx, "custo_madeira"] = float(madeira_edit)
            df.at[idx, "custo_servicos"] = float(servicos_edit)
            df.at[idx, "km_total"] = float(km_edit)
            df.at[idx, "preco_km"] = float(pk_edit)
            df.at[idx, "frete_fixo_unidade"] = float(frete_fix_edit)
            df.at[idx, "comissao_compra"] = float(comp_edit)
            df.at[idx, "comissao_venda"] = float(vend_edit)
            # Derivados
            df.at[idx, "imposto"] = float(preview["imposto"])
            df.at[idx, "transporte"] = float(preview["transporte"])
            df.at[idx, "custo_total"] = float(preview["custo_total"])
            df.at[idx, "liquido"] = float(preview["liquido"])
            df.at[idx, "%_lucro"] = float(preview["pct_frac"])  # fração 0-1
            save_table(df, CSV_PATH)
            st.success("Orçamento atualizado com sucesso!")
            st.experimental_rerun()
