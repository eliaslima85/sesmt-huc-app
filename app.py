import streamlit as st
from supabase import create_client, Client
import random
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse
from fpdf import FPDF

# --- CREDENCIAIS ---
SUPABASE_URL = "https://aatkjhtrafuepwzzlrbm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFhdGtqaHRyYWZ1ZXB3enpscmJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg2Mjg5MTYsImV4cCI6MjA5NDIwNDkxNn0.65izu7Zhc3kUZrVIRXGvVQ5o-Lhk-7PCK9CMg4zIwuk"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="SESMT - HUC Digital", layout="wide")

# --- FUNÇÕES ---
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

# --- PDF ---
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
    cols = [("DATA", 25), ("QTD", 10), ("DESCRICAO", 56), ("C.A.", 20), ("TOKEN", 25), ("STATUS", 40)]
    for txt, w in cols: pdf.cell(w, 8, txt, 1, 0, 'C', fill=True)
    pdf.ln()
    pdf.set_font("Arial", size=7)
    for _, r in df.iterrows():
        pdf.cell(25, 8, formatar_data_br(r['data_entrega']), 1, 0, 'C')
        pdf.cell(10, 8, str(r['quantidade']), 1, 0, 'C')
        pdf.cell(56, 8, remover_acentos(str(r['epi_nome'])[:35]), 1)
        pdf.cell(20, 8, str(r['ca']), 1, 0, 'C')
        pdf.cell(25, 8, str(r['token']), 1, 0, 'C')
        pdf.cell(40, 8, remover_acentos(str(r['status'])), 1, ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1')

# --- LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛡️ SESMT HUC</h1>", unsafe_allow_html=True)
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if senha == obter_config("app_password", "1234"):
            st.session_state.logado = True; st.rerun()
    st.stop()

# --- MENU ---
menu = st.sidebar.radio("SESMT", ["📊 Dashboard", "🚀 Entregar EPI", "👥 Funcionários", "📦 Catálogo", "📄 Ficha de EPI", "📈 Consumo Semanal", "⚙️ Configurações"])

# --- FUNCIONÁRIOS ---
if menu == "👥 Funcionários":
    st.markdown("### 👥 Gestão de Colaboradores")
    t1, t2 = st.tabs(["➕ Novo", "🔍 Buscar/Filtrar"])
    
    with t1:
        v_list = [v['nome'] for v in supabase.table("vinculos").select("nome").execute().data]
        s_list = sorted([s['nome'] for s in supabase.table("setores").select("nome").execute().data])
        f_list = sorted([f['nome'] for f in supabase.table("funcoes").select("nome").execute().data])
        
        with st.form("cad_f", clear_on_submit=True):
            nome = st.text_input("Nome Completo")
            mat = st.text_input("Matricula")
            setor = st.selectbox("Setor (CAIXA ALTA)", s_list)
            funcao = st.selectbox("Função (CAIXA ALTA)", f_list)
            adm = st.date_input("Admissão")
            zap = st.text_input("WhatsApp")
            vinc = st.selectbox("Vínculo", v_list)
            if st.form_submit_button("Salvar"):
                supabase.table("oficiais").insert({"nome": nome, "matricula": mat, "setor": setor, "funcao": funcao, "admissao": str(adm), "vinculo": vinc, "whatsapp": zap}).execute()
                st.success("Cadastrado!"); st.rerun()
    
    with t2:
        df = pd.DataFrame(supabase.table("oficiais").select("*").not_.eq("matricula", "URL_SISTEMA").execute().data)
        if not df.empty:
            busca = st.text_input("Filtrar por nome")
            df_f = df[df['nome'].str.contains(busca, case=False)] if busca else df
            df_f['admissao'] = df_f['admissao'].apply(formatar_data_br)
            st.dataframe(df_f, use_container_width=True)

# --- FICHA DE EPI ---
elif menu == "📄 Ficha de EPI":
    st.markdown("### 📄 Histórico do Funcionário")
    df_f = pd.DataFrame(supabase.table("oficiais").select("*").not_.eq("matricula", "URL_SISTEMA").execute().data)
    if not df_f.empty:
        sel = st.selectbox("Selecione", df_f['nome'])
        f = df_f[df_f['nome'] == sel].iloc[0]
        res_h = supabase.table("entregas").select("*, ep(nome, ca)").eq("id_func", int(f['id'])).order("data_entrega", desc=True).execute()
        if res_h.data:
            h_data = [{"data_entrega": r['data_entrega'], "epi_nome": r['ep']['nome'], "ca": r['ep']['ca'], "quantidade": r['quantidade'], "token": r['token'], "status": r['status']} for r in res_h.data]
            df_h = pd.DataFrame(h_data)
            df_tab = df_h.copy()
            df_tab['data_entrega'] = df_tab['data_entrega'].apply(formatar_data_br)
            st.table(df_tab)
            st.download_button("📥 BAIXAR PDF COMPLETO", gerar_pdf_ficha(f, df_h), f"Ficha_{f['nome']}.pdf")

# --- CONFIGURAÇÕES ---
elif menu == "⚙️ Configurações":
    st.markdown("### ⚙️ Painel de Gestão")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔗 Sistema", "📋 Vínculos", "🏢 Setores", "🛠️ Funções", "📄 Texto Ficha"])
    
    with tab2: # Vínculos
        nv = st.text_input("Novo Vínculo", key="in_vinc")
        if st.button("Adicionar", key="btn_vinc"):
            supabase.table("vinculos").insert({"nome": nv}).execute(); st.rerun()
        st.data_editor(pd.DataFrame(supabase.table("vinculos").select("*").execute().data), key="edit_vinc", num_rows="dynamic")
    
    with tab3: # Setores
        ns = st.text_input("Novo Setor", key="in_setor")
        if st.button("Adicionar", key="btn_setor"):
            supabase.table("setores").insert({"nome": ns}).execute(); st.rerun()
        st.data_editor(pd.DataFrame(supabase.table("setores").select("*").execute().data), key="edit_setor", num_rows="dynamic")
        
    with tab4: # Funções
        nf = st.text_input("Nova Função", key="in_func")
        if st.button("Adicionar", key="btn_func"):
            supabase.table("funcoes").insert({"nome": nf}).execute(); st.rerun()
        st.data_editor(pd.DataFrame(supabase.table("funcoes").select("*").execute().data), key="edit_func", num_rows="dynamic")
        
    with tab5: # Texto da Ficha
        termo = st.text_area("Texto Legal", obter_config("ficha_descricao"), key="txt_ficha")
        if st.button("Salvar Texto", key="btn_ficha"):
            supabase.table("configuracoes").upsert({"chave": "ficha_descricao", "valor": termo}).execute()
            st.success("Salvo!")

# (Lógica de Dashboard, Entregas e Consumo mantida...)
