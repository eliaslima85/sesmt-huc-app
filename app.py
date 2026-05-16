"""
🛡️ SESMT HUC - Sistema Digital de Gestão de EPI v7.0 (PRODUCTION READY)
Hospital Universitário do Ceará - Padrão Oficial ISGH
📱 Mobile-First | 🔒 Segurança Enterprise | ✨ UI Profissional
"""

import logging
import time
import urllib.parse
import requests
import hashlib
import os
from datetime import datetime, timedelta
from io import BytesIO

import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas

# ============================================================================
# 🔧 CONFIGURAÇÕES E INICIALIZAÇÃO
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="SESMT HUC - Digital",
    layout="wide",
    page_icon="🛡️",
    initial_sidebar_state="collapsed"
)

# CSS Global Mobile-First e Moderno
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif !important;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        min-width: 260px !important;
        max-width: 280px !important;
    }
    [data-testid="stSidebar"] .stRadio > label {
        color: white !important;
        font-size: 0.9rem !important;
        padding: 8px 12px !important;
        border-radius: 8px !important;
        margin: 2px 0 !important;
        transition: all 0.2s ease;
    }
    [data-testid="stSidebar"] .stRadio > label:hover {
        background: rgba(255,255,255,0.1) !important;
    }
    .stMetric {
        background: white !important;
        border-radius: 12px !important;
        padding: 16px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
        border: 1px solid #f0f0f0 !important;
    }
    .stButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
        min-height: 44px !important;
        font-size: 0.95rem !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    }
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select,
    .stDateInput > div > div > input {
        border-radius: 10px !important;
        border: 2px solid #e8e8e8 !important;
        min-height: 44px !important;
        font-size: 1rem !important;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus,
    .stDateInput > div > div > input:focus {
        border-color: #4a90d9 !important;
        box-shadow: 0 0 0 3px rgba(74,144,217,0.15) !important;
    }
    [data-testid="stForm"] {
        background: #fafbfc !important;
        border-radius: 16px !important;
        padding: 24px !important;
        border: 1px solid #eef0f2 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    }
    h1 {
        font-weight: 700 !important;
        color: #1a1a2e !important;
        letter-spacing: -0.5px !important;
        font-size: 1.6rem !important;
    }
    h2, h3 {
        font-weight: 600 !important;
        color: #2d3748 !important;
        font-size: 1.3rem !important;
    }
    hr {
        border-color: #edf2f7 !important;
        margin: 1.5rem 0 !important;
    }
    .stDataFrame {
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
    }
    .stAlert {
        border-radius: 12px !important;
        border: none !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px !important;
        border-bottom: 2px solid #edf2f7 !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0 !important;
        padding: 10px 16px !important;
        font-weight: 500 !important;
    }
    @media (max-width: 768px) {
        h1 { font-size: 1.3rem !important; }
        h2, h3 { font-size: 1.1rem !important; }
        .stMetric { padding: 12px !important; }
        [data-testid="stForm"] { padding: 16px !important; }
        .stButton > button { font-size: 0.9rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# Carregamento inteligente de credenciais
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://aatkjhtrafuepwzzlrbm.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFhdGtqaHRyYWZ1ZXB3enpscmJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg2Mjg5MTYsImV4cCI6MjA5NDIwNDkxNn0.65izu7Zhc3kUZrVIRXGvVQ5o-Lhk-7PCK9CMg4zIwuk")

@st.cache_resource
def init_supabase() -> Client:
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logger.error(f"Erro de conexão com Supabase: {str(e)}")
        st.error("🚨 Erro crítico de conexão com o banco de dados na nuvem.")
        st.stop()

supabase: Client = init_supabase()

# Padrões Institucionais Oficiais
HOSPITAL_NAME = "HOSPITAL UNIVERSITÁRIO DO CEARÁ"
HOSPITAL_ISGH = "ISGH - INSTITUTO DE SAÚDE E GESTÃO HOSPITALAR"
CNPJ_ENDERECO = "CNPJ: 05.268.526/0024-67 | AV DOUTOR SILAS MUNGUBA, 1700-ITAPERI | FORTALEZA/CE | CEP: 60.714-242"
GOVERNO_SUB = "GOVERNO DO ESTADO DO CEARÁ"
STATUS_ENTREGA = {"PENDENTE": "Pendente ⏳", "CONFIRMADO": "Confirmado ✅"}

# ============================================================================
# 🛠️ UTILITÁRIOS E FORMATAÇÃO BRASILEIRA
# ============================================================================

def clean_str(text):
    if not text: return ""
    text_str = str(text).replace('✅', '!').replace('⏳', '...')
    return text_str.encode('latin-1', 'replace').decode('latin-1')

def format_br(date_str, include_time=False):
    if not date_str: return "N/A"
    try:
        d_str = str(date_str).strip()
        if "/" in d_str and len(d_str.split('/')) == 3:
            return d_str
        clean_date = d_str.replace('Z', '').split('+')[0]
        if "T" in clean_date or " " in clean_date:
            clean_date = clean_date.replace('T', ' ')
            clean_date = clean_date.split('.')[0]
            dt = datetime.strptime(clean_date, '%Y-%m-%d %H:%M:%S')
            if include_time:
                return dt.strftime('%d/%m/%Y %H:%M')
            return dt.strftime('%d/%m/%Y')
        else:
            dt = datetime.strptime(clean_date, '%Y-%m-%d')
            return dt.strftime('%d/%m/%Y')
    except Exception as e:
        logger.warning(f"Erro ao formatar data '{date_str}': {e}")
        return str(date_str)

def format_date_obj(date_obj, include_time=False):
    if not date_obj: return "N/A"
    try:
        if isinstance(date_obj, datetime):
            if include_time:
                return date_obj.strftime('%d/%m/%Y %H:%M')
            return date_obj.strftime('%d/%m/%Y')
        elif isinstance(date_obj, str):
            return format_br(date_obj, include_time)
        else:
            return str(date_obj)
    except:
        return str(date_obj)

@st.cache_data(ttl=2)
def load_data(table, order=None):
    try:
        q = supabase.table(table).select("*")
        if order: q = q.order(order)
        res = q.execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        logger.error(f"Erro ao carregar tabela {table}: {e}")
        return pd.DataFrame()

def get_cfg(k, d=""):
    try:
        res = supabase.table("configuracoes").select("valor").eq("chave", k).execute()
        return res.data[0]['valor'] if res.data else d
    except: return d

def abrir_whatsapp(numero, mensagem):
    msg_url = urllib.parse.quote(mensagem)
    link = f"https://api.whatsapp.com/send?phone=55{numero}&text={msg_url}"
    btn_html = f'<a href="{link}" target="_blank"><button style="background: linear-gradient(135deg, #25D366 0%, #128C7E 100%); color:white; border:none; padding:12px 20px; border-radius:10px; width:100%; cursor:pointer; font-weight:600; font-size:0.95rem; box-shadow: 0 2px 8px rgba(37,211,102,0.3); display:flex; align-items:center; justify-content:center; gap:8px;">🚀 ENVIAR PARA WHATSAPP</button></a>'
    st.markdown(btn_html, unsafe_allow_html=True)

# ============================================================================
# 📲 LINK DO WHATSAPP: CONFIRMAÇÃO DE TOKEN E CAPTURA INTELIGENTE
# ============================================================================

if "confirmar" in st.query_params:
    tk = st.query_params["confirmar"]
    if tk:
        ent_res = supabase.table("entregas").select("*, oficiais(*)").eq("token", tk).execute()
        if ent_res.data:
            entrega = ent_res.data[0]
            func = entrega['oficiais']
            epi_res = supabase.table("ep").select("nome, ca").eq("id", entrega['id_epi']).execute()
            epi_nome = epi_res.data[0]['nome'] if epi_res.data else "EPI"
            
            st.markdown('<div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; padding: 16px; border-radius: 12px; margin-bottom: 20px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.1);"><h3 style="color:white; margin:0; font-size:1.1rem;">🛡️ Confirmação Digital de EPI - SESMT HUC</h3><p style="margin:4px 0 0 0; font-size:0.8rem; opacity:0.85;">Hospital Universitário do Ceará | ISGH</p></div>', unsafe_allow_html=True)
            
            st.markdown("##### 👤 Dados do Colaborador")
            c1, c2 = st.columns(2)
            c1.markdown(f"**Nome:** {func['nome']}")
            c2.markdown(f"**Matrícula:** {func['matricula']}")
            
            st.markdown("##### 📦 Dados da Entrega")
            c3, c4 = st.columns(2)
            c3.markdown(f"**Item:** {epi_nome}")
            c4.markdown(f"**Quantidade:** {entrega['quantidade']}")
            
            st.divider()
            
            if not func.get('assinatura_url'):
                st.warning("📝 Esta é sua primeira confirmação eletrônica. Desenhe sua assinatura na tela abaixo para salvá-la em sua ficha definitiva.")
                canvas_zap = st_canvas(
                    stroke_width=2, 
                    stroke_color="#000", 
                    background_color="#eee", 
                    height=140, 
                    width=340, 
                    key="canvas_zap"
                )
                
                if st.button("✍️ Gravar Assinatura e Confirmar", use_container_width=True, type="primary"):
                    if canvas_zap.image_data is not None:
                        img = Image.fromarray(canvas_zap.image_data.astype('uint8'), 'RGBA')
                        buffered = BytesIO()
                        img.save(buffered, format="PNG")
                        
                        path = f"sig_{func['id']}_{int(time.time())}.png"
                        
                        try:
                            supabase.storage.from_("assinaturas").upload(
                                path=path, 
                                file=buffered.getvalue(), 
                                file_options={"content-type": "image/png"}
                            )
                            url = supabase.storage.from_("assinaturas").get_public_url(path)
                            
                            try:
                                supabase.table("oficiais").update({"assinatura_url": url}).eq("id", func['id']).execute()
                            except Exception as db_col_err:
                                logger.error(f"Erro PGRST204 interceptado: {db_col_err}")
                                st.error("⚠️ Atenção: A coluna 'assinatura_url' não foi encontrada na tabela 'oficiais'. Execute o comando SQL indicado no painel do Supabase.")
                            
                            supabase.table("entregas").update({"status": STATUS_ENTREGA["CONFIRMADO"]}).eq("token", tk).execute()
                            st.balloons()
                            st.success("✅ ASSINATURA REGISTRADA E EPI CONFIRMADO COM SUCESSO!")
                            time.sleep(2)
                            st.query_params.clear()
                            st.rerun()
                        except Exception as upload_err:
                            st.error(f"⚠️ Erro de armazenamento na nuvem. Verifique o Bucket público 'assinaturas'. Detalhes: {upload_err}")
            else:
                st.success("✨ Sua assinatura digital master já está vinculada de forma segura ao seu prontuário.")
                if st.button("👍 Confirmar Recebimento deste EPI", use_container_width=True, type="primary"):
                    supabase.table("entregas").update({"status": STATUS_ENTREGA["CONFIRMADO"]}).eq("token", tk).execute()
                    st.balloons()
                    st.success("🛡️ RECEBIMENTO VALIDADO COM SUCESSO!")
                    time.sleep(2)
                    st.query_params.clear()
                    st.rerun()
        else:
            st.error("❌ Token inválido ou link de confirmação expirado.")
    st.stop()

# ============================================================================
# GERADOR DE PDF PROFISSIONAL
# ============================================================================

def generate_pdf(title, headers, data_rows, func_info=None, is_ficha=False, custom_text=None):
    from fpdf import FPDF
    try:
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 8, clean_str(HOSPITAL_NAME), border=0, ln=1, align='C')
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(0, 5, clean_str(HOSPITAL_ISGH), border=0, ln=1, align='C')
        pdf.set_font("Arial", '', 8)
        pdf.cell(0, 5, clean_str(CNPJ_ENDERECO), border=0, ln=1, align='C')
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(0, 5, clean_str(GOVERNO_SUB), border=0, ln=1, align='C')
        pdf.ln(5)
        
        pdf.set_fill_color(40, 40, 40)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, clean_str(title), border=0, ln=1, fill=True, align='C')
        pdf.ln(4)
        
        pdf.set_text_color(0, 0, 0)
        if is_ficha and func_info:
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(140, 8, clean_str(f"COLABORADOR: {func_info['nome']}"), border=1)
            pdf.cell(0, 8, clean_str(f"MATRÍCULA: {func_info['matricula']}"), border=1, ln=1)
            pdf.cell(140, 8, clean_str(f"SETOR: {func_info['setor']}"), border=1)
            pdf.cell(0, 8, clean_str(f"FUNÇÃO: {func_info.get('funcao', 'N/A')}"), border=1, ln=1)
            
            data_adm = func_info.get('data_admissao', 'N/A')
            if data_adm and data_adm != 'N/A':
                data_adm = format_br(data_adm)
            pdf.cell(0, 8, clean_str(f"DATA DE ADMISSÃO: {data_adm}"), border=1, ln=1)
            pdf.ln(5)

        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Arial", 'B', 8)
        col_widths = [35, 15, 90, 30, 30, 0] if is_ficha else [80, 110, 0]
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 8, clean_str(h), border=1, align='C', fill=True)
        pdf.ln()
        
        pdf.set_font("Arial", '', 8)
        for row in data_rows:
            for i, val in enumerate(row):
                pdf.cell(
                    col_widths[i], 
                    8, 
                    clean_str(str(val)), 
                    border=1, 
                    ln=(1 if i == len(row)-1 else 0), 
                    align=('L' if i==2 and is_ficha else 'C')
                )
            
        if is_ficha:
            pdf.ln(10)
            pdf.set_font("Arial", 'I', 8)
            texto_render = custom_text if custom_text else get_cfg(
                "ficha_descricao", 
                "Declaro que recebi os EPIs listados e fui orientado sobre o correto uso e conservacao."
            )
            pdf.multi_cell(0, 4, clean_str(texto_render))
            
            pdf.ln(8)
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(0, 5, clean_str("ASSINATURA ELETRONICA DO FUNCIONARIO"), border=0, ln=1)
            pdf.ln(2)
            
            if func_info.get('assinatura_url'):
                try:
                    r = requests.get(func_info['assinatura_url'], timeout=5)
                    img = Image.open(BytesIO(r.content)).convert("RGB")
                    img.save("temp_sig.jpg")
                    pdf.image("temp_sig.jpg", x=20, y=pdf.get_y(), w=40)
                    pdf.ln(15)
                except: pass

        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}")
        return None

