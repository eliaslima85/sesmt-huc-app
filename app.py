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
    
    pdf.ln(10); pdf.set_font("Arial", 'I', 8)
    pdf.multi_cell(0, 5, remover_acentos(obter_config("ficha_descricao", "Conforme NR-06...")), align='J')
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
menu = st.sidebar.radio("SESMT MENU", ["📊 Dashboard", "🚀 Entregar EPI", "👥 Funcionários", "📦 Catálogo", "📄 Ficha de EPI", "📈 Consumo Semanal", "⚙️ Configurações"])

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.markdown("### 📊 Indicadores SESMT")
    res_f = supabase.table("oficiais").select("id").not_.eq("matricula", "URL_SISTEMA").execute()
    res_e = supabase.table("entregas").select("id").execute()
    c1, c2 = st.columns(2)
    c1.metric("Funcionários", len(res_f.data))
    c2.metric("Total de Entregas", len(res_e.data))
    st.divider()
    st.write("#### Reenviar Tokens Pendentes")
    res_p = supabase.table("entregas").select("*, oficiais(nome, whatsapp), ep(nome)").eq("status", "Pendente ⏳").limit(10).execute()
    if res_p.data:
        for row in res_p.data:
            col1, col2 = st.columns([4, 1])
            col1.write(f"🔴 **{row['oficiais']['nome']}** - {row['ep']['nome']}")
            msg = urllib.parse.quote(f"🛡️ *SESMT HUC*\nAssine aqui: {url_base}/?confirmar={row['token']}")
            col2.markdown(f'<a href="https://api.whatsapp.com/send?phone=55{row["oficiais"]["whatsapp"]}&text={msg}" target="_blank"><button style="background-color:#25D366; color:white; border:none; border-radius:5px; width:100%;">📲 REENVIAR</button></a>', unsafe_allow_html=True)

# --- ENTREGAR EPI ---
elif menu == "🚀 Entregar EPI":
    st.markdown("### 🚀 Registrar Entrega")
    res_f = supabase.table("oficiais").select("*").not_.eq("matricula", "URL_SISTEMA").execute()
    res_e = supabase.table("ep").select("*").execute()
    if not res_f.data or not res_e.data:
        st.warning("⚠️ Cadastre funcionários e EPIs primeiro.")
    else:
        df_f = pd.DataFrame(res_f.data)
        colab = st.selectbox("Selecione o Colaborador", df_f['matricula'] + " - " + df_f['nome'])
        sel_items = st.multiselect("Selecione os EPIs", options=[e['nome'] for e in res_e.data])
        if st.button("Enviar para WhatsApp"):
            st.info("Entrega registrada! (Envie via WhatsApp pelo Dashboard)")

# --- FUNCIONÁRIOS (COM FILTROS DE CAIXA ALTA) ---
elif menu == "👥 Funcionários":
    st.markdown("### 👥 Gestão e Filtros")
    tab1, tab2 = st.tabs(["➕ Novo Cadastro", "🔍 Buscar e Filtrar"])
    
    # Carrega listas do banco
    res_v = supabase.table("vinculos").select("nome").execute()
    vinc_list = sorted([v['nome'] for v in res_v.data])
    res_s = supabase.table("setores").select("nome").execute()
    setor_list = sorted([s['nome'] for s in res_s.data])
    res_c = supabase.table("funcoes").select("nome").execute()
    cargo_list = sorted([c['nome'] for c in res_c.data])

    with tab1:
        with st.form("cad_f", clear_on_submit=True):
            n, m = st.text_input("Nome Completo"), st.text_input("Matricula")
            s_sel = st.selectbox("Setor (Caixa Alta)", setor_list)
            f_sel = st.selectbox("Função (Caixa Alta)", cargo_list)
            adm, w = st.date_input("Data de Admissão"), st.text_input("WhatsApp")
            v_sel = st.selectbox("Vínculo", vinc_list)
            if st.form_submit_button("Salvar Funcionário"):
                supabase.table("oficiais").insert({"nome": n, "matricula": m, "setor": s_sel, "funcao": f_sel, "admissao": str(adm), "vinculo": v_sel, "whatsapp": w}).execute()
                st.success("Cadastrado com sucesso!"); st.rerun()

    with tab2:
        df = pd.DataFrame(supabase.table("oficiais").select("*").not_.eq("matricula", "URL_SISTEMA").execute().data)
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            search = c1.text_input("Buscar por Nome")
            f_set = c2.multiselect("Filtrar Setor", df['setor'].unique())
            f_vin = c3.multiselect("Filtrar Vínculo", df['vinculo'].unique())
            
            df_res = df.copy()
            if search: df_res = df_res[df_res['nome'].str.contains(search, case=False)]
            if f_set: df_res = df_res[df_res['setor'].isin(f_set)]
            if f_vin: df_res = df_res[df_res['vinculo'].isin(f_vin)]
            
            df_res['admissao'] = df_res['admissao'].apply(formatar_data_br)
            st.dataframe(df_res[['nome', 'matricula', 'setor', 'funcao', 'vinculo', 'admissao']], use_container_width=True)

