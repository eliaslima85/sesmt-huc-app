"""
🛡️ SESMT HUC - Sistema Digital de Gestão de EPI v5.0 (FINAL)
Hospital Universitário do Ceará - Padrão Oficial ISGH
"""

import logging
import time
import urllib.parse
import requests
import hashlib
from datetime import datetime, timedelta
from io import BytesIO

import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas

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
    st.error("Erro na conexão com o banco de dados na nuvem.")
    st.stop()

# Padrão Institucional HUC
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
    st.markdown(f'<a href="{link}" target="_blank"><button style="background-color:#25D366;color:white;border:none;padding:10px;border-radius:5px;width:100%;cursor:pointer;font-weight:bold;">🚀 ENVIAR PARA WHATSAPP</button></a>', unsafe_allow_html=True)

# ============================================================================
# GERADOR DE PDF PROFISSIONAL (HUC)
# ============================================================================

def generate_pdf(title, headers, data_rows, func_info=None, is_ficha=False):
    from fpdf import FPDF
    try:
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        
        # CABEÇALHO NO TOPO (CNPJ E ENDEREÇO)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 8, clean_str(HOSPITAL_NAME), border=0, ln=1, align='C')
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(0, 5, clean_str(HOSPITAL_ISGH), border=0, ln=1, align='C')
        pdf.set_font("Arial", '', 8)
        pdf.cell(0, 5, clean_str(CNPJ_ENDERECO), border=0, ln=1, align='C')
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(0, 5, clean_str(GOVERNO_SUB), border=0, ln=1, align='C')
        pdf.ln(5)
        
        # BARRA PRETA TÍTULO
        pdf.set_fill_color(40, 40, 40); pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, clean_str(title), border=0, ln=1, fill=True, align='C')
        pdf.ln(4)
        
        # DADOS DO COLABORADOR
        pdf.set_text_color(0, 0, 0)
        if is_ficha and func_info:
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(140, 8, clean_str(f"COLABORADOR: {func_info['nome']}"), border=1)
            pdf.cell(0, 8, clean_str(f"MATRICULA: {func_info['matricula']}"), border=1, ln=1)
            pdf.cell(140, 8, clean_str(f"SETOR: {func_info['setor']}"), border=1)
            pdf.cell(0, 8, clean_str(f"FUNCAO: {func_info.get('funcao', 'N/A')}"), border=1, ln=1)
            pdf.ln(5)

        # TABELA
        pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", 'B', 8)
        col_widths = [35, 15, 90, 30, 30, 0] if is_ficha else [80, 110, 0]
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 8, clean_str(h), border=1, align='C', fill=True)
        pdf.ln()
        
        pdf.set_font("Arial", '', 8)
        for row in data_rows:
            for i, val in enumerate(row):
                pdf.cell(col_widths[i], 8, clean_str(str(val)), border=1, ln=(1 if i == len(row)-1 else 0), align=('L' if i==2 and is_ficha else 'C'))
            
        if is_ficha:
            pdf.ln(10); pdf.set_font("Arial", 'I', 8)
            pdf.multi_cell(0, 4, clean_str(get_cfg("ficha_descricao", "Declaro que recebi os EPIs listados e fui orientado sobre o uso.")))
            
            if func_info.get('assinatura_url'):
                try:
                    r = requests.get(func_info['assinatura_url'], timeout=5)
                    img = Image.open(BytesIO(r.content)).convert("RGB")
                    img.save("temp_sig.jpg")
                    pdf.image("temp_sig.jpg", x=20, y=pdf.get_y()+2, w=40)
                except: pass

        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        st.error(f"Erro PDF: {e}")
        return None

# ============================================================================
# LOGIN E MENUS
# ============================================================================

if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.title("🛡️ SESMT HUC")
    pw = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if pw == get_cfg("app_password", "1234"): st.session_state.logado = True; st.rerun()
    st.stop()

# MENU LATERAL - TODAS AS OPÇÕES ESTÃO AQUI
menu = st.sidebar.radio("SESMT MENU", [
    "📊 Painel", 
    "🚀 Registrar Entrega", 
    "👥 Colaboradores", 
    "🎖️ Funções", 
    "📦 Catálogo EPI", 
    "📄 Ficha Individual", 
    "📈 Balanço Semanal",
    "⚙️ Ajustes"
])
if st.sidebar.button("Sair"): st.session_state.logado = False; st.rerun()

