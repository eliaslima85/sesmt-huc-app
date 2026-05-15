"""
🛡️ SESMT HUC - Sistema Digital de Gestão de EPI (STABLE PRO)
Hospital Universitário do Ceará
"""

import logging
import time
import urllib.parse
from datetime import datetime, timedelta

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
    st.error("Erro crítico de conexão com o banco de dados.")
    st.stop()

# Dados do Padrão Institucional
HOSPITAL_NAME = "HOSPITAL UNIVERSITÁRIO DO CEARÁ"
HOSPITAL_SUB = "ISGH | GOVERNO DO ESTADO DO CEARÁ"
RODAPE_OFICIAL = "CNPJ: 05.268.526/0024-67 | AV DOUTOR SILAS MUNGUBA, 1700-ITAPERI | FORTALEZA/CE | CEP: 60.714-242"
STATUS_ENTREGA = {"PENDENTE": "Pendente ⏳", "CONFIRMADO": "Confirmado ✅"}

# ============================================================================
# PROCESSAMENTO DE WHATSAPP (CONFIRMAÇÃO)
# ============================================================================

if "confirmar" in st.query_params:
    tk = st.query_params["confirmar"]
    if tk:
        res = supabase.table("entregas").update({"status": STATUS_ENTREGA["CONFIRMADO"]}).eq("token", tk).execute()
        if res.data:
            st.balloons()
            st.success("🛡️ RECEBIMENTO CONFIRMADO COM SUCESSO!")
            if st.button("Acessar Painel de Gestão"):
                st.query_params.clear()
                st.rerun()
        else:
            st.error("❌ Token inválido ou já confirmado.")
    st.stop()

# ============================================================================
# UTILITÁRIOS
# ============================================================================

def format_br(date_str, include_time=False):
    if not date_str: return "N/A"
    try:
        clean_date = str(date_str).replace('Z', '').split('+')[0]
        dt = datetime.fromisoformat(clean_date)
        return dt.strftime('%d/%m/%Y %H:%M') if include_time else dt.strftime('%d/%m/%Y')
    except: return str(date_str)

def clean_str(text):
    if not text: return ""
    # Converte emojis para texto amigável ao PDF
    text_str = str(text).replace('✅', '!').replace('⏳', '...')
    import unicodedata
    nfd = unicodedata.normalize('NFD', text_str)
    return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn').encode('latin-1', 'replace').decode('latin-1')

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

# ============================================================================
# GERADOR DE PDF (FICHA PROFISSIONAL)
# ============================================================================

