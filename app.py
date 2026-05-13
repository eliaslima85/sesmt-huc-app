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
    .stButton>button { background-color: #004a87; color: white; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS ---
def conectar(): return sqlite3.connect('gestao_epi_sesmt.db', check_same_thread=False)
conn = conectar()
c = conn.cursor()

c.execute('CREATE TABLE IF NOT EXISTS funcionarios (id INTEGER PRIMARY KEY, nome TEXT, matricula TEXT UNIQUE, setor TEXT, funcao TEXT, admissao TEXT, turno TEXT, vinculo TEXT, whatsapp TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS epis (id INTEGER PRIMARY KEY, nome TEXT, ca TEXT)')
# O status nasce como Pendente por padrão
c.execute('CREATE TABLE IF NOT EXISTS entregas (id INTEGER PRIMARY KEY, id_func INTEGER, id_epi INTEGER, data TEXT, token TEXT, status TEXT DEFAULT "Pendente ⏳")')
c.execute('CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY, senha TEXT, url_sistema TEXT)')

try:
    c.execute('ALTER TABLE config ADD COLUMN url_sistema TEXT')
    conn.commit()
except:
    pass

c.execute("INSERT OR IGNORE INTO config (id, senha, url_sistema) VALUES (1, '1234', 'http://localhost:8501')")
conn.commit()

# --- FUNÇÕES AUXILIARES ---
def colorir_status(val):
    if not isinstance(val, str): return ""
    color = 'red' if 'Pendente' in val else 'green'
    return f'color: {color}; font-weight: bold'

def limpar_texto(texto):
    return str(texto).replace("✅", "").replace("⏳", "").replace("🛡️", "").strip().encode('latin-1', 'replace').decode('latin-1')

# --- ROTA DE CONFIRMAÇÃO (O que o funcionário acessa) ---
if "confirmar" in st.query_params:
    tk = st.query_params["confirmar"]
    c.execute("UPDATE entregas SET status = 'Confirmado ✅' WHERE token = ?", (tk,))
    conn.commit()
    st.balloons()
    st.success("🛡️ Assinatura Digital SESMT HUC Confirmada!")
    st.info("Sua confirmação foi registrada com sucesso.")
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

# --- PDF SETORIAL DETALHADO ---
def gerar_pdf_setor(df, setor):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, f"RELATORIO EPI - SETOR: {limpar_texto(setor)}", ln=True, align='C')
    pdf.ln(5); pdf.set_font("Arial", 'B', 8)
    pdf.cell(25, 8, "DATA", 1); pdf.cell(50, 8, "FUNCIONARIO", 1); pdf.cell(60, 8, "EPI", 1); pdf.cell(20, 8, "C.A.", 1); pdf.cell(35, 8, "STATUS", 1, ln=True)
    pdf.set_font("Arial", size=8)
    for _, r in df.iterrows():
        pdf.cell(25, 8, limpar_texto(r['data']), 1); pdf.cell(50, 8, limpar_texto(r['Colaborador'])[:30], 1); pdf.cell(60, 8, limpar_texto(r['EPI'])[:35], 1); pdf.cell(20, 8, limpar_texto(r['ca']), 1); pdf.cell(35, 8, limpar_texto(r['status']), 1, ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- MENU ---
menu = st.sidebar.radio("SESMT MENU", ["📊 Dashboard", "🚀 Entregar EPI", "👥 Funcionários", "📦 Catálogo EPI", "📑 Relatórios", "⚙️ Configurações"])

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.markdown('<div class="main-header">📊 Painel de Controle SESMT</div>', unsafe_allow_html=True)
    recentes = pd.read_sql_query('''SELECT f.nome as Colaborador, ep.nome as EPI, e.data, e.status 
                                     FROM entregas e JOIN funcionarios f ON e.id_func = f.id 
                                     JOIN epis ep ON e.id_epi = ep.id ORDER BY e.id DESC LIMIT 10''', conn)
    st.subheader("Status de Entregas (Pendente em Vermelho)")
    # Correção: usando .map para compatibilidade
    st.dataframe(recentes.style.map(colorir_status, subset=['status']), use_container_width=True)

# --- ENTREGAR EPI ---
elif menu == "🚀 Entregar EPI":
    st.markdown('<div class="main-header">🚀 Registrar Entrega</div>', unsafe_allow_html=True)
    df_f = pd.read_sql_query("SELECT id, matricula, nome, whatsapp FROM funcionarios", conn)
    df_e = pd.read_sql_query("SELECT id, nome, ca FROM epis", conn)
    c.execute("SELECT url_sistema FROM config WHERE id=1")
    url_base = c.fetchone()[0]

    if df_f.empty: st.warning("Cadastre funcionários primeiro.")
    else:
        f_sel = st.selectbox("Colaborador", df_f['matricula'] + " - " + df_f['nome'])
        e_sel = st.multiselect("EPIs", df_e['nome'] + " (CA: " + df_e['ca'] + ")")
        if st.button("Gerar Entrega (Ficará Pendente)"):
            if e_sel:
                tk = str(random.randint(100000, 999999)); dt = datetime.now().strftime("%d/%m/%Y %H:%M")
                f_data = df_f[df_f['matricula'] == f_sel.split(" - ")[0]].iloc[0]
                for item in e_sel:
                    epi_id = df_e[df_e['nome'] == item.split(" (CA: ")[0]].iloc[0]['id']
                    c.execute("INSERT INTO entregas (id_func, id_epi, data, token) VALUES (?,?,?,?)", (int(f_data['id']), int(epi_id), dt, tk))
                conn.commit()
                link = f"{url_base}/?confirmar={tk}"
                msg = urllib.parse.quote(f"🛡️ *SESMT HUC*\nOlá, {f_data['nome']}!\nConfirme o recebimento: {', '.join(e_sel)}\nLink: {link}")
                st.success("Status: PENDENTE ⏳ (Aguardando assinatura)")
                st.markdown(f'<a href="https://api.whatsapp.com/send?phone=55{f_data["whatsapp"]}&text={msg}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:12px; border-radius:5px; font-weight:bold; cursor:pointer;">📲 ENVIAR WHATSAPP</button></a>', unsafe_allow_html=True)

# --- RELATÓRIOS POR SETOR ---
elif menu == "📑 Relatórios":
    st.markdown('<div class="main-header">📑 Relatórios Setoriais</div>', unsafe_allow_html=True)
    setores = pd.read_sql_query("SELECT DISTINCT setor FROM funcionarios", conn)
    if not setores.empty:
        s_esc = st.selectbox("Selecione o Setor", setores['setor'])
        query = '''SELECT e.data, f.nome as Colaborador, ep.nome as EPI, ep.ca, e.status 
                   FROM entregas e JOIN funcionarios f ON e.id_func = f.id 
                   JOIN epis ep ON e.id_epi = ep.id WHERE f.setor = ?'''
        df_set = pd.read_sql_query(query, conn, params=(s_esc,))
        st.dataframe(df_set.style.map(colorir_status, subset=['status']), use_container_width=True)
        if st.button("📥 Baixar PDF do Setor"):
            st.download_button("Download PDF", gerar_pdf_setor(df_set, s_esc), f"Relatorio_{s_esc}.pdf")

# --- CONFIGURAÇÕES ---
elif menu == "⚙️ Configurações":
    st.markdown('<div class="main-header">⚙️ Ajustar Link Oficial</div>', unsafe_allow_html=True)
    c.execute("SELECT url_sistema FROM config WHERE id=1")
    url_at = c.fetchone()[0]
    st.info(f"Link atual cadastrado: {url_at}")
    nova_u = st.text_input("Cole aqui o link do seu app (Ex: https://sesmt-huc.streamlit.app)")
    if st.button("Salvar Novo Link"):
        c.execute("UPDATE config SET url_sistema = ? WHERE id=1", (nova_u,))
        conn.commit(); st.success("Link atualizado com sucesso!")
