
import streamlit as st
import pandas as pd
import sqlite3
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# Conexão SQLite
conn = sqlite3.connect("produtos.db", check_same_thread=False)
cursor = conn.cursor()

# Criar tabela
cursor.execute("""
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto TEXT,
    tipo TEXT,
    quantidade INTEGER,
    peso REAL,
    desconto REAL,
    peso_final REAL
)
""")
conn.commit()

st.title("📦 Pesagem das frutas")

# ===== CALCULADORA =====
calc_container = st.container()
with calc_container:
    st.subheader("🧮 Calcular e descontar peso")
    num1 = st.number_input("Número 1", step=1.0, format="%.2f")
    num2 = st.number_input("Número 2", step=1.0, format="%.2f")
    operacao = st.selectbox("Operação", ["Somar", "Subtrair", "Multiplicar", "Dividir"])
    if st.button("Calcular"):
        if operacao == "Somar":
            resultado = num1 + num2
        elif operacao == "Subtrair":
            resultado = num1 - num2
        elif operacao == "Multiplicar":
            resultado = num1 * num2
        elif operacao == "Dividir":
            resultado = num1 / num2 if num2 != 0 else "Erro: divisão por zero"
        st.success(f"Resultado: {resultado}")

st.markdown("---")

# Lista de produtos
produtos_lista = {
    "a": "tomate", "b": "cebola", "c": "cenoura", "d": "melão",
    "e": "manga", "f": "abacate", "g": "beterraba", "h": "goiaba",
    "i": "chuchu", "j": "pepino", "l": "pocam", "m": "laranja",
    "n": "batata", "o": "repolho", "p": "coco", "q": "limão", "r": "maracujá",
    "s": "pêra", "t": "kiwí"
}

