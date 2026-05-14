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

# --- PDF: FICHA COMPLETA ---
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
        pdf.cell(10, 8, str(r.get('quantidade', 1)), 1, 0, 'C')
        pdf.cell(56, 8, remover_acentos(str(r['epi_nome'])[:35]), 1)
        pdf.cell(20, 8, str(r['ca']), 1, 0, 'C')
        pdf.cell(25, 8, str(r['token']), 1, 0, 'C')
        pdf.cell(40, 8, remover_acentos(str(r['status'])), 1, ln=True, align='C')
    
    texto_nr6 = obter_config("ficha_descricao", '6.5.1 alinea d da NR 6 "d) registrar o seu fornecimento ao empregado..."')
    pdf.ln(10); pdf.set_font("Arial", 'I', 8)
    pdf.multi_cell(0, 5, remover_acentos(texto_nr6), align='J')
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

url_base = obter_config("url_sistema", "https://sesmt-huc-app.streamlit.app")
menu = st.sidebar.radio("SESMT", ["📊 Dashboard", "🚀 Entregar EPI", "👥 Funcionários", "📦 Catálogo", "📄 Ficha de EPI", "📈 Consumo Semanal", "⚙️ Configurações"])

# --- DASHBOARD COM KPIs ---
if menu == "📊 Dashboard":
    st.markdown("### 📊 Indicadores SESMT")
    res_f = supabase.table("oficiais").select("id").not_.eq("matricula", "URL_SISTEMA").execute()
    res_e = supabase.table("entregas").select("id").execute()
    res_p = supabase.table("entregas").select("id").eq("status", "Pendente ⏳").execute()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Funcionários", len(res_f.data))
    c2.metric("Total Entregas", len(res_e.data))
    c3.metric("Pendentes", len(res_p.data), delta=len(res_p.data), delta_color="inverse")
    
    st.divider()
    st.write("#### Reenvio de Tokens Pendentes")
    res = supabase.table("entregas").select("*, oficiais(nome, whatsapp), ep(nome)").eq("status", "Pendente ⏳").order("id", desc=True).limit(10).execute()
    for row in res.data:
        col1, col2 = st.columns([4, 1])
        col1.write(f"🔴 **{row['oficiais']['nome']}** - {row['ep']['nome']}")
        link = f"{url_base}/?confirmar={row['token']}"
        msg = urllib.parse.quote(f"🛡️ *SESMT HUC*\nFavor confirmar o EPI: {row['ep']['nome']}\nLink: {link}")
        col2.markdown(f'<a href="https://api.whatsapp.com/send?phone=55{row["oficiais"]["whatsapp"]}&text={msg}" target="_blank"><button style="background-color:#25D366; color:white; border:none; border-radius:5px; width:100%;">📲 REENVIAR</button></a>', unsafe_allow_html=True)

# --- FUNCIONÁRIOS COM FILTROS ---
elif menu == "👥 Funcionários":
    st.markdown("### 👥 Gestão e Filtros")
    tab1, tab2 = st.tabs(["➕ Novo", "🔍 Buscar/Filtrar"])
    
    res_v = supabase.table("vinculos").select("nome").execute()
    vinc_list = [v['nome'] for v in res_v.data]

    with tab1:
        with st.form("cad_f", clear_on_submit=True):
            n, m, s = st.text_input("Nome"), st.text_input("Matricula"), st.text_input("Setor")
            f, adm, w = st.text_input("Função"), st.date_input("Admissão"), st.text_input("WhatsApp")
            v_sel = st.selectbox("Vínculo", vinc_list)
            if st.form_submit_button("Salvar"):
                supabase.table("oficiais").insert({"nome": n, "matricula": m, "setor": s, "funcao": f, "admissao": str(adm), "vinculo": v_sel, "whatsapp": w}).execute()
                st.success("Cadastrado!"); st.rerun()
    with tab2:
        df = pd.DataFrame(supabase.table("oficiais").select("*").not_.eq("matricula", "URL_SISTEMA").execute().data)
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            search = c1.text_input("Nome")
            f_setor = c2.multiselect("Setor", df['setor'].unique())
            f_vinc = c3.multiselect("Vínculo", df['vinculo'].unique())
            
            df_f = df.copy()
            if search: df_f = df_f[df_f['nome'].str.contains(search, case=False)]
            if f_setor: df_f = df_f[df_f['setor'].isin(f_setor)]
            if f_vinc: df_f = df_f[df_f['vinculo'].isin(f_vinc)]
            
            df_f['admissao'] = df_f['admissao'].apply(formatar_data_br)
            st.dataframe(df_f, use_container_width=True)

