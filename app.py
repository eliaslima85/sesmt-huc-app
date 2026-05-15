"""
🛡️ SESMT HUC - Sistema Digital de Gestão de EPI v3.9
Hospital Universitário do Ceará - Padrão Oficial ISGH
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

# Dados Institucionais para o Topo do PDF
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

def format_br(date_str, include_time=False):
    if not date_str: return "N/A"
    try:
        clean_date = str(date_str).replace('Z', '').split('+')[0]
        dt = datetime.fromisoformat(clean_date)
        return dt.strftime('%d/%m/%Y %H:%M') if include_time else dt.strftime('%d/%m/%Y')
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
# GERADOR DE PDF (PADRÃO HUC)
# ============================================================================

def generate_pdf_ficha(func, hist_df):
    from fpdf import FPDF
    try:
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        
        # CABEÇALHO (CNPJ E ENDEREÇO NO TOPO)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 8, clean_str(HOSPITAL_NAME), border=0, ln=1, align='C')
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(0, 5, clean_str(HOSPITAL_ISGH), border=0, ln=1, align='C')
        pdf.set_font("Arial", '', 8)
        pdf.cell(0, 5, clean_str(CNPJ_ENDERECO), border=0, ln=1, align='C')
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(0, 5, clean_str(GOVERNO_SUB), border=0, ln=1, align='C')
        pdf.ln(5)
        
        # Título Black Bar
        pdf.set_fill_color(40, 40, 40); pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, clean_str("FICHA INDIVIDUAL DE CONTROLE DE EPI"), border=0, ln=1, fill=True, align='C')
        pdf.ln(4)
        
        # Dados do Colaborador
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
        termo = get_cfg("ficha_descricao", "Declaro que recebi os EPIs listados e fui orientado quanto ao uso.")
        pdf.multi_cell(0, 4, clean_str(termo))
        
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        st.error(f"Erro PDF: {e}")
        return None

# ============================================================================
# LOGIN E NAVEGAÇÃO
# ============================================================================

if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.title("🛡️ SESMT HUC")
    pw = st.text_input("Acesso SESMT", type="password")
    if st.button("Entrar"):
        if pw == get_cfg("app_password", "1234"): st.session_state.logado = True; st.rerun()
    st.stop()

menu = st.sidebar.radio("MENU", ["📊 Painel", "🚀 Registrar Entrega", "👥 Colaboradores", "🎖️ Funções", "📦 Catálogo EPI", "📄 Ficha Individual"])
if st.sidebar.button("Sair"): st.session_state.logado = False; st.rerun()

# ----------------------------------------------------------------------------
# 1. PAINEL (DASHBOARD)
# ----------------------------------------------------------------------------
if menu == "📊 Painel":
    st.title("📊 Painel SESMT")
    df_f, df_e = load_data("oficiais"), load_data("entregas")
    c1, c2 = st.columns(2)
    c1.metric("Colaboradores", len(df_f))
    c2.metric("Entregas Realizadas", len(df_e))
    st.divider()
    st.subheader("📲 Pendências de Assinatura")
    if not df_e.empty:
        pend = df_e[df_e['status'].str.contains("Pendente", na=False)]
        for _, p in pend.iterrows():
            f_res = supabase.table("oficiais").select("nome, whatsapp").eq("id", p['id_func']).execute()
            if f_res.data:
                f = f_res.data[0]
                col1, col2 = st.columns([3, 1])
                col1.write(f"🔴 **{f['nome']}** | Token: {p['token']}")
                link = f"{get_cfg('url_sistema')}/?confirmar={p['token']}"
                msg = f"🛡️ *SESMT HUC*\nOlá {f['nome']},\nAssine seu EPI pelo link: {link}"
                with col2: abrir_whatsapp(f['whatsapp'], msg)

# ----------------------------------------------------------------------------
# 2. REGISTRAR ENTREGA
# ----------------------------------------------------------------------------
elif menu == "🚀 Registrar Entrega":
    st.title("🚀 Registrar Entrega")
    df_f, df_ep = load_data("oficiais", "nome"), load_data("ep", "nome")
    if df_f.empty or df_ep.empty: st.warning("Cadastre Colaboradores e EPIs primeiro.")
    else:
        with st.form("ent"):
            f = st.selectbox("Colaborador", df_f['matricula'] + " - " + df_f['nome'])
            e = st.selectbox("EPI", df_ep['nome'])
            q = st.number_input("Qtd", 1)
            if st.form_submit_button("Gerar Registro"):
                rf, re = df_f[df_f['matricula'] + " - " + df_f['nome'] == f].iloc[0], df_ep[df_ep['nome'] == e].iloc[0]
                tk = str(int(time.time()))[-6:]
                supabase.table("entregas").insert({"id_func":int(rf['id']), "id_epi":int(re['id']), "token":tk, "quantidade":q, "status":STATUS_ENTREGA["PENDENTE"]}).execute()
                st.success(f"Registrado! Token: {tk}")
                abrir_whatsapp(rf['whatsapp'], f"🛡️ *SESMT HUC*\nOlá {rf['nome']},\nConfirme o EPI: {get_cfg('url_sistema')}/?confirmar={tk}")

# ----------------------------------------------------------------------------
# 3. COLABORADORES
# ----------------------------------------------------------------------------
elif menu == "👥 Colaboradores":
    st.title("👥 Gestão de Colaboradores")
    df_funcoes = load_data("funcoes", "nome")
    if df_funcoes.empty: st.error("Cadastre 'Funções' primeiro.")
    else:
        with st.form("cad_col"):
            n, m = st.text_input("Nome").upper(), st.text_input("Matrícula")
            s = st.selectbox("Setor", ["CME", "MANUTENÇÃO", "SESMT", "UTI"])
            f = st.selectbox("Função", df_funcoes['nome'].tolist())
            z = st.text_input("WhatsApp")
            if st.form_submit_button("Salvar"):
                supabase.table("oficiais").insert({"nome":n, "matricula":m, "setor":s, "funcao":f, "whatsapp":z}).execute()
                st.success("Salvo!"); st.cache_data.clear()
        st.dataframe(load_data("oficiais", "nome"), use_container_width=True)

# ----------------------------------------------------------------------------
# 4. FUNÇÕES
# ----------------------------------------------------------------------------
elif menu == "🎖️ Funções":
    st.title("🎖️ Funções / Cargos")
    with st.form("add_f"):
        nf = st.text_input("Nova Função").upper()
        if st.form_submit_button("Adicionar"):
            supabase.table("funcoes").insert({"nome":nf}).execute()
            st.cache_data.clear(); st.rerun()
    st.dataframe(load_data("funcoes", "nome"), use_container_width=True)

# ----------------------------------------------------------------------------
# 5. CATÁLOGO EPI (O QUE TINHA SUMIDO!)
# ----------------------------------------------------------------------------
elif menu == "📦 Catálogo EPI":
    st.title("📦 Catálogo de EPIs e C.A.")
    t1, t2 = st.tabs(["➕ Novo EPI", "🛠️ Gerenciar Catálogo"])
    
    with t1:
        with st.form("new_epi"):
            n, ca, v = st.text_input("Nome do EPI").upper(), st.text_input("C.A."), st.date_input("Validade")
            if st.form_submit_button("Salvar no Catálogo"):
                supabase.table("ep").insert({"nome":n, "ca":ca, "validade":str(v)}).execute()
                st.success("EPI Adicionado!"); st.cache_data.clear(); st.rerun()
                
    with t2:
        df_ep = load_data("ep", "nome")
        if not df_ep.empty:
            sel = st.selectbox("Item para Modificar/Excluir", df_ep['nome'])
            item = df_ep[df_ep['nome'] == sel].iloc[0]
            with st.form("edit_epi"):
                en, eca, ev = st.text_input("Nome", item['nome']).upper(), st.text_input("C.A.", item['ca']), st.date_input("Validade", datetime.strptime(item['validade'], '%Y-%m-%d'))
                c1, c2 = st.columns(2)
                if c1.form_submit_button("💾 Salvar Alterações"):
                    supabase.table("ep").update({"nome":en, "ca":eca, "validade":str(ev)}).eq("id", int(item['id'])).execute()
                    st.success("Atualizado!"); st.cache_data.clear(); st.rerun()
                if c2.form_submit_button("🗑️ Excluir EPI"):
                    try:
                        supabase.table("ep").delete().eq("id", int(item['id'])).execute()
                        st.warning("Excluído!"); st.cache_data.clear(); st.rerun()
                    except: st.error("Este EPI já possui entregas e não pode ser deletado.")
        st.dataframe(df_ep, use_container_width=True, hide_index=True)

# ----------------------------------------------------------------------------
# 6. FICHA INDIVIDUAL
# ----------------------------------------------------------------------------
elif menu == "📄 Ficha Individual":
    st.title("📄 Ficha Individual")
    df_f = load_data("oficiais", "nome")
    if not df_f.empty:
        sel = st.selectbox("Colaborador", df_f['nome'])
        f_info = df_f[df_f['nome'] == sel].iloc[0]
        res = supabase.table("entregas").select("*, ep(*)").eq("id_func", int(f_info['id'])).execute().data
        if res:
            rows = [{"Data/Hora": format_br(h['data_entrega'], True), "Qtd": h['quantidade'], "EPI": h['ep']['nome'], "CA": h['ep']['ca'], "Token": h['token'], "Status": h['status']} for h in res]
            df_h = pd.DataFrame(rows)
            st.dataframe(df_h, use_container_width=True, hide_index=True)
            pdf = generate_pdf_ficha(dict(f_info), df_h)
            if pdf: st.download_button("📥 BAIXAR PDF", data=pdf, file_name=f"Ficha_{sel}.pdf", mime="application/pdf")
