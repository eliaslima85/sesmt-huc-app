import streamlit as st
from supabase import create_client, Client
import random
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse
from fpdf import FPDF

# --- CREDENCIAIS REAIS ---
SUPABASE_URL = "https://aatkjhtrafuepwzzlrbm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFhdGtqaHRyYWZ1ZXB3enpscmJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg2Mjg5MTYsImV4cCI6MjA5NDIwNDkxNn0.65izu7Zhc3kUZrVIRXGvVQ5o-Lhk-7PCK9CMg4zIwuk"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="SESMT - HUC Digital", layout="wide", page_icon="🛡️")

# --- FUNÇÕES DE UTILIDADE ---
def formatar_data_br(data_str):
    if not data_str: return ""
    try:
        dt = datetime.strptime(str(data_str).split('T')[0], '%Y-%m-%d')
        return dt.strftime('%d/%m/%Y')
    except: return data_str

def remover_acentos(texto):
    return str(texto).encode('latin-1', 'replace').decode('latin-1')

def obter_config(chave, padrao=""):
    try:
        res = supabase.table("configuracoes").select("valor").eq("chave", chave).execute()
        return res.data[0]['valor'] if res.data else padrao
    except: return padrao

# --- PDF FICHA INDIVIDUAL ---
def gerar_pdf_ficha(f, df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 8, "HOSPITAL UNIVERSITARIO DO CEARA - HUC - ISGH", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, "CNPJ: 05.268.526/0024-67", ln=True, align='C'); pdf.ln(5)
    pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, remover_acentos(f" FICHA DE EPI - {f['nome'].upper()}"), ln=True, align='L', fill=True); pdf.ln(2)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(100, 7, f"NOME: {remover_acentos(f['nome'])}", 0); pdf.cell(90, 7, f"MATRICULA: {f['matricula']}", ln=True)
    pdf.cell(100, 7, f"SETOR: {remover_acentos(f['setor'])}", 0); pdf.cell(90, 7, f"VINCULO: {remover_acentos(f['vinculo'])}", ln=True); pdf.ln(5)
    pdf.set_font("Arial", 'B', 7)
    pdf.cell(25, 8, "DATA", 1, 0, 'C', fill=True); pdf.cell(10, 8, "QTD", 1, 0, 'C', fill=True)
    pdf.cell(56, 8, "DESCRICAO DO EPI", 1, 0, 'C', fill=True); pdf.cell(20, 8, "C.A.", 1, 0, 'C', fill=True)
    pdf.cell(25, 8, "TOKEN", 1, 0, 'C', fill=True); pdf.cell(40, 8, "STATUS", 1, ln=True, align='C', fill=True)
    pdf.set_font("Arial", size=7)
    for _, r in df.iterrows():
        pdf.cell(25, 8, formatar_data_br(r['data_entrega']), 1, 0, 'C')
        pdf.cell(10, 8, str(r['quantidade']), 1, 0, 'C')
        pdf.cell(56, 8, remover_acentos(str(r['epi_nome'])[:35]), 1)
        pdf.cell(20, 8, str(r['ca']), 1, 0, 'C')
        pdf.cell(25, 8, str(r['token']), 1, 0, 'C')
        pdf.cell(40, 8, remover_acentos(str(r['status'])), 1, ln=True, align='C')
    pdf.ln(10); pdf.set_font("Arial", 'I', 8)
    pdf.multi_cell(0, 5, remover_acentos(obter_config("ficha_descricao", "Conforme NR-06...")), align='J')
    return pdf.output(dest='S').encode('latin-1')

# --- LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛡️ SESMT HUC</h1>", unsafe_allow_html=True)
    senha = st.text_input("Senha", type="password", key="login_pass")
    if st.button("Entrar", key="login_btn"):
        if senha == obter_config("app_password", "1234"):
            st.session_state.logado = True; st.rerun()
    st.stop()

url_base = obter_config("url_sistema", "https://sesmt-huc-app.streamlit.app")
menu = st.sidebar.radio("SESMT MENU", ["📊 Dashboard", "🚀 Entregar EPI", "👥 Funcionários", "📦 Catálogo", "📄 Ficha de EPI", "📈 Consumo Semanal", "⚙️ Configurações"])

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.markdown("### 📊 Indicadores SESMT")
    res_f = supabase.table("oficiais").select("id").not_.eq("matricula", "URL_SISTEMA").execute()
    res_e = supabase.table("entregas").select("id").execute()
    c1, c2 = st.columns(2)
    c1.metric("Funcionários", len(res_f.data))
    c2.metric("Total Entregas", len(res_e.data))
    st.divider()
    res_p = supabase.table("entregas").select("*, oficiais(nome, whatsapp), ep(nome)").eq("status", "Pendente ⏳").limit(10).execute()
    if res_p.data:
        for row in res_p.data:
            col1, col2 = st.columns([4, 1])
            col1.write(f"🔴 **{row['oficiais']['nome']}** - {row['ep']['nome']}")
            msg = urllib.parse.quote(f"🛡️ *SESMT HUC*\nAssine: {url_base}/?confirmar={row['token']}")
            col2.markdown(f'<a href="https://api.whatsapp.com/send?phone=55{row["oficiais"]["whatsapp"]}&text={msg}" target="_blank"><button style="background-color:#25D366; color:white; border:none; border-radius:5px; width:100%;">📲 REENVIAR</button></a>', unsafe_allow_html=True)

