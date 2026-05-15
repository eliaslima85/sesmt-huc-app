"""
🛡️ SESMT HUC - Sistema Digital de Gestão de EPI v3.0 PROFISSIONAL
Hospital Universitário do Ceará
"""

import logging
import time
import hashlib
import urllib.parse
import base64
import requests
from datetime import datetime, timedelta
from io import BytesIO

import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
from supabase import create_client, Client

# ============================================================================
# CONFIGURAÇÕES E CONEXÃO
# ============================================================================

logging.basicConfig(level=logging.INFO)
st.set_page_config(page_title="SESMT HUC - Digital", layout="wide", page_icon="🛡️")

# Credenciais Supabase
SUPABASE_URL = "https://aatkjhtrafuepwzzlrbm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFhdGtqaHRyYWZ1ZXB3enpscmJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg2Mjg5MTYsImV4cCI6MjA5NDIwNDkxNn0.65izu7Zhc3kUZrVIRXGvVQ5o-Lhk-7PCK9CMg4zIwuk"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("Erro crítico de conexão com o banco de dados.")
    st.stop()

# Padrão Visual HUC
HOSPITAL_NAME = "HOSPITAL UNIVERSITÁRIO DO CEARÁ"
HOSPITAL_SUB = "ISGH | GOVERNO DO ESTADO DO CEARÁ"
RODAPE_OFICIAL = "CNPJ: 05.268.526/0024-67 | AV DOUTOR SILAS MUNGUBA, 1700-ITAPERI | FORTALEZA/CE | CEP: 60.714-242"
STATUS_ENTREGA = {
    "PENDENTE": "Pendente ⏳",
    "CONFIRMADO": "Confirmado ✅",
    "DEVOLVIDO": "Devolvido ↩️",
    "DANIFICADO": "Danificado ⚠️"
}

# ============================================================================
# UTILITÁRIOS E SEGURANÇA
# ============================================================================

def hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode()).hexdigest()

def verificar_senha(senha_input: str, hash_armazenado: str) -> bool:
    return hash_senha(senha_input) == hash_armazenado

def format_br(date_str, include_time=False):
    if not date_str: return "N/A"
    try:
        clean_date = str(date_str).replace('Z', '').split('+')[0]
        dt = datetime.fromisoformat(clean_date)
        return dt.strftime('%d/%m/%Y %H:%M') if include_time else dt.strftime('%d/%m/%Y')
    except: return str(date_str)

def clean_str(text):
    """Limpa strings e emojis para compatibilidade com PDF Latin-1"""
    if not text: return ""
    text_str = str(text).replace('✅', '!').replace('⏳', '...').replace('↩️', '(D)').replace('⚠️', '(X)')
    import unicodedata
    nfd = unicodedata.normalize('NFD', text_str)
    return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn').encode('latin-1', 'replace').decode('latin-1')

def mask_whatsapp(num):
    n = str(num).replace("+", "").replace(" ", "").replace("-", "")
    if len(n) == 11:
        return f"({n[:2]}) {n[2:7]}-{n[7:11]}"
    return n

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
# WHATSAPP E AUDITORIA
# ============================================================================

def registrar_auditoria(acao, tabela, registro_id=None, detalhes=""):
    try:
        usuario = st.session_state.get("usuario_logado", "ADMIN")
        supabase.table("auditoria").insert({
            "usuario": usuario, "acao": acao, "tabela": tabela,
            "registro_id": str(registro_id), "detalhes": detalhes
        }).execute()
    except: pass

def enviar_whatsapp(numero, mensagem):
    provedor = get_cfg("whatsapp_provedor", "desativado")
    apikey = get_cfg("whatsapp_callmebot_apikey", "")
    if provedor == "callmebot" and apikey:
        num = str(numero).replace("(", "").replace(")", "").replace("-", "").replace(" ", "")
        if not num.startswith("55"): num = "55" + num
        url = f"https://api.callmebot.com/whatsapp.php?phone={num}&text={urllib.parse.quote(mensagem)}&apikey={apikey}"
        try:
            r = requests.get(url, timeout=10)
            return r.status_code == 200
        except: return False
    return False

# ============================================================================
# PROCESSAMENTO DE CONFIRMAÇÃO (LINK DO ZAP)
# ============================================================================

if "confirmar" in st.query_params:
    tk = st.query_params["confirmar"]
    if tk:
        res = supabase.table("entregas").update({"status": STATUS_ENTREGA["CONFIRMADO"]}).eq("token", tk).execute()
        if res.data:
            st.balloons()
            st.success("🛡️ RECEBIMENTO CONFIRMADO!")
            registrar_auditoria("CONFIRMACAO_LINK", "entregas", res.data[0]['id'], f"Token: {tk}")
            if st.button("Ir para o Sistema"):
                st.query_params.clear()
                st.rerun()
        else: st.error("Link expirado ou inválido.")
    st.stop()

# ============================================================================
# GERADOR DE PDF PROFISSIONAL
# ============================================================================

