"""
🛡️ SESMT HUC - Sistema Digital de Gestão de EPI v7.0 (PRODUCTION READY - ULTRA REFINED)
Hospital Universitário do Ceará - Padrão Oficial ISGH
📱 Otimizado para Mobile | 🔒 Segurança Enterprise | ✨ UI Premium
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
# 🎨 ESTILOS CSS CUSTOMIZADOS E CONFIGURAÇÃO VISUAL
# ============================================================================

CUSTOM_CSS = """
<style>
    /* Cores corporativas */
    :root {
        --primary: #2d5a7b;
        --primary-dark: #1a3a52;
        --accent: #25D366;
        --danger: #e74c3c;
        --warning: #f39c12;
        --success: #27ae60;
        --bg-light: #f8f9fa;
        --text-dark: #2c3e50;
    }
    
    /* Layout geral */
    .main {
        max-width: 1400px;
        margin: 0 auto;
    }
    
    .stContainer {
        padding: 1rem;
    }
    
    /* Headers e títulos */
    h1 { color: var(--primary); font-weight: 700; letter-spacing: -0.5px; }
    h2 { color: var(--primary-dark); font-weight: 600; margin-top: 2rem; }
    h3 { color: var(--text-dark); font-weight: 600; }
    
    /* Cards customizados */
    .card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid var(--primary);
        transition: all 0.3s ease;
    }
    
    .card:hover {
        box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        transform: translateY(-2px);
    }
    
    .card-accent { border-left-color: var(--accent); }
    .card-danger { border-left-color: var(--danger); }
    .card-warning { border-left-color: var(--warning); }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 0.4rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }
    
    .badge-success { background: #d4edda; color: var(--success); }
    .badge-warning { background: #fff3cd; color: var(--warning); }
    .badge-danger { background: #f8d7da; color: var(--danger); }
    .badge-info { background: #d1ecf1; color: #0c5460; }
    
    /* Botões */
    .stButton > button {
        background: var(--primary);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
        padding: 0.75rem 1.5rem;
    }
    
    .stButton > button:hover {
        background: var(--primary-dark);
        box-shadow: 0 4px 12px rgba(45,90,123,0.3);
        transform: translateY(-2px);
    }
    
    .stButton > button[data-kind="secondary"] {
        background: var(--bg-light);
        color: var(--primary);
        border: 2px solid var(--primary);
    }
    
    /* Inputs e formulários */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select {
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        padding: 0.7rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus {
        border-color: var(--primary);
        box-shadow: 0 0 0 3px rgba(45,90,123,0.1);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        border-bottom: 2px solid #e0e0e0;
    }
    
    .stTabs [aria-selected="true"] {
        color: var(--primary);
        border-bottom: 3px solid var(--primary);
    }
    
    /* Dataframes */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* Alertas e mensagens */
    .stSuccess { background: #d4edda; padding: 1rem; border-radius: 8px; }
    .stError { background: #f8d7da; padding: 1rem; border-radius: 8px; }
    .stWarning { background: #fff3cd; padding: 1rem; border-radius: 8px; }
    .stInfo { background: #d1ecf1; padding: 1rem; border-radius: 8px; }
    
    /* Separadores */
    .stDivider { margin: 2rem 0 !important; }
    
    /* Sidebar */
    .stSidebar {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
    }
    
    .stSidebar [data-testid="stMarkdownContainer"] {
        color: white;
    }
    
    /* Métrica cards */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--primary);
        margin: 0.5rem 0;
    }
    
    .metric-label {
        font-size: 0.95rem;
        color: #666;
        font-weight: 500;
    }
    
    /* Animações */
    @keyframes slideIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .stContainer { animation: slideIn 0.3s ease-out; }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

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
    initial_sidebar_state="expanded"
)

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

HOSPITAL_NAME = "HOSPITAL UNIVERSITÁRIO DO CEARÁ"
HOSPITAL_ISGH = "ISGH - INSTITUTO DE SAÚDE E GESTÃO HOSPITALAR"
CNPJ_ENDERECO = "CNPJ: 05.268.526/0024-67 | AV DOUTOR SILAS MUNGUBA, 1700-ITAPERI | FORTALEZA/CE | CEP: 60.714-242"
STATUS_ENTREGA = {"PENDENTE": "Pendente ⏳", "CONFIRMADO": "Confirmado ✅"}

if 'carrinho_epi' not in st.session_state:
    st.session_state.carrinho_epi = []

# ============================================================================
# 🎨 COMPONENTES REUTILIZÁVEIS DE UI
# ============================================================================

def render_metric_card(label, value, icon="📊", color="primary"):
    """Renderiza um card de métrica padronizado"""
    color_map = {
        "primary": "#2d5a7b",
        "success": "#27ae60",
        "warning": "#f39c12",
        "danger": "#e74c3c"
    }
    col = st.container()
    col.markdown(f"""
    <div class="metric-card" style="border-top: 4px solid {color_map.get(color, color_map['primary'])};">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">{icon}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)

def render_badge(text, style="success"):
    """Renderiza um badge com estilo"""
    return f'<span class="badge badge-{style}">{text}</span>'

def render_card(title, content, icon="📌", style="primary"):
    """Renderiza um card com conteúdo customizado"""
    style_class = f"card card-{style}" if style != "primary" else "card"
    st.markdown(f"""
    <div class="{style_class}">
        <div style="font-size: 1.2rem; font-weight: 600; color: #2d5a7b;">
            {icon} {title}
        </div>
        <div style="margin-top: 1rem;">
            {content}
        </div>
    </div>
    """, unsafe_allow_html=True)

def section_divider(title=""):
    """Separador visual de seção"""
    st.markdown("---")
    if title:
        st.markdown(f"### {title}")

def status_badge(status):
    """Badge visual para status de entrega"""
    if "Confirmado" in status:
        return render_badge("✅ Confirmado", "success")
    elif "Pendente" in status:
        return render_badge("⏳ Pendente", "warning")
    else:
        return render_badge("⚠️ Desconhecido", "danger")

# ============================================================================
# 🛠️ UTILITÁRIOS E TRATAMENTO DE ERROS
# ============================================================================

def clean_str(text):
    if not text: return ""
    text_str = str(text).replace('✅', '!').replace('⏳', '...')
    return text_str.encode('latin-1', 'replace').decode('latin-1')

def format_br(date_str, include_time=False):
    if not date_str: return "N/A"
    try:
        d_str = str(date_str).strip()
        if len(d_str) >= 10 and d_str[2] == '/' and d_str[5] == '/': 
            return d_str[:16] if include_time else d_str[:10]
        
        clean_date = d_str.replace('Z', '').replace('/', '-').split('+')[0]
        if "T" in clean_date or " " in clean_date:
            clean_date = clean_date.replace('T', ' ')
            dt = datetime.strptime(clean_date.split('.')[0], '%Y-%m-%d %H:%M:%S')
            return dt.strftime('%d/%m/%Y %H:%M') if include_time else dt.strftime('%d/%m/%Y')
        else:
            dt = datetime.strptime(clean_date, '%Y-%m-%d')
            return dt.strftime('%d/%m/%Y')
    except:
        return str(date_str)

def extrair_erro_db(e):
    try:
        if hasattr(e, 'message'): return str(e.message)
        if hasattr(e, 'details'): return str(e.details)
        if isinstance(e, dict) and 'message' in e: return e['message']
        return str(e)
    except: return "Erro desconhecido de transação."

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
    st.markdown(f'<a href="{link}" target="_blank"><button style="background-color:#25D366;color:white;border:none;padding:12px;border-radius:8px;width:100%;cursor:pointer;font-weight:bold;font-size:0.95rem;">🚀 ENVIAR PARA WHATSAPP</button></a>', unsafe_allow_html=True)

# ============================================================================
# 📲 FLUXO DE CONFIRMAÇÃO COM WHATSAPP
# ============================================================================

if "confirmar" in st.query_params:
    tk = st.query_params["confirmar"]
    if tk:
        ent_res = supabase.table("entregas").select("*, oficiais(*)").eq("token", tk).execute()
        if ent_res.data:
            func = ent_res.data[0]['oficiais']
            
            st.markdown("""
            <div style="text-align: center; padding: 2rem 0;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">🛡️</div>
                <h1 style="color: #2d5a7b; margin-bottom: 0.5rem;">Confirmação Digital de EPI</h1>
                <p style="color: #666; font-size: 1.1rem;">SESMT HUC - Hospital Universitário do Ceará</p>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**👤 Colaborador:** {func['nome']}")
            with col2:
                st.markdown(f"**📋 Matrícula:** {func['matricula']}")
            
            st.divider()
            
            st.subheader("📦 Itens Recebidos Nesta Entrega")
            for e in ent_res.data:
                epi_res = supabase.table("ep").select("nome, ca").eq("id", e['id_epi']).execute()
                epi_nome = epi_res.data[0]['nome'] if epi_res.data else "EPI"
                epi_ca = epi_res.data[0].get('ca', 'N/A') if epi_res.data else "N/A"
                st.markdown(f"✓ **{e['quantidade']}x** {epi_nome} · **C.A:** {epi_ca}")
            
            st.divider()
            
            if not func.get('assinatura_url'):
                st.info("📝 **Primeira Assinatura Eletrônica**\nDesenhe sua assinatura abaixo para registro permanente em seu prontuário.")
                
                col_canvas, col_info = st.columns([2, 1])
                with col_canvas:
                    canvas_zap = st_canvas(
                        stroke_width=2, 
                        stroke_color="#2d5a7b", 
                        background_color="#f8f9fa", 
                        height=140, 
                        width=320, 
                        key="canvas_zap"
                    )
                with col_info:
                    st.markdown("""
                    <div style="padding: 1rem; background: #e8f4f8; border-radius: 8px;">
                        <h4>💡 Dicas</h4>
                        <ul style="margin: 0; padding-left: 1.2rem; font-size: 0.9rem;">
                            <li>Use caneta ou mouse</li>
                            <li>Assinatura clara</li>
                            <li>Evite borrados</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                
                if st.button("✍️ Gravar Assinatura e Confirmar", use_container_width=True, type="primary"):
                    if canvas_zap.image_data is not None:
                        try:
                            img = Image.fromarray(canvas_zap.image_data.astype('uint8'), 'RGBA')
                            buffered = BytesIO()
                            img.save(buffered, format="PNG")
                            
                            path = f"sig_{func['id']}_{int(time.time())}.png"
                            supabase.storage.from_("assinaturas").upload(path=path, file=buffered.getvalue(), file_options={"content-type": "image/png"})
                            url = supabase.storage.from_("assinaturas").get_public_url(path)
                            
                            supabase.table("oficiais").update({"assinatura_url": url}).eq("id", func['id']).execute()
                            supabase.table("entregas").update({"status": STATUS_ENTREGA["CONFIRMADO"]}).eq("token", tk).execute()
                            
                            st.balloons()
                            st.success("✅ **ASSINATURA REGISTRADA E PACOTE CONFIRMADO COM SUCESSO!**")
                            time.sleep(2)
                            st.query_params.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"⚠️ Erro: {extrair_erro_db(e)}")
                    else:
                        st.warning("⚠️ Desenhe sua assinatura antes de confirmar.")
            else:
                st.success("✨ **Sua assinatura digital está vinculada ao prontuário.**")
                st.image(func['assinatura_url'], width=200)
                
                if st.button("👍 Confirmar Recebimento", use_container_width=True, type="primary"):
                    supabase.table("entregas").update({"status": STATUS_ENTREGA["CONFIRMADO"]}).eq("token", tk).execute()
                    st.balloons()
                    st.success("🛡️ **RECEBIMENTO VALIDADO COM SUCESSO!**")
                    time.sleep(2)
                    st.query_params.clear()
                    st.rerun()
        else:
            st.error("❌ Token inválido ou link de confirmação expirado.")
    st.stop()

# ============================================================================
# 📄 GERADOR DE PDF PROFISSIONAL
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
        pdf.ln(5)
        
        pdf.set_fill_color(45, 90, 123)
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
            pdf.cell(0, 8, clean_str(f"DATA DE ADMISSÃO: {format_br(func_info.get('data_admissao', 'N/A'))}"), border=1, ln=1)
            pdf.ln(5)

        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Arial", 'B', 8)
        
        col_widths = [30, 12, 75, 20, 22, 25, 0] if is_ficha else [80, 110, 0]
        
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 8, clean_str(h), border=1, align='C', fill=True)
        pdf.ln()
        
        pdf.set_font("Arial", '', 8)
        for row in data_rows:
            for i, val in enumerate(row):
                pdf.cell(col_widths[i], 8, clean_str(str(val)), border=1, ln=(1 if i == len(row)-1 else 0), align=('L' if i==2 and is_ficha else 'C'))
            
        if is_ficha:
            pdf.ln(10)
            pdf.set_font("Arial", 'I', 8)
            texto_render = custom_text if custom_text else get_cfg("ficha_descricao", "Declaro que recebi os EPIs listados e fui orientado sobre o correto uso e conservacao.")
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
# 🔐 AUTENTICAÇÃO
# ============================================================================

if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.markdown("""
    <div style="text-align: center; padding: 3rem 0;">
        <div style="font-size: 4rem; margin-bottom: 1rem;">🛡️</div>
        <h1 style="color: #2d5a7b; font-size: 2.5rem; margin-bottom: 0.5rem;">SESMT HUC</h1>
        <p style="color: #666; font-size: 1.1rem; margin-bottom: 2rem;">Sistema Digital de Gestão de EPI</p>
        <p style="color: #999; font-size: 0.9rem;">Hospital Universitário do Ceará</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔑 Acesso Restrito")
        pw = st.text_input("Senha Administrativa", type="password", key="pw_login")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🔓 Entrar", use_container_width=True, type="primary"):
                if pw == os.getenv("SESMT_PASSWORD", get_cfg("app_password", "1234")):
                    st.session_state.logado = True
                    st.rerun()
                else:
                    st.error("❌ Senha incorreta. Tente novamente.")
    st.stop()

# ============================================================================
# 📌 MENU PRINCIPAL
# ============================================================================

with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 1.5rem 0; border-bottom: 2px solid rgba(255,255,255,0.2);">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🛡️</div>
        <h2 style="color: white; margin: 0; font-size: 1.2rem;">SESMT HUC</h2>
        <p style="color: rgba(255,255,255,0.8); margin: 0.3rem 0 0 0; font-size: 0.85rem;">Hospital Universitário do Ceará</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    menu = st.radio(
        "📋 NAVEGAÇÃO",
        [
            "📊 Painel",
            "🚀 Registrar Entrega",
            "👥 Colaboradores",
            "🎖️ Funções",
            "📦 Catálogo EPI",
            "📄 Ficha Individual",
            "📈 Balanço Semanal",
            "⚙️ Ajustes"
        ],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    if st.button("🚪 Sair do Sistema", use_container_width=True):
        st.session_state.logado = False
        st.rerun()

# ============================================================================
# 1. 📊 PAINEL PRINCIPAL
# ============================================================================

if menu == "📊 Painel":
    st.markdown("""
    <h1 style="color: #2d5a7b; margin-bottom: 2rem;">
        📊 Indicadores e Controles Operacionais
    </h1>
    """, unsafe_allow_html=True)
    
    df_f, df_e = load_data("oficiais"), load_data("entregas")
    
    col1, col2, col3 = st.columns(3, gap="large")
    
    with col1:
        render_metric_card("Total de Colaboradores", len(df_f), "👥", "primary")
    with col2:
        render_metric_card("Entregas Realizadas", len(df_e), "📦", "success")
    with col3:
        pendentes = df_e[df_e['status'].str.contains("Pendente", na=False)] if not df_e.empty else pd.DataFrame()
        tokens_pendentes = pendentes['token'].nunique() if not pendentes.empty else 0
        render_metric_card("Lotes Pendentes", tokens_pendentes, "⏳", "warning")
    
    st.divider()
    
    st.subheader("📲 Pendências de Confirmação")
    
    if not pendentes.empty:
        for tk_pendente, df_tk in pendentes.groupby('token'):
            f_id = df_tk.iloc[0]['id_func']
            f_res = supabase.table("oficiais").select("nome, whatsapp").eq("id", int(f_id)).execute()
            
            if f_res.data:
                f = f_res.data[0]
                
                nomes_epis = []
                for _, row_tk in df_tk.iterrows():
                    epi_res = supabase.table("ep").select("nome").eq("id", int(row_tk['id_epi'])).execute()
                    epi_nome = epi_res.data[0]['nome'] if epi_res.data else "EPI"
                    nomes_epis.append(f"{row_tk['quantidade']}x {epi_nome}")
                
                itens_str = ", ".join(nomes_epis)
                
                with st.container():
                    col1, col2, col3 = st.columns([2, 2, 1], gap="small")
                    
                    with col1:
                        st.markdown(f"**{f['nome']}**")
                        st.caption(f"Matrícula: (em registros)")
                    
                    with col2:
                        st.markdown(f"📦 {itens_str}")
                        st.caption(f"Token: `{tk_pendente}`")
                    
                    with col3:
                        link = f"{get_cfg('url_sistema')}/?confirmar={tk_pendente}"
                        msg = f"🛡️ *SESMT HUC*\nOlá *{f['nome']}*,\nVocê possui um pacote de EPIs pendente de confirmação: *{itens_str}*. Acesse o link seguro para assinar digitalmente: {link}"
                        abrir_whatsapp(f['whatsapp'], msg)
                    
                    st.divider()
    else:
        st.success("✅ Nenhuma assinatura pendente no momento!")

# ============================================================================
# 2. 🚀 REGISTRAR ENTREGA
# ============================================================================

elif menu == "🚀 Registrar Entrega":
    st.markdown("""
    <h1 style="color: #2d5a7b; margin-bottom: 2rem;">
        🚀 Registrar Lote de Entrega
    </h1>
    """, unsafe_allow_html=True)
    
    df_f = load_data("oficiais", "nome")
    df_ep = load_data("ep", "nome")
    
    if df_f.empty or df_ep.empty:
        st.warning("⚠️ É necessário cadastrar Colaboradores e EPIs antes de uma entrega.")
    else:
        df_ep['nome_display'] = df_ep['nome'] + " (C.A: " + df_ep['ca'].fillna("N/A").astype(str) + ")"
        
        st.markdown("### 1️⃣ Selecionar Colaborador")
        f_selecionado = st.selectbox(
            "Busque a matrícula ou nome",
            df_f['matricula'] + " - " + df_f['nome'],
            label_visibility="collapsed"
        )
        
        st.divider()
        
        st.markdown("### 2️⃣ Adicionar EPIs ao Pacote")
        colA, colB, colC = st.columns([3, 1, 1])
        
        with colA:
            e_display = st.selectbox(
                "Selecione o EPI",
                df_ep['nome_display'],
                label_visibility="collapsed"
            )
        with colB:
            q = st.number_input("Qtd", min_value=1, value=1, label_visibility="collapsed")
        with colC:
            st.write("")
            st.write("")
            if st.button("➕ Adicionar", use_container_width=True):
                re = df_ep[df_ep['nome_display'] == e_display].iloc[0]
                hoje = datetime.today().date()
                ca_venc = False
                
                if pd.notna(re['validade']):
                    try:
                        if datetime.strptime(str(re['validade']), '%Y-%m-%d').date() < hoje:
                            ca_venc = True
                    except: pass
                
                st.session_state.carrinho_epi.append({
                    "id_epi": int(re['id']),
                    "nome_display": e_display,
                    "nome_puro": re['nome'],
                    "qtd": q,
                    "vencido": ca_venc
                })
                st.rerun()
        
        st.divider()
        
        if st.session_state.carrinho_epi:
            st.markdown(f"### 🛒 Lista de Entrega ({len(st.session_state.carrinho_epi)} itens)")
            
            for i, item in enumerate(st.session_state.carrinho_epi):
                alerta = "🔴 (C.A. Vencido)" if item['vencido'] else "✅"
                
                col1, col2, col3 = st.columns([4, 1, 1])
                with col1:
                    st.markdown(f"**{item['nome_display']}** {alerta}")
                with col2:
                    st.markdown(f"**{item['qtd']}x**")
                with col3:
                    if st.button("🗑️", key=f"del_epi_{i}", use_container_width=True):
                        st.session_state.carrinho_epi.pop(i)
                        st.rerun()
            
            st.write("")
            if st.button(f"🚀 FECHAR PACOTE ({len(st.session_state.carrinho_epi)} ITENS)", type="primary", use_container_width=True):
                rf = df_f[df_f['matricula'] + " - " + df_f['nome'] == f_selecionado].iloc[0]
                tk = str(int(time.time()))[-6:]
                
                nomes_msg = []
                try:
                    for epi_item in st.session_state.carrinho_epi:
                        supabase.table("entregas").insert({
                            "id_func": int(rf['id']),
                            "id_epi": epi_item["id_epi"],
                            "token": tk,
                            "quantidade": epi_item["qtd"],
                            "status": STATUS_ENTREGA["PENDENTE"]
                        }).execute()
                        nomes_msg.append(f"{epi_item['qtd']}x {epi_item['nome_puro']}")
                    
                    st.session_state.carrinho_epi = []
                    st.success(f"✅ Pacote registrado! Token: `{tk}`")
                    
                    link = f"{get_cfg('url_sistema')}/?confirmar={tk}"
                    itens_txt = ", ".join(nomes_msg)
                    msg = f"🛡️ *SESMT HUC*\nOlá *{rf['nome']}*,\nConfirme o recebimento:\n*{itens_txt}*\n\nLink seguro: {link}"
                    abrir_whatsapp(rf['whatsapp'], msg)
                    
                except Exception as e_db:
                    st.error(f"⚠️ Erro: {extrair_erro_db(e_db)}")
        else:
            st.info("ℹ️ Nenhum EPI adicionado à lista ainda.")

# ============================================================================
# 3. 👥 COLABORADORES
# ============================================================================

elif menu == "👥 Colaboradores":
    st.markdown("""
    <h1 style="color: #2d5a7b; margin-bottom: 2rem;">
        👥 Gestão de Colaboradores
    </h1>
    """, unsafe_allow_html=True)
    
    df_funcoes = load_data("funcoes", "nome")
    
    if df_funcoes.empty:
        st.error("⚠️ Cadastre 'Funções/Cargos' antes de adicionar colaboradores.")
    else:
        tab1, tab2, tab3 = st.tabs(["➕ Novo", "🔄 Gerenciar", "📋 Listar"])
        
        with tab1:
            st.subheader("Cadastrar Novo Colaborador")
            with st.form("cad_col"):
                n = st.text_input("Nome Completo").upper()
                m = st.text_input("Matrícula")
                da = st.date_input("Data de Admissão", format="DD/MM/YYYY")
                s = st.selectbox("Setor", ["CME", "SESMT", "UTI", "MANUTENÇÃO", "CENTRO CIRÚRGICO", "EMERGÊNCIA", "PEDIATRIA", "ADMINISTRATIVO"])
                f = st.selectbox("Função", df_funcoes['nome'].tolist())
                z = st.text_input("WhatsApp (DDD + Número)")
                
                col_submit, col_cancel = st.columns(2)
                with col_submit:
                    if st.form_submit_button("💾 Salvar", use_container_width=True):
                        if n and m and z:
                            try:
                                supabase.table("oficiais").insert({
                                    "nome": n,
                                    "matricula": m,
                                    "data_admissao": str(da),
                                    "setor": s,
                                    "funcao": f,
                                    "whatsapp": z
                                }).execute()
                                st.success("✅ Colaborador cadastrado!")
                                st.cache_data.clear()
                            except Exception as e_db:
                                st.error(f"⚠️ Erro: {extrair_erro_db(e_db)}")
                        else:
                            st.error("⚠️ Preencha todos os campos obrigatórios.")
        
        with tab2:
            st.subheader("Gerenciar Colaborador")
            df_oficiais = load_data("oficiais", "nome")
            
            if not df_oficiais.empty:
                sel_excluir = st.selectbox("Selecione para excluir", df_oficiais['nome'], key="sel_excluir_tab2")
                func_del = df_oficiais[df_oficiais['nome'] == sel_excluir].iloc[0]
                
                st.warning(f"⚠️ Você selecionou: **{func_del['nome']}**")
                
                res_del = supabase.table("entregas").select("*, ep(*)").eq("id_func", int(func_del['id'])).execute().data
                
                if res_del:
                    st.info("💡 Baixar histórico antes de excluir")
                    df_h_del = pd.DataFrame([{
                        "Data": format_br(h['data_entrega'], True),
                        "Qtd": h['quantidade'],
                        "EPI": h['ep']['nome'],
                        "C.A.": h['ep']['ca'],
                        "Token": h['token'],
                        "Status": h['status']
                    } for h in res_del])
                    
                    pdf_backup = generate_pdf(
                        f"BACKUP - {sel_excluir}",
                        ["Data", "Qtd", "EPI", "C.A.", "Token", "Status"],
                        df_h_del.values.tolist(),
                        dict(func_del),
                        True
                    )
                    if pdf_backup:
                        st.download_button("📥 Baixar Backup", data=pdf_backup, file_name=f"Backup_{sel_excluir}.pdf", mime="application/pdf", use_container_width=True)
                
                if st.button("🗑️ Excluir Definitivamente", type="primary", use_container_width=True):
                    try:
                        supabase.table("entregas").delete().eq("id_func", int(func_del['id'])).execute()
                        supabase.table("oficiais").delete().eq("id", int(func_del['id'])).execute()
                        st.success(f"✅ {func_del['nome']} removido com sucesso.")
                        st.cache_data.clear()
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"⚠️ Erro: {extrair_erro_db(e)}")
        
        with tab3:
            st.subheader("Lista de Colaboradores")
            df_oficiais = load_data("oficiais", "nome")
            
            if not df_oficiais.empty:
                df_view = df_oficiais.copy()
                df_view['Admissão'] = df_view['data_admissao'].apply(format_br)
                st.dataframe(df_view[['nome', 'matricula', 'Admissão', 'setor', 'funcao']], use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum colaborador cadastrado.")

# ============================================================================
# 4. 🎖️ FUNÇÕES
# ============================================================================

elif menu == "🎖️ Funções":
    st.markdown("""
    <h1 style="color: #2d5a7b; margin-bottom: 2rem;">
        🎖️ Cadastro de Funções e Cargos
    </h1>
    """, unsafe_allow_html=True)
    
    with st.form("add_f"):
        nf = st.text_input("Nome da Função (Ex: TÉCNICO DE ENFERMAGEM)").upper()
        if st.form_submit_button("➕ Adicionar", use_container_width=True):
            if nf:
                try:
                    supabase.table("funcoes").insert({"nome": nf}).execute()
                    st.success(f"✅ '{nf}' adicionada!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"⚠️ Erro: {extrair_erro_db(e)}")
    
    st.divider()
    st.subheader("Funções Cadastradas")
    df_f = load_data("funcoes", "nome")
    if not df_f.empty:
        st.dataframe(df_f[['nome']], use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma função cadastrada.")

# ============================================================================
# 5. 📦 CATÁLOGO EPI
# ============================================================================

elif menu == "📦 Catálogo EPI":
    st.markdown("""
    <h1 style="color: #2d5a7b; margin-bottom: 2rem;">
        📦 Catálogo de Equipamentos de Proteção
    </h1>
    """, unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["➕ Novo EPI", "🛠️ Gerenciar"])
    
    with t1:
        st.subheader("Adicionar Novo EPI")
        with st.form("new_epi"):
            n = st.text_input("Nome Técnico").upper()
            ca = st.text_input("Número do C.A.")
            v = st.date_input("Data de Validade", format="DD/MM/YYYY")
            
            if st.form_submit_button("💾 Salvar no Catálogo", use_container_width=True):
                if n and ca:
                    try:
                        supabase.table("ep").insert({
                            "nome": n,
                            "ca": ca,
                            "validade": str(v)
                        }).execute()
                        st.success("✅ EPI integrado ao catálogo!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"⚠️ Erro: {extrair_erro_db(e)}")
                else:
                    st.error("⚠️ Preencha todos os campos.")
    
    with t2:
        st.subheader("Gerenciar Catálogo")
        df_ep = load_data("ep", "nome")
        
        if not df_ep.empty:
            df_ep['nome_display'] = df_ep['nome'] + " (C.A: " + df_ep['ca'].fillna("N/A").astype(str) + ")"
            sel = st.selectbox("Selecione para editar", df_ep['nome_display'])
            it = df_ep[df_ep['nome_display'] == sel].iloc[0]
            
            with st.form("edit_epi"):
                en = st.text_input("Nome", it['nome']).upper()
                eca = st.text_input("C.A.", it['ca'])
                ev = st.date_input("Validade", datetime.strptime(it['validade'], '%Y-%m-%d') if it['validade'] else datetime.today(), format="DD/MM/YYYY")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                        try:
                            supabase.table("ep").update({
                                "nome": en,
                                "ca": eca,
                                "validade": str(ev)
                            }).eq("id", int(it['id'])).execute()
                            st.success("✅ Atualizado!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"⚠️ Erro: {extrair_erro_db(e)}")
                
                with col2:
                    if st.form_submit_button("🗑️ Deletar", use_container_width=True):
                        try:
                            supabase.table("ep").delete().eq("id", int(it['id'])).execute()
                            st.success("✅ Excluído!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"⚠️ Erro: {extrair_erro_db(e)}")
            
            st.divider()
            st.subheader("Visão Geral do Catálogo")
            
            df_view = df_ep.copy()
            hoje = datetime.today().date()
            
            def status_ca(data_str):
                if not data_str or pd.isna(data_str):
                    return "⚠️ S/ Info"
                try:
                    dt = datetime.strptime(str(data_str).split(" ")[0], '%Y-%m-%d').date()
                    return "✅ Ativo" if dt >= hoje else "🔴 Vencido"
                except:
                    return "❌ Erro"
            
            df_view['Status'] = df_view['validade'].apply(status_ca)
            df_view['Validade'] = df_view['validade'].apply(lambda x: format_br(x) if x else "")
            
            st.dataframe(df_view[['nome', 'ca', 'Validade', 'Status']], use_container_width=True, hide_index=True)

# ============================================================================
# 6. 📄 FICHA INDIVIDUAL
# ============================================================================

elif menu == "📄 Ficha Individual":
    st.markdown("""
    <h1 style="color: #2d5a7b; margin-bottom: 2rem;">
        📄 Ficha Individual de Controle de EPI (NR-06)
    </h1>
    """, unsafe_allow_html=True)
    
    df_f = load_data("oficiais", "nome")
    
    if not df_f.empty:
        sel = st.selectbox("Selecione o Colaborador", df_f['nome'])
        f_info = df_f[df_f['nome'] == sel].iloc[0]
        
        col1, col2 = st.columns(2)
        with col1:
            if f_info.get('assinatura_url'):
                st.success("✅ Assinatura Digital Master vinculada")
                st.image(f_info['assinatura_url'], width=150)
            else:
                st.info("ℹ️ Sem assinatura eletrônica ainda")
        
        with col2:
            st.markdown(f"**Colaborador:** {f_info['nome']}")
            st.markdown(f"**Matrícula:** {f_info['matricula']}")
            st.markdown(f"**Setor:** {f_info['setor']}")
            st.markdown(f"**Admissão:** {format_br(f_info.get('data_admissao'))}")
        
        st.divider()
        
        termo_padrao = get_cfg("ficha_descricao", "Declaro que recebi os EPIs listados e fui orientado sobre o correto uso e conservacao.")
        texto_ficha = st.text_area("📝 Texto de Declaração", value=termo_padrao, height=80)
        
        if st.button("💾 Salvar como Padrão", use_container_width=True):
            try:
                supabase.table("configuracoes").upsert(
                    {"chave": "ficha_descricao", "valor": texto_ficha},
                    on_conflict="chave"
                ).execute()
                st.success("✅ Texto atualizado!")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"⚠️ Erro: {extrair_erro_db(e)}")
        
        st.divider()
        
        res = supabase.table("entregas").select("*, ep(*)").eq("id_func", int(f_info['id'])).order("data_entrega", desc=True).execute().data
        
        if res:
            df_h = pd.DataFrame([{
                "Data": format_br(h['data_entrega'], True),
                "Qtd": h['quantidade'],
                "EPI": h['ep']['nome'] if h.get('ep') else "N/A",
                "C.A.": h['ep']['ca'] if h.get('ep') else "N/A",
                "Validade": format_br(h['ep'].get('validade', 'N/A')) if h.get('ep') else "N/A",
                "Token": h['token'],
                "Status": h['status']
            } for h in res])
            
            st.subheader(f"📋 Histórico ({len(df_h)} entregas)")
            
            if len(df_h) >= 20:
                st.warning(f"⚠️ **Alerta:** {len(df_h)} itens. Considere fechar este ciclo.")
            
            st.dataframe(df_h, use_container_width=True, hide_index=True)
            
            headers = ["Data", "Qtd", "EPI", "C.A.", "Validade", "Token", "Status"]
            
            col_b1, col_b2 = st.columns(2)
            
            pdf_c = generate_pdf(
                "FICHA CICLO ATUAL",
                headers,
                df_h.head(20).values.tolist(),
                dict(f_info),
                True,
                custom_text=texto_ficha
            )
            if pdf_c:
                col_b1.download_button("📥 Ciclo (20 últimos)", data=pdf_c, file_name=f"Ciclo_{sel}.pdf", mime="application/pdf", use_container_width=True)
            
            pdf_g = generate_pdf(
                "FICHA HISTÓRICO COMPLETO",
                headers,
                df_h.values.tolist(),
                dict(f_info),
                True,
                custom_text=texto_ficha
            )
            if pdf_g:
                col_b2.download_button("📥 Histórico Completo", data=pdf_g, file_name=f"Historico_{sel}.pdf", mime="application/pdf", use_container_width=True)
        else:
            st.info("Nenhuma entrega registrada ainda.")

# ============================================================================
# 7. 📈 BALANÇO SEMANAL
# ============================================================================

elif menu == "📈 Balanço Semanal":
    st.markdown("""
    <h1 style="color: #2d5a7b; margin-bottom: 2rem;">
        📈 Balanço Semanal de Consumo
    </h1>
    """, unsafe_allow_html=True)
    
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
            st.success("✅ Movimentações detectadas")
            df_s = pd.DataFrame(list_s).groupby(['Setor', 'EPI'])['Qtd'].sum().reset_index()
            st.dataframe(df_s, use_container_width=True, hide_index=True)
            
            pdf_s = generate_pdf(
                "RELATÓRIO SEMANAL POR SETOR",
                ["SETOR", "TIPO DE EPI", "QUANTIDADE"],
                df_s.values.tolist()
            )
            if pdf_s:
                st.download_button("📥 Baixar Balanço", data=pdf_s, file_name="Semanal_Setores.pdf", mime="application/pdf", use_container_width=True)
        else:
            st.info("Nenhuma movimentação nos últimos 7 dias.")
    else:
        st.info("Sem dados disponíveis.")

# ============================================================================
# 8. ⚙️ AJUSTES E CONFIGURAÇÕES
# ============================================================================

elif menu == "⚙️ Ajustes":
    st.markdown("""
    <h1 style="color: #2d5a7b; margin-bottom: 2rem;">
        ⚙️ Configurações do Sistema
    </h1>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🌐 URL do Sistema", "🔑 Segurança"])
    
    with tab1:
        st.subheader("Link de Acesso Público")
        url = st.text_input("URL (ex: https://seu-app.streamlit.app)", get_cfg("url_sistema"), label_visibility="collapsed")
        
        if st.button("💾 Salvar URL", use_container_width=True):
            try:
                supabase.table("configuracoes").upsert(
                    {"chave": "url_sistema", "valor": url},
                    on_conflict="chave"
                ).execute()
                st.success("✅ URL sincronizada!")
            except Exception as e:
                st.error(f"⚠️ Erro: {extrair_erro_db(e)}")
    
    with tab2:
        st.subheader("Alterar Senha de Acesso")
        st.warning("⚠️ Esta ação afeta todos os usuários do sistema")
        
        nova_senha = st.text_input("Nova Senha", type="password")
        confirma_senha = st.text_input("Confirme", type="password")
        
        if st.button("🔒 Gravar Nova Senha", use_container_width=True, type="primary"):
            if nova_senha:
                if nova_senha == confirma_senha:
                    try:
                        supabase.table("configuracoes").upsert(
                            {"chave": "app_password", "valor": nova_senha},
                            on_conflict="chave"
                        ).execute()
                        st.success("🔒 Senha atualizada com sucesso!")
                        logger.info("Senha alterada")
                    except Exception as e:
                        st.error(f"⚠️ Erro: {extrair_erro_db(e)}")
                else:
                    st.error("❌ As senhas não coincidem.")
            else:
                st.error("❌ Digite uma senha.")