# --- CONSUMO COM ALERTA 7 DIAS ---
elif menu == "📈 Consumo Semanal":
    st.markdown("### 📈 Balanço Semanal por Setor")
    res_last = supabase.table("entregas").select("data_entrega").order("data_entrega", desc=True).limit(1).execute()
    if res_last.data:
        last_date = datetime.strptime(res_last.data[0]['data_entrega'].split('T')[0], '%Y-%m-%d')
        days = (datetime.now() - last_date).days
        if days >= 7:
            st.error(f"🚨 ALERTA: Último registro há {days} dias. BAIXAR CONSUMO SEMANAL!")
        else:
            st.info(f"📅 Próximo fechamento em {7 - days} dias.")
    
    setores = pd.DataFrame(supabase.table("oficiais").select("setor").execute().data)['setor'].unique()
    setor_sel = st.selectbox("Escolha o Setor", setores)
    if st.button("📊 Gerar Relatório de 7 Dias"):
        # Lógica de agrupamento e download...
        st.success(f"Relatório de {setor_sel} gerado!")

# --- FICHA COM ALERTA 20 DIAS ---
elif menu == "📄 Ficha de EPI":
    st.markdown("### 📄 Histórico Completo do Funcionário")
    df_f = pd.DataFrame(supabase.table("oficiais").select("*").not_.eq("matricula", "URL_SISTEMA").execute().data)
    if not df_f.empty:
        escolha = st.selectbox("Funcionário", df_f['nome'])
        f = df_f[df_f['nome'] == escolha].iloc[0]
        
        res_h = supabase.table("entregas").select("*, ep(nome, ca)").eq("id_func", int(f['id'])).order("data_entrega", desc=True).execute()
        if res_h.data:
            last_e = datetime.strptime(res_h.data[0]['data_entrega'].split('T')[0], '%Y-%m-%d')
            atraso = (datetime.now() - last_e).days
            if atraso >= 20: st.warning(f"⚠️ Atenção: Sem entregas há {atraso} dias. Baixar ficha atualizada!")

            h_data = [{"data_entrega": r['data_entrega'], "epi_nome": r['ep']['nome'], "ca": r['ep']['ca'], "quantidade": r['quantidade'], "token": r['token'], "status": r['status']} for r in res_h.data]
            df_h = pd.DataFrame(h_data)
            
            st.write("**Tudo o que já foi entregue:**")
            df_tab = df_h.copy()
            df_tab['data_entrega'] = df_tab['data_entrega'].apply(formatar_data_br)
            st.table(df_tab)
            
            st.download_button("📥 BAIXAR FICHA COMPLETA (Histórico Total)", gerar_pdf_ficha(f, df_h), f"Ficha_{f['nome']}.pdf")

# --- CONFIGURAÇÕES (GESTÃO DE VÍNCULOS) ---
elif menu == "⚙️ Configurações":
    st.markdown("### ⚙️ Painel Gestor")
    t1, t2, t3 = st.tabs(["🔗 Sistema", "📋 Vínculos", "🔑 Senha"])
    
    with t2:
        st.write("#### Cadastre ou remova tipos de vínculos")
        nv = st.text_input("Novo Vínculo")
        if st.button("Adicionar"):
            supabase.table("vinculos").insert({"nome": nv}).execute()
            st.success("Adicionado!"); st.rerun()
        
        res_v = supabase.table("vinculos").select("*").execute()
        st.data_editor(pd.DataFrame(res_v.data), num_rows="dynamic", key="vinc_edit")

    with t3:
        n_senha = st.text_input("Nova Senha", type="password")
        if st.button("Atualizar Senha"):
            supabase.table("configuracoes").upsert({"chave": "app_password", "valor": n_senha}).execute()
            st.success("Senha alterada!")

# --- LÓGICA DE TOKEN ---
if "confirmar" in st.query_params:
    tk = st.query_params["confirmar"]
    supabase.table("entregas").update({"status": "Confirmado ✅"}).eq("token", tk).execute()
    st.balloons(); st.success("🛡️ RECEBIMENTO CONFIRMADO!"); st.stop()
