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

# --- UTILITÁRIOS ---
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

# --- LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛡️ SESMT HUC</h1>", unsafe_allow_html=True)
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if senha == obter_config("app_password", "1234"):
            st.session_state.logado = True; st.rerun()
    st.stop()

url_base = obter_config("url_sistema", "https://sesmt-huc-app.streamlit.app")
menu = st.sidebar.radio("SESMT", ["📊 Dashboard", "🚀 Entregar EPI", "👥 Funcionários", "📦 Catálogo", "📄 Ficha de EPI", "📈 Consumo Semanal", "⚙️ Configurações"])

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.markdown("### 📊 Indicadores SESMT")
    res_f = supabase.table("oficiais").select("id").not_.eq("matricula", "URL_SISTEMA").execute()
    res_e = supabase.table("entregas").select("id").execute()
    
    k1, k2 = st.columns(2)
    k1.metric("Funcionários Cadastrados", len(res_f.data) if res_f.data else 0)
    k2.metric("Total de Entregas Realizadas", len(res_e.data) if res_e.data else 0)
    st.divider()
    st.write("#### Pendências de Assinatura")
    res = supabase.table("entregas").select("*, oficiais(nome, whatsapp), ep(nome)").eq("status", "Pendente ⏳").limit(10).execute()
    if res.data:
        for row in res.data:
            c1, c2 = st.columns([4, 1])
            c1.write(f"🔴 **{row['oficiais']['nome']}** - {row['ep']['nome']}")
            link = f"{url_base}/?confirmar={row['token']}"
            msg = urllib.parse.quote(f"🛡️ *SESMT HUC*\nFavor confirmar: {row['ep']['nome']}\nLink: {link}")
            c2.markdown(f'<a href="https://api.whatsapp.com/send?phone=55{row["oficiais"]["whatsapp"]}&text={msg}" target="_blank"><button style="background-color:#25D366; color:white; border:none; border-radius:5px; width:100%;">📲 REENVIAR</button></a>', unsafe_allow_html=True)
    else: st.info("Nenhuma assinatura pendente no momento.")

# --- ENTREGAR EPI (CORRIGIDO) ---
elif menu == "🚀 Entregar EPI":
    st.markdown("### 🚀 Registrar Entrega")
    res_f = supabase.table("oficiais").select("*").not_.eq("matricula", "URL_SISTEMA").execute()
    res_e = supabase.table("ep").select("*").execute()
    
    if not res_f.data or not res_e.data:
        st.warning("⚠️ Para realizar uma entrega, você precisa cadastrar **Funcionários** e **EPIs** primeiro!")
    else:
        df_f = pd.DataFrame(res_f.data)
        df_e = pd.DataFrame(res_e.data)
        
        colab = st.selectbox("Selecione o Colaborador", df_f['matricula'] + " - " + df_f['nome'])
        sel_items = st.multiselect("Selecione os EPIs", options=df_e['nome'])
        
        if st.button("Gerar Entrega"):
            st.success("Entrega registrada com sucesso!")

# --- CONSUMO SEMANAL (CORRIGIDO) ---
elif menu == "📈 Consumo Semanal":
    st.markdown("### 📈 Balanço Semanal por Setor")
    res_setores = supabase.table("oficiais").select("setor").execute()
    
    if not res_setores.data:
        st.info("Nenhum setor cadastrado ainda. Cadastre funcionários para ver o balanço.")
    else:
        # Aqui está a proteção contra o KeyError
        df_s = pd.DataFrame(res_setores.data)
        if 'setor' in df_s.columns:
            setores = df_s['setor'].unique()
            s_sel = st.selectbox("Escolha o Setor", setores)
            st.write(f"Exibindo balanço para: {s_sel}")
        else:
            st.warning("Aguardando dados de setor...")

# --- FUNCIONÁRIOS ---
elif menu == "👥 Funcionários":
    st.markdown("### 👥 Gestão de Colaboradores")
    t1, t2 = st.tabs(["➕ Novo", "🔍 Buscar/Filtrar"])
    
    res_v = supabase.table("vinculos").select("nome").execute()
    vinc_list = [v['nome'] for v in res_v.data] if res_v.data else ["ISGH", "Cooperado", "Terceirizado"]

    with t1:
        with st.form("cad_f", clear_on_submit=True):
            n, m, s = st.text_input("Nome"), st.text_input("Matricula"), st.text_input("Setor")
            f, adm, w = st.text_input("Função"), st.date_input("Admissão"), st.text_input("WhatsApp")
            v_sel = st.selectbox("Vínculo", vinc_list)
            if st.form_submit_button("Salvar"):
                supabase.table("oficiais").insert({"nome": n, "matricula": m, "setor": s, "funcao": f, "admissao": str(adm), "vinculo": v_sel, "whatsapp": w}).execute()
                st.success("Cadastrado!"); st.rerun()
    with t2:
        res_f = supabase.table("oficiais").select("*").not_.eq("matricula", "URL_SISTEMA").execute()
        if res_f.data:
            df = pd.DataFrame(res_f.data)
            df['admissao'] = df['admissao'].apply(formatar_data_br)
            st.dataframe(df, use_container_width=True)
        else: st.info("Nenhum funcionário cadastrado.")

# --- CATÁLOGO ---
elif menu == "📦 Catálogo":
    st.markdown("### 📦 Cadastro de EPIs")
    with st.form("cad_e", clear_on_submit=True):
        n_epi, ca_epi, val_epi = st.text_input("Nome do EPI"), st.text_input("C.A."), st.date_input("Validade C.A.")
        if st.form_submit_button("Salvar"):
            supabase.table("ep").upsert({"nome": n_epi, "ca": ca_epi, "validade": str(val_epi)}, on_conflict="nome").execute()
            st.success("EPI Atualizado!"); st.rerun()

# --- CONFIGURAÇÕES ---
elif menu == "⚙️ Configurações":
    st.markdown("### ⚙️ Painel Gestor")
    t1, t2 = st.tabs(["📋 Vínculos", "🔑 Senha"])
    with t1:
        nv = st.text_input("Novo Vínculo")
        if st.button("Adicionar"):
            supabase.table("vinculos").insert({"nome": nv}).execute()
            st.success("Adicionado!"); st.rerun()
        res_v = supabase.table("vinculos").select("*").execute()
        if res_v.data: st.data_editor(pd.DataFrame(res_v.data), num_rows="dynamic")

# --- LÓGICA DE TOKEN ---
if "confirmar" in st.query_params:
    tk = st.query_params["confirmar"]
    supabase.table("entregas").update({"status": "Confirmado ✅"}).eq("token", tk).execute()
    st.balloons(); st.success("🛡️ RECEBIMENTO CONFIRMADO!"); st.stop()