# ----------------------------------------------------------------------------
# 1. PAINEL (PENDÊNCIAS)
# ----------------------------------------------------------------------------
if menu == "📊 Painel":
    st.title("📊 Indicadores e Pendências")
    df_f, df_e = load_data("oficiais"), load_data("entregas")
    c1, c2, c3 = st.columns(3)
    c1.metric("Colaboradores", len(df_f))
    c2.metric("Entregas Total", len(df_e))
    pendentes = df_e[df_e['status'].str.contains("Pendente", na=False)] if not df_e.empty else []
    c3.metric("Aguardando Assinatura", len(pendentes))
    
    st.divider()
    st.subheader("📲 WhatsApp de Confirmação")
    if len(pendentes) > 0:
        for _, p in pendentes.iterrows():
            f_res = supabase.table("oficiais").select("nome, whatsapp").eq("id", p['id_func']).execute()
            if f_res.data:
                f = f_res.data[0]
                col1, col2 = st.columns([3, 1])
                col1.write(f"⏳ **{f['nome']}** | Token: {p['token']}")
                link = f"{get_cfg('url_sistema')}/?confirmar={p['token']}"
                msg = f"🛡️ *SESMT HUC*\nOlá {f['nome']},\nConfirme o seu EPI: {link}"
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
                abrir_whatsapp(rf['whatsapp'], f"🛡️ *SESMT HUC*\nOlá {rf['nome']},\nConfirme seu EPI: {get_cfg('url_sistema')}/?confirmar={tk}")

# ----------------------------------------------------------------------------
# 3. COLABORADORES
# ----------------------------------------------------------------------------
elif menu == "👥 Colaboradores":
    st.title("👥 Gestão de Colaboradores")
    df_funcoes = load_data("funcoes", "nome")
    if df_funcoes.empty: st.error("Cadastre as 'Funções' primeiro.")
    else:
        with st.form("cad_col"):
            n, m = st.text_input("Nome").upper(), st.text_input("Matrícula")
            s = st.selectbox("Setor", ["CME", "SESMT", "UTI", "MANUTENÇÃO", "CENTRO CIRÚRGICO"])
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
# 5. CATÁLOGO EPI (RECUPERADO)
# ----------------------------------------------------------------------------
elif menu == "📦 Catálogo EPI":
    st.title("📦 Catálogo de Itens")
    t1, t2 = st.tabs(["➕ Novo EPI", "🛠️ Gerenciar"])
    with t1:
        with st.form("new_epi"):
            n, ca, v = st.text_input("Nome do EPI").upper(), st.text_input("C.A."), st.date_input("Validade")
            if st.form_submit_button("Salvar"):
                supabase.table("ep").insert({"nome":n, "ca":ca, "validade":str(v)}).execute()
                st.success("Adicionado!"); st.cache_data.clear(); st.rerun()
    with t2:
        df_ep = load_data("ep", "nome")
        if not df_ep.empty:
            sel = st.selectbox("Item", df_ep['nome'])
            it = df_ep[df_ep['nome'] == sel].iloc[0]
            with st.form("edit_epi"):
                en, eca, ev = st.text_input("Nome", it['nome']).upper(), st.text_input("C.A.", it['ca']), st.date_input("Validade", datetime.strptime(it['validade'], '%Y-%m-%d'))
                c1, c2 = st.columns(2)
                if c1.form_submit_button("💾 Salvar"):
                    supabase.table("ep").update({"nome":en, "ca":eca, "validade":str(ev)}).eq("id", int(it['id'])).execute()
                    st.success("OK!"); st.cache_data.clear(); st.rerun()
                if c2.form_submit_button("🗑️ Deletar"):
                    supabase.table("ep").delete().eq("id", int(it['id'])).execute()
                    st.warning("Removido!"); st.cache_data.clear(); st.rerun()