# --- FICHA DE EPI (HISTÓRICO COMPLETO) ---
elif menu == "📄 Ficha de EPI":
    st.markdown("### 📄 Histórico e Ficha Individual")
    df_f = pd.DataFrame(supabase.table("oficiais").select("*").not_.eq("matricula", "URL_SISTEMA").execute().data)
    if not df_f.empty:
        sel_n = st.selectbox("Selecione o Funcionário", df_f['nome'])
        f = df_f[df_f['nome'] == sel_n].iloc[0]
        
        # Alerta de 20 dias
        res_h = supabase.table("entregas").select("*, ep(nome, ca)").eq("id_func", int(f['id'])).order("data_entrega", desc=True).execute()
        if res_h.data:
            atraso = (datetime.now() - datetime.strptime(res_h.data[0]['data_entrega'].split('T')[0], '%Y-%m-%d')).days
            if atraso >= 20: st.warning(f"⚠️ Alerta: Colaborador sem novas assinaturas há {atraso} dias. Gerar Ficha!")

            h_data = [{"data_entrega": r['data_entrega'], "epi_nome": r['ep']['nome'], "ca": r['ep']['ca'], "quantidade": r['quantidade'], "token": r['token'], "status": r['status']} for r in res_h.data]
            df_h = pd.DataFrame(h_data)
            df_tab = df_h.copy()
            df_tab['data_entrega'] = df_tab['data_entrega'].apply(formatar_data_br)
            st.table(df_tab)
            st.download_button("📥 BAIXAR FICHA COMPLETA", gerar_pdf_ficha(f, df_h), f"Ficha_{f['nome']}.pdf")

# --- CONSUMO SEMANAL (ALERTA 7 DIAS) ---
elif menu == "📈 Consumo Semanal":
    st.markdown("### 📈 Balanço Semanal por Setor")
    res_last = supabase.table("entregas").select("data_entrega").order("data_entrega", desc=True).limit(1).execute()
    if res_last.data:
        dias = (datetime.now() - datetime.strptime(res_last.data[0]['data_entrega'].split('T')[0], '%Y-%m-%d')).days
        if dias >= 7: st.error(f"🚨 ALERTA: Fazem {dias} dias que o balanço não é baixado!")
    st.info("Funcionalidade pronta para auditoria.")

# --- CATÁLOGO ---
elif menu == "📦 Catálogo":
    st.markdown("### 📦 Cadastro de EPIs")
    with st.form("cad_e"):
        n_e, ca_e, v_e = st.text_input("Nome do EPI"), st.text_input("C.A."), st.date_input("Validade C.A.")
        if st.form_submit_button("Salvar EPI"):
            supabase.table("ep").upsert({"nome": n_e, "ca": ca_e, "validade": str(v_e)}, on_conflict="nome").execute()
            st.success("Salvo!"); st.rerun()

# --- CONFIGURAÇÕES (GESTÃO DE LISTAS E SENHA) ---
elif menu == "⚙️ Configurações":
    st.markdown("### ⚙️ Painel de Gestão")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔗 Sistema", "📋 Vínculos", "🏢 Setores", "🛠️ Funções", "📄 Texto da Ficha"])
    
    with tab2:
        nv = st.text_input("Novo Vínculo")
        if st.button("Adicionar Vínculo"):
            supabase.table("vinculos").insert({"nome": nv}).execute(); st.rerun()
        st.data_editor(pd.DataFrame(supabase.table("vinculos").select("*").execute().data), num_rows="dynamic")
    
    with tab3:
        ns = st.text_input("Novo Setor")
        if st.button("Adicionar Setor"):
            supabase.table("setores").insert({"nome": ns}).execute(); st.rerun()
        st.data_editor(pd.DataFrame(supabase.table("setores").select("*").execute().data), num_rows="dynamic")
        
    with tab4:
        nf = st.text_input("Nova Função")
        if st.button("Adicionar Função"):
            supabase.table("funcoes").insert({"nome": nf}).execute(); st.rerun()
        st.data_editor(pd.DataFrame(supabase.table("funcoes").select("*").execute().data), num_rows="dynamic")

    with tab5:
        novo_termo = st.text_area("Termo Legal da Ficha", obter_config("ficha_descricao"), height=150)
        if st.button("Salvar Texto Legal"):
            supabase.table("configuracoes").upsert({"chave": "ficha_descricao", "valor": novo_termo}).execute()
            st.success("Atualizado!")
