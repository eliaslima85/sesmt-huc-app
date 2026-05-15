"""
🛡️ SESMT HUC - Sistema Digital de Gestão de EPI
Hospital Universitário do Ceará

Aplicação para gestão de Equipamentos de Proteção Individual (EPI)
e segurança do trabalho.
"""

import os
import sys
import logging
import time
import urllib.parse
from datetime import datetime

import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

# Carregar variáveis de ambiente
load_dotenv()

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Streamlit
st.set_page_config(
    page_title="SESMT HUC - Digital",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ Erro: SUPABASE_URL e SUPABASE_KEY não configuradas!")
    st.info("Configure as variáveis de ambiente no Streamlit Cloud ou localmente em .env")
    st.stop()

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    logger.error(f"Erro ao conectar Supabase: {e}")
    st.error("❌ Erro ao conectar ao banco de dados")
    st.stop()

# ============================================================================
# CONSTANTES
# ============================================================================

HOSPITAL_NAME = "HOSPITAL UNIVERSITARIO DO CEARA - HUC"
CNPJ_HUC = "05.268.526/0024-67"

MENU_OPTIONS = {
    "dashboard": "📊 Dashboard",
    "entregar_epi": "🚀 Entregar EPI",
    "funcionarios": "👥 Funcionários",
    "catalogo": "📦 Catálogo",
    "ficha_epi": "📄 Ficha de EPI",
    "consumo": "📈 Consumo Semanal",
    "config": "⚙️ Configurações",
}

TABELAS = {
    "OFICIAIS": "oficiais",
    "ENTREGAS": "entregas",
    "EP": "ep",
    "VINCULOS": "vinculos",
    "SETORES": "setores",
    "FUNCOES": "funcoes",
    "CONFIG": "configuracoes",
}

STATUS_ENTREGA = {
    "PENDENTE": "Pendente ⏳",
    "CONFIRMADO": "Confirmado ✅",
}

SESSION_TIMEOUT = 3600  # 1 hora

# ============================================================================
# FUNÇÕES AUXILIARES - FORMATAÇÃO
# ============================================================================

def format_br(date_str: str) -> str:
    """Formata data para DD/MM/YYYY."""
    if not date_str:
        return ""
    try:
        date_part = str(date_str).split('T')[0]
        dt = datetime.strptime(date_part, '%Y-%m-%d')
        return dt.strftime('%d/%m/%Y')
    except (ValueError, AttributeError):
        return ""

def dias_desde(date_str: str) -> int:
    """Calcula dias desde uma data até agora."""
    try:
        date_part = str(date_str).split('T')[0]
        dt = datetime.strptime(date_part, '%Y-%m-%d')
        return (datetime.now() - dt).days
    except Exception:
        return -1

def remove_accents(text: str) -> str:
    """Remove acentos de um texto."""
    import unicodedata
    try:
        nfd = unicodedata.normalize('NFD', str(text))
        return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    except Exception:
        return str(text)

def gerar_token() -> str:
    """Gera token único para entrega."""
    import uuid
    return str(uuid.uuid4())[:8].upper()

# ============================================================================
# FUNÇÕES AUXILIARES - VALIDAÇÃO
# ============================================================================

def validar_whatsapp(valor: str) -> tuple:
    """Valida WhatsApp."""
    import re
    if not valor:
        return False, "WhatsApp é obrigatório"
    if not re.match(r'^\d{10,11}$', valor):
        return False, "WhatsApp deve ter 10 ou 11 dígitos"
    return True, ""

def validar_nome(valor: str) -> tuple:
    """Valida nome."""
    if not valor:
        return False, "Nome é obrigatório"
    if len(valor) < 3 or len(valor) > 100:
        return False, "Nome deve ter entre 3 e 100 caracteres"
    return True, ""

def validar_matricula(valor: str) -> tuple:
    """Valida matrícula."""
    import re
    if not valor:
        return False, "Matrícula é obrigatória"
    if not re.match(r'^[A-Z0-9]{1,20}$', valor):
        return False, "Matrícula inválida"
    return True, ""

# ============================================================================
# FUNÇÕES - BANCO DE DADOS (CACHE)
# ============================================================================

@st.cache_data(ttl=3600)
def get_oficiais():
    """Retorna todos os funcionários."""
    try:
        res = supabase.table(TABELAS["OFICIAIS"]).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        logger.error(f"Erro ao obter oficiais: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_epis():
    """Retorna todos os EPIs."""
    try:
        res = supabase.table(TABELAS["EP"]).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        logger.error(f"Erro ao obter EPIs: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_vinculos():
    """Retorna lista de vínculos."""
    try:
        res = supabase.table(TABELAS["VINCULOS"]).select("nome").execute()
        return [v['nome'] for v in res.data] if res.data else []
    except Exception as e:
        logger.error(f"Erro ao obter vínculos: {e}")
        return []

@st.cache_data(ttl=3600)
def get_setores():
    """Retorna lista de setores."""
    try:
        res = supabase.table(TABELAS["SETORES"]).select("nome").order("nome").execute()
        return [s['nome'] for s in res.data] if res.data else []
    except Exception as e:
        logger.error(f"Erro ao obter setores: {e}")
        return []

@st.cache_data(ttl=3600)
def get_funcoes():
    """Retorna lista de funções."""
    try:
        res = supabase.table(TABELAS["FUNCOES"]).select("nome").order("nome").execute()
        return [f['nome'] for f in res.data] if res.data else []
    except Exception as e:
        logger.error(f"Erro ao obter funções: {e}")
        return []

def get_config(key: str, default: str = "") -> str:
    """Recupera configuração do banco de dados."""
    try:
        res = supabase.table(TABELAS["CONFIG"]).select("valor").eq("chave", key).execute()
        return res.data[0]['valor'] if res.data else default
    except Exception as e:
        logger.error(f"Erro ao obter config {key}: {e}")
        return default

def set_config(key: str, valor: str) -> bool:
    """Salva configuração no banco de dados."""
    try:
        supabase.table(TABELAS["CONFIG"]).upsert({"chave": key, "valor": valor}).execute()
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar config {key}: {e}")
        return False

def get_estatisticas() -> dict:
    """Retorna estatísticas gerais."""
    try:
        oficiais = supabase.table(TABELAS["OFICIAIS"]).select("id").execute()
        entregas = supabase.table(TABELAS["ENTREGAS"]).select("id").execute()
        pendentes = supabase.table(TABELAS["ENTREGAS"]).select("id").eq("status", STATUS_ENTREGA["PENDENTE"]).execute()
        
        return {
            "total_oficiais": len(oficiais.data) if oficiais.data else 0,
            "total_entregas": len(entregas.data) if entregas.data else 0,
            "entregas_pendentes": len(pendentes.data) if pendentes.data else 0,
        }
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        return {"total_oficiais": 0, "total_entregas": 0, "entregas_pendentes": 0}

def get_entregas_pendentes(limit: int = 10):
    """Retorna entregas pendentes de confirmação."""
    try:
        res = supabase.table(TABELAS["ENTREGAS"]).select("*, oficiais(nome, whatsapp), ep(nome)").eq("status", STATUS_ENTREGA["PENDENTE"]).limit(limit).execute()
        return res.data if res.data else []
    except Exception as e:
        logger.error(f"Erro ao obter entregas pendentes: {e}")
        return []

def get_historico_oficial(id_func: int):
    """Retorna histórico de entregas de um funcionário."""
    try:
        res = supabase.table(TABELAS["ENTREGAS"]).select("*, ep(nome, ca)").eq("id_func", id_func).order("data_entrega", desc=True).execute()
        if not res.data:
            return pd.DataFrame()
        
        return pd.DataFrame([{
            "data_entrega": r['data_entrega'],
            "epi_nome": r['ep']['nome'],
            "ca": r['ep']['ca'],
            "quantidade": r['quantidade'],
            "token": r['token'],
            "status": r['status']
        } for r in res.data])
    except Exception as e:
        logger.error(f"Erro ao obter histórico: {e}")
        return pd.DataFrame()

# ============================================================================
# FUNÇÕES - PDF
# ============================================================================

def create_pdf(f: dict, df: pd.DataFrame) -> bytes:
    """Cria PDF da ficha de EPI."""
    try:
        from fpdf import FPDF
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, HOSPITAL_NAME, ln=True, align='C')
        
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 5, f"CNPJ: {CNPJ_HUC}", ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 10, remove_accents(f"FICHA DE EPI - {f['nome'].upper()}"), ln=True, fill=True)
        pdf.ln(2)
        
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(100, 7, f"NOME: {remove_accents(f['nome'])}", 0)
        pdf.cell(90, 7, f"MATRICULA: {f.get('matricula', 'N/A')}", ln=True)
        pdf.cell(100, 7, f"SETOR: {remove_accents(f.get('setor', 'N/A'))}", 0)
        pdf.cell(90, 7, f"VINCULO: {remove_accents(f.get('vinculo', 'N/A'))}", ln=True)
        pdf.ln(5)
        
        pdf.set_font("Arial", 'B', 7)
        pdf.set_fill_color(200, 200, 200)
        headers = [("DATA", 25), ("QTD", 10), ("EPI", 60), ("C.A.", 20), ("TOKEN", 25), ("STATUS", 40)]
        for txt, w in headers:
            pdf.cell(w, 8, txt, 1, 0, 'C', fill=True)
        pdf.ln()
        
        pdf.set_font("Arial", '', 7)
        for _, r in df.iterrows():
            pdf.cell(25, 8, format_br(r['data_entrega']), 1, 0, 'C')
            pdf.cell(10, 8, str(r['quantidade']), 1, 0, 'C')
            pdf.cell(60, 8, remove_accents(str(r['epi_nome'])[:35]), 1)
            pdf.cell(20, 8, str(r['ca']), 1, 0, 'C')
            pdf.cell(25, 8, str(r['token']), 1, 0, 'C')
            pdf.cell(40, 8, remove_accents(str(r['status'])), 1, ln=True, align='C')
        
        pdf.ln(10)
        pdf.set_font("Arial", 'I', 8)
        pdf.multi_cell(0, 5, remove_accents(get_config("ficha_descricao", "")), align='J')
        
        return pdf.output(dest='S').encode('utf-8')
    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {e}")
        return None

# ============================================================================
# INICIALIZAÇÃO DE SESSÃO
# ============================================================================

def init_session_state():
    """Inicializa variáveis de sessão."""
    if 'logado' not in st.session_state:
        st.session_state.logado = False
    if 'login_time' not in st.session_state:
        st.session_state.login_time = None

init_session_state()

# ============================================================================
# AUTENTICAÇÃO
# ============================================================================

def check_session_timeout():
    """Verifica timeout de sessão."""
    if st.session_state.logado and st.session_state.login_time:
        tempo_decorrido = time.time() - st.session_state.login_time
        if tempo_decorrido > SESSION_TIMEOUT:
            st.session_state.logado = False
            st.warning("⏰ Sessão expirada. Faça login novamente.")
            st.stop()

def show_login():
    """Exibe tela de login."""
    st.markdown("<h1 style='text-align:center;'>🛡️ SESMT HUC</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        senha_input = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True):
            senha_correcta = get_config("app_password", "1234")
            
            if not senha_input:
                st.error("Digite a senha")
            elif senha_input == senha_correcta:
                st.session_state.logado = True
                st.session_state.login_time = time.time()
                st.success("✅ Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("❌ Senha incorreta")

# ============================================================================
# PÁGINAS
# ============================================================================

def show_dashboard():
    """Página: Dashboard"""
    st.title("📊 Indicadores de Gestão")
    
    try:
        stats = get_estatisticas()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("👥 Funcionários", stats['total_oficiais'])
        col2.metric("📦 Total Entregas", stats['total_entregas'])
        col3.metric("⏳ Assinaturas Pendentes", stats['entregas_pendentes'], delta_color="inverse")
        
        st.divider()
        st.subheader("🔴 Tokens Pendentes de Confirmação")
        
        entregas_pendentes = get_entregas_pendentes(10)
        
        if not entregas_pendentes:
            st.info("✅ Todas as entregas foram confirmadas!")
        else:
            for entrega in entregas_pendentes:
                col1, col2 = st.columns([4, 1])
                
                nome = entrega['oficiais']['nome']
                epi = entrega['ep']['nome']
                col1.write(f"🔴 **{nome}** | {epi}")
                
                url_base = get_config("url_sistema", "https://sesmt-huc-app.streamlit.app")
                token = entrega['token']
                
                mensagem = f"🛡️ *SESMT HUC*\nAssine seu EPI: {url_base}/?confirmar={token}"
                msg_encoded = urllib.parse.quote(mensagem)
                
                whatsapp = entrega['oficiais']['whatsapp']
                link_whatsapp = f"https://api.whatsapp.com/send?phone=55{whatsapp}&text={msg_encoded}"
                
                col2.markdown(f'<a href="{link_whatsapp}" target="_blank"><button style="background-color:#25D366; color:white; border:none; border-radius:5px; width:100%; cursor:pointer;">📲 REZAP</button></a>', unsafe_allow_html=True)
    
    except Exception as e:
        logger.error(f"Erro no dashboard: {e}")
        st.error(f"Erro ao carregar dashboard: {e}")

def show_funcionarios():
    """Página: Funcionários"""
    st.title("👥 Gestão de Colaboradores")
    
    tab1, tab2 = st.tabs(["➕ Novo", "🔍 Filtrar/Buscar"])
    
    with tab1:
        st.subheader("Cadastro de Novo Colaborador")
        
        with st.form("form_novo_funcionario", clear_on_submit=True):
            nome = st.text_input("Nome *")
            matricula = st.text_input("Matrícula *")
            
            setores = get_setores()
            setor = st.selectbox("Setor *", setores if setores else ["Nenhum"])
            
            funcoes = get_funcoes()
            funcao = st.selectbox("Função *", funcoes if funcoes else ["Nenhum"])
            
            data_admissao = st.date_input("Data de Admissão *", format="DD/MM/YYYY")
            whatsapp = st.text_input("WhatsApp (10 ou 11 dígitos) *")
            
            vinculos = get_vinculos()
            vinculo = st.selectbox("Vínculo *", vinculos if vinculos else ["Nenhum"])
            
            if st.form_submit_button("💾 Salvar"):
                # Validar
                val_nome = validar_nome(nome)
                val_mat = validar_matricula(matricula)
                val_zap = validar_whatsapp(whatsapp)
                
                erros = [msg for ok, msg in [val_nome, val_mat, val_zap] if not ok]
                
                if erros:
                    for erro in erros:
                        st.error(f"❌ {erro}")
                else:
                    try:
                        dados = {
                            "nome": nome,
                            "matricula": matricula,
                            "setor": setor,
                            "funcao": funcao,
                            "admissao": str(data_admissao),
                            "whatsapp": whatsapp,
                            "vinculo": vinculo,
                        }
                        
                        supabase.table(TABELAS["OFICIAIS"]).insert(dados).execute()
                        st.cache_data.clear()
                        st.success("✅ Funcionário cadastrado com sucesso!")
                    except Exception as e:
                        logger.error(f"Erro ao cadastrar: {e}")
                        st.error(f"❌ Erro ao cadastrar: {e}")
    
    with tab2:
        st.subheader("Buscar e Filtrar")
        
        df_oficiais = get_oficiais()
        
        if df_oficiais.empty:
            st.info("Nenhum funcionário cadastrado")
        else:
            col1, col2 = st.columns(2)
            
            busca_nome = col1.text_input("🔍 Buscar por nome")
            setores_unicos = df_oficiais['setor'].unique()
            filtro_setores = col2.multiselect("Filtrar por setor", setores_unicos)
            
            df_filtrado = df_oficiais.copy()
            
            if busca_nome:
                df_filtrado = df_filtrado[df_filtrado['nome'].str.contains(busca_nome, case=False, na=False)]
            
            if filtro_setores:
                df_filtrado = df_filtrado[df_filtrado['setor'].isin(filtro_setores)]
            
            if 'admissao' in df_filtrado.columns:
                df_filtrado['admissao'] = df_filtrado['admissao'].apply(format_br)
            
            st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

def show_entregar_epi():
    """Página: Entregar EPI"""
    st.title("🚀 Registro de Entrega de EPI")
    
    df_oficiais = get_oficiais()
    df_epis = get_epis()
    
    if df_oficiais.empty or df_epis.empty:
        st.warning("⚠️ Cadastre funcionários e EPIs antes de registrar entregas")
        return
    
    with st.form("form_entrega"):
        opcoes_colab = df_oficiais['matricula'] + " - " + df_oficiais['nome']
        colab_selecionado = st.selectbox("Selecione o Colaborador *", opcoes_colab)
        
        epi_nomes = df_epis['nome'].tolist()
        epis_selecionados = st.multiselect("Selecione os EPIs *", epi_nomes)
        
        quantidade = st.number_input("Quantidade de itens", min_value=1, value=1)
        
        if st.form_submit_button("✅ Registrar Entrega"):
            if not colab_selecionado or not epis_selecionados:
                st.error("❌ Selecione colaborador e EPIs")
            else:
                try:
                    idx_colab = df_oficiais[(df_oficiais['matricula'] + " - " + df_oficiais['nome']) == colab_selecionado].index[0]
                    id_func = df_oficiais.loc[idx_colab, 'id']
                    
                    token = gerar_token()
                    
                    sucesso = True
                    for epi_nome in epis_selecionados:
                        idx_epi = df_epis[df_epis['nome'] == epi_nome].index[0]
                        id_epi = df_epis.loc[idx_epi, 'id']
                        
                        dados_entrega = {
                            "id_func": int(id_func),
                            "id_epi": int(id_epi),
                            "token": token,
                            "quantidade": quantidade,
                            "status": STATUS_ENTREGA["PENDENTE"],
                            "data_entrega": datetime.now().isoformat(),
                        }
                        
                        supabase.table(TABELAS["ENTREGAS"]).insert(dados_entrega).execute()
                    
                    st.cache_data.clear()
                    st.success("✅ Entrega registrada com sucesso!")
                    st.info(f"🔑 Token: {token} - Envie pelo Dashboard")
                    st.balloons()
                
                except Exception as e:
                    logger.error(f"Erro ao registrar entrega: {e}")
                    st.error(f"❌ Erro: {e}")

def show_ficha_epi():
    """Página: Ficha de EPI"""
    st.title("📄 Ficha Individual (Histórico Total)")
    
    df_oficiais = get_oficiais()
    
    if df_oficiais.empty:
        st.info("Nenhum funcionário cadastrado")
        return
    
    funcionario_selecionado = st.selectbox("Selecione o Funcionário", df_oficiais['nome'])
    
    if funcionario_selecionado:
        oficial = df_oficiais[df_oficiais['nome'] == funcionario_selecionado].iloc[0]
        
        historico = get_historico_oficial(int(oficial['id']))
        
        if historico.empty:
            st.info("Nenhuma entrega registrada para este funcionário")
        else:
            if 'data_entrega' in historico.columns:
                ultima_entrega = historico.iloc[0]['data_entrega']
                dias_sem_entrega = dias_desde(ultima_entrega)
                
                if dias_sem_entrega >= 20:
                    st.warning(f"⚠️ Atenção: Sem entregas há {dias_sem_entrega} dias. Gerar nova ficha!")
            
            df_exibicao = historico.copy()
            if 'data_entrega' in df_exibicao.columns:
                df_exibicao['data_entrega'] = df_exibicao['data_entrega'].apply(format_br)
            
            st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
            
            pdf_bytes = create_pdf(dict(oficial), historico)
            
            if pdf_bytes:
                st.download_button(
                    label="📥 Baixar Histórico Completo",
                    data=pdf_bytes,
                    file_name=f"Ficha_{oficial['nome']}.pdf",
                    mime="application/pdf"
                )

def show_catalogo():
    """Página: Catálogo de EPIs"""
    st.title("📦 Catálogo de EPIs")
    
    with st.form("form_novo_epi"):
        nome_epi = st.text_input("Nome do EPI *")
        ca_epi = st.text_input("Número C.A. *")
        data_validade = st.date_input("Data de Validade", format="DD/MM/YYYY")
        
        if st.form_submit_button("💾 Salvar"):
            if not nome_epi or not ca_epi:
                st.error("Nome e C.A. são obrigatórios")
            else:
                try:
                    dados = {
                        "nome": nome_epi,
                        "ca": ca_epi,
                        "validade": str(data_validade),
                    }
                    
                    supabase.table(TABELAS["EP"]).upsert(dados, on_conflict="nome").execute()
                    st.cache_data.clear()
                    st.success("✅ EPI salvo com sucesso!")
                except Exception as e:
                    logger.error(f"Erro ao salvar EPI: {e}")
                    st.error(f"❌ Erro: {e}")
    
    st.divider()
    st.subheader("EPIs Cadastrados")
    
    df_epis = get_epis()
    if not df_epis.empty:
        if 'validade' in df_epis.columns:
            df_epis['validade'] = df_epis['validade'].apply(format_br)
        st.dataframe(df_epis, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum EPI cadastrado")

def show_configuracoes():
    """Página: Configurações"""
    st.title("⚙️ Painel do Administrador")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔗 Sistema", "📋 Vínculos", "🏢 Setores", "🛠️ Funções", "🔑 Senha/Texto"
    ])
    
    with tab1:
        st.subheader("Configurações do Sistema")
        url_sistema = st.text_input(
            "URL do Sistema",
            value=get_config("url_sistema", "https://sesmt-huc-app.streamlit.app")
        )
        
        if st.button("Salvar URL"):
            if set_config("url_sistema", url_sistema):
                st.cache_data.clear()
                st.success("✅ URL salva com sucesso!")
            else:
                st.error("❌ Erro ao salvar URL")
    
    with tab2:
        st.subheader("Gerenciar Vínculos")
        novo_vinculo = st.text_input("Novo Vínculo")
        
        if st.button("Adicionar Vínculo"):
            if novo_vinculo:
                try:
                    supabase.table(TABELAS["VINCULOS"]).insert({"nome": novo_vinculo}).execute()
                    st.cache_data.clear()
                    st.success("✅ Vínculo adicionado!")
                except Exception as e:
                    st.error(f"❌ Erro: {e}")
    
    with tab3:
        st.subheader("Gerenciar Setores")
        novo_setor = st.text_input("Novo Setor")
        
        if st.button("Adicionar Setor"):
            if novo_setor:
                try:
                    supabase.table(TABELAS["SETORES"]).insert({"nome": novo_setor}).execute()
                    st.cache_data.clear()
                    st.success("✅ Setor adicionado!")
                except Exception as e:
                    st.error(f"❌ Erro: {e}")
    
    with tab4:
        st.subheader("Gerenciar Funções")
        nova_funcao = st.text_input("Nova Função")
        
        if st.button("Adicionar Função"):
            if nova_funcao:
                try:
                    supabase.table(TABELAS["FUNCOES"]).insert({"nome": nova_funcao}).execute()
                    st.cache_data.clear()
                    st.success("✅ Função adicionada!")
                except Exception as e:
                    st.error(f"❌ Erro: {e}")
    
    with tab5:
        st.subheader("Segurança e Conteúdo")
        
        nova_senha = st.text_input("Nova Senha", type="password")
        if st.button("Mudar Senha"):
            if nova_senha:
                if set_config("app_password", nova_senha):
                    st.success("✅ Senha alterada com sucesso!")
                else:
                    st.error("❌ Erro ao alterar senha")
        
        st.divider()
        
        texto_ficha = st.text_area(
            "Termos da Ficha",
            value=get_config("ficha_descricao", ""),
            height=150
        )
        
        if st.button("Salvar Texto Legal"):
            if set_config("ficha_descricao", texto_ficha):
                st.success("✅ Texto salvo com sucesso!")
            else:
                st.error("❌ Erro ao salvar texto")

def show_consumo():
    """Página: Consumo Semanal"""
    st.title("📈 Balanço Semanal por Setor")
    st.info("📋 Funcionalidade em desenvolvimento")

def processar_confirmacao_epi():
    """Processa confirmação de recebimento de EPI via link."""
    if "confirmar" in st.query_params:
        token = st.query_params["confirmar"]
        
        if not token:
            st.error("❌ Token inválido")
            return
        
        try:
            res = supabase.table(TABELAS["ENTREGAS"]).update({"status": STATUS_ENTREGA["CONFIRMADO"]}).eq("token", token).execute()
            
            if res.data:
                st.balloons()
                st.success("🛡️ RECEBIMENTO CONFIRMADO COM SUCESSO!")
            else:
                st.error("❌ Token não encontrado ou já confirmado")
        except Exception as e:
            logger.error(f"Erro ao confirmar: {e}")
            st.error("❌ Erro ao confirmar recebimento")
        
        st.stop()

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Função principal."""
    
    # Verificar timeout
    check_session_timeout()
    
    # Exibir login se não autenticado
    if not st.session_state.logado:
        show_login()
        st.stop()
    
    # Menu
    with st.sidebar:
        st.markdown("### 🛡️ SESMT HUC")
        menu_opcao = st.radio(
            "Menu",
            list(MENU_OPTIONS.keys()),
            format_func=lambda x: MENU_OPTIONS[x]
        )
        
        st.divider()
        
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.logado = False
            st.rerun()
    
    # Renderizar página
    menu_funcoes = {
        "dashboard": show_dashboard,
        "entregar_epi": show_entregar_epi,
        "funcionarios": show_funcionarios,
        "catalogo": show_catalogo,
        "ficha_epi": show_ficha_epi,
        "consumo": show_consumo,
        "config": show_configuracoes,
    }
    
    if menu_opcao in menu_funcoes:
        menu_funcoes[menu_opcao]()
    
    # Processar confirmação
    processar_confirmacao_epi()

if __name__ == "__main__":
    main()
