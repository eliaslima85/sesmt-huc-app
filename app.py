"""
🛡️ SESMT HUC - Sistema Digital de Gestão de EPI v6.12 (PRODUCTION READY)
Hospital Universitário do Ceará - Padrão Oficial ISGH
📱 Otimizado para Mobile | 🔒 Segurança Enterprise | ✨ UI Profissional
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
GOVERNO_SUB = "GOVERNO DO ESTADO DO CEARÁ"
STATUS_ENTREGA = {"PENDENTE": "Pendente ⏳", "CONFIRMADO": "Confirmado ✅"}

if 'carrinho_epi' not in st.session_state:
    st.session_state.carrinho_epi = []

# ============================================================================
# 🛠️ UTILITÁRIOS E TRATAMENTO DE ERROS DO SUPABASE
# ============================================================================

def clean_str(text):
    if not text: return ""
    text_str = str(text).replace('✅', '!').replace('⏳', '...')
    return text_str.encode('latin-1', 'replace').decode('latin-1')

def format_br(date_str, include_time=False):
    if not date_str: return "N/A"
    try:
        d_str = str(date_str).strip()
        if len(d_str) >= 10 and d_str[2] == '/' and d_str[5] == '/': return d_str[:16] if include_time else d_str[:10]
        
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
    st.markdown(f'<a href="{link}" target="_blank"><button style="background-color:#25D366;color:white;border:none;padding:10px;border-radius:5px;width:100%;cursor:pointer;font-weight:bold;">🚀 ENVIAR PARA WHATSAPP</button></a>', unsafe_allow_html=True)

# ============================================================================
# 📲 LINK DO WHATSAPP: CONFIRMAÇÃO DE TOKEN COM MÚLTIPLOS ITENS
# ============================================================================

if "confirmar" in st.query_params:
    tk = st.query_params["confirmar"]
    if tk:
        ent_res = supabase.table("entregas").select("*, oficiais(*)").eq("token", tk).execute()
        if ent_res.data:
            func = ent_res.data[0]['oficiais']
            
            st.title("🛡️ Confirmação Digital de EPI - SESMT HUC")
            st.write(f"**COLABORADOR:** {func['nome']} | **Matrícula:** {func['matricula']}")
            
            st.write("📦 **ITENS RECEBIDOS NESTA ENTREGA:**")
            for e in ent_res.data:
                epi_res = supabase.table("ep").select("nome, ca").eq("id", e['id_epi']).execute()
                epi_nome = epi_res.data[0]['nome'] if epi_res.data else "EPI"
                st.write(f"- {e['quantidade']}x {epi_nome} (C.A: {epi_res.data[0].get('ca', 'N/A')})")
                
            st.divider()
            
            if not func.get('assinatura_url'):
                st.warning("📝 Esta é sua primeira confirmação eletrônica. Desenhe sua assinatura na tela abaixo para salvá-la em sua ficha definitiva.")
                canvas_zap = st_canvas(stroke_width=2, stroke_color="#000", background_color="#eee", height=140, width=340, key="canvas_zap")
                
                if st.button("✍️ Gravar Assinatura e Confirmar Todos", use_container_width=True, type="primary"):
                    if canvas_zap.image_data is not None:
                        img = Image.fromarray(canvas_zap.image_data.astype('uint8'), 'RGBA')
                        buffered = BytesIO()
                        img.save(buffered, format="PNG")
                        
                        path = f"sig_{func['id']}_{int(time.time())}.png"
                        
                        try:
                            supabase.storage.from_("assinaturas").upload(path=path, file=buffered.getvalue(), file_options={"content-type": "image/png"})
                            url = supabase.storage.from_("assinaturas").get_public_url(path)
                            
                            try:
                                supabase.table("oficiais").update({"assinatura_url": url}).eq("id", func['id']).execute()
                            except Exception as db_col_err:
                                st.error(f"⚠️ Atenção (Erro Banco): {extrair_erro_db(db_col_err)}")
                            
                            supabase.table("entregas").update({"status": STATUS_ENTREGA["CONFIRMADO"]}).eq("token", tk).execute()
                            st.balloons()
                            st.success("✅ ASSINATURA REGISTRADA E PACOTE DE EPIs CONFIRMADO COM SUCESSO!")
                            time.sleep(2); st.query_params.clear(); st.rerun()
                        except Exception as upload_err:
                            st.error(f"⚠️ Erro de armazenamento na nuvem. Detalhes: {upload_err}")
            else:
                st.success("✨ Sua assinatura digital master já está vinculada de forma segura ao seu prontuário.")
                if st.button("👍 Confirmar Recebimento do Pacote", use_container_width=True, type="primary"):
                    supabase.table("entregas").update({"status": STATUS_ENTREGA["CONFIRMADO"]}).eq("token", tk).execute()
                    st.balloons()
                    st.success("🛡️ RECEBIMENTO VALIDADO COM SUCESSO!")
                    time.sleep(2); st.query_params.clear(); st.rerun()
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
        
        pdf.set_fill_color(40, 40, 40); pdf.set_text_color(255, 255, 255)
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
# INTERFACE ADMINISTRATIVA E ROTEAMENTO DE MENUS
# ============================================================================

if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛡️ SESMT HUC</h1>", unsafe_allow_html=True)
    pw = st.text_input("Senha Administrativa", type="password")
    if st.button("Entrar", use_container_width=True):
        if pw == os.getenv("SESMT_PASSWORD", get_cfg("app_password", "1234")): 
            st.session_state.logado = True
            st.rerun()
        else: st.error("Acesso Negado.")
    st.stop()

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
if st.sidebar.button("Sair do Sistema"): st.session_state.logado = False; st.rerun()

# ----------------------------------------------------------------------------
# 1. 📊 PAINEL (AGRUPADO POR TOKEN DE ENTREGA)
# ----------------------------------------------------------------------------
if menu == "📊 Painel":
    st.title("📊 Indicadores e Controles Operacionais")
    df_f, df_e = load_data("oficiais"), load_data("entregas")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Colaboradores", len(df_f))
    c2.metric("Total Entregas Realizadas", len(df_e))
    
    pendentes = df_e[df_e['status'].str.contains("Pendente", na=False)] if not df_e.empty else pd.DataFrame()
    
    # O dashboard agora conta por lote/token único, e não cada linha individual para não repetir
    tokens_pendentes = pendentes['token'].nunique() if not pendentes.empty else 0
    c3.metric("Lotes Aguardando Confirmação", tokens_pendentes)
    
    st.divider()
    st.subheader("📲 Pendências de Assinatura Eletrônica")
    if not pendentes.empty:
        # Agrupamento lógico: junta todos os EPIs de um mesmo token na mesma mensagem
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
                
                col1, col2 = st.columns([3, 1])
                col1.write(f"⏳ **{f['nome']}** | 📦 {itens_str} | Token: `{tk_pendente}`")
                link = f"{get_cfg('url_sistema')}/?confirmar={tk_pendente}"
                msg = f"🛡️ *SESMT HUC*\nOlá *{f['nome']}*,\nVocê possui um pacote de EPIs pendente de confirmação: *{itens_str}*. Acesse o link seguro para assinar digitalmente: {link}"
                with col2: abrir_whatsapp(f['whatsapp'], msg)
    else:
        st.success("Nenhuma assinatura pendente no momento!")

# ----------------------------------------------------------------------------
# 2. 🚀 REGISTRAR ENTREGA (NOVO SISTEMA DE CARRINHO MÚLTIPLO)
# ----------------------------------------------------------------------------
elif menu == "🚀 Registrar Entrega":
    st.title("🚀 Registrar Lote de Entrega")
    df_f = load_data("oficiais", "nome")
    df_ep = load_data("ep", "nome")
    
    if df_f.empty or df_ep.empty: 
        st.warning("É necessário cadastrar Colaboradores e EPIs no catálogo antes de realizar uma entrega.")
    else:
        df_ep['nome_display'] = df_ep['nome'] + " (C.A: " + df_ep['ca'].fillna("N/A").astype(str) + ")"
        
        st.subheader("1️⃣ Selecionar Colaborador")
        f_selecionado = st.selectbox("Busque a matrícula ou nome", df_f['matricula'] + " - " + df_f['nome'])
        st.divider()
        
        st.subheader("2️⃣ Adicionar EPIs ao Pacote")
        colA, colB, colC = st.columns([3, 1, 1])
        with colA: e_display = st.selectbox("Selecione o EPI", df_ep['nome_display'])
        with colB: q = st.number_input("Quantidade", min_value=1, value=1)
        with colC:
            st.write("") 
            st.write("")
            if st.button("➕ Adicionar à Lista", use_container_width=True):
                re = df_ep[df_ep['nome_display'] == e_display].iloc[0]
                
                hoje = datetime.today().date()
                ca_venc = False
                if pd.notna(re['validade']):
                    try:
                        if datetime.strptime(str(re['validade']), '%Y-%m-%d').date() < hoje: ca_venc = True
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
            st.subheader(f"🛒 Lista de Entrega (Total: {len(st.session_state.carrinho_epi)} itens)")
            
            for i, item in enumerate(st.session_state.carrinho_epi):
                alerta = "🔴 (C.A. VENCIDO)" if item['vencido'] else "✅"
                c1, c2, c3 = st.columns([4, 1, 1])
                c1.write(f"**{item['nome_display']}** {alerta}")
                c2.write(f"Qtd: **{item['qtd']}**")
                if c3.button("🗑️ Excluir", key=f"del_epi_{i}"):
                    st.session_state.carrinho_epi.pop(i)
                    st.rerun()
                    
            st.write("")
            if st.button(f"🚀 FECHAR PACOTE E REGISTRAR ({len(st.session_state.carrinho_epi)} ITENS)", type="primary", use_container_width=True):
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
                        
                    st.session_state.carrinho_epi = [] # Esvazia o carrinho após o sucesso
                    st.success(f"✅ Pacote registrado com sucesso! Token único gerado: `{tk}`")
                    
                    link = f"{get_cfg('url_sistema')}/?confirmar={tk}"
                    itens_txt = ", ".join(nomes_msg)
                    msg = f"🛡️ *SESMT HUC*\nOlá *{rf['nome']}*,\nConfirme o recebimento do pacote de EPIs:\n*{itens_txt}*\n\nAcesse o link seguro de assinatura: {link}"
                    abrir_whatsapp(rf['whatsapp'], msg)
                    
                except Exception as e_db:
                    st.error(f"⚠️ Rejeição do Supabase ao processar lote: {extrair_erro_db(e_db)}")
        else:
            st.info("Nenhum EPI adicionado à lista de entrega no momento.")

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
                n = st.text_input("Nome Completo").upper()
                m = st.text_input("Número de Matrícula")
                da = st.date_input("Data de Admissão", value=datetime.today(), format="DD/MM/YYYY")
                s = st.selectbox("Setor de Lotação", ["CME", "SESMT", "UTI", "MANUTENÇÃO", "CENTRO CIRÚRGICO", "EMERGÊNCIA", "PEDIATRIA", "ADMINISTRATIVO"])
                f = st.selectbox("Função / Cargo", df_funcoes['nome'].tolist())
                z = st.text_input("WhatsApp (DDD + Número, ex: 85912345678)")
                if st.form_submit_button("Salvar Registro"):
                    if n and m and z:
                        try:
                            supabase.table("oficiais").insert({"nome":n, "matricula":m, "data_admissao": str(da), "setor":s, "funcao":f, "whatsapp":z}).execute()
                            st.success("Colaborador cadastrado perfeitamente!"); st.cache_data.clear()
                        except Exception as e_db:
                            st.error(f"⚠️ Rejeição do Supabase: {extrair_erro_db(e_db)}")
                    else: st.error("Preencha todos os campos obrigatórios.")
        
        with tab2:
            df_oficiais = load_data("oficiais", "nome")
            if not df_oficiais.empty:
                sel_excluir = st.selectbox("Selecione o Colaborador para Excluir", df_oficiais['nome'])
                func_del = df_oficiais[df_oficiais['nome'] == sel_excluir].iloc[0]
                
                st.warning(f"⚠️ **Atenção:** Você selecionou o colaborador **{func_del['nome']}** para exclusão. Esta ação é permanente.")
                
                res_del = supabase.table("entregas").select("*, ep(*)").eq("id_func", int(func_del['id'])).order("data_entrega", desc=True).execute().data
                if res_del:
                    st.info("💡 É estritamente recomendado fazer o download do histórico completo deste colaborador antes de realizar a exclusão.")
                    df_h_del = pd.DataFrame([{"Data/Hora": format_br(h['data_entrega'], True), "Qtd": h['quantidade'], "EPI": h['ep']['nome'], "C.A.": h['ep']['ca'], "Token": h['token'], "Status": h['status']} for h in res_del])
                    headers_del = ["DATA/HORA", "QTD", "DESCRIÇÃO DO EPI", "C.A.", "TOKEN", "STATUS"]
                    texto_padrao = get_cfg("ficha_descricao", "Declaro que recebi os EPIs listados e fui orientado sobre o correto uso e conservacao.")
                    
                    pdf_backup = generate_pdf(f"FICHA DE EPI - BACKUP DE EXCLUSAO", headers_del, df_h_del.values.tolist(), dict(func_del), True, custom_text=texto_padrao)
                    if pdf_backup:
                        st.download_button("📥 Baixar Ficha Completa Antes de Excluir", data=pdf_backup, file_name=f"Backup_Exclusao_{sel_excluir}.pdf", mime="application/pdf", use_container_width=True)
                else:
                    st.info("Este colaborador não possui nenhum registro de retirada de EPI.")

                if st.button("🗑️ Deletar Colaborador Definitivamente", type="primary", use_container_width=True):
                    try:
                        supabase.table("entregas").delete().eq("id_func", int(func_del['id'])).execute()
                        supabase.table("oficiais").delete().eq("id", int(func_del['id'])).execute()
                        st.success(f"✅ O colaborador {func_del['nome']} e todo seu histórico foram removidos do sistema.")
                        st.cache_data.clear()
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"⚠️ Rejeição do Supabase: {extrair_erro_db(e)}")

        st.write("---")
        df_oficiais = load_data("oficiais", "nome")
        if not df_oficiais.empty:
            df_oficiais_view = df_oficiais.copy()
            for col in ['data_admissao', 'data_consentimento', 'data_criacao']:
                if col in df_oficiais_view.columns:
                    df_oficiais_view[col] = df_oficiais_view[col].apply(lambda x: format_br(x, True) if 'criacao' in col else format_br(x) if x else "")
            st.dataframe(df_oficiais_view[['nome', 'matricula', 'data_admissao', 'setor', 'funcao', 'whatsapp']], use_container_width=True, hide_index=True)

# ----------------------------------------------------------------------------
# 4. 🎖️ FUNÇÕES
# ----------------------------------------------------------------------------
elif menu == "🎖️ Funções":
    st.title("🎖️ Cadastro de Funções e Cargos")
    with st.form("add_f"):
        nf = st.text_input("Nome da Nova Função (Ex: TÉCNICO DE ENFERMAGEM)").upper()
        if st.form_submit_button("Adicionar ao Sistema"):
            if nf:
                try:
                    supabase.table("funcoes").insert({"nome":nf}).execute()
                    st.success(f"Função '{nf}' incluída com sucesso!"); st.cache_data.clear(); st.rerun()
                except Exception as e:
                    st.error(f"⚠️ Rejeição do Supabase: {extrair_erro_db(e)}")
    st.dataframe(load_data("funcoes", "nome"), use_container_width=True)

# ----------------------------------------------------------------------------
# 5. 📦 CATÁLOGO EPI
# ----------------------------------------------------------------------------
elif menu == "📦 Catálogo EPI":
    st.title("📦 Catálogo de Equipamentos e Certificados de Aprovação (C.A.)")
    t1, t2 = st.tabs(["➕ Novo EPI", "🛠️ Gerenciar Catálogo"])
    
    with t1:
        with st.form("new_epi"):
            n = st.text_input("Nome Técnico do EPI").upper()
            ca = st.text_input("Número do C.A.")
            v = st.date_input("Data de Validade do C.A.", format="DD/MM/YYYY")
            if st.form_submit_button("Salvar no Catálogo"):
                if n and ca:
                    try:
                        supabase.table("ep").insert({"nome":n, "ca":ca, "validade":str(v)}).execute()
                        st.success("EPI integrado ao catálogo!"); st.cache_data.clear(); st.rerun()
                    except Exception as e:
                        st.error(f"⚠️ Erro ao salvar. Verifique se executou o comando SQL no Supabase. Detalhes: {extrair_erro_db(e)}")
    
    with t2:
        df_ep = load_data("ep", "nome")
        if not df_ep.empty:
            df_ep['nome_display'] = df_ep['nome'] + " (C.A: " + df_ep['ca'].fillna("N/A").astype(str) + ")"
            
            sel = st.selectbox("Selecione o Item para Atualizar/Renovar C.A.", df_ep['nome_display'])
            it = df_ep[df_ep['nome_display'] == sel].iloc[0]
            
            with st.form("edit_epi"):
                en = st.text_input("Nome do EPI", it['nome']).upper()
                eca = st.text_input("Número do C.A.", it['ca'])
                ev = st.date_input("Validade do C.A.", datetime.strptime(it['validade'], '%Y-%m-%d') if it['validade'] else datetime.today(), format="DD/MM/YYYY")
                c1, c2 = st.columns(2)
                
                if c1.form_submit_button("💾 Salvar Alterações / Renovar C.A."):
                    try:
                        supabase.table("ep").update({"nome":en, "ca":eca, "validade":str(ev)}).eq("id", int(it['id'])).execute()
                        st.success("EPI Atualizado com Sucesso!"); st.cache_data.clear(); st.rerun()
                    except Exception as e:
                        st.error(f"⚠️ Rejeição do Supabase: {extrair_erro_db(e)}")
                if c2.form_submit_button("🗑️ Deletar do Catálogo"):
                    try:
                        supabase.table("ep").delete().eq("id", int(it['id'])).execute()
                        st.warning("EPI excluído."); st.cache_data.clear(); st.rerun()
                    except Exception as e: 
                        st.error(f"Erro: {extrair_erro_db(e)} - Talvez o EPI já possua registros de entrega vinculados.")
            
            st.divider()
            st.subheader("📋 Visão Geral do Catálogo")
            
            df_ep_view = df_ep.copy()
            hoje = datetime.today().date()
            
            def verificar_status_ca(data_str):
                if not data_str or pd.isna(data_str): return "S/ Info ⚠️"
                try:
                    dt = datetime.strptime(str(data_str).split(" ")[0], '%Y-%m-%d').date()
                    return "Ativo ✅" if dt >= hoje else "Vencido 🔴"
                except: return "Erro Formato"
                
            df_ep_view['Status_CA'] = df_ep_view['validade'].apply(verificar_status_ca)
            if 'validade' in df_ep_view.columns:
                df_ep_view['validade'] = df_ep_view['validade'].apply(lambda x: format_br(x) if x else "")
            
            st.dataframe(df_ep_view[['nome', 'ca', 'validade', 'Status_CA']], use_container_width=True, hide_index=True)

# ----------------------------------------------------------------------------
# 6. 📄 FICHA INDIVIDUAL
# ----------------------------------------------------------------------------
elif menu == "📄 Ficha Individual":
    st.title("📄 Ficha Individual de Controle de EPI (NR-06)")
    df_f = load_data("oficiais", "nome")
    if not df_f.empty:
        sel = st.selectbox("Selecione o Colaborador para Análise", df_f['nome'])
        f_info = df_f[df_f['nome'] == sel].iloc[0]
        
        if f_info.get('assinatura_url'):
            st.success("✅ Assinatura Digital Master vinculada legalmente ao prontuário do colaborador.")
            st.image(f_info['assinatura_url'], width=200)
        else:
            st.info("ℹ️ Este funcionário não realizou nenhuma assinatura eletrônica. A coleta será feita no primeiro link do WhatsApp enviado.")

        st.write(f"📅 **Data de Admissão:** {format_br(f_info.get('data_admissao'))}")
        
        st.write("---")
        termo_padrao = get_cfg("ficha_descricao", "Declaro que recebi os EPIs listados e fui orientado sobre o correto uso e conservacao.")
        texto_ficha = st.text_area("📝 Ajustar Texto de Declaração / Termo de Responsabilidade da Ficha", value=termo_padrao, height=100)
        
        if st.button("💾 Salvar Texto como Padrão para Todos", use_container_width=True):
            try:
                supabase.table("configuracoes").upsert({"chave":"ficha_descricao", "valor": texto_ficha}, on_conflict="chave").execute()
                st.success("✅ Texto atualizado e salvo com sucesso na nuvem!")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"⚠️ Rejeição do Supabase: {extrair_erro_db(e)}")
            
        st.write("---")

        res = supabase.table("entregas").select("*, ep(*)").eq("id_func", int(f_info['id'])).order("data_entrega", desc=True).execute().data
        if res:
            df_h = pd.DataFrame([{"Data/Hora": format_br(h['data_entrega'], True), "Qtd": h['quantidade'], "EPI": h['ep']['nome'], "C.A.": h['ep']['ca'], "Token": h['token'], "Status": h['status']} for h in res])
            
            if len(df_h) >= 20: 
                st.warning(f"⚠️ Alerta Fiscal: Ciclo de 20 itens atingido ({len(df_h)} retiradas). É recomendado fechar este ciclo e abrir um novo prontuário.")
            
            st.dataframe(df_h, use_container_width=True, hide_index=True)
            headers = ["DATA/HORA", "QTD", "DESCRIÇÃO DO EPI", "C.A.", "TOKEN", "STATUS"]
            
            col_b1, col_b2 = st.columns(2)
            
            pdf_c = generate_pdf("FICHA DE EPI - CICLO ATUAL (20 ITENS MAX)", headers, df_h.head(20).values.tolist(), dict(f_info), True, custom_text=texto_ficha)
            if pdf_c: col_b1.download_button("📥 BAIXAR CICLO ATUAL (Últimos 20)", data=pdf_c, file_name=f"Ciclo_20_{sel}.pdf", mime="application/pdf", use_container_width=True)
            
            pdf_g = generate_pdf("FICHA DE EPI - HISTORICO COMPLETO", headers, df_h.values.tolist(), dict(f_info), True, custom_text=texto_ficha)
            if pdf_g: col_b2.download_button("📥 BAIXAR HISTÓRICO GERAL (Completo)", data=pdf_g, file_name=f"Ficha_Geral_{sel}.pdf", mime="application/pdf", use_container_width=True)
        else:
            st.info("Nenhum EPI foi fornecido a este colaborador ainda.")

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
                    list_s.append({"Setor": h['oficiais']['setor'] if h['oficiais'] else "N/A", "EPI": h['ep']['nome'] if h['ep'] else "N/A", "Qtd": h['quantidade']})
            except: pass
        
        if list_s:
            st.success("✅ Alerta de Consumo: Movimentações detectadas nos últimos 7 dias.")
            df_s = pd.DataFrame(list_s).groupby(['Setor', 'EPI'])['Qtd'].sum().reset_index()
            st.dataframe(df_s, use_container_width=True, hide_index=True)
            
            pdf_s = generate_pdf("RELATÓRIO DE CONSUMO SEMANAL POR SETOR", ["SETOR", "TIPO DE EPI", "QUANTIDADE"], df_s.values.tolist())
            if pdf_s: st.download_button("📥 BAIXAR BALANÇO SEMANAL (PDF)", data=pdf_s, file_name="Semanal_Setores.pdf", mime="application/pdf", use_container_width=True)
        else: 
            st.info("Nenhuma retirada ou movimentação de EPI nos últimos 7 dias.")

# ----------------------------------------------------------------------------
# 8. ⚙️ AJUSTES
# ----------------------------------------------------------------------------
elif menu == "⚙️ Ajustes":
    st.title("⚙️ Configurações Gerais do Sistema")
    
    st.subheader("🌐 Link de Production do Sistema")
    url = st.text_input("URL Pública do Aplicativo (Ex: https://seu-app.streamlit.app)", get_cfg("url_sistema"))
    if st.button("Salvar URL do Sistema", use_container_width=True):
        try:
            supabase.table("configuracoes").upsert({"chave":"url_sistema", "valor":url}, on_conflict="chave").execute()
            st.success("URL pública do sistema sincronizada com a nuvem!")
        except Exception as e:
            st.error(f"⚠️ Rejeição do Supabase: {extrair_erro_db(e)}")
        
    st.divider()
    
    st.subheader("🔑 Segurança Administrativa (Alterar Senha)")
    nova_senha = st.text_input("Nova Senha de Acesso", type="password")
    confirma_senha = st.text_input("Confirme a Nova Senha", type="password")
    
    if st.button("Gravar Nova Senha", use_container_width=True):
        if nova_senha:
            if nova_senha == confirma_senha:
                try:
                    supabase.table("configuracoes").upsert({"chave": "app_password", "valor": nova_senha}, on_conflict="chave").execute()
                    st.success("🔒 Senha administrativa de acesso atualizada com sucesso na nuvem!")
                    logger.info("🔒 Senha de acesso do aplicativo alterada.")
                except Exception as e:
                    st.error(f"⚠️ Rejeição do Supabase: {extrair_erro_db(e)}")
            else:
                st.error("❌ As senhas digitadas não coincidem. Tente novamente.")
        else:
            st.error("❌ O campo de nova senha não pode estar vazio.")
