import streamlit as st
import sqlite3
import random
import pandas as pd
from datetime import datetime
import urllib.parse
from fpdf import FPDF
# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="SESMT - HUC", layout="wide", page_icon="🛡️")
st.markdown("""
    <style>
    .stApp { background-color: #f4f6f9; }
    .main-header { color: #004a87; font-weight: bold; font-size: 32px; margin-bottom: 20px; }
    .card { background-color: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #004a87; margin-bottom: 20px; }
    .stButton>button { width: 100%; background-color: #004a87; color: white; border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)
# --- BANCO DE DADOS ---
def conectar():
    return sqlite3.connect('gestao_epi_sesmt.db', check_same_thread=False)
conn = conectar()
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS funcionarios (id INTEGER PRIMARY KEY, nome TEXT, matricula TEXT UNIQUE, setor TEXT, funcao TEXT, admissao TEXT, turno TEXT, vinculo TEXT, whatsapp TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS epis (id INTEGER PRIMARY KEY, nome TEXT, ca TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS entregas (id INTEGER PRIMARY KEY, id_func INTEGER, id_epi INTEGER, data TEXT, token TEXT, status TEXT DEFAULT 'Pendente ⏳')''')
c.execute('''CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY, senha TEXT)''')
c.execute("INSERT OR IGNORE INTO config (id, senha) VALUES (1, '1234')")
conn.commit()
# =====================================================================
# A MÁGICA: ROTA DO FUNCIONÁRIO (Assinatura Digital)
# Se o link tiver "?confirmar=TOKEN", ele abre só esta tela!
# =====================================================================
query_params = st.query_params
if "confirmar" in query_params:
    tk_recebido = query_params["confirmar"]
    c.execute("UPDATE entregas SET status = 'Confirmado ✅' WHERE token = ?", (tk_recebido,))
    conn.commit()
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.success("🛡️ **Assinatura Digital Confirmada com Sucesso!**")
    st.info("O recebimento do seu EPI foi registrado oficialmente no banco de dados do SESMT/HUC. Você já pode fechar esta tela.")
    st.stop() # Para o sistema aqui para o funcionário não ver as abas de Admin
# =====================================================================
# SISTEMA DE LOGIN (ADMIN)
# =====================================================================
if 'logado' not in st.session_state: st.session_state['logado'] = False
if not st.session_state['logado']:
    st.markdown('<div class="main-header" style="text-align: center; margin-top: 50px;">🔐 Acesso Restrito - SESMT HUC</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        senha_input = st.text_input("Senha do Administrador", type="password")
        if st.button("Entrar"):
            c.execute("SELECT senha FROM config WHERE id=1")
            if senha_input == c.fetchone()[0]:
                st.session_state['logado'] = True
                st.rerun()
            else:
                st.error("Senha incorreta!")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()
# --- FUNÇÃO GERAR PDF ---
def gerar_pdf_ficha(dados_f, entregas_df, titulo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "HOSPITAL UNIVERSITARIO DO CEARA - ISGH / SESMT", ln=True, align='C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, titulo, ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 7, f"COLABORADOR: {dados_f['nome'].upper()}", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 7, f"MATRICULA: {dados_f['matricula']} | SETOR: {dados_f['setor']} | FUNCAO: {dados_f['funcao']}", ln=True)
    pdf.cell(0, 7, f"ADMISSAO: {dados_f['admissao']} | TURNO: {dados_f['turno']} | VINCULO: {dados_f['vinculo']}", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(30, 8, "DATA", 1); pdf.cell(80, 8, "EPI", 1); pdf.cell(20, 8, "C.A.", 1); pdf.cell(25, 8, "TOKEN", 1); pdf.cell(35, 8, "STATUS", 1, ln=True)
    pdf.set_font("Arial", size=9)
    for _, row in entregas_df.iterrows():
        pdf.cell(30, 8, str(row['data']), 1)
        pdf.cell(80, 8, str(row['nome'])[:40], 1)
        pdf.cell(20, 8, str(row['ca']), 1)
        pdf.cell(25, 8, str(row['token']), 1)
        pdf.cell(35, 8, str(row['status']), 1, ln=True)
    return pdf.output(dest='S').encode('latin-1')
# --- INTERFACE PRINCIPAL ---
col_head1, col_head2 = st.columns([4, 1])
with col_head1: st.markdown('<div class="main-header">🛡️ Gestão de EPI - SESMT HUC</div>', unsafe_allow_html=True)
with col_head2: 
    if st.button("Sair / Bloquear"): 
        st.session_state['logado'] = False
        st.rerun()
aba1, aba2, aba3, aba4 = st.tabs(["🚀 Entregar EPI", "👥 Funcionários", "📦 Cadastro EPI", "📊 Relatórios e Fichas"])
# --- ABA 1: ENTREGA DE EPI ---
with aba1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Nova Movimentação")
    df_f = pd.read_sql_query("SELECT * FROM funcionarios", conn)
    df_e = pd.read_sql_query("SELECT * FROM epis", conn)
    if df_f.empty or df_e.empty:
        st.warning("Cadastre Funcionários e EPIs nas abas ao lado para iniciar.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            sel_f = st.selectbox("1. Selecione o Profissional", df_f['matricula'] + " - " + df_f['nome'])
            func_data = df_f[df_f['matricula'] == sel_f.split(" - ")[0]].iloc[0]
        with col2:
            epis_sel = st.multiselect("2. Selecione os EPIs", df_e['nome'] + " (CA: " + df_e['ca'] + ")")
        if st.button("Gerar Entrega e Link de Assinatura"):
            if epis_sel:
                tk = str(random.randint(100000, 999999))
                dt = datetime.now().strftime("%d/%m/%Y %H:%M")
                for item in epis_sel:
                    n_epi = item.split(" (CA: ")[0]
                    id_e = df_e[df_e['nome'] == n_epi]['id'].iloc[0]
                    c.execute("INSERT INTO entregas (id_func, id_epi, data, token, status) VALUES (?,?,?,?,?)", (int(func_data['id']), int(id_e), dt, tk, 'Pendente ⏳'))
                conn.commit()
                link_conf = f"http://localhost:8501/?confirmar={tk}"
                msg = f"🛡️ *SESMT HUC*\n\nOlá, {func_data['nome']}!\nVocê recebeu: *{', '.join(epis_sel)}*.\n\nPara assinar sua ficha, clique no link abaixo:\n👉 {link_conf}"
                link_zap = f"https://api.whatsapp.com/send?phone=55{func_data['whatsapp']}&text={urllib.parse.quote(msg)}"
                st.success(f"✅ Protocolo Gerado. Status: PENDENTE.")
                st.markdown(f'<a href="{link_zap}" target="_blank"><button style="background-color: #25D366; border:none; color:white; padding:15px; border-radius:8px; cursor:pointer; width:100%; font-size:16px;">📲 ENVIAR LINK PARA O WHATSAPP DO COLABORADOR</button></a>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
# --- ABA 2: FUNCIONÁRIOS (LIMPA APÓS SALVAR) ---
with aba2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Cadastro Rápido de Colaborador")
    with st.form("cad_func", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        nome = c1.text_input("Nome Completo")
        mat = c2.text_input("Matrícula")
        setor = c3.text_input("Setor")
        c4, c5, c6 = st.columns(3)
        func = c4.text_input("Função")
        adm = c5.date_input("Data de Admissão")
        turno = c6.selectbox("Turno", ["Diurno", "Noturno", "12x36", "Comercial"])
        c7, c8 = st.columns(2)
        vinc = c7.selectbox("Vínculo", ["Efetivo", "Cooperado", "Terceirizado"])
        zap = c8.text_input("WhatsApp (Ex: 85988887766)")
        if st.form_submit_button("Salvar Colaborador"):
            if nome and mat:
                c.execute("INSERT INTO funcionarios (nome, matricula, setor, funcao, admissao, turno, vinculo, whatsapp) VALUES (?,?,?,?,?,?,?,?)", (nome, mat, setor, func, str(adm), turno, vinc, zap))
                conn.commit()
                st.success(f"✅ {nome} cadastrado! Pode digitar o próximo.")
            else:
                st.error("Nome e Matrícula são obrigatórios.")
    st.write("📋 **Colaboradores já cadastrados:**")
    st.dataframe(pd.read_sql_query("SELECT matricula, nome, setor, funcao FROM funcionarios", conn), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
# --- ABA 3: EPI (LIMPA APÓS SALVAR) ---
with aba3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Cadastro Rápido de EPI")
    with st.form("cad_epi", clear_on_submit=True):
        col_e1, col_e2 = st.columns(2)
        n_epi = col_e1.text_input("Nome do EPI (Ex: Bota de Segurança)")
        ca_epi = col_e2.text_input("Número do C.A.")
        if st.form_submit_button("Salvar EPI"):
            if n_epi and ca_epi:
                c.execute("INSERT INTO epis (nome, ca) VALUES (?,?)", (n_epi, ca_epi))
                conn.commit()
                st.success(f"✅ {n_epi} cadastrado! Pode digitar o próximo.")
            else:
                st.error("Preencha o Nome e o CA.")
    st.write("📋 **Estoque de EPIs Cadastrados:**")
    st.dataframe(pd.read_sql_query("SELECT ca, nome FROM epis", conn), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
# --- ABA 4: RELATÓRIOS ---
with aba4:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Auditoria e Emissão de Fichas")
    df_f_rel = pd.read_sql_query("SELECT * FROM funcionarios", conn)
    if not df_f_rel.empty:
        busca_f = st.selectbox("Escolha o Colaborador para Visualizar Ficha", df_f_rel['matricula'] + " - " + df_f_rel['nome'])
        f_sel = df_f_rel[df_f_rel['matricula'] == busca_f.split(" - ")[0]].iloc[0]
        query_h = '''SELECT e.data, ep.nome, ep.ca, e.token, e.status FROM entregas e JOIN epis ep ON e.id_epi = ep.id WHERE e.id_func = ? ORDER BY e.id DESC'''
        hist_df = pd.read_sql_query(query_h, conn, params=(int(f_sel['id']),))
        total = len(hist_df)
        st.write(f"**Total de Equipamentos Registrados:** {total}")
        if total > 0 and total % 30 == 0:
            st.error("🚨 ATENÇÃO: Limite de 30 itens atingido. Gere o PDF atual para arquivamento no SESMT!")
        st.dataframe(hist_df, use_container_width=True)
        col_pdf1, col_pdf2 = st.columns(2)
        with col_pdf1:
            if st.button("📄 Baixar Ficha Atual (Últimos 30 itens)"):
                st.download_button("📥 Confirmar Download", gerar_pdf_ficha(f_sel, hist_df.head(30), "FICHA DE EPI - CICLO ATUAL"), f"Ficha_{f_sel['matricula']}.pdf")
        with col_pdf2:
            if st.button("📂 Baixar Histórico Completo"):
                st.download_button("📥 Confirmar Download", gerar_pdf_ficha(f_sel, hist_df, "HISTORICO COMPLETO"), f"Historico_{f_sel['matricula']}.pdf")
    st.markdown('</div>', unsafe_allow_html=True)
