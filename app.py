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

st.set_page_config(page_title="SESMT - HUC Digital", layout="wide")

# --- FUNÇÕES ---
def formatar_data_br(data_str):
    if not data_str: return ""
    try:
        dt = datetime.strptime(str(data_str).split('T')[0], '%Y-%m-%d')
        return dt.strftime('%d/%m/%Y')
    except: return data_str

def obter_config(chave, padrao=""):
    try:
        res = supabase.table("configuracoes").select("valor").eq("chave", chave).execute()
        return res.data[0]['valor'] if res.data else padrao
    except: return padrao

# --- LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛡️ SESMT HUC</h1>", unsafe_allow_html=True)
    senha = st.text_input("Senha", type="password", key="main_login")
    if st.button("Entrar", key="btn_login"):
        if senha == obter_config("app_password", "1234"):
            st.session_state.logado = True; st.rerun()
    st.stop()

menu = st.sidebar.radio("MENU", ["📊 Dashboard", "🚀 Entregar EPI", "👥 Funcionários", "📦 Catálogo", "📄 Ficha de EPI", "📈 Consumo Semanal", "⚙️ Configurações"])

# --- PÁGINA: FUNCIONÁRIOS ---
if menu == "👥 Funcionários":
    st.markdown("### 👥 Gestão de Colaboradores")
    t1, t2 = st.tabs(["➕ Novo Cadastro", "🔍 Buscar/Filtrar"])
    
    # Carregar listas do banco (Puxando os dados reais que você inseriu no Passo 1)
    v_data = supabase.table("vinculos").select("nome").execute().data
    s_data = supabase.table("setores").select("nome").execute().data
    f_data = supabase.table("funcoes").select("nome").execute().data
    
    v_list = [v['nome'] for v in v_data] if v_data else ["ISGH"]
    s_list = sorted([s['nome'] for s in s_data]) if s_data else ["Erro ao carregar setores"]
    f_list = sorted([f['nome'] for f in f_data]) if f_data else ["Erro ao carregar funções"]

    with t1:
        with st.form("form_funcionario", clear_on_submit=True):
            n = st.text_input("Nome Completo")
            m = st.text_input("Matricula")
            # Forçando formato BR no calendário
            adm = st.date_input("Admissão", format="DD/MM/YYYY")
            s_sel = st.selectbox("Setor", s_list)
            f_sel = st.selectbox("Função", f_list)
            w = st.text_input("WhatsApp")
            v_sel = st.selectbox("Vínculo", v_list)
            if st.form_submit_button("Salvar Funcionário"):
                supabase.table("oficiais").insert({
                    "nome": n, "matricula": m, "setor": s_sel, "funcao": f_sel, 
                    "admissao": str(adm), "vinculo": v_sel, "whatsapp": w
                }).execute()
                st.success("Salvo com sucesso!"); st.rerun()

# --- PÁGINA: CONFIGURAÇÕES (RESOLVENDO O ERRO DE INSERÇÃO) ---
elif menu == "⚙️ Configurações":
    st.markdown("### ⚙️ Painel de Gestão")
    tab1, tab2, tab3, tab4 = st.tabs(["🔗 Sistema", "📋 Vínculos", "🏢 Setores", "🛠️ Funções"])
    
    with tab2:
        nv = st.text_input("Novo Vínculo", key="add_vinc_in")
        if st.button("Adicionar Vínculo", key="btn_v"):
            supabase.table("vinculos").insert({"nome": nv}).execute(); st.rerun()
        st.data_editor(pd.DataFrame(supabase.table("vinculos").select("*").execute().data), key="edit_vinc")

    with tab3:
        ns = st.text_input("Novo Setor", key="add_set_in")
        if st.button("Adicionar Setor", key="btn_s"):
            supabase.table("setores").insert({"nome": ns}).execute(); st.rerun()
        st.data_editor(pd.DataFrame(supabase.table("setores").select("*").execute().data), key="edit_set")

    with tab4:
        nf = st.text_input("Nova Função", key="add_func_in")
        if st.button("Adicionar Função", key="btn_f"):
            supabase.table("funcoes").insert({"nome": nf}).execute(); st.rerun()
        st.data_editor(pd.DataFrame(supabase.table("funcoes").select("*").execute().data), key="edit_func")
