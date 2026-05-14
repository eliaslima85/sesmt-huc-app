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

# --- UTILITÁRIOS ---
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
    senha = st.text_input("Senha", type="password", key="login_pass")
    if st.button("Entrar", key="login_btn"):
        if senha == obter_config("app_password", "1234"):
            st.session_state.logado = True; st.rerun()
    st.stop()

menu = st.sidebar.radio("MENU", ["📊 Dashboard", "🚀 Entregar EPI", "👥 Funcionários", "📦 Catálogo", "📄 Ficha de EPI", "📈 Consumo Semanal", "⚙️ Configurações"])

# --- PÁGINA: FUNCIONÁRIOS ---
if menu == "👥 Funcionários":
    st.markdown("### 👥 Gestão de Colaboradores")
    t1, t2 = st.tabs(["➕ Novo Cadastro", "🔍 Buscar/Filtrar"])
    
    # Carregar listas com tratamento de erro
    vinc_data = supabase.table("vinculos").select("nome").execute().data
    setor_data = supabase.table("setores").select("nome").execute().data
    func_data = supabase.table("funcoes").select("nome").execute().data
    
    v_list = [v['nome'] for v in vinc_data] if vinc_data else ["Cadastre em Configurações"]
    s_list = sorted([s['nome'] for s in setor_data]) if setor_data else ["Sem setores"]
    f_list = sorted([f['nome'] for f in func_data]) if func_data else ["Sem funções"]

    with t1:
        with st.form("form_novo_func", clear_on_submit=True):
            n = st.text_input("Nome Completo", key="f_nome")
            m = st.text_input("Matricula", key="f_mat")
            # Agora com data no formato BR
            adm = st.date_input("Admissão", format="DD/MM/YYYY", key="f_adm")
            s_sel = st.selectbox("Setor (CAIXA ALTA)", s_list, key="f_setor")
            f_sel = st.selectbox("Função (CAIXA ALTA)", f_list, key="f_funcao")
            w = st.text_input("WhatsApp", key="f_zap")
            v_sel = st.selectbox("Vínculo", v_list, key="f_vinc")
            
            if st.form_submit_button("Salvar Funcionário"):
                if "Sem" in s_sel or "Sem" in f_sel:
                    st.error("Erro: Cadastre Setores e Funções em Configurações primeiro!")
                else:
                    supabase.table("oficiais").insert({
                        "nome": n, "matricula": m, "setor": s_sel, "funcao": f_sel, 
                        "admissao": str(adm), "vinculo": v_sel, "whatsapp": w
                    }).execute()
                    st.success("Funcionário salvo com sucesso!"); st.rerun()

# --- PÁGINA: CONFIGURAÇÕES (RESOLVENDO O ERRO DE DUPLICIDADE) ---
elif menu == "⚙️ Configurações":
    st.markdown("### ⚙️ Painel de Gestão")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔗 Sistema", "📋 Vínculos", "🏢 Setores", "🛠️ Funções", "📄 Texto da Ficha"])
    
    with tab2: # Vínculos
        st.write("#### Gerenciar Vínculos")
        nv = st.text_input("Novo Vínculo", key="in_nv_vinc")
        if st.button("Adicionar Vínculo", key="btn_add_vinc"):
            supabase.table("vinculos").insert({"nome": nv}).execute(); st.rerun()
        # Chave única para o editor
        st.data_editor(pd.DataFrame(supabase.table("vinculos").select("*").execute().data), key="editor_vinc", num_rows="dynamic")
    
    with tab3: # Setores
        st.write("#### Gerenciar Setores")
        ns = st.text_input("Novo Setor", key="in_nv_setor")
        if st.button("Adicionar Setor", key="btn_add_setor"):
            supabase.table("setores").insert({"nome": ns}).execute(); st.rerun()
        st.data_editor(pd.DataFrame(supabase.table("setores").select("*").execute().data), key="editor_setor", num_rows="dynamic")
        
    with tab4: # Funções
        st.write("#### Gerenciar Funções")
        nf = st.text_input("Nova Função", key="in_nv_func")
        if st.button("Adicionar Função", key="btn_add_func"):
            supabase.table("funcoes").insert({"nome": nf}).execute(); st.rerun()
        st.data_editor(pd.DataFrame(supabase.table("funcoes").select("*").execute().data), key="editor_func", num_rows="dynamic")

    with tab5: # Texto da Ficha
        texto_atual = obter_config("ficha_descricao", "Termos da NR-06...")
        novo_texto = st.text_area("Texto da Ficha de EPI", texto_atual, height=200, key="txt_area_ficha")
        if st.button("Salvar Texto Legal", key="btn_save_txt"):
            supabase.table("configuracoes").upsert({"chave": "ficha_descricao", "valor": novo_texto}).execute()
            st.success("Texto atualizado!")
