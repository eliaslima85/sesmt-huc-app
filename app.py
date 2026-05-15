"""
🛡️ SESMT HUC - Sistema Digital de Gestão de EPI (PRO VERSION 2.0)
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

HOSPITAL_NAME = "HOSPITAL UNIVERSITÁRIO DO CEARÁ"
HOSPITAL_SUB = "ISGH | GOVERNO DO ESTADO DO CEARÁ"
RODAPE_OFICIAL = "CNPJ: 05.268.526/0024-67 | AV DOUTOR SILAS MUNGUBA, 1700-ITAPERI | FORTALEZA/CE | CEP: 60.714-242"
STATUS_ENTREGA = {"PENDENTE": "Pendente ⏳", "CONFIRMADO": "Confirmado ✅"}

# ============================================================================
# VERIFICADOR DE TOKEN (ZAP)
# ============================================================================

if "confirmar" in st.query_params:
    tk = st.query_params["confirmar"]
    if tk:
        res = supabase.table("entregas").update({"status": STATUS_ENTREGA["CONFIRMADO"]}).eq("token", tk).execute()
        if res.data:
            st.balloons()
            st.success("🛡️ RECEBIMENTO CONFIRMADO COM SUCESSO!")
            if st.button("Voltar ao Início"):
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

@st.cache_data(ttl=2)
def get_full_history():
    try:
        res = supabase.table("entregas").select("*, oficiais(*), ep(*)").execute()
        return res.data if res.data else []
    except: return []

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
        
        # --- Cabeçalho Estilo Padrão HUC ---
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, clean_str(HOSPITAL_NAME), ln=True, align='C')
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 5, clean_str(HOSPITAL_SUB), ln=True, align='C')
        pdf.ln(8)
        
        # --- Título do Documento ---
        pdf.set_fill_color(40, 40, 40); pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, clean_str("FICHA INDIVIDUAL DE CONTROLE DE EQUIPAMENTO DE PROTEÇÃO INDIVIDUAL"), ln=True, fill=True, align='C')
        pdf.ln(4)
        
        # --- Dados do Colaborador ---
        pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 10)
        pdf.cell(140, 7, clean_str(f"NOME: {func['nome']}"), 1)
        pdf.cell(0, 7, clean_str(f"MATRÍCULA: {func['matricula']}"), 1, ln=True)
        pdf.cell(140, 7, clean_str(f"SETOR: {func['setor']}"), 1)
        pdf.cell(0, 7, clean_str(f"FUNÇÃO: {func.get('funcao', 'N/A')}"), 1, ln=True)
        pdf.ln(5)
        
        # --- Tabela de Movimentação ---
        pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", 'B', 8)
        pdf.cell(35, 8, clean_str("DATA/HORA"), 1, 0, 'C', True)
        pdf.cell(15, 8, clean_str("QTD"), 1, 0, 'C', True)
        pdf.cell(90, 8, clean_str("DESCRIÇÃO DO EPI"), 1, 0, 'C', True)
        pdf.cell(25, 8, clean_str("C.A."), 1, 0, 'C', True)
        pdf.cell(30, 8, clean_str("VAL. C.A."), 1, 0, 'C', True)
        pdf.cell(30, 8, clean_str("TOKEN"), 1, 0, 'C', True)
        pdf.cell(0, 8, clean_str("STATUS"), 1, ln=True, align='C', True)
        
        pdf.set_font("Arial", '', 8)
        for _, row in hist_df.iterrows():
            pdf.cell(35, 8, str(row['Data/Hora']), 1, 0, 'C')
            pdf.cell(15, 8, str(row['Qtd']), 1, 0, 'C')
            pdf.cell(90, 8, clean_str(row['EPI']), 1)
            pdf.cell(25, 8, str(row['CA']), 1, 0, 'C')
            pdf.cell(30, 8, str(row['Validade']), 1, 0, 'C')
            pdf.cell(30, 8, str(row['Token']), 1, 0, 'C')
            pdf.cell(0, 8, clean_str(row['Status']), 1, ln=True, align='C')
            
        # --- Rodapé Normativo ---
        pdf.ln(10)
        pdf.set_font("Arial", 'I', 8)
        pdf.multi_cell(0, 4, clean_str(get_cfg("ficha_descricao", "Declaro que recebi os EPIs listados e fui orientado quanto ao uso e conservação.")))
        
        pdf.set_y(-15)
        pdf.set_font("Arial", '', 7)
        pdf.cell(0, 5, clean_str(RODAPE_OFICIAL), 0, 0, 'C')
        
        return pdf.output(dest='S').encode('latin-1')
    except: return None

# ============================================================================
# LOGIN
# ============================================================================

if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛡️ SESMT HUC</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        pw = st.text_input("Acesso Restrito", type="password")
        if st.button("Entrar", use_container_width=True):
            if pw == get_cfg("app_password", "1234"): st.session_state.logado = True; st.rerun()
            else: st.error("Acesso negado.")
    st.stop()

# ============================================================================
# NAVEGAÇÃO
# ============================================================================

menu = st.sidebar.radio("SESMT MENU", ["📊 Início", "🚀 Registrar Entrega", "👥 Colaboradores", "📦 Catálogo EPI", "📄 Ficha Individual", "📈 Balanço Semanal", "⚙️ Ajustes"])
if st.sidebar.button("Sair"): st.session_state.logado = False; st.rerun()

# ----------------------------------------------------------------------------
# DASHBOARD (INÍCIO)
# ----------------------------------------------------------------------------
if menu == "📊 Início":
    st.title("📊 Painel de Controle SESMT")
    df_f = load_data("oficiais")
    df_e = load_data("entregas")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Funcionários", len(df_f))
    c2.metric("Total de Entregas", len(df_e))
    pend = len(df_e[df_e['status'].str.contains("Pendente", na=False)]) if not df_e.empty else 0
    c3.metric("Assinaturas Pendentes", pend)
    st.divider()
    st.subheader("📲 Pendências de Assinatura")
    hist = get_full_history()
    for p in [e for e in hist if "Pendente" in str(e.get('status'))][:10]:
        c1, c2 = st.columns([4, 1])
        n = p['oficiais']['nome'] if p['oficiais'] else "N/A"
        c1.write(f"⏳ **{n}** | {p['ep']['nome']} (C.A. {p['ep']['ca']})")
        link = f"{get_cfg('url_sistema')}/?confirmar={p['token']}"
        msg = urllib.parse.quote(f"🛡️ *SESMT HUC*\nOlá {n},\nAssine seu EPI: {p['ep']['nome']}\n🔗 Link: {link}")
        c2.markdown(f'<a href="https://api.whatsapp.com/send?phone=55{p["oficiais"]["whatsapp"]}&text={msg}" target="_blank"><button style="background-color:#25D366;color:white;border:none;border-radius:5px;width:100%">Enviar</button></a>', unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# REGISTRAR ENTREGA
# ----------------------------------------------------------------------------
elif menu == "🚀 Registrar Entrega":
    st.title("🚀 Nova Entrega de EPI")
    df_f = load_data("oficiais", "nome")
    df_e = load_data("ep", "nome")
    if df_f.empty or df_e.empty: st.error("Cadastre dados primeiro."); st.stop()
    with st.form("entrega"):
        f = st.selectbox("Colaborador", df_f['matricula'] + " - " + df_f['nome'])
        e = st.selectbox("Equipamento (EPI)", df_e['nome'])
        q = st.number_input("Quantidade", min_value=1, value=1)
        if st.form_submit_button("Registrar"):
            row_f = df_f[df_f['matricula'] + " - " + df_f['nome'] == f].iloc[0]
            row_e = df_e[df_e['nome'] == e].iloc[0]
            tk = str(int(time.time()))[-6:]
            supabase.table("entregas").insert({"id_func":int(row_f['id']), "id_epi":int(row_e['id']), "token":tk, "quantidade":q, "status":STATUS_ENTREGA["PENDENTE"]}).execute()
            st.success(f"Registrado! Token: {tk}"); st.cache_data.clear(); st.balloons()

# ----------------------------------------------------------------------------
# CATÁLOGO DE EPI (COM EDIÇÃO E EXCLUSÃO)
# ----------------------------------------------------------------------------
elif menu == "📦 Catálogo EPI":
    st.title("📦 Gestão de Itens e C.A.")
    t1, t2 = st.tabs(["➕ Cadastrar Novo", "🛠️ Gerenciar Existentes"])
    
    with t1:
        with st.form("new_epi"):
            n, ca, v = st.text_input("Nome do EPI").upper(), st.text_input("C.A."), st.date_input("Validade C.A.")
            if st.form_submit_button("Salvar Item"):
                supabase.table("ep").insert({"nome":n, "ca":ca, "validade":str(v)}).execute()
                st.success("Item adicionado!"); st.cache_data.clear(); st.rerun()
                
    with t2:
        df_ep = load_data("ep", "nome")
        if df_ep.empty: st.info("Nenhum item cadastrado.")
        else:
            sel_edit = st.selectbox("Selecione um item para Modificar ou Deletar", df_ep['nome'])
            item_data = df_ep[df_ep['nome'] == sel_edit].iloc[0]
            
            with st.form("edit_epi"):
                new_n = st.text_input("Alterar Nome", value=item_data['nome']).upper()
                new_ca = st.text_input("Alterar C.A.", value=item_data['ca'])
                new_v = st.date_input("Alterar Validade", value=datetime.strptime(item_data['validade'], '%Y-%m-%d'))
                
                c1, c2 = st.columns(2)
                if c1.form_submit_button("💾 Salvar Alterações"):
                    supabase.table("ep").update({"nome":new_n, "ca":new_ca, "validade":str(new_v)}).eq("id", int(item_data['id'])).execute()
                    st.success("Atualizado!"); st.cache_data.clear(); st.rerun()
                
                if c2.form_submit_button("🗑️ EXCLUIR ITEM"):
                    try:
                        supabase.table("ep").delete().eq("id", int(item_data['id'])).execute()
                        st.warning("Item removido!"); st.cache_data.clear(); st.rerun()
                    except: st.error("Não é possível excluir um EPI que já possui entregas registradas.")

# ----------------------------------------------------------------------------
# FICHA INDIVIDUAL (PROFISSIONAL)
# ----------------------------------------------------------------------------
elif menu == "📄 Ficha Individual":
    st.title("📄 Ficha de Controle de EPI")
    df_f = load_data("oficiais", "nome")
    if df_f.empty: st.info("Sem funcionários."); st.stop()
    target = st.selectbox("Buscar Funcionário", df_f['nome'])
    f_info = df_f[df_f['nome'] == target].iloc[0]
    hist = [h for h in get_full_history() if h['oficiais'] and h['oficiais']['id'] == f_info['id']]
    
    if not hist: st.warning("Nenhum registro para este colaborador.")
    else:
        rows = []
        for h in hist:
            rows.append({"Data/Hora": format_br(h['data_entrega'], True), "Qtd": h['quantidade'], "EPI": h['ep']['nome'] if h['ep'] else "N/A", "CA": h['ep']['ca'] if h['ep'] else "N/A", "Validade": format_br(h['ep']['validade']) if h['ep'] else "N/A", "Token": h['token'], "Status": h['status']})
        df_h = pd.DataFrame(rows)
        st.dataframe(df_h, use_container_width=True, hide_index=True)
        pdf = generate_pdf_ficha(dict(f_info), df_h)
        if pdf: st.download_button("📥 BAIXAR FICHA (PDF)", data=pdf, file_name=f"Ficha_{target.replace(' ', '_')}.pdf", mime="application/pdf")

# ----------------------------------------------------------------------------
# BALANÇO SEMANAL
# ----------------------------------------------------------------------------
elif menu == "📈 Balanço Semanal":
    st.title("📈 Relatório Semanal de Consumo")
    hist = get_full_history()
    if not hist: st.info("Sem dados."); st.stop()
    recentes = []
    for h in hist:
        try:
            if (datetime.now() - datetime.fromisoformat(h['data_entrega'].split('T')[0])).days <= 7:
                recentes.append({"Setor": h['oficiais']['setor'] if h['oficiais'] else "N/A", "EPI": h['ep']['nome'] if h['ep'] else "N/A", "Quantidade": h['quantidade']})
        except: continue
    if not recentes: st.warning("Sem entregas nos últimos 7 dias.")
    else:
        df_b = pd.DataFrame(recentes).groupby(['Setor', 'EPI'])['Quantidade'].sum().reset_index()
        st.table(df_b)
        pdf_b = generate_pdf_balanco(df_b)
        if pdf_b: st.download_button("📥 BAIXAR RELATÓRIO (PDF)", data=pdf_b, file_name="Balanco_Semanal_SESMT.pdf")

# ----------------------------------------------------------------------------
# AJUSTES E CADASTROS BASE
# ----------------------------------------------------------------------------
elif menu == "⚙️ Ajustes":
    st.title("⚙️ Configurações do Sistema")
    t1, t2, t3, t4 = st.tabs(["🔗 Sistema", "🏢 Setores", "👥 Funcionários", "📄 Texto Ficha"])
    with t1:
        u = st.text_input("URL do App", value=get_cfg("url_sistema"))
        if st.button("Salvar URL"): supabase.table("configuracoes").upsert({"chave":"url_sistema", "valor":u}, on_conflict="chave").execute(); st.success("Salvo!")
        s = st.text_input("Nova Senha Admin", type="password")
        if st.button("Mudar Senha"): supabase.table("configuracoes").upsert({"chave":"app_password", "valor":s}, on_conflict="chave").execute(); st.success("Senha alterada!")
    with t2:
        ns = st.text_input("Novo Setor").upper()
        if st.button("Add Setor"): supabase.table("setores").insert({"nome":ns}).execute(); st.cache_data.clear(); st.success("Setor adicionado!")
        st.dataframe(load_data("setores"), use_container_width=True)
    with t3:
        st.write("Para cadastrar novos funcionários:")
        with st.form("f_add"):
            n, m = st.text_input("Nome").upper(), st.text_input("Matrícula").upper()
            s = st.selectbox("Setor", [x['nome'] for x in load_data("setores").to_dict('records')] or ["Nenhum"])
            z = st.text_input("WhatsApp (85...)")
            if st.form_submit_button("Salvar Funcionário"):
                supabase.table("oficiais").insert({"nome":n, "matricula":m, "setor":s, "whatsapp":z, "funcao":"TECNICO", "vinculo":"ISGH"}).execute()
                st.success("Cadastrado!"); st.cache_data.clear()
        st.dataframe(load_data("oficiais"), use_container_width=True)
    with t4:
        txt = st.text_area("Termo Legal", value=get_cfg("ficha_descricao"))
        if st.button("Salvar Termo"): supabase.table("configuracoes").upsert({"chave":"ficha_descricao", "valor":txt}, on_conflict="chave").execute(); st.success("Texto salvo!")
