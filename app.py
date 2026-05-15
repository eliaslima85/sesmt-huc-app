"""
🛡️ SESMT HUC - Sistema Digital de Gestão de EPI (ULTRA STABLE)
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

HOSPITAL_NAME = "HOSPITAL UNIVERSITARIO DO CEARA - HUC"
CNPJ_HUC = "05.268.526/0024-67"
STATUS_ENTREGA = {"PENDENTE": "Pendente ⏳", "CONFIRMADO": "Confirmado ✅"}

# ============================================================================
# PROCESSAMENTO DE WHATSAPP (LADO DE FORA DO LOGIN)
# ============================================================================

if "confirmar" in st.query_params:
    tk = st.query_params["confirmar"]
    if tk:
        res = supabase.table("entregas").update({"status": STATUS_ENTREGA["CONFIRMADO"]}).eq("token", tk).execute()
        if res.data:
            st.balloons()
            st.success("🛡️ RECEBIMENTO CONFIRMADO COM SUCESSO!")
            st.info(f"Registrado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            if st.button("Voltar ao Início"):
                st.query_params.clear()
                st.rerun()
        else:
            st.error("❌ Token inválido ou já confirmado.")
    st.stop()

# ============================================================================
# FUNÇÕES DE APOIO
# ============================================================================

def format_br(date_str, include_time=False):
    if not date_str: return "N/A"
    try:
        # Tenta converter diversos formatos de data do Supabase
        clean_date = str(date_str).replace('Z', '').split('+')[0]
        dt = datetime.fromisoformat(clean_date)
        return dt.strftime('%d/%m/%Y %H:%M') if include_time else dt.strftime('%d/%m/%Y')
    except: return str(date_str)

def remove_accents(text):
    import unicodedata
    if not text: return ""
    nfd = unicodedata.normalize('NFD', str(text))
    return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')

def clean_str(text):
    """Limpa strings para evitar erros no PDF"""
    return remove_accents(str(text)).encode('latin-1', 'replace').decode('latin-1')

# ============================================================================
# ACESSO AO BANCO DE DADOS
# ============================================================================

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
        # Busca entregas trazendo dados das tabelas relacionadas
        res = supabase.table("entregas").select("*, oficiais(*), ep(*)").execute()
        return res.data if res.data else []
    except: return []

def get_cfg(k, d=""):
    try:
        res = supabase.table("configuracoes").select("valor").eq("chave", k).execute()
        return res.data[0]['valor'] if res.data else d
    except: return d

# ============================================================================
# GERADOR DE PDF PROFISSIONAL (FPDF)
# ============================================================================

def generate_pdf_ficha(func, hist_df):
    from fpdf import FPDF
    try:
        pdf = FPDF(orientation='L')
        pdf.add_page()
        pdf.set_font("Arial", 'B', 15)
        pdf.cell(0, 10, clean_str(HOSPITAL_NAME), ln=True, align='C')
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 5, f"CNPJ: {CNPJ_HUC}", ln=True, align='C'); pdf.ln(10)
        
        pdf.set_fill_color(220, 220, 220); pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, clean_str(f"FICHA DE CONTROLE DE EPI - {func['nome']}"), ln=True, fill=True, align='C'); pdf.ln(5)
        
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(140, 7, clean_str(f"COLABORADOR: {func['nome']}"), 0)
        pdf.cell(0, 7, clean_str(f"MATRÍCULA: {func['matricula']}"), ln=True)
        pdf.cell(140, 7, clean_str(f"SETOR: {func['setor']}"), 0)
        pdf.cell(0, 7, clean_str(f"FUNÇÃO: {func['funcao']}"), ln=True); pdf.ln(5)
        
        # Tabela
        pdf.set_font("Arial", 'B', 8); pdf.set_fill_color(200, 200, 200)
        pdf.cell(35, 8, "DATA/HORA", 1, 0, 'C', True)
        pdf.cell(15, 8, "QTD", 1, 0, 'C', True)
        pdf.cell(90, 8, clean_str("DESCRIÇÃO DO EQUIPAMENTO"), 1, 0, 'C', True)
        pdf.cell(25, 8, "C.A.", 1, 0, 'C', True)
        pdf.cell(30, 8, clean_str("VALID. C.A."), 1, 0, 'C', True)
        pdf.cell(30, 8, "TOKEN", 1, 0, 'C', True)
        pdf.cell(0, 8, "STATUS", 1, ln=True, align='C', True)
        
        pdf.set_font("Arial", '', 8)
        for _, row in hist_df.iterrows():
            pdf.cell(35, 8, str(row['Data/Hora']), 1, 0, 'C')
            pdf.cell(15, 8, str(row['Qtd']), 1, 0, 'C')
            pdf.cell(90, 8, clean_str(row['EPI']), 1)
            pdf.cell(25, 8, str(row['CA']), 1, 0, 'C')
            pdf.cell(30, 8, str(row['Validade']), 1, 0, 'C')
            pdf.cell(30, 8, str(row['Token']), 1, 0, 'C')
            pdf.cell(0, 8, clean_str(row['Status']), 1, ln=True, align='C')
            
        pdf.ln(10); pdf.set_font("Arial", 'I', 8)
        pdf.multi_cell(0, 5, clean_str(get_cfg("ficha_descricao", "Declaro que recebi os EPIs acima listados.")))
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        return None

def generate_pdf_balanco(df_group):
    from fpdf import FPDF
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, clean_str("BALANÇO SEMANAL DE CONSUMO - SESMT HUC"), ln=True, align='C'); pdf.ln(10)
        
        pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(200, 200, 200)
        pdf.cell(80, 8, "SETOR", 1, 0, 'C', True)
        pdf.cell(80, 8, "EPI", 1, 0, 'C', True)
        pdf.cell(30, 8, "TOTAL QTD", 1, ln=True, align='C', True)
        
        pdf.set_font("Arial", '', 9)
        for _, row in df_group.iterrows():
            pdf.cell(80, 8, clean_str(row['Setor']), 1)
            pdf.cell(80, 8, clean_str(row['EPI']), 1)
            pdf.cell(30, 8, str(row['Quantidade']), 1, ln=True, align='C')
        return pdf.output(dest='S').encode('latin-1')
    except: return None

# ============================================================================
# SISTEMA DE LOGIN
# ============================================================================

if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛡️ SESMT HUC</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        pw = st.text_input("Senha Admin", type="password")
        if st.button("Acessar Painel", use_container_width=True):
            if pw == get_cfg("app_password", "1234"):
                st.session_state.logado = True
                st.rerun()
            else: st.error("Senha incorreta.")
    st.stop()

# ============================================================================
# NAVEGAÇÃO
# ============================================================================

menu = st.sidebar.radio("SESMT MENU", ["📊 Início", "🚀 Registrar Entrega", "👥 Colaboradores", "📦 Itens/EPIs", "📄 Ficha Individual", "📈 Balanço Semanal", "⚙️ Ajustes"])
if st.sidebar.button("Sair"): st.session_state.logado = False; st.rerun()

# ----------------------------------------------------------------------------
# 1. INÍCIO (DASHBOARD)
# ----------------------------------------------------------------------------
if menu == "📊 Início":
    st.title("📊 Indicadores de Segurança")
    df_f = load_data("oficiais")
    df_e = load_data("entregas")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Funcionários", len(df_f))
    col2.metric("Entregas Total", len(df_e))
    pend = len(df_e[df_e['status'].str.contains("Pendente", na=False)]) if not df_e.empty else 0
    col3.metric("Pendentes", pend)
    
    st.divider()
    st.subheader("📲 Pendências de Assinatura")
    all_data = get_full_history()
    pendentes = [e for e in all_data if "Pendente" in str(e.get('status'))]
    
    if not pendentes: st.success("✅ Nenhuma assinatura pendente!")
    else:
        for p in pendentes[:15]:
            c1, c2 = st.columns([4, 1])
            nome = p['oficiais']['nome'] if p['oficiais'] else "N/A"
            epi = p['ep']['nome'] if p['ep'] else "N/A"
            c1.write(f"⏳ **{nome}** espera: {epi} (Token: {p['token']})")
            
            link = f"{get_cfg('url_sistema')}/?confirmar={p['token']}"
            msg = urllib.parse.quote(f"🛡️ *SESMT HUC*\nOlá {nome},\nAssine seu EPI: {epi}\n🔗 Link: {link}")
            c2.markdown(f' <a href="https://api.whatsapp.com/send?phone=55{p["oficiais"]["whatsapp"]}&text={msg}" target="_blank"><button style="background-color:#25D366;color:white;border:none;padding:5px;border-radius:5px;width:100%">WhatsApp</button></a>', unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# 2. REGISTRAR ENTREGA
# ----------------------------------------------------------------------------
elif menu == "🚀 Registrar Entrega":
    st.title("🚀 Nova Entrega de EPI")
    df_f = load_data("oficiais", "nome")
    df_e = load_data("ep", "nome")
    
    if df_f.empty or df_e.empty:
        st.error("Cadastre funcionários e EPIs primeiro.")
    else:
        with st.form("entrega_epi"):
            f_sel = st.selectbox("Colaborador", df_f['matricula'] + " - " + df_f['nome'])
            e_sel = st.selectbox("EPI", df_e['nome'])
            qtd = st.number_input("Quantidade", min_value=1, value=1)
            if st.form_submit_button("Confirmar Entrega"):
                row_f = df_f[df_f['matricula'] + " - " + df_f['nome'] == f_sel].iloc[0]
                row_e = df_e[df_e['nome'] == e_sel].iloc[0]
                tk = str(int(time.time()))[-6:] # Token baseado no tempo
                
                supabase.table("entregas").insert({
                    "id_func": int(row_f['id']), "id_epi": int(row_e['id']),
                    "token": tk, "quantidade": qtd, "status": STATUS_ENTREGA["PENDENTE"]
                }).execute()
                st.cache_data.clear(); st.success(f"Registrado! Token: {tk}"); st.balloons()

# ----------------------------------------------------------------------------
# 5. FICHA INDIVIDUAL (O QUE VOCÊ PEDIU)
# ----------------------------------------------------------------------------
elif menu == "📄 Ficha Individual":
    st.title("📄 Ficha de EPI por Funcionário")
    df_f = load_data("oficiais", "nome")
    if df_f.empty: st.info("Nenhum funcionário encontrado.")
    else:
        target = st.selectbox("Selecione o Colaborador", df_f['nome'])
        f_info = df_f[df_f['nome'] == target].iloc[0]
        
        history = get_full_history()
        # Filtro robusto
        my_hist = [h for h in history if h['oficiais'] and h['oficiais']['id'] == f_info['id']]
        
        if not my_hist:
            st.warning("Este colaborador ainda não possui registros de entrega.")
        else:
            rows = []
            for m in my_hist:
                rows.append({
                    "Data/Hora": format_br(m['data_entrega'], True),
                    "Qtd": m['quantidade'],
                    "EPI": m['ep']['nome'] if m['ep'] else "N/A",
                    "CA": m['ep']['ca'] if m['ep'] else "N/A",
                    "Validade": format_br(m['ep']['validade']) if m['ep'] else "N/A",
                    "Token": m['token'],
                    "Status": m['status']
                })
            df_display = pd.DataFrame(rows)
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # Geração do PDF
            pdf_data = generate_pdf_ficha(dict(f_info), df_display)
            if pdf_data:
                st.download_button(
                    label="📥 BAIXAR FICHA COMPLETA (PDF)",
                    data=pdf_data,
                    file_name=f"Ficha_EPI_{target.replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("Erro ao gerar o arquivo PDF. Verifique caracteres especiais.")

# ----------------------------------------------------------------------------
# 6. BALANÇO SEMANAL (O QUE VOCÊ PEDIU)
# ----------------------------------------------------------------------------
elif menu == "📈 Balanço Semanal":
    st.title("📈 Resumo de Consumo (7 Dias)")
    history = get_full_history()
    
    if not history: st.info("Sem dados para exibir.")
    else:
        # Filtro de 7 dias simplificado
        lista_semanal = []
        hoje = datetime.now()
        for h in history:
            try:
                data_e = datetime.fromisoformat(h['data_entrega'].split('T')[0])
                if (hoje - data_e).days <= 7:
                    lista_semanal.append({
                        "Setor": h['oficiais']['setor'] if h['oficiais'] else "N/A",
                        "EPI": h['ep']['nome'] if h['ep'] else "N/A",
                        "Quantidade": h['quantidade']
                    })
            except: continue
            
        if not lista_semanal:
            st.warning("Nenhuma entrega realizada nos últimos 7 dias.")
        else:
            df_balanco = pd.DataFrame(lista_semanal).groupby(['Setor', 'EPI'])['Quantidade'].sum().reset_index()
            st.table(df_balanco)
            
            pdf_bal = generate_pdf_balanco(df_balanco)
            if pdf_bal:
                st.download_button("📥 BAIXAR RESUMO SEMANAL (PDF)", data=pdf_bal, file_name="Resumo_Consumo_HUC.pdf", mime="application/pdf")

# ----------------------------------------------------------------------------
# RESTANTE DO CÓDIGO (COMO ANTES)
# ----------------------------------------------------------------------------
elif menu == "👥 Colaboradores":
    st.title("👥 Gestão de Pessoal")
    t1, t2 = st.tabs(["Cadastrar", "Lista"])
    with t1:
        with st.form("f_new"):
            n, m = st.text_input("Nome").upper(), st.text_input("Matrícula").upper()
            s = st.selectbox("Setor", [x['nome'] for x in load_data("setores").to_dict('records')] or ["Nenhum"])
            w = st.text_input("Zap (859...)")
            if st.form_submit_button("Salvar"):
                supabase.table("oficiais").insert({"nome":n, "matricula":m, "setor":s, "whatsapp":w, "funcao":"TECNICO", "vinculo":"ISGH"}).execute()
                st.success("Salvo!"); st.cache_data.clear()
    with t2: st.dataframe(load_data("oficiais"), use_container_width=True)

elif menu == "📦 Itens/EPIs":
    st.title("📦 Gestão de Itens")
    with st.form("e_new"):
        n, c, v = st.text_input("EPI").upper(), st.text_input("CA"), st.date_input("Validade")
        if st.form_submit_button("Salvar"):
            supabase.table("ep").insert({"nome":n, "ca":c, "validade":str(v)}).execute()
            st.success("Salvo!"); st.cache_data.clear()
    st.dataframe(load_data("ep"), use_container_width=True)

elif menu == "⚙️ Ajustes":
    st.title("⚙️ Configurações do SESMT")
    u = st.text_input("URL do App", value=get_cfg("url_sistema"))
    if st.button("Salvar URL"):
        supabase.table("configuracoes").upsert({"chave":"url_sistema", "valor":u}, on_conflict="chave").execute()
        st.success("URL Salva!")
    t_legal = st.text_area("Termos da Ficha", value=get_cfg("ficha_descricao"))
    if st.button("Salvar Texto"):
        supabase.table("configuracoes").upsert({"chave":"ficha_descricao", "valor":t_legal}, on_conflict="chave").execute()
        st.success("Texto Salvo!")
