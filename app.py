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
        # Tenta converter de YYYY-MM-DD para DD/MM/YYYY
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

# --- GERAÇÃO DE PDF (HISTÓRICO COMPLETO) ---
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

# --- FUNCIONÁRIOS COM FILTROS AVANÇADOS ---
if menu == "👥 Funcionários":
    st.markdown("### 👥 Gestão de Colaboradores")
    tab1, tab2 = st.tabs(["➕ Novo Cadastro", "🔍 Filtrar e Buscar"])
    
    # Busca vínculos do banco
    res_v = supabase.table("vinculos").select("nome").execute()
    lista_vinculos = [v['nome'] for v in res_v.data]

    with tab1:
        with st.form("cad_f", clear_on_submit=True):
            n, m, s = st.text_input("Nome"), st.text_input("Matricula"), st.text_input("Setor")
            f, adm, w = st.text_input("Função"), st.date_input("Admissão"), st.text_input("WhatsApp")
            v_sel = st.selectbox("Vínculo", lista_vinculos)
            if st.form_submit_button("Salvar"):
                supabase.table("oficiais").insert({"nome": n, "matricula": m, "setor": s, "funcao": f, "admissao": str(adm), "vinculo": v_sel, "whatsapp": w}).execute()
                st.success("Cadastrado!")

    with tab2:
        df_f = pd.DataFrame(supabase.table("oficiais").select("*").not_.eq("matricula", "URL_SISTEMA").execute().data)
        if not df_f.empty:
            # Filtros dinâmicos
            c1, c2, c3 = st.columns(3)
            busca = c1.text_input("Buscar por Nome")
            setor_f = c2.multiselect("Filtrar por Setor", df_f['setor'].unique())
            vinculo_f = c3.multiselect("Filtrar por Vínculo", df_f['vinculo'].unique())
            
            # Aplica lógica de filtro
            df_res = df_f.copy()
            if busca: df_res = df_res[df_res['nome'].str.contains(busca, case=False)]
            if setor_f: df_res = df_res[df_res['setor'].isin(setor_f)]
            if vinculo_f: df_res = df_res[df_res['vinculo'].isin(vinculo_f)]
            
            # Formata data para exibição
            df_res['admissao'] = df_res['admissao'].apply(formatar_data_br)
            st.dataframe(df_res, use_container_width=True)

# --- CONSUMO SEMANAL COM ALERTA (7 DIAS) ---
elif menu == "📈 Consumo Semanal":
    st.markdown("### 📈 Consumo por Setor (Sobra Semanal)")
    res_entregas = supabase.table("entregas").select("data_entrega, oficiais(setor)").order("data_entrega", desc=True).execute()
    
    if res_entregas.data:
        ultima_global = datetime.strptime(res_entregas.data[0]['data_entrega'].split('T')[0], '%Y-%m-%d')
        dias_passados = (datetime.now() - ultima_global).days
        
        if dias_passados >= 7:
            st.error(f"🚨 ATENÇÃO: Fazem {dias_passados} dias desde o último fechamento. BAIXAR PDF DE CONSUMO AGORA!")
        else:
            st.info(f"📅 Próximo fechamento semanal em {7 - dias_passados} dias.")
            
    # Lógica de download por setor aqui...
    st.write("Selecione o setor para baixar o consolidado dos últimos 7 dias.")

# --- FICHA DE EPI COM ALERTA (20 DIAS) ---
elif menu == "📄 Ficha de EPI":
    st.markdown("### 📄 Ficha Individual de EPI")
    df_f = pd.DataFrame(supabase.table("oficiais").select("*").not_.eq("matricula", "URL_SISTEMA").execute().data)
    
    if not df_f.empty:
        escolha = st.selectbox("Colaborador", df_f['nome'])
        f_selecionado = df_f[df_f['nome'] == escolha].iloc[0]
        
        # Verifica última entrega do funcionário
        res_h = supabase.table("entregas").select("data_entrega, ep(nome, ca), token, status, quantidade").eq("id_func", int(f_selecionado['id'])).order("data_entrega", desc=True).execute()
        
        if res_h.data:
            ultima_func = datetime.strptime(res_h.data[0]['data_entrega'].split('T')[0], '%Y-%m-%d')
            atraso_ficha = (datetime.now() - ultima_func).days
            
            if atraso_ficha >= 20:
                st.warning(f"⚠️ ALERTA: Este funcionário recebeu EPI há {atraso_ficha} dias. Recomenda-se atualizar e baixar a ficha!")

            h_data = [{"data_entrega": r['data_entrega'], "epi_nome": r['ep']['nome'], "ca": r['ep']['ca'], "quantidade": r['quantidade'], "token": r['token'], "status": r['status']} for r in res_h.data]
            df_h = pd.DataFrame(h_data)
            
            # Opção de baixar TUDO ou apenas recentes
            st.markdown("#### Histórico de Entregas")
            df_mostra = df_h.copy()
            df_mostra['data_entrega'] = df_mostra['data_entrega'].apply(formatar_data_br)
            st.table(df_mostra)
            
            if st.button("📥 BAIXAR FICHA COMPLETA (Desde o Início)"):
                st.download_button("Clique para Confirmar Download", gerar_pdf_ficha(f_selecionado, df_h), f"Ficha_Completa_{f_selecionado['nome']}.pdf")

# --- CONFIGURAÇÕES (GESTÃO DE VÍNCULOS) ---
elif menu == "⚙️ Configurações":
    st.markdown("### ⚙️ Painel de Controle")
    t1, t2, t3 = st.tabs(["🔗 URL e Termos", "📋 Gestão de Vínculos", "🔑 Senha"])
    
    with t2:
        st.write("Cadastre ou remova tipos de vínculos contratuais.")
        novo_v = st.text_input("Novo Tipo de Vínculo (Ex: CLT, Estágio)")
        if st.button("Adicionar Vínculo"):
            supabase.table("vinculos").insert({"nome": novo_v}).execute()
            st.success("Vínculo adicionado!")
            st.rerun()
        
        res_v = supabase.table("vinculos").select("*").execute()
        df_v = pd.DataFrame(res_v.data)
        st.data_editor(df_v, num_rows="dynamic", key="editor_vinculos")