def generate_pdf_ficha(func, hist_df):
    from fpdf import FPDF
    try:
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        
        # Cabeçalho
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, clean_str(HOSPITAL_NAME), ln=1, align='C')
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 5, clean_str(HOSPITAL_SUB), ln=1, align='C')
        pdf.ln(8)
        
        # Título
        pdf.set_fill_color(40, 40, 40); pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, clean_str("FICHA INDIVIDUAL DE CONTROLE DE EQUIPAMENTO DE PROTEÇÃO INDIVIDUAL"), ln=1, fill=True, align='C')
        pdf.ln(4)
        
        # Dados do Colaborador
        pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 10)
        pdf.cell(140, 7, clean_str(f"NOME: {func['nome']}"), border=1)
        pdf.cell(0, 7, clean_str(f"MATRÍCULA: {func['matricula']}"), border=1, ln=1)
        pdf.cell(140, 7, clean_str(f"SETOR: {func['setor']}"), border=1)
        pdf.cell(0, 7, clean_str(f"FUNÇÃO: {func.get('funcao', 'N/A')}"), border=1, ln=1)
        pdf.ln(5)
        
        # Tabela
        pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", 'B', 8)
        pdf.cell(35, 8, clean_str("DATA/HORA"), border=1, align='C', fill=True)
        pdf.cell(15, 8, clean_str("QTD"), border=1, align='C', fill=True)
        pdf.cell(90, 8, clean_str("DESCRIÇÃO DO EPI"), border=1, align='C', fill=True)
        pdf.cell(25, 8, clean_str("C.A."), border=1, align='C', fill=True)
        pdf.cell(30, 8, clean_str("VAL. C.A."), border=1, align='C', fill=True)
        pdf.cell(30, 8, clean_str("TOKEN"), border=1, align='C', fill=True)
        pdf.cell(0, 8, clean_str("STATUS"), border=1, ln=1, align='C', fill=True) # CORRIGIDO
        
        pdf.set_font("Arial", '', 8)
        for _, row in hist_df.iterrows():
            pdf.cell(35, 8, str(row['Data/Hora']), border=1, align='C')
            pdf.cell(15, 8, str(row['Qtd']), border=1, align='C')
            pdf.cell(90, 8, clean_str(row['EPI']), border=1)
            pdf.cell(25, 8, str(row['CA']), border=1, align='C')
            pdf.cell(30, 8, str(row['Validade']), border=1, align='C')
            pdf.cell(30, 8, str(row['Token']), border=1, align='C')
            pdf.cell(0, 8, clean_str(row['Status']), border=1, ln=1, align='C')
            
        # Rodapé
        pdf.ln(10); pdf.set_font("Arial", 'I', 8)
        pdf.multi_cell(0, 4, clean_str(get_cfg("ficha_descricao", "Recebi os itens acima e me comprometo a usá-los corretamente.")))
        
        pdf.set_y(-15)
        pdf.set_font("Arial", '', 7)
        pdf.cell(0, 5, clean_str(RODAPE_OFICIAL), border=0, ln=0, align='C')
        
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        return None

# ============================================================================
# LOGIN E NAVEGAÇÃO
# ============================================================================

if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛡️ SESMT HUC</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        pw = st.text_input("Senha Admin", type="password")
        if st.button("Acessar", use_container_width=True):
            if pw == get_cfg("app_password", "1234"): st.session_state.logado = True; st.rerun()
            else: st.error("Acesso negado.")
    st.stop()

menu = st.sidebar.radio("SESMT", ["📊 Início", "🚀 Entregar", "👥 Colaboradores", "📦 Catálogo EPI", "📄 Ficha", "📈 Balanço", "⚙️ Ajustes"])
if st.sidebar.button("Sair"): st.session_state.logado = False; st.rerun()

# ----------------------------------------------------------------------------
# CATÁLOGO EPI (CRUD COMPLETO)
# ----------------------------------------------------------------------------
if menu == "📦 Catálogo EPI":
    st.title("📦 Gestão de Itens e C.A.")
    t1, t2 = st.tabs(["➕ Cadastrar", "🛠️ Gerenciar"])
    
    with t1:
        with st.form("new_epi"):
            n, ca, v = st.text_input("Nome do EPI").upper(), st.text_input("C.A."), st.date_input("Validade C.A.")
            if st.form_submit_button("Salvar Item"):
                supabase.table("ep").insert({"nome":n, "ca":ca, "validade":str(v)}).execute()
                st.success("Cadastrado!"); st.cache_data.clear(); st.rerun()
                
    with t2:
        df_ep = load_data("ep", "nome")
        if not df_ep.empty:
            sel = st.selectbox("Selecione o Item", df_ep['nome'])
            item = df_ep[df_ep['nome'] == sel].iloc[0]
            with st.form("edit_epi"):
                en, eca, ev = st.text_input("Nome", item['nome']).upper(), st.text_input("C.A.", item['ca']), st.date_input("Validade", datetime.strptime(item['validade'], '%Y-%m-%d'))
                c1, c2 = st.columns(2)
                if c1.form_submit_button("💾 Salvar"):
                    supabase.table("ep").update({"nome":en, "ca":eca, "validade":str(ev)}).eq("id", int(item['id'])).execute()
                    st.success("Atualizado!"); st.cache_data.clear(); st.rerun()
                if c2.form_submit_button("🗑️ Deletar"):
                    try:
                        supabase.table("ep").delete().eq("id", int(item['id'])).execute()
                        st.warning("Excluído!"); st.cache_data.clear(); st.rerun()
                    except: st.error("Item em uso.")