# ============================================================================
# INTERFACE ADMINISTRATIVA E ROTEAMENTO DE MENUS
# ============================================================================

if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    st.markdown("""
        <style>
            .login-container {
                max-width: 400px;
                margin: 0 auto;
                padding: 40px 24px;
                background: white;
                border-radius: 20px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                margin-top: 10vh;
            }
            .login-title {
                text-align: center;
                font-size: 2.5rem;
                margin-bottom: 8px;
            }
            .login-subtitle {
                text-align: center;
                color: #666;
                font-size: 0.9rem;
                margin-bottom: 32px;
            }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div class="login-container">
            <div class="login-title">🛡️</div>
            <h2 style="text-align:center; margin:0; color:#1a1a2e;">SESMT HUC</h2>
            <p class="login-subtitle">Sistema Digital de Gestão de EPI<br>Hospital Universitário do Ceará</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        pw = st.text_input("Senha Administrativa", type="password", placeholder="Digite sua senha...")
        if st.button("🔐 Entrar no Sistema", use_container_width=True, type="primary"):
            if pw == os.getenv("SESMT_PASSWORD", get_cfg("app_password", "1234")): 
                st.session_state.logado = True
                st.rerun()
            else: 
                st.error("🔒 Acesso Negado. Senha incorreta.")
    st.stop()

# Menu lateral moderno
st.sidebar.markdown("""
    <div style="text-align:center; padding: 16px 8px; margin-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.1);">
        <h3 style="color:white; margin:0; font-size:1.1rem;">🛡️ SESMT HUC</h3>
        <p style="color:rgba(255,255,255,0.6); margin:4px 0 0 0; font-size:0.75rem;">Gestão Digital de EPI</p>
    </div>
""", unsafe_allow_html=True)

menu = st.sidebar.radio("", [
    "📊 Painel", 
    "🚀 Registrar Entrega", 
    "👥 Colaboradores", 
    "🎖️ Funções", 
    "📦 Catálogo EPI", 
    "📄 Ficha Individual", 
    "📈 Balanço Semanal",
    "⚙️ Ajustes"
])

st.sidebar.markdown("<br>", unsafe_allow_html=True)
if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
    st.session_state.logado = False
    st.rerun()

# ----------------------------------------------------------------------------
# 1. 📊 PAINEL
# ----------------------------------------------------------------------------
if menu == "📊 Painel":
    st.title("📊 Indicadores e Controles Operacionais")
    
    df_f, df_e = load_data("oficiais"), load_data("entregas")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("👥 Colaboradores", len(df_f), delta="Ativos")
    c2.metric("📦 Entregas", len(df_e), delta="Total")
    pendentes = df_e[df_e['status'].str.contains("Pendente", na=False)] if not df_e.empty else pd.DataFrame()
    c3.metric("⏳ Pendentes", len(pendentes), delta="Aguardando", delta_color="inverse")
    
    st.divider()
    
    st.subheader("📲 Pendências de Assinatura Eletrônica")
    if len(pendentes) > 0:
        for _, p in pendentes.iterrows():
            f_res = supabase.table("oficiais").select("nome, whatsapp").eq("id", p['id_func']).execute()
            epi_res = supabase.table("ep").select("nome").eq("id", p['id_epi']).execute()
            epi_nome = epi_res.data[0]['nome'] if epi_res.data else "EPI"
            
            if f_res.data:
                f = f_res.data[0]
                with st.container():
                    st.markdown('<div style="background: white; border-radius: 12px; padding: 16px; margin: 8px 0; border: 1px solid #edf2f7; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">', unsafe_allow_html=True)
                    
                    col1, col2 = st.columns([3, 1])
                    col1.markdown(f"**{f['nome']}**  \n🧤 {p['quantidade']}x {epi_nome}  \n🔑 Token: `{p['token']}`")
                    
                    link = f"{get_cfg('url_sistema')}/?confirmar={p['token']}"
                    msg = f"🛡️ *SESMT HUC*\nOlá *{f['nome']}*,\nVocê possui uma entrega pendente de confirmação para o EPI: *{p['quantidade']}x {epi_nome}*. Acesse o link seguro para assinar digitalmente: {link}"
                    with col2: 
                        abrir_whatsapp(f['whatsapp'], msg)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.success("✅ Nenhuma assinatura pendente no momento!")

# ----------------------------------------------------------------------------
# 2. 🚀 REGISTRAR ENTREGA
# ----------------------------------------------------------------------------
elif menu == "🚀 Registrar Entrega":
    st.title("🚀 Registrar Entrega de Equipamentos")
    
    df_f, df_ep = load_data("oficiais", "nome"), load_data("ep", "nome")
    
    if df_f.empty or df_ep.empty: 
        st.warning("⚠️ É necessário cadastrar Colaboradores e EPIs no catálogo antes de realizar uma entrega.")
    else:
        with st.form("ent"):
            st.markdown("##### 📋 Dados da Entrega")
            
            f = st.selectbox("👤 Colaborador", df_f['matricula'] + " - " + df_f['nome'])
            e = st.selectbox("🧤 EPI", df_ep['nome'])
            q = st.number_input("📊 Quantidade", min_value=1, value=1)
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("✅ Gerar Registro de Entrega", use_container_width=True):
                rf = df_f[df_f['matricula'] + " - " + df_f['nome'] == f].iloc[0]
                re = df_ep[df_ep['nome'] == e].iloc[0]
                tk = str(int(time.time()))[-6:]
                
                supabase.table("entregas").insert({
                    "id_func": int(rf['id']), 
                    "id_epi": int(re['id']), 
                    "token": tk, 
                    "quantidade": q, 
                    "status": STATUS_ENTREGA["PENDENTE"]
                }).execute()
                
                st.success(f"✅ Entrega registrada! Token: `{tk}`")
                link = f"{get_cfg('url_sistema')}/?confirmar={tk}"
                msg = f"🛡️ *SESMT HUC*\nOlá *{rf['nome']}*,\nConfirme o recebimento de *{q}x {e}* acessando o link seguro de assinatura: {link}"
                abrir_whatsapp(rf['whatsapp'], msg)

# ----------------------------------------------------------------------------
# 3. 👥 COLABORADORES
# ----------------------------------------------------------------------------
elif menu == "👥 Colaboradores":
    st.title("👥 Gestão de Prontuários de Colaboradores")
    
    df_funcoes = load_data("funcoes", "nome")
    
    if df_funcoes.empty: 
        st.error("⚠️ Cadastre as 'Funções/Cargos' no sistema antes de incluir colaboradores.")
    else:
        tab1, tab2 = st.tabs(["➕ Novo Colaborador", "🛠️ Gerenciar / Excluir"])
        
        with tab1:
            with st.form("cad_col"):
                st.markdown("##### 📝 Dados Pessoais")
                n = st.text_input("Nome Completo", placeholder="DIGITE O NOME COMPLETO").upper()
                m = st.text_input("Matrícula", placeholder="Número da matrícula")
                
                st.markdown("##### 🏢 Dados Corporativos")
                da = st.date_input("Data de Admissão", value=datetime.today(), format="DD/MM/YYYY")
                s = st.selectbox("Setor", [
                    "CME", "SESMT", "UTI", "MANUTENÇÃO", "CENTRO CIRÚRGICO", 
                    "EMERGÊNCIA", "PEDIATRIA", "ADMINISTRATIVO"
                ])
                func = st.selectbox("Função / Cargo", df_funcoes['nome'].tolist())
                z = st.text_input("WhatsApp", placeholder="85912345678 (DDD + Número)")
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("💾 Salvar Registro", use_container_width=True):
                    if n and m and z:
                        supabase.table("oficiais").insert({
                            "nome": n, 
                            "matricula": m, 
                            "data_admissao": da.strftime('%Y-%m-%d'), 
                            "setor": s, 
                            "funcao": func, 
                            "whatsapp": z
                        }).execute()
                        st.success("✅ Colaborador cadastrado com sucesso!")
                        st.cache_data.clear()
                    else: 
                        st.error("⚠️ Preencha todos os campos obrigatórios.")
        
        with tab2:
            df_oficiais = load_data("oficiais", "nome")
            if not df_oficiais.empty:
                sel_excluir = st.selectbox("Selecione para Excluir", df_oficiais['nome'])
                func_del = df_oficiais[df_oficiais['nome'] == sel_excluir].iloc[0]
                
                st.warning(f"⚠️ **Atenção:** Você selecionou **{func_del['nome']}** para exclusão. Esta ação é permanente.")
                
                res_del = supabase.table("entregas").select("*, ep(*)").eq("id_func", int(func_del['id'])).order("data_entrega", desc=True).execute().data
                if res_del:
                    st.info("💡 Recomendado fazer download do histórico antes da exclusão.")
                    df_h_del = pd.DataFrame([{
                        "Data/Hora": format_br(h['data_entrega'], True), 
                        "Qtd": h['quantidade'], 
                        "EPI": h['ep']['nome'], 
                        "C.A.": h['ep']['ca'], 
                        "Token": h['token'], 
                        "Status": h['status']
                    } for h in res_del])
                    headers_del = ["DATA/HORA", "QTD", "DESCRIÇÃO DO EPI", "C.A.", "TOKEN", "STATUS"]
                    texto_padrao = get_cfg("ficha_descricao", "Declaro que recebi os EPIs listados e fui orientado sobre o correto uso e conservacao.")
                    
                    pdf_backup = generate_pdf(
                        f"FICHA DE EPI - BACKUP DE EXCLUSAO", 
                        headers_del, 
                        df_h_del.values.tolist(), 
                        dict(func_del), 
                        True, 
                        custom_text=texto_padrao
                    )
                    if pdf_backup:
                        st.download_button(
                            "📥 Baixar Ficha Completa Antes de Excluir", 
                            data=pdf_backup, 
                            file_name=f"Backup_Exclusao_{sel_excluir}.pdf", 
                            mime="application/pdf", 
                            use_container_width=True
                        )
                else:
                    st.info("ℹ️ Este colaborador não possui registros de retirada de EPI.")

                if st.button("🗑️ Deletar Definitivamente", type="primary", use_container_width=True):
                    try:
                        supabase.table("entregas").delete().eq("id_func", int(func_del['id'])).execute()
                        supabase.table("oficiais").delete().eq("id", int(func_del['id'])).execute()
                        st.success(f"✅ Colaborador {func_del['nome']} removido.")
                        st.cache_data.clear()
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao excluir: {e}")

        st.write("---")
        df_oficiais = load_data("oficiais", "nome")
        if not df_oficiais.empty:
            df_oficiais_view = df_oficiais.copy()
            for col in ['data_admissao', 'data_consentimento', 'data_criacao']:
                if col in df_oficiais_view.columns:
                    df_oficiais_view[col] = df_oficiais_view[col].apply(
                        lambda x: format_br(x, True) if 'criacao' in col else format_br(x) if x else ""
                    )
            st.dataframe(
                df_oficiais_view[['nome', 'matricula', 'data_admissao', 'setor', 'funcao', 'whatsapp']], 
                use_container_width=True, 
                hide_index=True
            )

# ----------------------------------------------------------------------------
# 4. 🎖️ FUNÇÕES
# ----------------------------------------------------------------------------
elif menu == "🎖️ Funções":
    st.title("🎖️ Cadastro de Funções e Cargos")
    
    with st.form("add_f"):
        nf = st.text_input("Nome da Nova Função", placeholder="Ex: TÉCNICO DE ENFERMAGEM").upper()
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("➕ Adicionar ao Sistema", use_container_width=True):
            if nf:
                supabase.table("funcoes").insert({"nome": nf}).execute()
                st.success(f"✅ Função '{nf}' incluída!")
                st.cache_data.clear()
                st.rerun()
    
    st.markdown("##### 📋 Funções Cadastradas")
    st.dataframe(load_data("funcoes", "nome"), use_container_width=True, hide_index=True)

# ----------------------------------------------------------------------------
# 5. 📦 CATÁLOGO EPI
# ----------------------------------------------------------------------------
elif menu == "📦 Catálogo EPI":
    st.title("📦 Catálogo de Equipamentos e Certificados de Aprovação (C.A.)")
    
    t1, t2 = st.tabs(["➕ Novo EPI", "🛠️ Gerenciar Catálogo"])
    
    with t1:
        with st.form("new_epi"):
            st.markdown("##### 🧤 Dados do EPI")
            n = st.text_input("Nome Técnico", placeholder="NOME DO EPI").upper()
            ca = st.text_input("Número do C.A.", placeholder="Certificado de Aprovação")
            v = st.date_input("Validade do C.A.", format="DD/MM/YYYY")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("💾 Salvar no Catálogo", use_container_width=True):
                if n and ca:
                    supabase.table("ep").insert({
                        "nome": n, 
                        "ca": ca, 
                        "validade": v.strftime('%Y-%m-%d')
                    }).execute()
                    st.success("✅ EPI integrado ao catálogo!")
                    st.cache_data.clear()
                    st.rerun()
    
    with t2:
        df_ep = load_data("ep", "nome")
        if not df_ep.empty:
            sel = st.selectbox("Selecione para Edição/Exclusão", df_ep['nome'])
            it = df_ep[df_ep['nome'] == sel].iloc[0]
            
            with st.form("edit_epi"):
                st.markdown(f"##### ✏️ Editando: {sel}")
                en = st.text_input("Nome", it['nome']).upper()
                eca = st.text_input("C.A.", it['ca'])
                
                val_default = datetime.today()
                if it.get('validade'):
                    try:
                        val_default = datetime.strptime(it['validade'], '%Y-%m-%d')
                    except:
                        pass
                ev = st.date_input("Validade", val_default, format="DD/MM/YYYY")
                
                c1, c2 = st.columns(2)
                if c1.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                    supabase.table("ep").update({
                        "nome": en, 
                        "ca": eca, 
                        "validade": ev.strftime('%Y-%m-%d')
                    }).eq("id", int(it['id'])).execute()
                    st.success("✅ EPI Atualizado!")
                    st.cache_data.clear()
                    st.rerun()
                    
                if c2.form_submit_button("🗑️ Deletar", use_container_width=True):
                    try:
                        supabase.table("ep").delete().eq("id", int(it['id'])).execute()
                        st.warning("🗑️ EPI excluído.")
                        st.cache_data.clear()
                        st.rerun()
                    except: 
                        st.error("❌ Não é possível deletar um EPI com registros de entrega vinculados.")
            
            df_ep_view = df_ep.copy()
            if 'validade' in df_ep_view.columns:
                df_ep_view['validade'] = df_ep_view['validade'].apply(lambda x: format_br(x) if x else "")
            st.dataframe(df_ep_view[['nome', 'ca', 'validade']], use_container_width=True, hide_index=True)

# ----------------------------------------------------------------------------
# 6. 📄 FICHA INDIVIDUAL
# ----------------------------------------------------------------------------
elif menu == "📄 Ficha Individual":
    st.title("📄 Ficha Individual de Controle de EPI (NR-06)")
    
    df_f = load_data("oficiais", "nome")
    
    if not df_f.empty:
        sel = st.selectbox("Selecione o Colaborador", df_f['nome'])
        f_info = df_f[df_f['nome'] == sel].iloc[0]
        
        with st.container():
            st.markdown('<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 16px; margin-bottom: 20px;">', unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                if f_info.get('assinatura_url'):
                    st.image(f_info['assinatura_url'], width=150)
                else:
                    st.markdown("<div style='text-align:center; padding:20px; opacity:0.7;'>✍️ Sem assinatura</div>", unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"**{f_info['nome']}**")
                st.markdown(f"📋 Matrícula: {f_info['matricula']}")
                st.markdown(f"🏢 Setor: {f_info.get('setor', 'N/A')}")
                st.markdown(f"💼 Função: {f_info.get('funcao', 'N/A')}")
                st.markdown(f"📅 Admissão: {format_br(f_info.get('data_admissao'))}")
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        if f_info.get('assinatura_url'):
            st.success("✅ Assinatura Digital Master vinculada ao prontuário.")
        else:
            st.info("ℹ️ Este funcionário ainda não realizou assinatura eletrônica. A coleta será feita no primeiro link do WhatsApp.")
        
        st.write("---")
        termo_padrao = get_cfg("ficha_descricao", "Declaro que recebi os EPIs listados e fui orientado sobre o correto uso e conservacao.")
        texto_ficha = st.text_area("📝 Texto de Declaração / Termo de Responsabilidade", value=termo_padrao, height=100)
        
        if st.button("💾 Salvar Texto como Padrão", use_container_width=True):
            supabase.table("configuracoes").upsert(
                {"chave": "ficha_descricao", "valor": texto_ficha}, 
                on_conflict="chave"
            ).execute()
            st.success("✅ Texto atualizado na nuvem!")
            st.cache_data.clear()
            
        st.write("---")

        res = supabase.table("entregas").select("*, ep(*)").eq("id_func", int(f_info['id'])).order("data_entrega", desc=True).execute().data
        if res:
            df_h = pd.DataFrame([{
                "Data/Hora": format_br(h['data_entrega'], True), 
                "Qtd": h['quantidade'], 
                "EPI": h['ep']['nome'], 
                "C.A.": h['ep']['ca'], 
                "Token": h['token'], 
                "Status": h['status']
            } for h in res])
            
            if len(df_h) >= 20: 
                st.warning(f"⚠️ Alerta Fiscal: Ciclo de 20 itens atingido ({len(df_h)} retiradas). Recomendado fechar este ciclo.")
            
            st.dataframe(df_h, use_container_width=True, hide_index=True)
            headers = ["DATA/HORA", "QTD", "DESCRIÇÃO DO EPI", "C.A.", "TOKEN", "STATUS"]
            
            col_b1, col_b2 = st.columns(2)
            
            pdf_c = generate_pdf(
                "FICHA DE EPI - CICLO ATUAL (20 ITENS MAX)", 
                headers, 
                df_h.head(20).values.tolist(), 
                dict(f_info), 
                True, 
                custom_text=texto_ficha
            )
            if pdf_c: 
                col_b1.download_button(
                    "📥 CICLO ATUAL (20)", 
                    data=pdf_c, 
                    file_name=f"Ciclo_20_{sel}.pdf", 
                    mime="application/pdf", 
                    use_container_width=True
                )
            
            pdf_g = generate_pdf(
                "FICHA DE EPI - HISTORICO COMPLETO", 
                headers, 
                df_h.values.tolist(), 
                dict(f_info), 
                True, 
                custom_text=texto_ficha
            )
            if pdf_g: 
                col_b2.download_button(
                    "📥 HISTÓRICO COMPLETO", 
                    data=pdf_g, 
                    file_name=f"Ficha_Geral_{sel}.pdf", 
                    mime="application/pdf", 
                    use_container_width=True
                )
        else:
            st.info("ℹ️ Nenhum EPI foi fornecido a este colaborador ainda.")

# ----------------------------------------------------------------------------
# 7. 📈 BALANÇO SEMANAL
# ----------------------------------------------------------------------------
elif menu == "📈 Balanço Semanal":
    st.title("📈 Balanço Semanal de Consumo por Setores")
    
    res = supabase.table("entregas").select("*, oficiais(setor), ep(nome)").execute().data
    if res:
        sete_dias = datetime.now() - timedelta(days=7)
        list_s = []
        for h in res:
            try:
                dt_e = datetime.fromisoformat(h['data_entrega'].split('+')[0])
                if dt_e >= sete_dias:
                    list_s.append({
                        "Setor": h['oficiais']['setor'] if h['oficiais'] else "N/A", 
                        "EPI": h['ep']['nome'] if h['ep'] else "N/A", 
                        "Qtd": h['quantidade']
                    })
            except: 
                pass
        
        if list_s:
            st.success("✅ Movimentações detectadas nos últimos 7 dias.")
            df_s = pd.DataFrame(list_s).groupby(['Setor', 'EPI'])['Qtd'].sum().reset_index()
            
            st.dataframe(df_s, use_container_width=True, hide_index=True)
            
            pdf_s = generate_pdf(
                "RELATÓRIO DE CONSUMO SEMANAL POR SETOR", 
                ["SETOR", "TIPO DE EPI", "QUANTIDADE"], 
                df_s.values.tolist()
            )
            if pdf_s: 
                st.download_button(
                    "📥 BAIXAR BALANÇO SEMANAL (PDF)", 
                    data=pdf_s, 
                    file_name="Semanal_Setores.pdf", 
                    mime="application/pdf", 
                    use_container_width=True
                )
        else: 
            st.info("ℹ️ Nenhuma retirada de EPI nos últimos 7 dias.")

# ----------------------------------------------------------------------------
# 8. ⚙️ AJUSTES
# ----------------------------------------------------------------------------
elif menu == "⚙️ Ajustes":
    st.title("⚙️ Configurações Gerais do Sistema")
    
    st.subheader("🌐 Link de Produção")
    url = st.text_input("URL Pública do Aplicativo", get_cfg("url_sistema"), placeholder="https://seu-app.streamlit.app")
    if st.button("💾 Salvar URL", use_container_width=True):
        supabase.table("configuracoes").upsert(
            {"chave": "url_sistema", "valor": url}, 
            on_conflict="chave"
        ).execute()
        st.success("✅ URL sincronizada!")
        
    st.divider()
    
    st.subheader("🔑 Segurança Administrativa")
    nova_senha = st.text_input("Nova Senha", type="password", placeholder="••••••")
    confirma_senha = st.text_input("Confirme a Nova Senha", type="password", placeholder="••••••")
    
    if st.button("🔒 Gravar Nova Senha", use_container_width=True):
        if nova_senha:
            if nova_senha == confirma_senha:
                supabase.table("configuracoes").upsert(
                    {"chave": "app_password", "valor": nova_senha}, 
                    on_conflict="chave"
                ).execute()
                st.success("🔒 Senha atualizada!")
                logger.info("🔒 Senha de acesso alterada.")
            else:
                st.error("❌ As senhas não coincidem.")
        else:
            st.error("❌ O campo não pode estar vazio.")