# ----------------------------------------------------------------------------
# 6. FICHA INDIVIDUAL (LOGICA DE 20 ITENS)
# ----------------------------------------------------------------------------
elif menu == "📄 Ficha Individual":
    st.title("📄 Ficha Individual")
    df_f = load_data("oficiais", "nome")
    if not df_f.empty:
        sel = st.selectbox("Colaborador", df_f['nome'])
        f_info = df_f[df_f['nome'] == sel].iloc[0]
        
        # Assinatura Digital
        st.subheader("✍️ Assinatura Digital")
        canvas_result = st_canvas(stroke_width=2, stroke_color="#000", background_color="#eee", height=100, width=300, key="canvas")
        if st.button("💾 Salvar Assinatura"):
            if canvas_result.image_data is not None:
                img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                buffered = BytesIO(); img.save(buffered, format="PNG")
                path = f"assinaturas/sig_{f_info['id']}.png"
                supabase.storage.from_("assinaturas").upload(path, buffered.getvalue(), {"content-type": "image/png", "upsert": "true"})
                url = supabase.storage.from_("assinaturas").get_public_url(path)
                supabase.table("oficiais").update({"assinatura_url": url}).eq("id", int(f_info['id'])).execute()
                st.success("Assinatura Salva!")

        res = supabase.table("entregas").select("*, ep(*)").eq("id_func", int(f_info['id'])).order("data_entrega", desc=True).execute().data
        if res:
            df_h = pd.DataFrame([{"Data/Hora": format_br(h['data_entrega'], True), "Qtd": h['quantidade'], "EPI": h['ep']['nome'], "CA": h['ep']['ca'], "Token": h['token'], "Status": h['status']} for h in res])
            
            if len(df_h) >= 20: st.warning(f"⚠️ Ciclo de 20 itens atingido ({len(df_h)} entregas).")
            
            st.dataframe(df_h, use_container_width=True)
            headers = ["DATA/HORA", "QTD", "DESCRIÇÃO DO EPI", "C.A.", "TOKEN", "STATUS"]
            
            col_b1, col_b2 = st.columns(2)
            pdf_c = generate_pdf("FICHA DE EPI - CICLO ATUAL (20 ITENS)", headers, df_h.head(20).values.tolist(), dict(f_info), True)
            if pdf_c: col_b1.download_button("📥 BAIXAR CICLO (Últimos 20)", data=pdf_c, file_name=f"Ciclo_{sel}.pdf")
            
            pdf_g = generate_pdf("FICHA DE EPI - HISTÓRICO GERAL", headers, df_h.values.tolist(), dict(f_info), True)
            if pdf_g: col_b2.download_button("📥 BAIXAR FICHA GERAL", data=pdf_g, file_name=f"Geral_{sel}.pdf")

# ----------------------------------------------------------------------------
# 7. BALANÇO SEMANAL (POR SETOR - 7 DIAS)
# ----------------------------------------------------------------------------
elif menu == "📈 Balanço Semanal":
    st.title("📈 Consumo Semanal por Setor")
    res = supabase.table("entregas").select("*, oficiais(setor), ep(nome)").execute().data
    if res:
        sete_dias = datetime.now() - timedelta(days=7)
        list_s = []
        for h in res:
            dt_e = datetime.fromisoformat(h['data_entrega'].split('+')[0])
            if dt_e >= sete_dias:
                list_s.append({"Setor": h['oficiais']['setor'], "EPI": h['ep']['nome'], "Qtd": h['quantidade']})
        
        if list_s:
            st.success("✅ Consumo detectado nos últimos 7 dias.")
            df_s = pd.DataFrame(list_s).groupby(['Setor', 'EPI'])['Qtd'].sum().reset_index()
            st.table(df_s)
            pdf_s = generate_pdf("RELATÓRIO DE CONSUMO SEMANAL", ["SETOR", "TIPO DE EPI", "QUANTIDADE"], df_s.values.tolist())
            if pdf_s: st.download_button("📥 BAIXAR RELATÓRIO (PDF)", data=pdf_s, file_name="Semanal_Setores.pdf")
        else: st.info("Sem consumo nos últimos 7 dias.")

# ----------------------------------------------------------------------------
# 8. AJUSTES
# ----------------------------------------------------------------------------
elif menu == "⚙️ Ajustes":
    st.title("⚙️ Ajustes")
    url = st.text_input("URL do App", get_cfg("url_sistema"))
    if st.button("Salvar"):
        supabase.table("configuracoes").upsert({"chave":"url_sistema", "valor":url}, on_conflict="chave").execute()
        st.success("Salvo!")
