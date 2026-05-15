import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import urllib.parse
from fpdf import FPDF

# --- CREDENCIAIS REAIS ---
SUPABASE_URL = "https://aatkjhtrafuepwzzlrbm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFhdGtqaHRyYWZ1ZXB3enpscmJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg2Mjg5MTYsImV4cCI6MjA5NDIwNDkxNn0.65izu7Zhc3kUZrVIRXGvVQ5o-Lhk-7PCK9CMg4zIwuk"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="SESMT HUC - Digital", layout="wide")

# --- UTILITÁRIOS ---
def format_br(d):
    if not d: return ""
    try: return datetime.strptime(str(d).split('T')[0], '%Y-%m-%d').strftime('%d/%m/%Y')
    except: return d

def get_config(key, default=""):
    try:
        res = supabase.table("configuracoes").select("valor").eq("chave", key).execute()
        return res.data[0]['valor'] if res.data else default
    except: return default

# --- LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛡️ SESMT HUC</h1>", unsafe_allow_html=True)
    pw = st.text_input("Senha", type="password", key="login_pass")
    if st.button("Entrar", key="login_btn"):
        if pw == get_config("app_password", "1234"):
            st.session_state.logado = True; st.rerun()
    st.stop()

menu = st.sidebar.radio("MENU", ["📊 Dashboard", "🚀 Entregar EPI", "👥 Funcionários", "📦 Catálogo", "📄 Ficha de EPI", "📈 Consumo Semanal", "⚙️ Configurações"])

# --- PÁGINA: FUNCIONÁRIOS ---
if menu == "👥 Funcionários":
    st.title("👥 Gestão de Colaboradores")
    t1, t2 = st.tabs(["➕ Novo Cadastro", "🔍 Buscar/Filtrar"])
    
    # Puxar listas do banco
    s_data = supabase.table("setores").select("nome").order("nome").execute().data
    f_data = supabase.table("funcoes").select("nome").order("nome").execute().data
    v_data = supabase.table("vinculos").select("nome").execute().data
    
    with t1:
        with st.form("cad_func", clear_on_submit=True):
            nome = st.text_input("Nome Completo")
            mat = st.text_input("Matrícula")
            # Selectboxes com os dados do HUC
            setor = st.selectbox("Setor (Caixa Alta)", [s['nome'] for s in s_data] if s_data else ["Cadastre em Configurações"])
            funcao = st.selectbox("Função (Caixa Alta)", [f['nome'] for f in f_data] if f_data else ["Cadastre em Configurações"])
            adm = st.date_input("Admissão", format="DD/MM/YYYY")
            zap = st.text_input("WhatsApp")
            vinc = st.selectbox("Vínculo", [v['nome'] for v in v_data] if v_data else ["ISGH"])
            
            if st.form_submit_button("Salvar"):
                try:
                    supabase.table("oficiais").insert({
                        "nome": nome, "matricula": mat, "setor": setor, 
                        "funcao": funcao, "admissao": str(adm), "vinculo": vinc, "whatsapp": zap
                    }).execute()
                    st.success("✅ Salvo com sucesso!")
                except Exception as e:
                    st.error(f"❌ Erro ao salvar: Verifique se a matrícula já existe ou se as permissões no Supabase foram dadas.")

# --- PÁGINA: CONFIGURAÇÕES (REGISTRO DE SETOR E FUNÇÃO) ---
elif menu == "⚙️ Configurações":
    st.title("⚙️ Painel de Gestão")
    tab1, tab2, tab3, tab4 = st.tabs(["🔗 Sistema", "🏢 Setores", "🛠️ Funções", "📋 Vínculos"])
    
    with tab2:
        st.write("#### Cadastrar Novo Setor")
        ns = st.text_input("Nome do Setor", key="in_setor").upper()
        if st.button("Salvar Setor", key="btn_setor"):
            try:
                supabase.table("setores").insert({"nome": ns}).execute()
                st.success(f"Setor {ns} cadastrado!"); st.rerun()
            except: st.error("Erro: Setor já existe.")
        st.data_editor(pd.DataFrame(supabase.table("setores").select("*").execute().data), key="edit_set", num_rows="dynamic")

    with tab3:
        st.write("#### Cadastrar Nova Função")
        nf = st.text_input("Nome da Função", key="in_func").upper()
        if st.button("Salvar Função", key="btn_func"):
            try:
                supabase.table("funcoes").insert({"nome": nf}).execute()
                st.success(f"Função {nf} cadastrada!"); st.rerun()
            except: st.error("Erro: Função já existe.")
        st.data_editor(pd.DataFrame(supabase.table("funcoes").select("*").execute().data), key="edit_fun", num_rows="dynamic")
