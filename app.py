"""
🛡️ SESMT HUC - Sistema Digital de Gestão de EPI (PRO VERSION)
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
# CONFIGURAÇÕES GERAIS
# ============================================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

st.set_page_config(page_title="SESMT HUC - Digital", layout="wide", page_icon="🛡️")

SUPABASE_URL = "https://aatkjhtrafuepwzzlrbm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFhdGtqaHRyYWZ1ZXB3enpscmJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg2Mjg5MTYsImV4cCI6MjA5NDIwNDkxNn0.65izu7Zhc3kUZrVIRXGvVQ5o-Lhk-7PCK9CMg4zIwuk"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("❌ Erro ao conectar ao banco de dados")
    st.stop()

HOSPITAL_NAME = "HOSPITAL UNIVERSITARIO DO CEARA - HUC"
CNPJ_HUC = "05.268.526/0024-67"
STATUS_ENTREGA = {"PENDENTE": "Pendente ⏳", "CONFIRMADO": "Confirmado ✅"}

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def format_br(date_str: str, include_time=False) -> str:
    if not date_str: return ""
    try:
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        return dt.strftime('%d/%m/%Y %H:%M') if include_time else dt.strftime('%d/%m/%Y')
    except:
        try: 
            return datetime.strptime(str(date_str).split('T')[0], '%Y-%m-%d').strftime('%d/%m/%Y')
        except: return str(date_str)

def dias_desde(date_str: str) -> int:
    try:
        dt = datetime.strptime(str(date_str).split('T')[0], '%Y-%m-%d')
        return (datetime.now() - dt).days
    except: return 0

def remove_accents(text: str) -> str:
    import unicodedata
    try:
        nfd = unicodedata.normalize('NFD', str(text))
        return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    except: return str(text)

def gerar_token() -> str:
    import uuid
    return str(uuid.uuid4())[:8].upper()

# ============================================================================
# BANCO DE DADOS (CACHE 2s PARA ATUALIZAÇÃO IMEDIATA)
# ============================================================================

@st.cache_data(ttl=2)
def get_table_data(table_name: str, order_by: str = None):
    try:
        query = supabase.table(table_name).select("*")
        if order_by: query = query.order(order_by)
        res = query.execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        logger.error(f"Erro {table_name}: {e}")
        return pd.DataFrame()

def get_config(key: str, default: str = "") -> str:
    try:
        res = supabase.table("configuracoes").select("valor").eq("chave", key).execute()
        return res.data[0]['valor'] if res.data else default
    except: return default

@st.cache_data(ttl=2)
def get_entregas_detalhadas():
    try:
        # CORREÇÃO: Adicionado o campo 'whatsapp' na requisição da tabela 'oficiais'
        res = supabase.table("entregas").select("*, oficiais(nome, setor, whatsapp), ep(nome, ca, validade)").execute()
        return res.data if res.data else []
    except: return []

# ============================================================================
# GERADORES DE PDF (FICHA E CONSUMO)
# ============================================================================

def create_pdf_ficha(f: dict, df: pd.DataFrame) -> bytes:
    try:
        from fpdf import FPDF
        pdf = FPDF(orientation='L') 
        pdf.add_page()
        
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 8, HOSPITAL_NAME, ln=True, align='C')
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 5, f"CNPJ: {CNPJ_HUC}", ln=True, align='C'); pdf.ln(5)
        
        pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, remove_accents(f"FICHA DE EPI - {f['nome'].upper()}"), ln=True, fill=True); pdf.ln(2)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(130, 6, f"NOME: {remove_accents(f['nome'])}", 0)
        pdf.cell(100, 6, f"MATRICULA: {f.get('matricula', 'N/A')}", ln=True)
        pdf.cell(130, 6, f"SETOR: {remove_accents(f.get('setor', 'N/A'))}", 0)
        pdf.cell(100, 6, f"VINCULO: {remove_accents(f.get('vinculo', 'N/A'))}", ln=True); pdf.ln(5)
        
        pdf.set_font("Arial", 'B', 7); pdf.set_fill_color(200, 200, 200)
        headers = [("DATA E HORA", 28), ("QTD", 10), ("DESCRIÇÃO DO EPI", 80), ("C.A.", 20), ("VAL. C.A.", 22), ("TOKEN", 22), ("STATUS / ASSINATURA", 45)]
        for txt, w in headers: pdf.cell(w, 8, txt, 1, 0, 'C', fill=True)
        pdf.ln()
        
        pdf.set_font("Arial", '', 7)
        for _, r in df.iterrows():
            pdf.cell(28, 8, str(r.get('data_hora', '')), 1, 0, 'C')
            pdf.cell(10, 8, str(r.get('quantidade', 1)), 1, 0, 'C')
            pdf.cell(80, 8, remove_accents(str(r.get('epi_nome', ''))[:45]), 1)
            pdf.cell(20, 8, str(r.get('ca', '')), 1, 0, 'C')
            pdf.cell(22, 8, str(r.get('validade_ca', '')), 1, 0, 'C')
            pdf.cell(22, 8, str(r.get('token', '')), 1, 0, 'C')
            pdf.cell(45, 8, remove_accents(str(r.get('status', ''))), 1, ln=True, align='C')
        
        pdf.ln(8); pdf.set_font("Arial", 'I', 8)
        pdf.multi_cell(0, 5, remove_accents(get_config("ficha_descricao", "")), align='J')
        return pdf.output(dest='S').encode('utf-8')
    except Exception as e:
        logger.error(f"Erro PDF Ficha: {e}"); return None

def create_pdf_consumo(df: pd.DataFrame, data_ref: str) -> bytes:
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 8, "BALANCO SEMANAL DE CONSUMO DE EPI", ln=True, align='C')
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 5, f"Gerado em: {data_ref} - {HOSPITAL_NAME}", ln=True, align='C'); pdf.ln(8)
        
        pdf.set_font("Arial", 'B', 9); pdf.set_fill_color(200, 200, 200)
        pdf.cell(70, 8, "SETOR", 1, 0, 'C', fill=True)
        pdf.cell(95, 8, "EQUIPAMENTO (EPI)", 1, 0, 'C', fill=True)
        pdf.cell(25, 8, "QTD TOTAL", 1, ln=True, align='C', fill=True)
        
        pdf.set_font("Arial", '', 8)
        for _, row in df.iterrows():
            pdf.cell(70, 8, remove_accents(str(row['Setor'])[:35]), 1)
            pdf.cell(95, 8, remove_accents(str(row['EPI'])[:50]), 1)
            pdf.cell(25, 8, str(row['Quantidade']), 1, ln=True, align='C')
            
        return pdf.output(dest='S').encode('utf-8')
    except Exception as e: return None

# ============================================================================
# LOGIN
# ============================================================================

if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛡️ SESMT HUC</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        senha = st.text_input("Senha de Acesso", type="password")
        if st.button("Entrar", use_container_width=True):
            if senha == get_config("app_password", "1234"): st.session_state.logado = True; st.rerun()
            else: st.error("❌ Senha incorreta")
    st.stop()

# ============================================================================
# MENU E ROTAS
# ============================================================================

menu = st.sidebar.radio("Navegação", ["📊 Dashboard", "🚀 Entregar EPI", "👥 Funcionários", "📦 Catálogo", "📄 Ficha de EPI", "📈 Consumo Semanal", "⚙️ Configurações"])
if st.sidebar.button("🚪 Sair", use_container_width=True): st.session_state.logado = False; st.rerun()

# ----------------------------------------------------------------------------
# 1. DASHBOARD & RADAR DE VENCIMENTO
# ----------------------------------------------------------------------------
if menu == "📊 Dashboard":
    st.title("📊 Painel Geral de Gestão")
    df_f = get_table_data("oficiais")
    df_e = get_table_data("entregas")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("👥 Funcionários Ativos", len(df_f))
    c2.metric("📦 Entregas Realizadas", len(df_e))
    pendentes = len(df_e[df_e['status'] == STATUS_ENTREGA["PENDENTE"]]) if not df_e.empty else 0
    c3.metric("⏳ Assinaturas Pendentes", pendentes, delta_color="inverse")
    st.divider()
    
    st.subheader("🚨 Radar de Validade (C.A.)")
    df_cat = get_table_data("ep")
    alertas_ca = 0
    if not df_cat.empty:
        for _, row in df_cat.iterrows():
            if row['validade']:
                dias_para_vencer = (datetime.strptime(row['validade'].split('T')[0], '%Y-%m-%d') - datetime.now()).days
                if dias_para_vencer < 0:
                    st.error(f"🔴 VENCIDO: {row['nome']} (C.A. {row['ca']}) venceu há {abs(dias_para_vencer)} dias!")
                    alertas_ca += 1
                elif dias_para_vencer <= 30:
                    st.warning(f"🟡 ATENÇÃO: {row['nome']} (C.A. {row['ca']}) vence em {dias_para_vencer} dias!")
                    alertas_ca += 1
    if alertas_ca == 0: st.success("✅ Todos os C.A.s do catálogo estão na validade.")
    
    st.divider()
    st.subheader("📲 Reenviar Tokens Pendentes")
    entregas_all = get_entregas_detalhadas()
    pendentes_list = [e for e in entregas_all if e['status'] == STATUS_ENTREGA["PENDENTE"]]
    if not pendentes_list: st.info("Tudo assinado! Nenhuma pendência.")
    else:
        for e in pendentes_list[:10]:
            col1, col2 = st.columns([4, 1])
            nome_f = e['oficiais']['nome'] if e['oficiais'] else 'Desconhecido'
            nome_epi = e['ep']['nome'] if e['ep'] else 'Desconhecido'
            col1.write(f"🔴 **{nome_f}** | Falta assinar: {nome_epi} (Qtd: {e['quantidade']})")
            
            # BLINDAGEM: Usando .get() para evitar o KeyError
            zap = e['oficiais'].get('whatsapp', '') if e['oficiais'] else ''
            link = f"{get_config('url_sistema')}/?confirmar={e['token']}"
            msg = urllib.parse.quote(f"🛡️ *SESMT HUC*\nAssine o recebimento do seu EPI ({nome_epi}):\n{link}")
            col2.markdown(f'<a href="https://api.whatsapp.com/send?phone=55{zap}&text={msg}" target="_blank"><button style="background-color:#25D366; color:white; border:none; border-radius:5px; width:100%;">Reenviar Link</button></a>', unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# 2. ENTREGAR EPI
# ----------------------------------------------------------------------------
elif menu == "🚀 Entregar EPI":
    st.title("🚀 Registrar Entrega de EPI")
    df_f = get_table_data("oficiais", "nome")
    df_epi = get_table_data("ep", "nome")
    
    if df_f.empty or df_epi.empty:
        st.warning("⚠️ Cadastre Funcionários e EPIs no menu lateral para liberar esta tela.")
    else:
        with st.form("form_entrega"):
            c1, c2 = st.columns(2)
            func_str = c1.selectbox("Colaborador *", df_f['matricula'].astype(str) + " - " + df_f['nome'])
            epi_str = c2.selectbox("Selecione o EPI *", df_epi['nome'])
            qtd = st.number_input("Quantidade sendo entregue (Ex: 2 luvas) *", min_value=1, value=1)
            
            if st.form_submit_button("✅ Registrar Entrega"):
                id_f = int(df_f[df_f['matricula'].astype(str) + " - " + df_f['nome'] == func_str].iloc[0]['id'])
                id_e = int(df_epi[df_epi['nome'] == epi_str].iloc[0]['id'])
                tk = gerar_token()
                
                supabase.table("entregas").insert({
                    "id_func": id_f, "id_epi": id_e, "token": tk, "quantidade": qtd,
                    "status": STATUS_ENTREGA["PENDENTE"], "data_entrega": datetime.now().isoformat()
                }).execute()
                st.cache_data.clear()
                st.success(f"✅ Sucesso! {qtd}x {epi_str} registrado para o colaborador.")
                st.info(f"🔑 Copie o Token ou vá no Dashboard para enviar o link: **{tk}**")
                st.balloons()

# ----------------------------------------------------------------------------
# 3. FUNCIONÁRIOS
# ----------------------------------------------------------------------------
elif menu == "👥 Funcionários":
    st.title("👥 Quadro de Colaboradores")
    t1, t2 = st.tabs(["➕ Novo", "🔍 Consultar"])
    
    with t1:
        s_list = [s['nome'] for s in supabase.table("setores").select("nome").execute().data] or ["Nenhum"]
        f_list = [f['nome'] for f in supabase.table("funcoes").select("nome").execute().data] or ["Nenhum"]
        v_list = [v['nome'] for v in supabase.table("vinculos").select("nome").execute().data] or ["Nenhum"]
        
        with st.form("cad_func", clear_on_submit=True):
            n, m = st.text_input("Nome Completo *").upper(), st.text_input("Matrícula *").upper()
            c1, c2 = st.columns(2)
            setor, funcao = c1.selectbox("Setor *", s_list), c2.selectbox("Função *", f_list)
            adm, zap, vinc = c1.date_input("Admissão", format="DD/MM/YYYY"), c2.text_input("WhatsApp (Só números)"), st.selectbox("Vínculo", v_list)
            
            if st.form_submit_button("💾 Salvar"):
                if not n or not m: st.error("Nome e Matrícula são obrigatórios.")
                else:
                    try:
                        supabase.table("oficiais").insert({"nome": n, "matricula": m, "setor": setor, "funcao": funcao, "admissao": str(adm), "whatsapp": zap, "vinculo": vinc}).execute()
                        st.cache_data.clear(); st.success("✅ Funcionário cadastrado!"); st.rerun()
                    except: st.error("❌ Matrícula já existe!")
    
    with t2:
        df = get_table_data("oficiais", "nome")
        if not df.empty:
            busca = st.text_input("Buscar por nome")
            if busca: df = df[df['nome'].str.contains(busca, case=False, na=False)]
            df['admissao'] = df['admissao'].apply(lambda x: format_br(x))
            st.dataframe(df[['nome', 'matricula', 'setor', 'funcao', 'vinculo', 'admissao']], use_container_width=True, hide_index=True)

# ----------------------------------------------------------------------------
# 4. CATÁLOGO
# ----------------------------------------------------------------------------
elif menu == "📦 Catálogo":
    st.title("📦 Catálogo de EPIs e Validades")
    with st.form("form_epi"):
        c1, c2, c3 = st.columns(3)
        n = c1.text_input("Nome do EPI *").upper()
        ca = c2.text_input("Número C.A. *")
        v = c3.date_input("Data de Validade do C.A.", format="DD/MM/YYYY")
        if st.form_submit_button("💾 Salvar EPI no Catálogo"):
            if not n: st.error("Nome é obrigatório.")
            else:
                supabase.table("ep").upsert({"nome": n, "ca": ca, "validade": str(v)}, on_conflict="nome").execute()
                st.cache_data.clear(); st.success("✅ Salvo!"); st.rerun()
    st.divider()
    df = get_table_data("ep", "nome")
    if not df.empty:
        df['validade'] = df['validade'].apply(lambda x: format_br(x))
        st.dataframe(df[['nome', 'ca', 'validade']], use_container_width=True, hide_index=True)

# ----------------------------------------------------------------------------
# 5. FICHA DE EPI (COM HISTÓRICO TOTAL E ALERTA)
# ----------------------------------------------------------------------------
elif menu == "📄 Ficha de EPI":
    st.title("📄 Ficha e Histórico (Completo)")
    df_f = get_table_data("oficiais", "nome")
    if df_f.empty: st.info("Cadastre um funcionário primeiro."); st.stop()
    
    sel = st.selectbox("Selecione o Funcionário para gerar a Ficha", df_f['nome'])
    func_dados = df_f[df_f['nome'] == sel].iloc[0]
    
    entregas_all = get_entregas_detalhadas()
    hist_func = [e for e in entregas_all if e['id_func'] == func_dados['id']]
    
    if not hist_func: st.info(f"Nenhuma retirada registrada para {sel}.")
    else:
        hist_func.sort(key=lambda x: x['data_entrega'], reverse=True)
        dias_sem_assinar = dias_desde(hist_func[0]['data_entrega'])
        if dias_sem_assinar >= 20:
            st.warning(f"⚠️ **ALERTA DE SEGURANÇA:** Este colaborador está há {dias_sem_assinar} dias sem gerar uma nova ficha. Atualize o arquivo físico/digital!")
        else: st.success(f"Ficha atualizada (Última movimentação há {dias_sem_assinar} dias).")
        
        lista_limpa = []
        for e in hist_func:
            lista_limpa.append({
                "data_hora": format_br(e['data_entrega'], include_time=True),
                "quantidade": e.get('quantidade', 1),
                "epi_nome": e['ep']['nome'] if e['ep'] else 'EPI Excluído',
                "ca": e['ep']['ca'] if e['ep'] else '-',
                "validade_ca": format_br(e['ep']['validade']) if e['ep'] else '-',
                "token": e['token'],
                "status": e['status']
            })
        df_hist = pd.DataFrame(lista_limpa)
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
        
        pdf = create_pdf_ficha(dict(func_dados), df_hist)
        if pdf: st.download_button("📥 BAIXAR FICHA DE EPI (PDF)", data=pdf, file_name=f"Ficha_EPI_{sel.replace(' ', '_')}.pdf", mime="application/pdf")

# ----------------------------------------------------------------------------
# 6. CONSUMO SEMANAL (BALANÇO AGRUPADO)
# ----------------------------------------------------------------------------
elif menu == "📈 Consumo Semanal":
    st.title("📈 Balanço Semanal (Consumo por Setor)")
    
    entregas_all = get_entregas_detalhadas()
    if not entregas_all: st.info("Sem dados de entrega ainda."); st.stop()
    
    entregas_all.sort(key=lambda x: x['data_entrega'], reverse=True)
    dias_ultimo_registro = dias_desde(entregas_all[0]['data_entrega'])
    if dias_ultimo_registro >= 7:
        st.error(f"🚨 **COBRANÇA:** Fazem {dias_ultimo_registro} dias desde o último balanço. Gere o PDF de consumo da semana!")
    else: st.success(f"Balanço em dia! Faltam {7 - dias_ultimo_registro} dias para o próximo fechamento.")
    
    limite_data = datetime.now() - timedelta(days=7)
    recentes = [e for e in entregas_all if datetime.fromisoformat(e['data_entrega'].replace('Z', '+00:00')).replace(tzinfo=None) >= limite_data]
    
    if not recentes: st.info("Nenhuma entrega nos últimos 7 dias.")
    else:
        lista_agrupada = []
        for e in recentes:
            lista_agrupada.append({
                "Setor": e['oficiais']['setor'] if e['oficiais'] else 'Desconhecido',
                "EPI": e['ep']['nome'] if e['ep'] else 'Desconhecido',
                "Quantidade": e.get('quantidade', 1)
            })
        df_agrupado = pd.DataFrame(lista_agrupada).groupby(['Setor', 'EPI'])['Quantidade'].sum().reset_index()
        
        st.write("#### Consumo dos últimos 7 dias agrupado:")
        st.dataframe(df_agrupado, use_container_width=True, hide_index=True)
        
        pdf_consumo = create_pdf_consumo(df_agrupado, datetime.now().strftime('%d/%m/%Y'))
        if pdf_consumo: st.download_button("📥 BAIXAR BALANÇO DE CONSUMO (PDF)", data=pdf_consumo, file_name=f"Balanco_Semanal_{datetime.now().strftime('%d_%m')}.pdf", mime="application/pdf")

# ----------------------------------------------------------------------------
# 7. CONFIGURAÇÕES
# ----------------------------------------------------------------------------
elif menu == "⚙️ Configurações":
    st.title("⚙️ Painel de Gestão Avançada")
    t1, t2, t3, t4, t5 = st.tabs(["📄 Texto Ficha", "🏢 Setores", "🛠️ Funções", "📋 Vínculos", "🔗 Sistema"])
    
    with t1:
        st.write("#### Descrição Legal (Aparece no rodapé da Ficha de EPI)")
        txt = st.text_area("Texto", value=get_config("ficha_descricao"), height=150)
        if st.button("Salvar Texto"): set_config("ficha_descricao", txt); st.success("✅")
    with t2:
        ns = st.text_input("Novo Setor").upper()
        if st.button("Adicionar") and ns:
            try: supabase.table("setores").insert({"nome": ns}).execute(); st.cache_data.clear(); st.success("✅"); st.rerun()
            except: st.error("Erro ou já existe.")
        st.data_editor(get_table_data("setores"), key="ed_s")
    with t3:
        nf = st.text_input("Nova Função").upper()
        if st.button("Adicionar ") and nf:
            try: supabase.table("funcoes").insert({"nome": nf}).execute(); st.cache_data.clear(); st.success("✅"); st.rerun()
            except: st.error("Erro ou já existe.")
        st.data_editor(get_table_data("funcoes"), key="ed_f")
    with t4:
        nv = st.text_input("Novo Vínculo").upper()
        if st.button(" Adicionar") and nv:
            try: supabase.table("vinculos").insert({"nome": nv}).execute(); st.cache_data.clear(); st.success("✅"); st.rerun()
            except: st.error("Erro ou já existe.")
        st.data_editor(get_table_data("vinculos"), key="ed_v")
    with t5:
        url = st.text_input("URL do App (Para o Link do WhatsApp)", value=get_config("url_sistema"))
        if st.button("Salvar URL"): set_config("url_sistema", url); st.cache_data.clear(); st.success("✅")
        st.divider()
        senha = st.text_input("Nova Senha Admin", type="password")
        if st.button("Mudar Senha") and senha: set_config("app_password", senha); st.success("✅")

# ----------------------------------------------------------------------------
# VERIFICADOR DE TOKEN (LINK DO WHATSAPP)
# ----------------------------------------------------------------------------
if "confirmar" in st.query_params:
    tk = st.query_params["confirmar"]
    if tk:
        res = supabase.table("entregas").update({"status": STATUS_ENTREGA["CONFIRMADO"]}).eq("token", tk).execute()
        if res.data: st.balloons(); st.success(f"🛡️ RECEBIMENTO CONFIRMADO!\nData e Hora: {datetime.now().strftime('%d/%m/%Y %H:%M')}"); st.stop()
        else: st.error("❌ Link inválido ou já confirmado."); st.stop()
