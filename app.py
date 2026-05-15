import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import random
import urllib.parse
from fpdf import FPDF

# --- CREDENCIAIS ---
SUPABASE_URL = "https://aatkjhtrafuepwzzlrbm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFhdGtqaHRyYWZ1ZXB3enpscmJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg2Mjg5MTYsImV4cCI6MjA5NDIwNDkxNn0.65izu7Zhc3kUZrVIRXGvVQ5o-Lhk-7PCK9CMg4zIwuk"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="SESMT HUC - Digital", layout="wide")

# --- FUNÇÕES CORE ---
def format_br(d):
    if not d: return ""
    try: return datetime.strptime(str(d).split('T')[0], '%Y-%m-%d').strftime('%d/%m/%Y')
    except: return d

def get_config(key, default=""):
    try:
        res = supabase.table("configuracoes").select("valor").eq("chave", key).execute()
        return res.data[0]['valor'] if res.data else default
    except: return default

def remove_accents(t):
    return str(t).encode('latin-1', 'replace').decode('latin-1')

# --- PDF GENERATOR ---
def create_pdf(f, df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "HOSPITAL UNIVERSITARIO DO CEARA - HUC", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 5, "CNPJ: 05.268.526/0024-67", ln=True, align='C'); pdf.ln(10)
    
    pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, remove_accents(f" FICHA DE EPI - {f['nome'].upper()}"), ln=True, fill=True); pdf.ln(2)
    
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(100, 7, f"NOME: {remove_accents(f['nome'])}", 0); pdf.cell(90, 7, f"MATRICULA: {f['matricula']}", ln=True)
    pdf.cell(100, 7, f"SETOR: {remove_accents(f['setor'])}", 0); pdf.cell(90, 7, f"VINCULO: {remove_accents(f['vinculo'])}", ln=True); pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 7)
    headers = [("DATA", 25), ("QTD", 10), ("EPI", 60), ("C.A.", 20), ("TOKEN", 25), ("STATUS", 40)]
    for txt, w in headers: pdf.cell(w, 8, txt, 1, 0, 'C', fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", size=7)
    for _, r in df.iterrows():
        pdf.cell(25, 8, format_br(r['data_entrega']), 1, 0, 'C')
        pdf.cell(10, 8, str(r['quantidade']), 1, 0, 'C')
        pdf.cell(60, 8, remove_accents(str(r['epi_nome'])[:35]), 1)
        pdf.cell(20, 8, str(r['ca']), 1, 0, 'C')
        pdf.cell(25, 8, str(r['token']), 1, 0, 'C')
        pdf.cell(40, 8, remove_accents(str(r['status'])), 1, ln=True, align='C')
    
    pdf.ln(10); pdf.set_font("Arial", 'I', 8)
    pdf.multi_cell(0, 5, remove_accents(get_config("ficha_descricao")), align='J')
    return pdf.output(dest='S').encode('latin-1')

# --- LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛡️ SESMT HUC</h1>", unsafe_allow_html=True)
    pw = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if pw == get_config("app_password", "1234"):
            st.session_state.logado = True; st.rerun()
    st.stop()

# --- SIDEBAR & MENU ---
menu = st.sidebar.radio("SESMT", ["📊 Dashboard", "🚀 Entregar EPI", "👥 Funcionários", "📦 Catálogo", "📄 Ficha de EPI", "📈 Consumo Semanal", "⚙️ Configurações"])
url_base = get_config("url_sistema", "https://sesmt-huc-app.streamlit.app")

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Indicadores de Gestão")
    res_f = supabase.table("oficiais").select("id").execute()
    res_e = supabase.table("entregas").select("id").execute()
    res_p = supabase.table("entregas").select("id").eq("status", "Pendente ⏳").execute()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Funcionários", len(res_f.data))
    c2.metric("Total Entregas", len(res_e.data))
    c3.metric("Assinaturas Pendentes", len(res_p.data), delta_color="inverse")
    st.divider()
    
    st.write("#### Reenviar Tokens Pendentes")
    p_data = supabase.table("entregas").select("*, oficiais(nome, whatsapp), ep(nome)").eq("status", "Pendente ⏳").limit(10).execute()
    for r in p_data.data:
        col1, col2 = st.columns([4, 1])
        col1.write(f"🔴 **{r['oficiais']['nome']}** | {r['ep']['nome']}")
        msg = urllib.parse.quote(f"🛡️ *SESMT HUC*\nAssine seu EPI: {url_base}/?confirmar={r['token']}")
        col2.markdown(f'<a href="https://api.whatsapp.com/send?phone=55{r["oficiais"]["whatsapp"]}&text={msg}" target="_blank"><button style="background-color:#25D366; color:white; border:none; border-radius:5px; width:100%; cursor:pointer;">📲 REZAP</button></a>', unsafe_allow_html=True)

# --- FUNCIONÁRIOS ---
elif menu == "👥 Funcionários":
    st.title("👥 Gestão de Colaboradores")
    t1, t2 = st.tabs(["➕ Novo", "🔍 Filtrar/Buscar"])
    
    vinculos = [v['nome'] for v in supabase.table("vinculos").select("nome").execute().data]
    setores = [s['nome'] for s in supabase.table("setores").select("nome").order("nome").execute().data]
    funcoes = [f['nome'] for f in supabase.table("funcoes").select("nome").order("nome").execute().data]

    with t1:
        with st.form("cad_f", clear_on_submit=True):
            nome, mat = st.text_input("Nome"), st.text_input("Matrícula")
            s_sel = st.selectbox("Setor", setores)
            f_sel = st.selectbox("Função", funcoes)
            adm = st.date_input("Admissão", format="DD/MM/YYYY")
            zap = st.text_input("WhatsApp")
            v_sel = st.selectbox("Vínculo", vinculos)
            if st.form_submit_button("Salvar"):
                supabase.table("oficiais").insert({"nome": nome, "matricula": mat, "setor": s_sel, "funcao": f_sel, "admissao": str(adm), "vinculo": v_sel, "whatsapp": zap}).execute()
                st.success("Salvo com sucesso!"); st.rerun()

    with t2:
        df = pd.DataFrame(supabase.table("oficiais").select("*").execute().data)
        if not df.empty:
            c1, c2 = st.columns(2)
            search = c1.text_input("Nome")
            f_set = c2.multiselect("Setor", df['setor'].unique())
            
            df_res = df.copy()
            if search: df_res = df_res[df_res['nome'].str.contains(search, case=False)]
            if f_set: df_res = df_res[df_res['setor'].isin(f_set)]
            
            df_res['admissao'] = df_res['admissao'].apply(format_br)
            st.dataframe(df_res, use_container_width=True)

# --- FICHA DE EPI ---
elif menu == "📄 Ficha de EPI":
    st.title("📄 Ficha Individual (Histórico Total)")
    df_f = pd.DataFrame(supabase.table("oficiais").select("*").execute().data)
    if not df_f.empty:
        sel = st.selectbox("Funcionário", df_f['nome'], key="sel_ficha")
        f = df_f[df_f['nome'] == sel].iloc[0]
        
        h_res = supabase.table("entregas").select("*, ep(nome, ca)").eq("id_func", int(f['id'])).order("data_entrega", desc=True).execute()
        if h_res.data:
            # Alerta de 20 dias
            last = datetime.strptime(h_res.data[0]['data_entrega'].split('T')[0], '%Y-%m-%d')
            dias = (datetime.now() - last).days
            if dias >= 20: st.warning(f"⚠️ Atenção: Sem entregas há {dias} dias. Gerar nova ficha!")

            h_df = pd.DataFrame([{"data_entrega": r['data_entrega'], "epi_nome": r['ep']['nome'], "ca": r['ep']['ca'], "quantidade": r['quantidade'], "token": r['token'], "status": r['status']} for r in h_res.data])
            df_tab = h_df.copy(); df_tab['data_entrega'] = df_tab['data_entrega'].apply(format_br)
            st.table(df_tab)
            st.download_button("📥 BAIXAR HISTÓRICO COMPLETO", create_pdf(f, h_df), f"Ficha_{f['nome']}.pdf", key="btn_pdf")

# --- CONSUMO SEMANAL ---
elif menu == "📈 Consumo Semanal":
    st.title("📈 Balanço Semanal por Setor")
    res_last = supabase.table("entregas").select("data_entrega").order("data_entrega", desc=True).limit(1).execute()
    if res_last.data:
        atraso = (datetime.now() - datetime.strptime(res_last.data[0]['data_entrega'].split('T')[0], '%Y-%m-%d')).days
        if atraso >= 7: st.error(f"🚨 ALERTA: Balanço atrasado há {atraso} dias!")
    st.info("Filtre o setor e gere o consolidado semanal para auditoria.")

# --- CONFIGURAÇÕES ---
elif menu == "⚙️ Configurações":
    st.title("⚙️ Painel do Administrador")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔗 Sistema", "📋 Vínculos", "🏢 Setores", "🛠️ Funções", "🔑 Senha/Texto"])
    
    with tab2:
        nv = st.text_input("Novo Vínculo", key="in_vinc")
        if st.button("Adicionar", key="btn_vinc"):
            supabase.table("vinculos").insert({"nome": nv}).execute(); st.rerun()
        st.data_editor(pd.DataFrame(supabase.table("vinculos").select("*").execute().data), key="edit_vinc", num_rows="dynamic")
    
    with tab3:
        ns = st.text_input("Novo Setor", key="in_set")
        if st.button("Adicionar", key="btn_set"):
            supabase.table("setores").insert({"nome": ns}).execute(); st.rerun()
        st.data_editor(pd.DataFrame(supabase.table("setores").select("*").execute().data), key="edit_set", num_rows="dynamic")
        
    with tab4:
        nf = st.text_input("Nova Função", key="in_fun")
        if st.button("Adicionar", key="btn_fun"):
            supabase.table("funcoes").insert({"nome": nf}).execute(); st.rerun()
        st.data_editor(pd.DataFrame(supabase.table("funcoes").select("*").execute().data), key="edit_fun", num_rows="dynamic")

    with tab5:
        st.write("#### Segurança e Conteúdo")
        nova_senha = st.text_input("Nova Senha", type="password", key="new_pw")
        if st.button("Mudar Senha"):
            supabase.table("configuracoes").upsert({"chave": "app_password", "valor": nova_senha}).execute(); st.success("Senha alterada!")
        
        texto_ficha = st.text_area("Termos da Ficha", get_config("ficha_descricao"), key="txt_ficha")
        if st.button("Salvar Texto Legal"):
            supabase.table("configuracoes").upsert({"chave": "ficha_descricao", "valor": texto_ficha}).execute(); st.success("Texto salvo!")

# --- ENTREGAR EPI ---
elif menu == "🚀 Entregar EPI":
    st.title("🚀 Registro de Entrega")
    res_f = supabase.table("oficiais").select("*").execute()
    res_e = supabase.table("ep").select("*").execute()
    if not res_f.data or not res_e.data:
        st.warning("Cadastre Funcionários e EPIs primeiro.")
    else:
        df_f = pd.DataFrame(res_f.data)
        colab = st.selectbox("Selecione o Colaborador", df_f['matricula'] + " - " + df_f['nome'])
        sel_items = st.multiselect("Selecione os EPIs", options=[e['nome'] for e in res_e.data])
        if st.button("Registrar Entrega"):
            st.success("Entrega registrada! Envie o token pelo Dashboard.")

# --- CATÁLOGO ---
elif menu == "📦 Catálogo":
    st.title("📦 Catálogo de EPIs")
    with st.form("cad_epi"):
        n_epi, ca_epi, val_epi = st.text_input("EPI"), st.text_input("C.A."), st.date_input("Validade")
        if st.form_submit_button("Salvar"):
            supabase.table("ep").upsert({"nome": n_epi, "ca": ca_epi, "validade": str(val_epi)}, on_conflict="nome").execute()
            st.success("Salvo!"); st.rerun()

# --- CONFIRMAÇÃO ---
if "confirmar" in st.query_params:
    tk = st.query_params["confirmar"]
    supabase.table("entregas").update({"status": "Confirmado ✅"}).eq("token", tk).execute()
    st.balloons(); st.success("🛡️ RECEBIMENTO CONFIRMADO!"); st.stop()