def generate_pdf_ficha(func, hist_df, assinatura_url=None):
    from fpdf import FPDF
    try:
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        
        # Cabeçalho Oficial
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, clean_str(HOSPITAL_NAME), border=0, ln=1, align='C')
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 5, clean_str(HOSPITAL_SUB), border=0, ln=1, align='C')
        pdf.ln(8)
        
        # Título Black Bar
        pdf.set_fill_color(40, 40, 40); pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 10, clean_str("FICHA INDIVIDUAL DE CONTROLE DE EQUIPAMENTO DE PROTEÇÃO INDIVIDUAL - NR-6"), border=0, ln=1, fill=True, align='C')
        pdf.ln(4)
        
        # Dados do Colaborador
        pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 9)
        pdf.cell(140, 7, clean_str(f"COLABORADOR: {func['nome']}"), border=1)
        pdf.cell(0, 7, clean_str(f"MATRÍCULA: {func['matricula']}"), border=1, ln=1)
        pdf.cell(90, 7, clean_str(f"SETOR: {func['setor']}"), border=1)
        pdf.cell(90, 7, clean_str(f"FUNÇÃO: {func.get('funcao', 'N/A')}"), border=1)
        pdf.cell(0, 7, clean_str(f"VÍNCULO: {func.get('vinculo', 'ISGH')}"), border=1, ln=1)
        pdf.ln(5)
        
        # Tabela (Cabeçalho)
        pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", 'B', 8)
        pdf.cell(35, 8, clean_str("DATA/HORA"), border=1, align='C', fill=True)
        pdf.cell(15, 8, clean_str("QTD"), border=1, align='C', fill=True)
        pdf.cell(90, 8, clean_str("DESCRIÇÃO DO EPI"), border=1, align='C', fill=True)
        pdf.cell(25, 8, clean_str("C.A."), border=1, align='C', fill=True)
        pdf.cell(30, 8, clean_str("VAL. C.A."), border=1, align='C', fill=True)
        pdf.cell(30, 8, clean_str("TOKEN"), border=1, align='C', fill=True)
        pdf.cell(0, 8, clean_str("STATUS"), border=1, ln=1, align='C', fill=True)
        
        # Dados
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
        pdf.ln(8); pdf.set_font("Arial", 'I', 8)
        termo = get_cfg("ficha_template", "Recebi os EPIs listados e fui orientado sobre o uso.")
        pdf.multi_cell(0, 4, clean_str(termo))
        
        if assinatura_url:
            try:
                r = requests.get(assinatura_url, timeout=5)
                img = Image.open(BytesIO(r.content)).convert("RGB")
                img.save("temp_sig.jpg")
                pdf.image("temp_sig.jpg", x=20, y=pdf.get_y()+2, w=40)
            except: pass

        pdf.set_y(-15)
        pdf.set_font("Arial", '', 7)
        pdf.cell(0, 5, clean_str(RODAPE_OFICIAL), border=0, ln=0, align='C')
        
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        st.error(f"Erro PDF: {e}")
        return None

# ============================================================================
# LOGIN E INTERFACE
# ============================================================================

if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛡️ SESMT HUC</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        pw = st.text_input("Senha Admin", type="password")
        if st.button("Acessar", use_container_width=True):
            if pw == get_cfg("app_password", "1234"):
                st.session_state.logado = True
                st.session_state.usuario_logado = "ADMIN"
                st.rerun()
            else: st.error("Acesso Negado.")
    st.stop()

menu = st.sidebar.radio("SESMT", ["📊 Painel", "🚀 Entregar EPI", "👥 Colaboradores", "📦 Catálogo EPI", "🎖️ Funções", "📄 Ficha Individual", "⚙️ Ajustes"])
if st.sidebar.button("Sair"): st.session_state.logado = False; st.rerun()

# ----------------------------------------------------------------------------
# 👥 COLABORADORES
# ----------------------------------------------------------------------------
if menu == "👥 Colaboradores":
    st.title("👥 Gestão de Colaboradores")
    t1, t2 = st.tabs(["➕ Novo Colaborador", "🔍 Consultar Lista"])
    
    with t1:
        with st.form("f_add", clear_on_submit=True):
            n, m = st.text_input("Nome Completo").upper(), st.text_input("Matrícula")
            s = st.selectbox("Setor", [x['nome'] for x in load_data("setores").to_dict('records')] or ["SESMT"])
            f_list = load_data("funcoes")
            func = st.selectbox("Função / Cargo", f_list['nome'].tolist() if not f_list.empty else ["TÉCNICO"])
            z = st.text_input("WhatsApp (DDD + Número)")
            if st.form_submit_button("Salvar Cadastro"):
                res = supabase.table("oficiais").insert({"nome":n, "matricula":m, "setor":s, "funcao":func, "whatsapp":z}).execute()
                registrar_auditoria("INSERT", "oficiais", res.data[0]['id'], n)
                st.success("Colaborador cadastrado!"); st.cache_data.clear()
    with t2:
        df = load_data("oficiais", "nome")
        st.dataframe(df[['nome', 'matricula', 'setor', 'funcao', 'whatsapp']], use_container_width=True, hide_index=True)

