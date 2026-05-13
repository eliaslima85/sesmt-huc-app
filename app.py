import streamlit as st
import sqlite3
import random
import pandas as pd
from datetime import datetime
import urllib.parse
from fpdf import FPDF

# --- CONFIGURAÇÃO E ESTÉTICA ---
st.set_page_config(page_title="SESMT - HUC", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fb; }
    .main-header { color: #004a87; font-weight: bold; font-size: 28px; border-bottom: 3px solid #004a87; padding-bottom: 10px; margin-bottom: 20px; }
    .card { background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #e0e0e0; }
    .stButton>button { background-color: #004a87; color: white; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS COM AUTO-MIGRAÇÃO ---
def conectar(): return sqlite3.connect('gestao_epi_sesmt.db', check_same_thread=False)
conn = conectar()
c = conn.cursor()

# Criação das tabelas base
c.execute('CREATE TABLE IF NOT EXISTS funcionarios (id INTEGER PRIMARY KEY, nome TEXT, matricula TEXT UNIQUE, setor TEXT, funcao TEXT, admissao TEXT, turno TEXT, vinculo TEXT, whatsapp TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS epis (id INTEGER PRIMARY KEY, nome TEXT, ca TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS entregas (id INTEGER PRIMARY KEY, id_func INTEGER, id_epi INTEGER, data TEXT, token TEXT, status TEXT DEFAULT "Pendente ⏳")')
c.execute('CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY, senha TEXT)')

# --- MÁGICA DA ENGENHARIA: Atualiza a tabela se ela for antiga ---
try:
    c.execute('ALTER TABLE config ADD COLUMN url_sistema TEXT')
    conn.commit()
except:
    pass # Se der erro, é porque a coluna já existe. Vida que segue!

# Garante que existe uma senha padrão e uma URL inicial
c.execute("INSERT OR IGNORE INTO config (id, senha, url_sistema) VALUES (1, '1234', 'http://localhost:8501')")
conn.commit()

# --- ESTILIZAÇÃO DA TABELA ---
def colorir_status(val):
    color = 'red' if 'Pendente' in val else 'green'
    return f'color: {color}; font-weight: bold'

# --- TRATAMENTO DE TEXTO PARA O PDF ---
def limpar_texto(texto):
    texto_string = str(texto).replace("✅", "").replace("⏳", "").replace("🛡️", "").strip()
    return texto_string.encode('latin-1', 'replace').decode('latin-1')

# --- ROTA DE ASSINATURA DO COLABORADOR ---
if "confirmar" in st.query_params:
    tk = st.query_params["confirmar"]
    c.execute("UPDATE entregas SET status = 'Confirmado ✅' WHERE token = ?", (tk,))
    conn.commit()
    st.success("🛡️ Assinatura Digital SESMT HUC Confirmada!")
    st.info("Sua confirmação foi registrada. Pode fechar esta tela.")
    st.stop()

# --- LOGIN ADMIN ---
if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.markdown('<div style="text-align:center; margin-top:80px;"><h1>🔐 SESMT HUC - Acesso Restrito</h1></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            c.execute("SELECT senha FROM config WHERE id=1")
            if senha == c.fetchone()[0]:
                st.session_state.logado = True
                st.rerun()
            else: st.error("Senha Incorreta")
    st.stop()

# --- FUNÇÕES DE PDF ---
def gerar_pdf_ficha(dados_f, df, titulo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "HUC - ISGH / SESMT", ln=True, align='C')
    pdf.set_font("Arial", 'B', 11); pdf.cell(0, 10, limpar_texto(titulo), ln=True, align='C')
    pdf.ln(5); pdf.set_font("Arial", size=10)
    pdf.cell(0, 7, f"Nome: {limpar_texto(dados_f['nome'])} | Matricula: {limpar_texto(dados_f['matricula'])}", ln=True)
    pdf.cell(0, 7, f"Setor: {limpar_texto(dados_f['setor'])} | Funcao: {limpar_texto(dados_f['funcao'])} | Vinculo: {limpar_texto(dados_f['vinculo'])}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 9); pdf.cell(30, 8, "Data", 1); pdf.cell(85, 8, "EPI", 1); pdf.cell(25, 8, "C.A.", 1); pdf.cell(40, 8, "Status", 1, ln=True)
    pdf.set_font("Arial", size=9)
    for _, r in df.iterrows():
        pdf.cell(30, 8, limpar_texto(r['data']), 1)
        pdf.cell(85, 8, limpar_texto(r['nome'])[:40], 1)
        pdf.cell(25, 8, limpar_texto(r['ca']), 1)
        pdf.cell(40, 8, limpar_texto(r['status']), 1, ln=True)
    return pdf.output(dest='S').encode('latin-1')

def gerar_pdf_setores(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "HUC - RELATORIO DE CONSUMO POR SETOR", ln=True, align='C')
    pdf.set_font("Arial", '', 10); pdf.cell(0, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='R')
    pdf.ln(5); pdf.set_font("Arial", 'B', 10)
    pdf.cell(70, 10, "Setor", 1); pdf.cell(80, 10, "Tipo do EPI", 1); pdf.cell(40, 10, "Quantidade", 1, ln=True)
    pdf.set_font("Arial", size=10)
    for _, r in df.iterrows():
        pdf.cell(70, 10, limpar_texto(r['setor']), 1); pdf.cell(80, 10, limpar_texto(r['EPI']), 1); pdf.cell(40, 10, limpar_texto(r['Qtd']), 1, ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- MENU LATERAL ---
menu = st.sidebar.radio("SESMT MENU", ["📊 Dashboard", "🚀 Entregar EPI", "👥 Funcionários", "📦 Catálogo EPI", "📑 Relatórios", "⚙️ Configurações"])

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.markdown('<div class="main-header">📊 Painel de Controle SESMT</div>', unsafe_allow_html=True)
    c_f = pd.read_sql_query("SELECT COUNT(*) as t FROM funcionarios", conn).iloc[0]['t']
    c_e = pd.read_sql_query("SELECT COUNT(*) as t FROM entregas", conn).iloc[0]['t']
    c_p = pd.read_sql_query("SELECT COUNT(*) as t FROM entregas WHERE status LIKE 'Pendente%'", conn).iloc[0]['t']
    col1, col2, col3 = st.columns(3)
    col1.metric("Funcionários", c_f)
    col2.metric("Entregas Realizadas", c_e)
    col3.metric("Assinaturas Pendentes", c_p)
    
    st.subheader("Últimas 10 Movimentações")
    recentes = pd.read_sql_query('''SELECT f.nome as Colaborador, ep.nome as EPI, e.data, e.status 
                                     FROM entregas e JOIN funcionarios f ON e.id_func = f.id 
                                     JOIN epis ep ON e.id_epi = ep.id ORDER BY e.id DESC LIMIT 10''', conn)
    st.dataframe(recentes.style.applymap(colorir_status, subset=['status']), use_container_width=True)

# --- ENTREGAR EPI ---
elif menu == "🚀 Entregar EPI":
    st.markdown('<div class="main-header">🚀 Nova Entrega de EPI</div>', unsafe_allow_html=True)
    df_f = pd.read_sql_query("SELECT id, matricula, nome, whatsapp FROM funcionarios", conn)
    df_e = pd.read_sql_query("SELECT id, nome, ca FROM epis", conn)
    c.execute("SELECT url_sistema FROM config WHERE id=1")
    url_base = c.fetchone()[0]

    if df_f.empty or df_e.empty: st.warning("Cadastre Funcionários e EPIs primeiro.")
    else:
        with st.container():
            f_sel = st.selectbox("Selecione o Colaborador", df_f['matricula'] + " - " + df_f['nome'])
            e_sel = st.multiselect("Selecione os EPIs", df_e['nome'] + " (CA: " + df_e['ca'] + ")")
            if st.button("Gerar Entrega e Enviar WhatsApp"):
                if e_sel:
                    tk = str(random.randint(100000, 999999)); dt = datetime.now().strftime("%d/%m/%Y %H:%M")
                    f_id = df_f[df_f['matricula'] == f_sel.split(" - ")[0]].iloc[0]
                    for item in e_sel:
                        epi_id = df_e[df_e['nome'] == item.split(" (CA: ")[0]].iloc[0]['id']
                        c.execute("INSERT INTO entregas (id_func, id_epi, data, token) VALUES (?,?,?,?)", (int(f_id['id']), int(epi_id), dt, tk))
                    conn.commit()
                    
                    link_conf = f"{url_base}/?confirmar={tk}"
                    msg = urllib.parse.quote(f"🛡️ *SESMT HUC*\nOlá, {f_id['nome']}!\nVocê recebeu: {', '.join(e_sel)}.\n\n*Por favor, clique no link abaixo para confirmar o recebimento:*\n👉 {link_conf}")
                    st.success("Entrega registrada! Clique abaixo para enviar.")
                    st.markdown(f'<a href="https://api.whatsapp.com/send?phone=55{f_id['whatsapp']}&text={msg}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:12px; border-radius:5px; font-weight:bold; cursor:pointer;">📲 ENVIAR PARA WHATSAPP</button></a>', unsafe_allow_html=True)

# --- FUNCIONÁRIOS ---
elif menu == "👥 Funcionários":
    st.markdown('<div class="main-header">👥 Gestão de Colaboradores</div>', unsafe_allow_html=True)
    with st.expander("➕ Novo Cadastro"):
        with st.form("new_f", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            n = c1.text_input("Nome Completo"); m = c2.text_input("Matrícula"); s = c3.text_input("Setor")
            c4, c5, c6 = st.columns(3)
            f = c4.text_input("Função"); t = c5.selectbox("Turno", ["Comercial", "12x36 Dia", "12x36 Noite"]); v = c6.selectbox("Vínculo", ["Efetivo", "Cooperado", "Terceirizado"])
            w = st.text_input("WhatsApp (DDD + Número - Ex: 85988887766)")
            if st.form_submit_button("Salvar"):
                if n and m and w:
                    c.execute("INSERT INTO funcionarios (nome, matricula, setor, funcao, turno, vinculo, whatsapp) VALUES (?,?,?,?,?,?,?)", (n,m,s,f,t,v,w))
                    conn.commit(); st.success(f"{n} Cadastrado!")
                else: st.error("Preencha Nome, Matrícula e WhatsApp.")
    
    st.subheader("🔧 Manutenção de Dados")
    df_f_edit = pd.read_sql_query("SELECT * FROM funcionarios", conn)
    edited = st.data_editor(df_f_edit, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Salvar Alterações"):
        edited.to_sql('funcionarios', conn, if_exists='replace', index=False); st.success("Atualizado!")

# --- CATÁLOGO EPI ---
elif menu == "📦 Catálogo EPI":
    st.markdown('<div class="main-header">📦 Catálogo de Equipamentos</div>', unsafe_allow_html=True)
    with st.form("new_e", clear_on_submit=True):
        c1, c2 = st.columns(2); n_e = c1.text_input("Nome do EPI"); ca_e = c2.text_input("C.A.")
        if st.form_submit_button("Cadastrar"):
            c.execute("INSERT INTO epis (nome, ca) VALUES (?,?)", (n_e, ca_e))
            conn.commit(); st.success("EPI Adicionado!")
    df_e_edit = pd.read_sql_query("SELECT * FROM epis", conn)
    edited_e = st.data_editor(df_e_edit, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Salvar Alterações no Catálogo"):
        edited_e.to_sql('epis', conn, if_exists='replace', index=False); st.success("Atualizado!")

# --- RELATÓRIOS ---
elif menu == "📑 Relatórios":
    st.markdown('<div class="main-header">📑 Central de Relatórios</div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📄 Ficha Individual", "📊 Consumo por Setor"])
    with tab1:
        df_f = pd.read_sql_query("SELECT * FROM funcionarios", conn)
        if not df_f.empty:
            sel = st.selectbox("Selecionar Colaborador", df_f['matricula'] + " - " + df_f['nome'])
            f_id = df_f[df_f['matricula'] == sel.split(" - ")[0]].iloc[0]
            h_df = pd.read_sql_query('''SELECT e.data, ep.nome, ep.ca, e.status FROM entregas e JOIN epis ep ON e.id_epi = ep.id WHERE e.id_func = ? ORDER BY e.id DESC''', conn, params=(int(f_id['id']),))
            st.dataframe(h_df.style.applymap(colorir_status, subset=['status']), use_container_width=True)
            col_pdf1, col_pdf2 = st.columns(2)
            with col_pdf1:
                if st.button("📄 Ficha Atual (Últimos 30)"):
                    st.download_button("📥 Download", gerar_pdf_ficha(f_id, h_df.head(30), "FICHA DE EPI - CICLO ATUAL"), f"Ficha_{f_id['matricula']}.pdf")
            with col_pdf2:
                if st.button("📂 Histórico Completo"):
                    st.download_button("📥 Download Completo", gerar_pdf_ficha(f_id, h_df, "HISTORICO COMPLETO DE EPI"), f"Hist_{f_id['matricula']}.pdf")
    with tab2:
        df_s = pd.read_sql_query("SELECT f.setor, ep.nome as EPI, COUNT(e.id) as Qtd FROM entregas e JOIN funcionarios f ON e.id_func = f.id JOIN epis ep ON e.id_epi = ep.id GROUP BY f.setor, ep.nome", conn)
        st.dataframe(df_s, use_container_width=True)
        if st.button("📥 Baixar Relatório por Setor (PDF)"):
            st.download_button("Baixar PDF", gerar_pdf_setores(df_s), f"Relatorio_Setores_{datetime.now().strftime('%d_%m')}.pdf")

# --- CONFIGURAÇÕES ---
elif menu == "⚙️ Configurações":
    st.markdown('<div class="main-header">⚙️ Ajustes do Sistema</div>', unsafe_allow_html=True)
    c.execute("SELECT url_sistema FROM config WHERE id=1")
    url_atual = c.fetchone()[0]
    nova_url = st.text_input("Link do seu sistema na Nuvem (Ex: https://sesmt-huc.streamlit.app)", url_atual)
    if st.button("Salvar URL Oficial"):
        c.execute("UPDATE config SET url_sistema = ? WHERE id=1", (nova_url,))
        conn.commit(); st.success("URL Atualizada! Agora os links do WhatsApp funcionarão.")