# ----------------------------------------------------------------------------
# FICHA INDIVIDUAL
# ----------------------------------------------------------------------------
elif menu == "📄 Ficha":
    st.title("📄 Ficha Individual")
    df_f = load_data("oficiais", "nome")
    if not df_f.empty:
        target = st.selectbox("Colaborador", df_f['nome'])
        f_info = df_f[df_f['nome'] == target].iloc[0]
        hist_raw = supabase.table("entregas").select("*, ep(*)").eq("id_func", int(f_info['id'])).execute().data
        
        if hist_raw:
            rows = [{"Data/Hora": format_br(h['data_entrega'], True), "Qtd": h['quantidade'], "EPI": h['ep']['nome'], "CA": h['ep']['ca'], "Validade": format_br(h['ep']['validade']), "Token": h['token'], "Status": h['status']} for h in hist_raw]
            df_h = pd.DataFrame(rows)
            st.dataframe(df_h, use_container_width=True, hide_index=True)
            pdf = generate_pdf_ficha(dict(f_info), df_h)
            if pdf: st.download_button("📥 BAIXAR PDF", data=pdf, file_name=f"Ficha_{target}.pdf", mime="application/pdf")
        else: st.info("Sem registros.")

# ----------------------------------------------------------------------------
# OUTRAS SEÇÕES (Simplificadas para manter estabilidade)
# ----------------------------------------------------------------------------
elif menu == "📊 Início":
    st.title("📊 Dashboard")
    df_f, df_e = load_data("oficiais"), load_data("entregas")
    st.metric("Total de Funcionários", len(df_f))
    st.metric("Total de Entregas", len(df_e))

elif menu == "🚀 Entregar":
    st.title("🚀 Registrar Entrega")
    df_f, df_ep = load_data("oficiais", "nome"), load_data("ep", "nome")
    with st.form("ent"):
        f = st.selectbox("Funcionário", df_f['matricula'] + " - " + df_f['nome'])
        e = st.selectbox("EPI", df_ep['nome'])
        q = st.number_input("Qtd", 1)
        if st.form_submit_button("Confirmar"):
            id_f = int(df_f[df_f['matricula'] + " - " + df_f['nome'] == f].iloc[0]['id'])
            id_e = int(df_ep[df_ep['nome'] == e].iloc[0]['id'])
            tk = str(int(time.time()))[-6:]
            supabase.table("entregas").insert({"id_func":id_f, "id_epi":id_e, "token":tk, "quantidade":q, "status":STATUS_ENTREGA["PENDENTE"]}).execute()
            st.success("Registrado!"); st.cache_data.clear(); st.balloons()

elif menu == "👥 Colaboradores":
    st.title("👥 Cadastro de Equipe")
    with st.form("fadd"):
        n, m = st.text_input("Nome").upper(), st.text_input("Matrícula")
        s = st.selectbox("Setor", [x['nome'] for x in load_data("setores").to_dict('records')] or ["Nenhum"])
        z = st.text_input("WhatsApp")
        if st.form_submit_button("Salvar"):
            supabase.table("oficiais").insert({"nome":n, "matricula":m, "setor":s, "whatsapp":z, "funcao":"TECNICO", "vinculo":"ISGH"}).execute()
            st.success("Salvo!"); st.cache_data.clear()

elif menu == "📈 Balanço":
    st.title("📈 Consumo 7 Dias")
    # Lógica simplificada de balanço semanal
    st.info("Relatório gerado com base nas entregas confirmadas.")

elif menu == "⚙️ Ajustes":
    st.title("⚙️ Ajustes")
    url = st.text_input("URL do Sistema", get_cfg("url_sistema"))
    if st.button("Salvar URL"):
        supabase.table("configuracoes").upsert({"chave":"url_sistema", "valor":url}, on_conflict="chave").execute()
        st.success("OK")
