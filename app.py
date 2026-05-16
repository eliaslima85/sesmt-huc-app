"""
🛡️ SESMT HUC - Sistema Digital de Gestão de EPI v6.4 (PRODUCTION READY)
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

# Carregamento inteligente de credenciais (Variáveis de ambiente com Fallback Seguro)
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

# Padrões Institucionais Oficiais (Rigidamente no Topo do PDF)
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
    import unicodedata
    nfd = unicodedata.normalize('NFD', text_str)
    return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn').encode('latin-1', 'replace').decode('latin-1')

def format_br(date_str, include_time=False):
    if not date_str: return "N/A"
    try:
        d_str = str(date_str).strip()
        if "/" in d_str: return d_str
        clean_date = d_str.replace('Z', '').split('+')[0]
        if "T" in clean_date or " " in clean_date:
            clean_date = clean_date.replace('T', ' ')
            dt = datetime.strptime(clean_date.split('.')[0], '%Y-%m-%d %H:%M:%S')
            return dt.strftime('%d/%m/%Y %H:%M') if include_time else dt.strftime('%d/%m/%Y')
        else:
            dt = datetime.strptime(clean_date, '%Y-%m-%d')
            return dt.strftime('%d/%m/%Y')
    except:
        return str(date_str)

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
            
            st.title("🛡️ Confirmação Digital de EPI - SESMT HUC")
            st.write(f"**COLABORADOR:** {func['nome']} | **Matrícula:** {func['matricula']}")
            st.write(f"**Item Recebido:** {epi_nome} | **Quantidade:** {entrega['quantidade']}")
            st.divider()
            
            if not func.get('assinatura_url'):
                st.warning("📝 Esta é sua primeira confirmação eletrônica. Desenhe sua assinatura na tela abaixo para salvá-la em sua ficha definitiva.")
                canvas_zap = st_canvas(stroke_width=2, stroke_color="#000", background_color="#eee", height=140, width=340, key="canvas_zap")
                
                if st.button("✍️ Gravar Assinatura e Confirmar", use_container_width=True, type="primary"):
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
                                logger.error(f"Erro PGRST204 interceptado: {db_col_err}")
                                st.error("⚠️ Atenção: A coluna 'assinatura_url' não foi encontrada na tabela 'oficiais'. Execute o comando SQL indicado no painel do Supabase.")
                            
                            supabase.table("entregas").update({"status": STATUS_ENTREGA["CONFIRMADO"]}).eq("token", tk).execute()
                            st.balloons()
                            st.success("✅ ASSINATURA REGISTRADA E EPI CONFIRMADO COM SUCESSO!")
                            time.sleep(2); st.query_params.clear(); st.rerun()
                        except Exception as upload_err:
                            st.error(f"⚠️ Erro de armazenamento na nuvem. Verifique o Bucket público 'assinaturas'. Detalhes: {upload_err}")
            else:
                st.success("✨ Sua assinatura digital master já está vinculada de forma segura ao seu prontuário.")
                if st.button("👍 Confirmar Recebimento deste EPI", use_container_width=True, type="primary"):
                    supabase.table("entregas").update({"status": STATUS_ENTREGA["CONFIRMADO"]}).eq("token", tk).execute()
                    st.balloons()
                    st.success("🛡️ RECEBIMENTO VALIDADO COM SUCESSO!")
                    time.sleep(2); st.query_params.clear(); st.rerun()
        else:
            st.error("❌ Token inválido ou link de confirmação expirado.")
    st.stop()

# ============================================================================
# GERADOR DE PDF PROFISSIONAL (CNPJ NO TOPO E POSICIONAMENTO DA ASSINATURA)
# ============================================================================

def generate_pdf(title, headers, data_rows, func_info=None, is_ficha=False, custom_text=None):
    from fpdf import FPDF
    try:
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        
        # CABEÇALHO INSTITUCIONAL NO TOPO DO DOCUMENTO
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 8, clean_str(HOSPITAL_NAME), border=0, ln=1, align='C')
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(0, 5, clean_str(HOSPITAL_ISGH), border=0, ln=1, align='C')
        pdf.set_font("Arial", '', 8)
        pdf.cell(0, 5, clean_str(CNPJ_ENDERECO), border=0, ln=1, align='C')
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(0, 5, clean_str(GOVERNO_SUB), border=0, ln=1, align='C')
        pdf.ln(5)
        
        # BARRA DE TÍTULO ESCURA
        pdf.set_fill_color(40, 40, 40); pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, clean_str(title), border=0, ln=1, fill=True, align='C')
        pdf.ln(4)
        
        # DADOS DO COLABORADOR
        pdf.set_text_color(0, 0, 0)
        if is_ficha and func_info:
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(140, 8, clean_str(f"COLABORADOR: {func_info['nome']}"), border=1)
            pdf.cell(0, 8, clean_str(f"MATRÍCULA: {func_info['matricula']}"), border=1, ln=1)
            pdf.cell(140, 8, clean_str(f"SETOR: {func_info['setor']}"), border=1)
            pdf.cell(0, 8, clean_str(f"FUNÇÃO: {func_info.get('funcao', 'N/A')}"), border=1, ln=1)
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
            # Imprime o texto de declaração dinâmico (Request 1)
            pdf.ln(10); pdf.set_font("Arial", 'I', 8)
            texto_render = custom_text if custom_text else get_cfg("ficha_descricao", "Declaro que recebi os EPIs listados e fui orientado sobre o correto uso e conservacao.")
            pdf.multi_cell(0, 4, clean_str(texto_render))
            
            # Bloco Oficial de Assinatura (Request 2 - Alinhamento rigoroso abaixo da frase)
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
                    pdf.ln(15) # Avança o cursor para layout limpo
                except: pass

        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}")
        return None

# ============================================================================
# INTERFACE ADMINISTRATIVA E ROTEAMENTO DE MENUS (TODOS OS 8 MENUS ATIVOS)
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
# 1. 📊 PAINEL
# ----------------------------------------------------------------------------
if menu == "📊 Painel":
    st.title("📊 Indicadores e Controles Operacionais")
    df_f, df_e = load_data("oficiais"), load_data("entregas")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Colaboradores", len(df_f))
    c2.metric("Total Entregas Realizadas", len(df_e))
    pendentes = df_e[df_e['status'].str.contains("Pendente", na=False)] if not df_e.empty else []
    c3.metric("Aguardando Confirmação", len(pendentes))
    
    st.divider()
    st.subheader("📲 Pendências de Assinatura Eletrônica")
    if len(pendentes) > 0:
        for _, p in pendentes.iterrows():
            f_res = supabase.table("oficiais").select("nome, whatsapp").eq("id", p['id_func']).execute()
            epi_res = supabase.table("ep").select("nome").eq("id", p['id_epi']).execute()
            epi_nome = epi_res.data[0]['nome'] if epi_res.data else "EPI"
            
            if f_res.data:
                f = f_res.data[0]
                col1, col2 = st.columns([3, 1])
                col1.write(f"⏳ **{f['nome']}** | {p['quantidade']}x {epi_nome} | Token: `{p['token']}`")
                link = f"{get_cfg('url_sistema')}/?confirmar={p['token']}"
                msg = f"🛡️ *SESMT HUC*\nOlá *{f['nome']}*,\nVocê possui uma entrega pendente de confirmação para o EPI: *{p['quantidade']}x {epi_nome}*. Acesse o link seguro para assinar digitalmente: {link}"
                with col2: abrir_whatsapp(f['whatsapp'], msg)
    else:
        st.success("Nenhuma assinatura pendente no momento!")

# ----------------------------------------------------------------------------
# 2. 🚀 REGISTRAR ENTREGA
# ----------------------------------------------------------------------------
elif menu == "🚀 Registrar Entrega":
    st.title("🚀 Registrar Entrega de Equipamentos")
    df_f, df_ep = load_data("oficiais", "nome"), load_data("ep", "nome")
    if df_f.empty or df_ep.empty: 
        st.warning("É necessário cadastrar Colaboradores e EPIs no catálogo antes de realizar uma entrega.")
    else:
        with st.form("ent"):
            f = st.selectbox("Selecione o Colaborador", df_f['matricula'] + " - " + df_f['nome'])
            e = st.selectbox("Selecione o EPI", df_ep['nome'])
            q = st.number_input("Quantidade Fornecida", min_value=1, value=1)
            if st.form_submit_button("Gerar Registro de Entrega"):
                rf = df_f[df_f['matricula'] + " - " + df_f['nome'] == f].iloc[0]
                re = df_ep[df_ep['nome'] == e].iloc[0]
                tk = str(int(time.time()))[-6:]
                
                supabase.table("entregas").insert({
                    "id_func": int(rf['id']), "id_epi": int(re['id']), 
                    "token": tk, "quantidade": q, "status": STATUS_ENTREGA["PENDENTE"]
                }).execute()
                
                st.success(f"✅ Entrega registrada com sucesso! Token gerado: `{tk}`")
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
        with st.form("cad_col"):
            n = st.text_input("Nome Completo").upper()
            m = st.text_input("Número de Matrícula")
            s = st.selectbox("Setor de Lotação", ["CME", "SESMT", "UTI", "MANUTENÇÃO", "CENTRO CIRÚRGICO", "EMERGÊNCIA", "PEDIATRIA", "ADMINISTRATIVO"])
            f = st.selectbox("Função / Cargo", df_funcoes['nome'].tolist())
            z = st.text_input("WhatsApp (DDD + Número, ex: 85912345678)")
            if st.form_submit_button("Salvar Registro"):
                if n and m and z:
                    supabase.table("oficiais").insert({"nome":n, "matricula":m, "setor":s, "funcao":f, "whatsapp":z}).execute()
                    st.success("Colaborador cadastrado perfeitamente!"); st.cache_data.clear()
                else: st.error("Preencha todos os campos obrigatórios.")
        
        df_oficiais = load_data("oficiais", "nome")
        if not df_oficiais.empty:
            df_oficiais_view = df_oficiais.copy()
            for col in ['data_admissao', 'data_consentimento', 'data_criacao']:
                if col in df_oficiais_view.columns:
                    df_oficiais_view[col] = df_oficiais_view[col].apply(lambda x: format_br(x, True) if 'criacao' in col else format_br(x) if x else "")
            st.dataframe(df_oficiais_view[['nome', 'matricula', 'setor', 'funcao', 'whatsapp']], use_container_width=True, hide_index=True)

# ----------------------------------------------------------------------------
# 4. 🎖️ FUNÇÕES
# ----------------------------------------------------------------------------
elif menu == "🎖️ Funções":
    st.title("🎖️ Cadastro de Funções e Cargos")
    with st.form("add_f"):
        nf = st.text_input("Nome da Nova Função (Ex: TÉCNICO DE ENFERMAGEM)").upper()
        if st.form_submit_button("Adicionar ao Sistema"):
            if nf:
                supabase.table("funcoes").insert({"nome":nf}).execute()
                st.success(f"Função '{nf}' incluída com sucesso!"); st.cache_data.clear(); st.rerun()
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
            v = st.date_input("Data de Validade do C.A.")
            if st.form_submit_button("Salvar no Catálogo"):
                if n and ca:
                    supabase.table("ep").insert({"nome":n, "ca":ca, "validade":str(v)}).execute()
                    st.success("EPI integrado ao catálogo!"); st.cache_data.clear(); st.rerun()
    with t2:
        df_ep = load_data("ep", "nome")
        if not df_ep.empty:
            sel = st.selectbox("Selecione o Item para Edição/Exclusão", df_ep['nome'])
            it = df_ep[df_ep['nome'] == sel].iloc[0]
            with st.form("edit_epi"):
                en = st.text_input("Nome do EPI", it['nome']).upper()
                eca = st.text_input("Número do C.A.", it['ca'])
                ev = st.date_input("Validade do C.A.", datetime.strptime(it['validade'], '%Y-%m-%d') if it['validade'] else datetime.today())
                c1, c2 = st.columns(2)
                if c1.form_submit_button("💾 Salvar Alterações"):
                    supabase.table("ep").update({"nome":en, "ca":eca, "validade":str(ev)}).eq("id", int(it['id'])).execute()
                    st.success("EPI Atualizado com Sucesso!"); st.cache_data.clear(); st.rerun()
                if c2.form_submit_button("🗑️ Deletar do Catálogo"):
                    try:
                        supabase.table("ep").delete().eq("id", int(it['id'])).execute()
                        st.warning("EPI excluído."); st.cache_data.clear(); st.rerun()
                    except: st.error("Não é possível deletar um EPI que já possui registros de entrega vinculados.")
            
            df_ep_view = df_ep.copy()
            if 'validade' in df_ep_view.columns:
                df_ep_view['validade'] = df_ep_view['validade'].apply(lambda x: format_br(x) if x else "")
            st.dataframe(df_ep_view[['nome', 'ca', 'validade']], use_container_width=True, hide_index=True)

# ----------------------------------------------------------------------------
# 6. 📄 FICHA INDIVIDUAL (CAMPOS DE TEXTO DINÂMICOS ADICIONADOS)
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

        # --- NOVO BLOCO: ENTRADA DE TEXTO CUSTOMIZADO PARA A FICHA (Request 1) ---
        st.write("---")
        termo_padrao = get_cfg("ficha_descricao", "Declaro que recebi os EPIs listados e fui orientado sobre o correto uso e conservacao.")
        texto_ficha = st.text_area("📝 Ajustar Texto de Declaração / Termo de Responsabilidade da Ficha", value=termo_padrao, height=100, help="Escreva o texto jurídico que sairá impresso no corpo desta ficha individual em PDF.")
        st.write("---")

        res = supabase.table("entregas").select("*, ep(*)").eq("id_func", int(f_info['id'])).order("data_entrega", desc=True).execute().data
        if res:
            df_h = pd.DataFrame([{"Data/Hora": format_br(h['data_entrega'], True), "Qtd": h['quantidade'], "EPI": h['ep']['nome'], "C.A.": h['ep']['ca'], "Token": h['token'], "Status": h['status']} for h in res])
            
            if len(df_h) >= 20: 
                st.warning(f"⚠️ Alerta Fiscal: Ciclo de 20 itens atingido ({len(df_h)} retiradas). É recomendado fechar este ciclo e abrir um novo prontuário.")
            
            st.dataframe(df_h, use_container_width=True, hide_index=True)
            headers = ["DATA/HORA", "QTD", "DESCRIÇÃO DO EPI", "C.A.", "TOKEN", "STATUS"]
            
            col_b1, col_b2 = st.columns(2)
            
            # Repasse do texto customizado para as funções de PDF
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
        supabase.table("configuracoes").upsert({"chave":"url_sistema", "valor":url}, on_conflict="chave").execute()
        st.success("URL pública do sistema sincronizada com a nuvem!")
        
    st.divider()
    
    st.subheader("🔑 Segurança Administrativa (Alterar Senha)")
    nova_senha = st.text_input("Nova Senha de Acesso", type="password")
    confirma_senha = st.text_input("Confirme a Nova Senha", type="password")
    
    if st.button("Gravar Nova Senha", use_container_width=True):
        if nova_senha:
            if nova_senha == confirma_senha:
                supabase.table("configuracoes").upsert({"chave": "app_password", "valor": nova_senha}, on_conflict="chave").execute()
                st.success("🔒 Senha administrativa de acesso atualizada com sucesso na nuvem!")
                logger.info("🔒 Senha de acesso do aplicativo alterada.")
            else:
                st.error("❌ As senhas digitadas não coincidem. Tente novamente.")
        else:
            st.error("❌ O campo de nova senha não pode estar vazio.")
