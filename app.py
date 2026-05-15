"""
🛡️ SESMT HUC - Sistema Digital de Gestão de EPI v4.0
Hospital Universitário do Ceará - Padrão Oficial ISGH
Inclui: Ciclos de 20 itens, Relatório Semanal por Setor e Assinatura Digital
"""

import logging
import time
import urllib.parse
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

SUPABASE_URL = "https://aatkjhtrafuepwzzlrbm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFhdGtqaHRyYWZ1ZXB3enpscmJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg2Mjg5MTYsImV4cCI6MjA5NDIwNDkxNn0.65izu7Zhc3kUZrVIRXGvVQ5o-Lhk-7PCK9CMg4zIwuk"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except:
    st.error("Erro na conexão com o banco de dados.")
    st.stop()

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

# ============================================================================
# GERADOR DE PDF PROFISSIONAL (HUC PADRÃO)
# ============================================================================

def generate_pdf_document(title, subtitle, headers, data_rows, func_info=None, is_ficha=False):
    from fpdf import FPDF
    try:
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        
        # CABEÇALHO OFICIAL (CNPJ NO TOPO)
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
        pdf.cell(0, 10, clean_str(title), border=0, ln=1, fill=True, align='C')
        pdf.ln(4)
        
        # Se for Ficha, adiciona dados do Colaborador
        pdf.set_text_color(0, 0, 0)
        if is_ficha and func_info:
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(140, 8, clean_str(f"COLABORADOR: {func_info['nome']}"), border=1)
            pdf.cell(0, 8, clean_str(f"MATRICULA: {func_info['matricula']}"), border=1, ln=1)
            pdf.cell(140, 8, clean_str(f"SETOR: {func_info['setor']}"), border=1)
            pdf.cell(0, 8, clean_str(f"FUNÇÃO: {func_info.get('funcao', 'N/A')}"), border=1, ln=1)
            pdf.ln(5)

        # Tabela (Cabeçalho)
        pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", 'B', 8)
        col_widths = [35, 15, 90, 30, 30, 0] if is_ficha else [80, 110, 0]
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 8, clean_str(h), border=1, align='C', fill=True)
        pdf.ln()
        
        # Tabela (Dados)
        pdf.set_font("Arial", '', 8)
        for row in data_rows:
            for i, val in enumerate(row):
                pdf.cell(col_widths[i], 8, clean_str(str(val)), border=1, ln=(1 if i == len(row)-1 else 0), align=('L' if i==2 and is_ficha else 'C'))
            
        if is_ficha:
            pdf.ln(10); pdf.set_font("Arial", 'I', 8)
            pdf.multi_cell(0, 4, clean_str(get_cfg("ficha_descricao", "Declaro que recebi os EPIs listados conforme NR-06.")))
            
            # Assinatura (se houver)
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
# LOGIN E NAVEGAÇÃO
# ============================================================================

if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛡️ SESMT HUC</h1>", unsafe_allow_html=True)
    pw = st.text_input("Acesso Administrativo", type="password")
    if st.button("Entrar"):
        if pw == get_cfg("app_password", "1234"): st.session_state.logado = True; st.rerun()
    st.stop()

menu = st.sidebar.radio("MENU", ["📊 Painel", "🚀 Registrar Entrega", "👥 Colaboradores", "🎖️ Funções", "📦 Catálogo EPI", "📄 Ficha Individual", "📈 Balanço Semanal"])

