"""
🛡️ SESMT HUC - Sistema Digital de Gestão de EPI v3.8
Hospital Universitário do Ceará - Padrão Oficial
"""

import logging
import time
import urllib.parse
import requests
from datetime import datetime
from io import BytesIO
import streamlit as st
import pandas as pd
from supabase import create_client, Client

# ============================================================================
# CONFIGURAÇÕES E CONEXÃO
# ============================================================================
logging.basicConfig(level=logging.INFO)
st.set_page_config(page_title="SESMT HUC - Digital", layout="wide", page_icon="🛡️")

SUPABASE_URL = "https://aatkjhtrafuepwzzlrbm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFhdGtqaHRyYWZ1ZXB3enpscmJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg2Mjg5MTYsImV4cCI6MjA5NDIwNDkxNn0.65izu7Zhc3kUZrVIRXGvVQ5o-Lhk-7PCK9CMg4zIwuk"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except:
    st.error("Erro na conexão com o banco de dados.")
    st.stop()

# Dados Institucionais (Agora no Topo)
HOSPITAL_NAME = "HOSPITAL UNIVERSITÁRIO DO CEARÁ"
HOSPITAL_ISGH = "ISGH - INSTITUTO DE SAÚDE E GESTÃO HOSPITALAR"
CNPJ_ENDERECO = "CNPJ: 05.268.526/0024-67 | AV DOUTOR SILAS MUNGUBA, 1700-ITAPERI | FORTALEZA/CE"
GOVERNO_SUB = "GOVERNO DO ESTADO DO CEARÁ"

STATUS_ENTREGA = {"PENDENTE": "Pendente ⏳", "CONFIRMADO": "Confirmado ✅"}

# ============================================================================
# UTILITÁRIOS
# ============================================================================

def clean_str(text):
    if not text: return ""
    text_str = str(text).replace('✅', '!').replace('⏳', '...')
    import unicodedata
    nfd = unicodedata.normalize('NFD', text_str)
    return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn').encode('latin-1', 'replace').decode('latin-1')

def format_br(date_str):
    if not date_str: return "N/A"
    try:
        clean_date = str(date_str).replace('Z', '').split('+')[0]
        dt = datetime.fromisoformat(clean_date)
        return dt.strftime('%d/%m/%Y %H:%M')
    except: return str(date_str)

@st.cache_data(ttl=2)
def load_data(table, order=None):
    try:
        q = supabase.table(table).select("*")
        if order: q = q.order(order)
        res = q.execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except: return pd.DataFrame()

def get_cfg(k, d=""):
    try:
        res = supabase.table("configuracoes").select("valor").eq("chave", k).execute()
        return res.data[0]['valor'] if res.data else d
    except: return d

def abrir_whatsapp(numero, mensagem):
    msg_url = urllib.parse.quote(mensagem)
    link = f"https://api.whatsapp.com/send?phone=55{numero}&text={msg_url}"
    st.markdown(f'<a href="{link}" target="_blank"><button style="background-color:#25D366;color:white;border:none;padding:10px;border-radius:5px;width:100%;cursor:pointer;font-weight:bold;">🚀 ENVIAR PARA O WHATSAPP AGORA</button></a>', unsafe_allow_html=True)

# ============================================================================
# GERADOR DE PDF (COM CNPJ NO TOPO)
# ============================================================================

def generate_pdf_ficha(func, hist_df):
    from fpdf import FPDF
    try:
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        
        # --- CABEÇALHO (CNPJ NO TOPO) ---
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 8, clean_str(HOSPITAL_NAME), border=0, ln=1, align='C')
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(0, 5, clean_str(HOSPITAL_ISGH), border=0, ln=1, align='C')
        pdf.set_font("Arial", '', 8)
        pdf.cell(0, 5, clean_str(CNPJ_ENDERECO), border=0, ln=1, align='C')
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(0, 5, clean_str(GOVERNO_SUB), border=0, ln=1, align='C')
        pdf.ln(5)
        
        # Título da Ficha
        pdf.set_fill_color(40, 40, 40); pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, clean_str("FICHA INDIVIDUAL DE CONTROLE DE EPI"), border=0, ln=1, fill=True, align='C')
        pdf.ln(4)
        
        # Dados do Colaborador (Nomes Corrigidos)
        pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 10)
        pdf.cell(140, 8, clean_str(f"COLABORADOR: {func['nome']}"), border=1)
        pdf.cell(0, 8, clean_str(f"MATRICULA: {func['matricula']}"), border=1, ln=1)
        pdf.cell(140, 8, clean_str(f"SETOR: {func['setor']}"), border=1)
        pdf.cell(0, 8, clean_str(f"FUNCAO: {func.get('funcao', 'N/A')}"), border=1, ln=1)
        pdf.ln(5)
        
        # Tabela
        pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", 'B', 8)
        pdf.cell(35, 8, clean_str("DATA/HORA"), border=1, align='C', fill=True)
        pdf.cell(15, 8, clean_str("QTD"), border=1, align='C', fill=True)
        pdf.cell(90, 8, clean_str("DESCRIÇÃO DO EPI"), border=1, align='C', fill=True)
        pdf.cell(30, 8, clean_str("C.A."), border=1, align='C', fill=True)
        pdf.cell(30, 8, clean_str("TOKEN"), border=1, align='C', fill=True)
        pdf.cell(0, 8, clean_str("STATUS"), border=1, ln=1, align='C', fill=True)
        
        pdf.set_font("Arial", '', 8)
        for _, row in hist_df.iterrows():
            pdf.cell(35, 8, str(row['Data/Hora']), border=1, align='C')
            pdf.cell(15, 8, str(row['Qtd']), border=1, align='C')
            pdf.cell(90, 8, clean_str(row['EPI']), border=1)
            pdf.cell(30, 8, str(row['CA']), border=1, align='C')
            pdf.cell(30, 8, str(row['Token']), border=1, align='C')
            pdf.cell(0, 8, clean_str(row['Status']), border=1, ln=1, align='C')
            
        pdf.ln(10); pdf.set_font("Arial", 'I', 8)
        pdf.multi_cell(0, 4, clean_str(get_cfg("ficha_descricao", "Declaro que recebi os EPIs listados e fui orientado quanto ao uso e conservacao.")))
        
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}")
        return None