# ===== FORMULÁRIO =====
form_container = st.container()
with form_container:
    produto = st.selectbox("Selecione o produto:", list(produtos_lista.values()))
    tipo = st.radio("Tipo de embalagem:", ["Caixa", "Saco"])
    quantidade = st.number_input("Quantidade:", min_value=1, value=1)
    peso_total_informado = st.number_input("Peso total (kg):", min_value=0.0, step=0.1)
    descontar = st.checkbox("Descontar peso?")
    desconto = st.number_input("Descontar quantos kg no total?", min_value=0.0, step=0.1) if descontar else 0.0
    peso_final = max(peso_total_informado - desconto, 0)

    if st.button("Salvar dados"):
        cursor.execute("""
            SELECT id, quantidade, peso, desconto, peso_final
            FROM produtos
            WHERE produto = ? AND tipo = ?
        """, (produto, tipo))
        registro_existente = cursor.fetchone()

        if registro_existente:
            id_existente, qtd_existente, peso_existente, desconto_existente, peso_final_existente = registro_existente
            nova_quantidade = qtd_existente + quantidade
            novo_peso = peso_existente + peso_total_informado
            novo_desconto = desconto_existente + desconto
            novo_peso_final = peso_final_existente + peso_final
            cursor.execute("""
                UPDATE produtos
                SET quantidade = ?, peso = ?, desconto = ?, peso_final = ?
                WHERE id = ?
            """, (nova_quantidade, novo_peso, novo_desconto, novo_peso_final, id_existente))
            conn.commit()
            st.success(f"Registro atualizado: {nova_quantidade} {tipo.lower()}(s) de {produto} | Peso final total: {novo_peso_final:.2f} kg")
        else:
            cursor.execute("""
                INSERT INTO produtos (produto, tipo, quantidade, peso, desconto, peso_final)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (produto, tipo, quantidade, peso_total_informado, desconto, peso_final))
            conn.commit()
            st.success(f"{quantidade} {tipo.lower()}(s) de {produto} salvos com sucesso! Peso final: {peso_final:.2f} kg")

# ===== FILTRO =====
filtro_container = st.container()
with filtro_container:
    st.subheader("🔎 Filtro de produtos")
    todos_os_produtos = ["Todos"] + list(produtos_lista.values())
    filtro = st.selectbox("Filtrar por produto:", todos_os_produtos)
    query = "SELECT * FROM produtos"
    params = ()
    if filtro != "Todos":
        query += " WHERE produto = ?"
        params = (filtro,)
    df = pd.read_sql_query(query, conn, params=params)

    st.subheader("📋 Registros filtrados:")
    st.dataframe(df)

    peso_geral = df["peso_final"].sum() if not df.empty else 0
    st.info(f"🔢 Peso total ({filtro}): {peso_geral:.2f} kg")

# ===== EXPORTAÇÃO =====
def exportar_para_txt(dataframe):
    linhas = []
    for _, row in dataframe.iterrows():
        linhas.append(f"Produto: {row['produto']} | Tipo: {row['tipo']} | Quantidade: {row['quantidade']} | "
                      f"Peso total informado: {row['peso']} kg | Desconto: {row['desconto']} kg | "
                      f"Peso final: {row['peso_final']:.2f} kg")
    linhas.append(f"\nPeso total ({filtro}): {peso_geral:.2f} kg")
    with open("relatorio_produtos_filtrado.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))
    return "relatorio_produtos_filtrado.txt"

def exportar_para_pdf(dataframe):
    nome_arquivo = "relatorio_produtos_filtrado.pdf"
    doc = SimpleDocTemplate(nome_arquivo, pagesize=A4)
    styles = getSampleStyleSheet()
    elementos = [Paragraph("Relatório de Produtos Filtrados", styles["Title"]), Spacer(1, 12)]
    dados = [["Produto", "Tipo", "Qtd", "Peso", "Desconto", "Peso Final"]]
    for _, row in dataframe.iterrows():
        dados.append([row['produto'], row['tipo'], row['quantidade'],
                      f"{row['peso']} kg", f"{row['desconto']} kg", f"{row['peso_final']:.2f} kg"])
    dados.append(["", "", "", "", "Total", f"{peso_geral:.2f} kg"])
    tabela = Table(dados, repeatRows=1)
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    elementos.append(tabela)
    doc.build(elementos)
    return nome_arquivo

export_container = st.container()
with export_container:
    if not df.empty:
        if st.button("📄 Exportar filtrado para TXT"):
            arquivo_txt = exportar_para_txt(df)
            with open(arquivo_txt, "rb") as f:
                st.download_button("📥 Baixar relatório filtrado (.txt)", f, file_name=arquivo_txt)

        if st.button("📄 Exportar filtrado para PDF"):
            arquivo_pdf = exportar_para_pdf(df)
            with open(arquivo_pdf, "rb") as f:
                st.download_button("📥 Baixar relatório filtrado (.pdf)", f, file_name=arquivo_pdf, mime="application/pdf")

# ===== EXCLUSÕES =====
exclusao_container = st.container()
with exclusao_container:
    st.subheader("🗑 Excluir registro individual")
    if not df.empty:
        ids_disponiveis = df["id"].tolist()
        id_para_excluir = st.selectbox("Selecione o ID do registro para excluir:", ids_disponiveis)
        if st.button("Excluir registro selecionado"):
            cursor.execute("DELETE FROM produtos WHERE id = ?", (id_para_excluir,))
            conn.commit()
            st.success(f"Registro com ID {id_para_excluir} excluído com sucesso!")
            st.experimental_rerun()
    else:
        st.info("Nenhum registro disponível para exclusão.")

    st.subheader("⚠ Excluir TODOS os registros")
    senha_correta = "hortifruti"
    senha_usuario = st.text_input("Digite a senha para excluir todos os registros:", type="password")
    if st.button("Excluir TODOS os registros"):
        if senha_usuario == senha_correta:
            cursor.execute("DELETE FROM produtos")
            conn.commit()
            st.success("🚨 Todos os registros foram excluídos com sucesso!")
            st.experimental_rerun()
        else:
            st.error("❌ Senha incorreta. A exclusão foi cancelada.")