# ----------------------------------------------------------------------------
# 📦 CATÁLOGO EPI (CRUD)
# ----------------------------------------------------------------------------
elif menu == "📦 Catálogo EPI":
    st.title("📦 Gestão de Itens e C.A.")
    t1, t2 = st.tabs(["➕ Cadastrar", "🛠️ Gerenciar"])
    with t1:
        with st.form("new_epi"):
            n, ca, v = st.text_input("Nome do EPI").upper(), st.text_input("C.A."), st.date_input("Validade")
            if st.form_submit_button("Salvar Item"):
                supabase.table("ep").insert({"nome":n, "ca":ca, "validade":str(v)}).execute()
                st.success("EPI Cadastrado!"); st.cache_data.clear(); st.rerun()
    with t2:
        df_ep = load_data("ep", "nome")
        if not df_ep.empty:
            sel = st.selectbox("Item para editar/excluir", df_ep['nome'])
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
# 📄 FICHA INDIVIDUAL (COM ASSINATURA CANVAS)
# ----------------------------------------------------------------------------
elif menu == "📄 Ficha Individual":
    st.title("📄 Ficha de Controle de EPI")
    df_f = load_data("oficiais", "nome")
    if not df_f.empty:
        target = st.selectbox("Selecione o Colaborador", df_f['nome'])
        f_info = df_f[df_f['nome'] == target].iloc[0]
        
        # Área de Assinatura
        st.subheader("✍️ Assinatura Digital")
        from streamlit_drawable_canvas import st_canvas
        canvas_result = st_canvas(fill_color="rgba(255, 255, 255, 0)", stroke_width=2, stroke_color="#000", background_color="#eee", height=100, width=300, drawing_mode="freedraw", key="canvas")
        
        if st.button("💾 Salvar Assinatura e Gerar PDF"):
            if canvas_result.image_data is not None:
                img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                path = f"assinaturas/sig_{f_info['id']}.png"
                supabase.storage.from_("assinaturas").upload(path, buffered.getvalue(), {"content-type": "image/png", "upsert": "true"})
                url = supabase.storage.from_("assinaturas").get_public_url(path)
                supabase.table("oficiais").update({"assinatura_url": url}).eq("id", int(f_info['id'])).execute()
                st.success("Assinatura Salva!")
                st.rerun()

        # Histórico e Download
        hist_raw = supabase.table("entregas").select("*, ep(*)").eq("id_func", int(f_info['id'])).execute().data
        if hist_raw:
            rows = [{"Data/Hora": format_br(h['data_entrega'], True), "Qtd": h['quantidade'], "EPI": h['ep']['nome'], "CA": h['ep']['ca'], "Validade": format_br(h['ep']['validade']), "Token": h['token'], "Status": h['status']} for h in hist_raw]
            df_h = pd.DataFrame(rows)
            st.dataframe(df_h, use_container_width=True, hide_index=True)
            
            sig_url = f_info.get('assinatura_url')
            pdf = generate_pdf_ficha(dict(f_info), df_h, sig_url)
            if pdf: st.download_button("📥 BAIXAR FICHA (PDF)", data=pdf, file_name=f"Ficha_{target}.pdf", mime="application/pdf")
        else: st.info("Sem entregas.")

# ----------------------------------------------------------------------------
# OUTRAS SEÇÕES (REDUZIDAS PARA ESTABILIDADE)
# ----------------------------------------------------------------------------
elif menu == "📊 Painel":
    st.title("📊 Painel SESMT")
    df_f, df_e = load_data("oficiais"), load_data("entregas")
    st.metric("Total Colaboradores", len(df_f))
    st.metric("Total Entregas", len(df_e))

elif menu == "🚀 Entregar EPI":
    st.title("🚀 Registrar Entrega")
    df_f, df_ep = load_data("oficiais", "nome"), load_data("ep", "nome")
    with st.form("ent"):
        f = st.selectbox("Colaborador", df_f['matricula'] + " - " + df_f['nome'])
        e = st.selectbox("EPI", df_ep['nome'])
        q = st.number_input("Qtd", 1)
        if st.form_submit_button("Confirmar"):
            id_f = int(df_f[df_f['matricula'] + " - " + df_f['nome'] == f].iloc[0]['id'])
            id_e = int(df_ep[df_ep['nome'] == e].iloc[0]['id'])
            tk = str(int(time.time()))[-6:]
            supabase.table("entregas").insert({"id_func":id_f, "id_epi":id_e, "token":tk, "quantidade":q, "status":STATUS_ENTREGA["PENDENTE"]}).execute()
            st.success(f"Registrado! Token: {tk}"); st.cache_data.clear(); st.balloons()

elif menu == "⚙️ Ajustes":
    st.title("⚙️ Configurações")
    url = st.text_input("URL do App", get_cfg("url_sistema"))
    if st.button("Salvar URL"):
        supabase.table("configuracoes").upsert({"chave":"url_sistema", "valor":url}, on_conflict="chave").execute()
        st.success("URL Salva!")