# --- FUNCIONÁRIOS ---
elif menu == "👥 Funcionários":
    st.markdown("### 👥 Gestão e Filtros")
    t1, t2 = st.tabs(["➕ Novo", "🔍 Buscar/Filtrar"])
    with t1:
        v_list = [v['nome'] for v in supabase.table("vinculos").select("nome").execute().data]
        s_list = sorted([s['nome'] for s in supabase.table("setores").select("nome").execute().data])
        f_list = sorted([f['nome'] for f in supabase.table("funcoes").select("nome").execute().data])
        with st.form("cad_f", clear_on_submit=True):
            n, m = st.text_input("Nome"), st.text_input("Matricula")
            setor = st.selectbox("Setor", s_list); cargo = st.selectbox("Função", f_list)
            adm = st.date_input("Admissão", format="DD/MM/YYYY"); zap = st.text_input("WhatsApp")
            vinc = st.selectbox("Vínculo", v_list)
            if st.form_submit_button("Salvar"):
                supabase.table("oficiais").insert({"nome": n, "matricula": m, "setor": setor, "funcao": cargo, "admissao": str(adm), "vinculo": vinc, "whatsapp": zap}).execute()
                st.success("Cadastrado!"); st.rerun()
    with t2:
        df = pd.DataFrame(supabase.table("oficiais").select("*").not_.eq("matricula", "URL_SISTEMA").execute().data)
        if not df.empty:
            busca = st.text_input("Buscar por nome", key="busca_f")
            df_res = df[df['nome'].str.contains(busca, case=False)] if busca else df
            df_res['admissao'] = df_res['admissao'].apply(formatar_data_br)
            st.dataframe(df_res, use_container_width=True)

# --- FICHA DE EPI ---
elif menu == "📄 Ficha de EPI":
    st.markdown("### 📄 Histórico e Ficha Individual")
    df_f = pd.DataFrame(supabase.table("oficiais").select("*").not_.eq("matricula", "URL_SISTEMA").execute().data)
    if not df_f.empty:
        sel_n = st.selectbox("Escolha o Funcionário", df_f['nome'], key="sel_ficha")
        f = df_f[df_f['nome'] == sel_n].iloc[0]
        res_h = supabase.table("entregas").select("*, ep(nome, ca)").eq("id_func", int(f['id'])).order("data_entrega", desc=True).execute()
        if res_h.data:
            h_df = pd.DataFrame([{"data_entrega": r['data_entrega'], "epi_nome": r['ep']['nome'], "ca": r['ep']['ca'], "quantidade": r['quantidade'], "token": r['token'], "status": r['status']} for r in res_h.data])
            h_df_tab = h_df.copy(); h_df_tab['data_entrega'] = h_df_tab['data_entrega'].apply(formatar_data_br)
            st.table(h_df_tab)
            st.download_button("📥 BAIXAR PDF COMPLETO", gerar_pdf_ficha(f, h_df), f"Ficha_{f['nome']}.pdf", key="dl_pdf")

# --- CONFIGURAÇÕES ---
elif menu == "⚙️ Configurações":
    st.markdown("### ⚙️ Painel Gestor")
    ta1, ta2, ta3, ta4, ta5 = st.tabs(["🔗 Sistema", "📋 Vínculos", "🏢 Setores", "🛠️ Funções", "📄 Texto Ficha"])
    with ta2:
        nv = st.text_input("Novo Vínculo", key="in_v")
        if st.button("Adicionar Vínculo", key="bt_v"):
            supabase.table("vinculos").insert({"nome": nv}).execute(); st.rerun()
        st.data_editor(pd.DataFrame(supabase.table("vinculos").select("*").execute().data), key="ed_vinc", num_rows="dynamic")
    with ta3:
        ns = st.text_input("Novo Setor", key="in_s")
        if st.button("Adicionar Setor", key="bt_s"):
            supabase.table("setores").insert({"nome": ns}).execute(); st.rerun()
        st.data_editor(pd.DataFrame(supabase.table("setores").select("*").execute().data), key="ed_set", num_rows="dynamic")
    with ta4:
        nf = st.text_input("Nova Função", key="in_f")
        if st.button("Adicionar Função", key="bt_f"):
            supabase.table("funcoes").insert({"nome": nf}).execute(); st.rerun()
        st.data_editor(pd.DataFrame(supabase.table("funcoes").select("*").execute().data), key="ed_func", num_rows="dynamic")
