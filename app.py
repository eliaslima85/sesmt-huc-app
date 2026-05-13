import streamlit as st
import sqlite3
import random
import pandas as pd
from datetime import datetime
import urllib.parse
from fpdf import FPDF

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="SESMT - Gestão de Fichas", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    .main-header { color: #004a87; font-weight: bold; font-size: 28px; border-bottom: 3px solid #004a87; padding-bottom: 10px; }
    .status-alerta { background-color: #ffcccc; color: #b30000; padding: 10px; border-radius: 5px; font-weight: bold; border: 1px solid #b30000; }
    </style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS ---
def conectar(): return sqlite3.connect('gestao_epi_sesmt.db', check_same_thread=False)
conn = conectar()
c = conn.cursor()

# Tabelas básicas
c.execute('CREATE TABLE IF NOT EXISTS funcionarios (id INTEGER PRIMARY KEY, nome TEXT, matricula TEXT UNIQUE, setor TEXT, funcao TEXT, admissao TEXT, turno TEXT, vinculo TEXT, whatsapp TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS epis (id INTEGER PRIMARY KEY, nome TEXT, ca TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS entregas (id INTEGER PRIMARY KEY, id_func INTEGER, id_epi INTEGER, data TEXT, token TEXT, status TEXT DEFAULT "Pendente ⏳")')
c.execute('CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY, senha TEXT, url_sistema TEXT)')

# Garantir estrutura do banco
try:
    c.execute('ALTER TABLE config ADD COLUMN url_sistema TEXT')
    conn.commit()
except:
    pass

c.execute("INSERT OR IGNORE INTO config (id, senha, url_sistema) VALUES (1, '1234', 'http://localhost:8501')")
conn.commit()

# --- FUNÇÕES DE LIMPEZA E ESTILO ---
def limpar_texto(texto):
    return str(texto).replace("✅", "").replace("⏳", "").replace("🛡️", "").strip().encode('latin-1', 'replace').decode('latin-1')

def colorir_status(val):
    if not isinstance(val, str): return ""
    color = 'red' if 'Pendente' in val else 'green'
    return f'color: {color}; font-weight: bold'

# --- GERAÇÃO DE PDF ---
def gerar_pdf_epi(f, df, titulo_doc):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "CONTROLE DE ENTREGA DE EPI", ln=True, align='C')
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 8, f"NOME: {limpar_texto(f['nome'])} | MATRÍCULA: {limpar_texto(f['matricula'])}", ln=True)
    pdf.cell(0, 8, f"SETOR: {limpar_texto(f['setor'])} | FUNÇÃO: {limpar_texto(f['funcao'])}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(30, 8, "DATA", 1); pdf.cell(90, 8, "EQUIPAMENTO", 1); pdf.cell(30, 8, "C.A.", 1); pdf.cell(40, 8, "STATUS", 1, ln=True)
    pdf.set_font("Arial", size=9)
    for _, r in df.iterrows():
        pdf.cell(30, 8, limpar_texto(r['data']), 1); pdf.cell(90, 8, limpar_texto(r['nome'])[:45], 1); pdf.cell(30, 8, limpar_texto(r['ca']), 1); pdf.cell(40, 8, limpar_texto(r['status']), 1, ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- LOGICA DE ASSINATURA ---
if "confirmar" in st.query_params:
    tk = st.query_params["confirmar"]
    c.execute("UPDATE entregas SET status = 'Confirmado ✅' WHERE token = ?", (tk,))
    conn.commit()
    st.balloons(); st.success("Assinatura Confirmada!"); st.stop()

# --- LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.markdown('<h1 style="text-align:center;">🔐 SESMT Login</h1>', unsafe_allow_html=True)
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        c.execute("SELECT senha FROM config WHERE id=1")
        if senha == c.fetchone()[0]:
            st.session_state.logado = True; st.rerun()
    st.stop()

# --- MENU ---
menu = st.sidebar.radio("SESMT", ["📊 Dashboard", "🚀 Entregar EPI", "👥 Funcionários", "📦 Catálogo", "📑 Relatórios", "⚙️ Config"])

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.markdown('<div class="main-header">📊 Dashboard de Entregas</div>', unsafe_allow_html=True)
    res = pd.read_sql_query('''SELECT f.nome, ep.nome as EPI, e.data, e.status FROM entregas e 
                                JOIN funcionarios f ON e.id_func = f.id JOIN epis ep ON e.id_epi = ep.id 
                                ORDER BY e.id DESC LIMIT 15''', conn)
    st.dataframe(res.style.map(colorir_status, subset=['status']), use_container_width=True)

# --- ENTREGAR EPI ---
elif menu == "🚀 Entregar EPI":
    st.markdown('<div class="main-header">🚀 Registrar Nova Entrega</div>', unsafe_allow_html=True)
    df_f = pd.read_sql_query("SELECT id, matricula, nome, whatsapp FROM funcionarios", conn)
    df_e = pd.read_sql_query("SELECT id, nome, ca FROM epis", conn)
    c.execute("SELECT url_sistema FROM config WHERE id=1")
    url_base = c.fetchone()[0]

    if not df_f.empty:
        f_sel = st.selectbox("Colaborador", df_f['matricula'] + " - " + df_f['nome'])
        f_id_val = int(df_f[df_f['matricula'] == f_sel.split(" - ")[0]].iloc[0]['id'])
        
        # CONTADOR DE ITENS
        count_entregas = pd.read_sql_query("SELECT COUNT(*) as total FROM entregas WHERE id_func = ?", conn, params=(f_id_val,)).iloc[0]['total']
        
        st.write(f"Total de EPIs neste prontuário: **{count_entregas}**")
        
        if count_entregas > 0 and count_entregas % 20 == 0:
            st.markdown(f'<div class="status-alerta">⚠️ ATENÇÃO: Este funcionário atingiu {count_entregas} itens. Baixe a ficha atual antes de continuar!</div>', unsafe_allow_html=True)

        e_sel = st.multiselect("EPIs", df_e['nome'] + " (CA: " + df_e['ca'] + ")")
        if st.button("Finalizar Entrega"):
            if e_sel:
                tk = str(random.randint(100000, 999999)); dt = datetime.now().strftime("%d/%m/%Y %H:%M")
                f_zap = df_f[df_f['id'] == f_id_val].iloc[0]
                for item in e_sel:
                    epi_id = df_e[df_e['nome'] == item.split(" (CA: ")[0]].iloc[0]['id']
                    c.execute("INSERT INTO entregas (id_func, id_epi, data, token) VALUES (?,?,?,?)", (f_id_val, int(epi_id), dt, tk))
                conn.commit()
                link = f"{url_base}/?confirmar={tk}"
                msg = urllib.parse.quote(f"🛡️ *SESMT*\nConfirme o recebimento: {', '.join(e_sel)}\nLink: {link}")
                st.markdown(f'<a href="https://api.whatsapp.com/send?phone=55{f_zap["whatsapp"]}&text={msg}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:12px; border-radius:5px; font-weight:bold;">📲 ENVIAR WHATSAPP</button></a>', unsafe_allow_html=True)

# --- RELATÓRIOS (LOGICA DE CICLOS) ---
elif menu == "📑 Relatórios":
    st.markdown('<div class="main-header">📑 Central de Documentos</div>', unsafe_allow_html=True)
    df_f = pd.read_sql_query("SELECT * FROM funcionarios", conn)
    if not df_f.empty:
        sel = st.selectbox("Funcionário", df_f['matricula'] + " - " + df_f['nome'])
        f_dados = df_f[df_f['matricula'] == sel.split(" - ")[0]].iloc[0]
        
        # Busca TODO o histórico
        h_completo = pd.read_sql_query('''SELECT e.data, ep.nome, ep.ca, e.status FROM entregas e 
                                          JOIN epis ep ON e.id_epi = ep.id WHERE e.id_func = ? ORDER BY e.id DESC''', conn, params=(int(f_dados['id']),))
        
        st.subheader("Histórico de Entregas")
        st.dataframe(h_completo.style.map(colorir_status, subset=['status']), use_container_width=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.info("Gera apenas os últimos 20 itens (Ciclo Atual)")
            if st.button("📥 Baixar Ficha Atual (20 itens)"):
                pdf_atual = gerar_pdf_epi(f_dados, h_completo.head(20), "FICHA DE EPI - CICLO ATUAL")
                st.download_button("Confirmar Download Ficha", pdf_atual, f"Ficha_Atual_{f_dados['matricula']}.pdf")
        
        with c2:
            st.warning("Gera o documento com TODAS as entregas já feitas")
            if st.button("📂 Baixar Histórico Completo"):
                pdf_todo = gerar_pdf_epi(f_dados, h_completo, "PRONTUÁRIO COMPLETO DE EPI")
                st.download_button("Confirmar Download Histórico", pdf_todo, f"Historico_Total_{f_dados['matricula']}.pdf")

# --- FUNCIONÁRIOS E CATÁLOGO (MANTIDOS) ---
elif menu == "👥 Funcionários":
    df_f = pd.read_sql_query("SELECT * FROM funcionarios", conn)
    ed = st.data_editor(df_f, num_rows="dynamic", use_container_width=True)
    if st.button("Salvar"): ed.to_sql('funcionarios', conn, if_exists='replace', index=False); st.rerun()

elif menu == "📦 Catálogo":
    df_e = pd.read_sql_query("SELECT * FROM epis", conn)
    ed_e = st.data_editor(df_e, num_rows="dynamic", use_container_width=True)
    if st.button("Salvar"): ed_e.to_sql('epis', conn, if_exists='replace', index=False); st.rerun()

elif menu == "⚙️ Config":
    c.execute("SELECT url_sistema FROM config WHERE id=1")
    url_at = c.fetchone()[0]
    nova = st.text_input("URL do Sistema", url_at)
    if st.button("Salvar"): c.execute("UPDATE config SET url_sistema = ?", (nova,)); conn.commit(); st.success("OK!")