# ----------------------------------------------------------------------------
# 1. FICHA INDIVIDUAL (LOGICA DE CICLO DE 20 ITENS)
# ----------------------------------------------------------------------------
if menu == "📄 Ficha Individual":
    st.title("📄 Ficha Individual e Ciclos de Entrega")
    df_f = load_data("oficiais", "nome")
    if not df_f.empty:
        sel = st.selectbox("Selecione o Colaborador", df_f['nome'])
        f_info = df_f[df_f['nome'] == sel].iloc[0]
        
        # Histórico completo do Supabase
        res = supabase.table("entregas").select("*, ep(*)").eq("id_func", int(f_info['id'])).order("data_entrega", desc=True).execute().data
        if res:
            df_h = pd.DataFrame([{"Data/Hora": format_br(h['data_entrega'], True), "Qtd": h['quantidade'], "EPI": h['ep']['nome'], "CA": h['ep']['ca'], "Token": h['token'], "Status": h['status']} for h in res])
            
            # Alerta de Ciclo de 20
            total_itens = len(df_h)
            if total_itens >= 20:
                st.warning(f"⚠️ ATENÇÃO: Este colaborador atingiu {total_itens} entregas. Ciclo de 20 itens concluído!")
            
            st.write(f"Exibindo **{total_itens}** registros no total.")
            st.dataframe(df_h, use_container_width=True, hide_index=True)
            
            c1, c2 = st.columns(2)
            
            # Botão 1: Ciclo Atual (Últimos 20)
            df_ciclo = df_h.head(20)
            headers = ["DATA/HORA", "QTD", "DESCRIÇÃO DO EPI", "C.A.", "TOKEN", "STATUS"]
            data_ciclo = df_ciclo.values.tolist()
            pdf_ciclo = generate_pdf_document("FICHA DE EPI - CICLO ATUAL (20 ITENS)", "", headers, data_ciclo, dict(f_info), True)
            if pdf_ciclo: c1.download_button("📥 BAIXAR CICLO ATUAL (Últimos 20)", data=pdf_ciclo, file_name=f"Ciclo_20_{sel}.pdf")
            
            # Botão 2: Ficha Geral (Tudo)
            data_geral = df_h.values.tolist()
            pdf_geral = generate_pdf_document("FICHA DE EPI - HISTÓRICO GERAL", "", headers, data_geral, dict(f_info), True)
            if pdf_geral: c2.download_button("📥 BAIXAR FICHA GERAL (Histórico)", data=pdf_geral, file_name=f"Ficha_Geral_{sel}.pdf")
        else: st.info("Sem entregas registradas.")

# ----------------------------------------------------------------------------
# 2. BALANÇO SEMANAL (RELATORIO POR SETOR - 7 DIAS)
# ----------------------------------------------------------------------------
elif menu == "📈 Balanço Semanal":
    st.title("📈 Relatório de Consumo por Setor (Últimos 7 Dias)")
    
    # Busca entregas com join de oficiais (setor) e ep (nome)
    res = supabase.table("entregas").select("*, oficiais(setor), ep(nome)").execute().data
    if res:
        hoje = datetime.now()
        sete_dias_atras = hoje - timedelta(days=7)
        
        # Filtra na memória os últimos 7 dias
        recentes = []
        for h in res:
            data_e = datetime.fromisoformat(h['data_entrega'].replace('Z', '').split('+')[0])
            if data_e >= sete_dias_atras:
                recentes.append({
                    "Setor": h['oficiais']['setor'] if h['oficiais'] else "N/A",
                    "EPI": h['ep']['nome'] if h['ep'] else "N/A",
                    "Quantidade": h['quantidade']
                })
        
        if recentes:
            st.success(f"✅ Alerta: Consumo detectado nos últimos 7 dias!")
            df_recentes = pd.DataFrame(recentes)
            # Agrupa por Setor e EPI somando as quantidades
            df_agrupado = df_recentes.groupby(['Setor', 'EPI'])['Quantidade'].sum().reset_index()
            
            st.table(df_agrupado)
            
            # Gerar PDF do Balanço
            headers_b = ["SETOR", "TIPO DE EPI", "QUANTIDADE"]
            data_b = df_agrupado.values.tolist()
            pdf_b = generate_pdf_document("RELATÓRIO DE CONSUMO SEMANAL POR SETOR", f"Período: {sete_dias_atras.strftime('%d/%m/%Y')} a {hoje.strftime('%d/%m/%Y')}", headers_b, data_b)
            
            if pdf_b:
                st.download_button("📥 BAIXAR RELATÓRIO DE CONSUMO (PDF)", data=pdf_b, file_name="Consumo_Semanal_Setores.pdf")
        else:
            st.info("Nenhuma retirada de EPI nos últimos 7 dias.")

# ----------------------------------------------------------------------------
# RESTANTE DOS MENUS (ESTÁVEIS)
# ----------------------------------------------------------------------------
elif menu == "📊 Painel":
    st.title("📊 Painel Geral")
    # ... (Mantenha sua lógica de métricas e pendências aqui)

elif menu == "🚀 Registrar Entrega":
    st.title("🚀 Registrar Entrega")
    # ... (Mantenha seu formulário de registro aqui)

elif menu == "👥 Colaboradores":
    st.title("👥 Gestão de Colaboradores")
    # ... (Mantenha seu cadastro de oficiais aqui)

elif menu == "🎖️ Funções":
    st.title("🎖️ Funções")
    # ... (Mantenha seu cadastro de funções aqui)

elif menu == "📦 Catálogo EPI":
    st.title("📦 Catálogo de EPI")
    # ... (Mantenha seu cadastro de itens aqui)