# ============================================================================
# INTERFACE STREAMLIT
# ============================================================================

if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.title("🛡️ SESMT HUC")
    pw = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if pw == get_cfg("app_password", "1234"): st.session_state.logado = True; st.rerun()
    st.stop()

menu = st.sidebar.radio("MENU SESMT", ["📊 Painel", "🚀 Registrar Entrega", "👥 Colaboradores", "🎖️ Funções", "📦 Catálogo EPI", "📄 Ficha Individual"])

# --- FUNÇÕES ---
if menu == "🎖️ Funções":
    st.title("🎖️ Gestão de Funções e Cargos")
    with st.form("add_func"):
        nova_f = st.text_input("Nome da Função (Ex: TÉCNICO DE ENFERMAGEM)").upper()
        if st.form_submit_button("Salvar Função"):
            supabase.table("funcoes").insert({"nome": nova_f}).execute()
            st.success("Função cadastrada!"); st.cache_data.clear()
    
    st.write("### Funções Cadastradas")
    st.dataframe(load_data("funcoes", "nome"), use_container_width=True)

# --- COLABORADORES ---
elif menu == "👥 Colaboradores":
    st.title("👥 Cadastro de Colaborador")
    df_funcoes = load_data("funcoes", "nome")
    
    if df_funcoes.empty:
        st.warning("⚠️ Você precisa cadastrar as **Funções** primeiro no menu ao lado!")
    else:
        with st.form("cad_col"):
            n, m = st.text_input("Nome Completo").upper(), st.text_input("Matrícula")
            s = st.selectbox("Setor", ["CME", "CENTRO CIRÚRGICO", "UTI", "MANUTENÇÃO", "SESMT"])
            f = st.selectbox("Função", df_funcoes['nome'].tolist())
            z = st.text_input("WhatsApp (Ex: 85912345678)")
            if st.form_submit_button("Salvar Colaborador"):
                supabase.table("oficiais").insert({"nome":n, "matricula":m, "setor":s, "funcao":f, "whatsapp":z}).execute()
                st.success("Colaborador salvo com sucesso!"); st.cache_data.clear()
        
        st.write("### Lista de Colaboradores")
        st.dataframe(load_data("oficiais", "nome"), use_container_width=True)

# --- REGISTRAR ENTREGA ---
elif menu == "🚀 Registrar Entrega":
    st.title("🚀 Registrar Entrega de EPI")
    df_f, df_ep = load_data("oficiais", "nome"), load_data("ep", "nome")
    
    if df_f.empty or df_ep.empty:
        st.warning("Cadastre Colaboradores e EPIs primeiro.")
    else:
        with st.form("reg_ent"):
            colab = st.selectbox("Colaborador", df_f['matricula'] + " - " + df_f['nome'])
            epi = st.selectbox("EPI", df_ep['nome'])
            qtd = st.number_input("Quantidade", 1)
            if st.form_submit_button("Finalizar Entrega"):
                row_f = df_f[df_f['matricula'] + " - " + df_f['nome'] == colab].iloc[0]
                row_e = df_ep[df_ep['nome'] == epi].iloc[0]
                tk = str(int(time.time()))[-6:]
                
                supabase.table("entregas").insert({
                    "id_func": int(row_f['id']), "id_epi": int(row_e['id']),
                    "token": tk, "quantidade": qtd, "status": STATUS_ENTREGA["PENDENTE"]
                }).execute()
                
                st.success(f"✅ Entrega Registrada! Token: {tk}")
                link = f"{get_cfg('url_sistema')}/?confirmar={tk}"
                msg = f"🛡️ *SESMT HUC*\nOlá {row_f['nome']},\nConfirme o recebimento do seu EPI ({epi}) clicando no link: {link}"
                abrir_whatsapp(row_f['whatsapp'], msg)

# --- FICHA INDIVIDUAL ---
elif menu == "📄 Ficha Individual":
    st.title("📄 Ficha Individual")
    df_f = load_data("oficiais", "nome")
    if not df_f.empty:
        sel = st.selectbox("Selecione o Colaborador", df_f['nome'])
        f_info = df_f[df_f['nome'] == sel].iloc[0]
        
        # Histórico
        res = supabase.table("entregas").select("*, ep(*)").eq("id_func", int(f_info['id'])).execute().data
        if res:
            rows = [{"Data/Hora": format_br(h['data_entrega']), "Qtd": h['quantidade'], "EPI": h['ep']['nome'], "CA": h['ep']['ca'], "Token": h['token'], "Status": h['status']} for h in res]
            df_h = pd.DataFrame(rows)
            st.dataframe(df_h, use_container_width=True)
            
            pdf = generate_pdf_ficha(dict(f_info), df_h)
            if pdf: st.download_button("📥 BAIXAR FICHA (PDF)", data=pdf, file_name=f"Ficha_{sel}.pdf", mime="application/pdf")
