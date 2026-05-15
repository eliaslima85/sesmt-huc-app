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
# VERIFICADOR DE TOKEN (WHATSAPP) - CORRIGIDO
# ============================================================================
if "confirmar" in st.query_params:
    tk = st.query_params["confirmar"]
    if tk:
        res = supabase.table("entregas").update({"status": STATUS_ENTREGA["CONFIRMADO"]}).eq("token", tk).execute()
        if res.data: 
            st.balloons()
            st.success(f"🛡️ RECEBIMENTO CONFIRMADO!\nData e Hora: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            # Botão para limpar o link e voltar ao sistema normal
            if st.button("Voltar para o Painel de Gestão"):
                st.query_params.clear()
                st.rerun()
        else: 
            st.error("❌ Link inválido ou já confirmado.")
            if st.button("Ir para o Login"):
                st.query_params.clear()
                st.rerun()
        st.stop() 

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
# BANCO DE DADOS
# ============================================================================

@st.cache_data(ttl=2)
def get_table_data(table_name: str, order_by: str = None):
    try:
        query = supabase.table(table_name).select("*")
        if order_by: query = query.order(order_by)
        res = query.execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

def get_config(key: str, default: str = "") -> str:
    try:
        res = supabase.table("configuracoes").select("valor").eq("chave", key).execute()
        return res.data[0]['valor'] if res.data else default
    except: return default

def set_config(key: str, valor: str) -> bool:
    try:
        supabase.table("configuracoes").upsert({"chave": key, "valor": valor}, on_conflict="chave").execute()
        return True
    except: return False

@st.cache_data(ttl=2)
def get_entregas_detalhadas():
    try:
        res = supabase.table("entregas").select("*, oficiais(id, nome, setor, whatsapp, matricula, vinculo), ep(nome, ca, validade)").execute()
        return res.data if res.data else []
    except: return []

# ============================================================================
# GERADORES DE PDF
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
    except: return None

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
    except: return None

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
# MENU
# ============================================================================

menu = st.sidebar.radio("Navegação", ["📊 Dashboard", "🚀 Entregar EPI", "👥 Funcionários", "📦 Catálogo", "📄 Ficha de EPI", "📈 Consumo Semanal", "⚙️ Configurações"])
if st.sidebar.button("🚪 Sair", use_container_width=True):
    st.session_state.logado = False
    st.rerun()

# ----------------------------------------------------------------------------
# 1. DASHBOARD
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
    if not pendentes_list: st.info("Tudo assinado!")
    else:
        for e in pendentes_list[:10]:
            col1, col2 = st.columns([4, 1])
            nome_f = e['oficiais']['nome'] if e['oficiais'] else 'N/A'
            col1.write(f"🔴 **{nome_f}** | {e['ep']['nome']} (Qtd: {e['quantidade']})")
            zap = e['oficiais'].get('whatsapp', '') if e['oficiais'] else ''
            link = f"{get_config('url_sistema')}/?confirmar={e['token']}"
            msg = urllib.parse.quote(f"🛡️ *SESMT HUC*\nOlá {nome_f},\nAssine o recebimento do seu EPI:\n📦 *Item:* {e['ep']['nome']}\n🔢 *C.A.:* {e['ep']['ca']}\n📊 *Quantidade:* {e['quantidade']}\n🔗 {link}")
            col2.markdown(f'<a href="https://api.whatsapp.com/send?phone=55{zap}&text={msg}" target="_blank"><button style="background-color:#25D366; color:white; border:none; border-radius:5px; width:100%;">WhatsApp</button></a>', unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# 2. ENTREGAR EPI
# ----------------------------------------------------------------------------
elif menu == "🚀 Entregar EPI":
    st.title("🚀 Registrar Entrega de EPI")
    df_f = get_table_data("oficiais", "nome")
    df_epi = get_table_data("ep", "nome")
    if df_f.empty or df_epi.empty:
        st.warning("Cadastre funcionários e EPIs primeiro.")
    else:
        with st.form("form_entrega"):
            func_str = st.selectbox("Colaborador", df_f['matricula'] + " - " + df_f['nome'])
            epi_str = st.selectbox("Selecione o EPI", df_epi['nome'])
            qtd = st.number_input("Quantidade", min_value=1, value=1)
            if st.form_submit_button("✅ Registrar Entrega"):
                id_f = int(df_f[df_f['matricula'] + " - " + df_f['nome'] == func_str].iloc[0]['id'])
                id_e = int(df_epi[df_epi['nome'] == epi_str].iloc[0]['id'])
                tk = gerar_token()
                supabase.table("entregas").insert({"id_func": id_f, "id_epi": id_e, "token": tk, "quantidade": qtd, "status": STATUS_ENTREGA["PENDENTE"], "data_entrega": datetime.now().isoformat()}).execute()
                st.cache_data.clear(); st.success(f"Registrado! Token: {tk}"); st.balloons()

# ----------------------------------------------------------------------------
# 3. FUNCIONÁRIOS
# ----------------------------------------------------------------------------
elif menu == "👥 Funcionários":
    st.title("👥 Gestão de Pessoas")
    t1, t2 = st.tabs(["➕ Novo", "🔍 Consultar"])
    with t1:
        with st.form("cad_func", clear_on_submit=True):
            n, m = st.text_input("Nome").upper(), st.text_input("Matrícula").upper()
            s = st.selectbox("Setor", [x['nome'] for x in supabase.table("setores").select("nome").execute().data] or ["Nenhum"])
            f = st.selectbox("Função", [x['nome'] for x in supabase.table("funcoes").select("nome").execute().data] or ["Nenhum"])
            z, v = st.text_input("WhatsApp"), st.selectbox("Vínculo", [x['nome'] for x in supabase.table("vinculos").select("nome").execute().data] or ["Nenhum"])
            if st.form_submit_button("Salvar"):
                supabase.table("oficiais").insert({"nome": n, "matricula": m, "setor": s, "funcao": f, "whatsapp": z, "vinculo": v}).execute()
                st.cache_data.clear(); st.success("✅")
    with t2:
        df = get_table_data("oficiais", "nome")
        if not df.empty: st.dataframe(df, use_container_width=True, hide_index=True)

# ----------------------------------------------------------------------------
# 4. CATÁLOGO
# ----------------------------------------------------------------------------
elif menu == "📦 Catálogo":
    st.title("📦 Catálogo de EPIs")
    with st.form("form_epi"):
        n, ca, v = st.text_input("EPI").upper(), st.text_input("C.A."), st.date_input("Validade")
        if st.form_submit_button("Salvar"):
            supabase.table("ep").upsert({"nome": n, "ca": ca, "validade": str(v)}, on_conflict="nome").execute()
            st.cache_data.clear(); st.success("✅")
    df = get_table_data("ep", "nome")
    if not df.empty: st.dataframe(df, use_container_width=True, hide_index=True)

# ----------------------------------------------------------------------------
# 5. FICHA DE EPI - CORRIGIDA
# ----------------------------------------------------------------------------
elif menu == "📄 Ficha de EPI":
    st.title("📄 Ficha e Histórico")
    df_f = get_table_data("oficiais", "nome")
    if df_f.empty: st.info("Sem funcionários cadastrados.")
    else:
        sel = st.selectbox("Selecione o Colaborador", df_f['nome'])
        func_dados = df_f[df_f['nome'] == sel].iloc[0]
        
        # Puxa entregas detalhadas
        entregas_all = get_entregas_detalhadas()
        # Filtra histórico deste funcionário
        hist_func = [e for e in entregas_all if e['oficiais'] and e['oficiais']['id'] == func_dados['id']]
        
        if not hist_func:
            st.warning("Este funcionário ainda não possui retiradas de EPI.")
        else:
            # Mostra alerta de 20 dias
            hist_func.sort(key=lambda x: x['data_entrega'], reverse=True)
            dias = dias_desde(hist_func[0]['data_entrega'])
            if dias >= 20: st.warning(f"⚠️ Há {dias} dias sem novas movimentações.")

            # Monta tabela para visualização
            dados_tabela = []
            for e in hist_func:
                dados_tabela.append({
                    "data_hora": format_br(e['data_entrega'], include_time=True),
                    "quantidade": e['quantidade'],
                    "epi_nome": e['ep']['nome'] if e['ep'] else 'EPI Excluído',
                    "ca": e['ep']['ca'] if e['ep'] else '-',
                    "validade_ca": format_br(e['ep']['validade']) if e['ep'] else '-',
                    "token": e['token'],
                    "status": e['status']
                })
            df_hist = pd.DataFrame(dados_tabela)
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
            
            # Botão de download
            pdf = create_pdf_ficha(dict(func_dados), df_hist)
            if pdf:
                st.download_button("📥 BAIXAR FICHA (PDF)", data=pdf, file_name=f"Ficha_{sel}.pdf", mime="application/pdf")

# ----------------------------------------------------------------------------
# 6. CONSUMO SEMANAL
# ----------------------------------------------------------------------------
elif menu == "📈 Consumo Semanal":
    st.title("📈 Balanço Semanal")
    entregas = get_entregas_detalhadas()
    if not entregas: st.info("Sem dados.")
    else:
        limite = datetime.now() - timedelta(days=7)
        recentes = [e for e in entregas if datetime.fromisoformat(e['data_entrega'].replace('Z', '+00:00')).replace(tzinfo=None) >= limite]
        if not recentes: st.info("Nada nos últimos 7 dias.")
        else:
            lista = [{"Setor": e['oficiais']['setor'], "EPI": e['ep']['nome'], "Quantidade": e['quantidade']} for e in recentes if e['oficiais'] and e['ep']]
            df_ag = pd.DataFrame(lista).groupby(['Setor', 'EPI'])['Quantidade'].sum().reset_index()
            st.table(df_ag)
            pdf = create_pdf_consumo(df_ag, datetime.now().strftime('%d/%m/%Y'))
            if pdf: st.download_button("📥 BAIXAR BALANÇO (PDF)", data=pdf, file_name="Balanco_Semanal.pdf")

# ----------------------------------------------------------------------------
# 7. CONFIGURAÇÕES
# ----------------------------------------------------------------------------
elif menu == "⚙️ Configurações":
    st.title("⚙️ Configurações")
    t1, t2, t3, t4, t5 = st.tabs(["📄 Texto Legal", "🏢 Setores", "🛠️ Funções", "📋 Vínculos", "🔗 Sistema"])
    with t1:
        txt = st.text_area("Descrição da Ficha", value=get_config("ficha_descricao"), height=150)
        if st.button("Salvar Texto"): set_config("ficha_descricao", txt); st.success("✅")
    with t2:
        ns = st.text_input("Novo Setor").upper()
        if st.button("Add Setor") and ns: supabase.table("setores").insert({"nome": ns}).execute(); st.cache_data.clear(); st.rerun()
    with t3:
        nf = st.text_input("Nova Função").upper()
        if st.button("Add Função") and nf: supabase.table("funcoes").insert({"nome": nf}).execute(); st.cache_data.clear(); st.rerun()
    with t4:
        nv = st.text_input("Novo Vínculo").upper()
        if st.button("Add Vínculo") and nv: supabase.table("vinculos").insert({"nome": nv}).execute(); st.cache_data.clear(); st.rerun()
    with t5:
        url = st.text_input("URL do App", value=get_config("url_sistema"))
        if st.button("Salvar URL"): set_config("url_sistema", url); st.cache_data.clear(); st.success("✅")
        st.divider()
        senha = st.text_input("Nova Senha", type="password")
        if st.button("Mudar Senha") and senha: set_config("app_password", senha); st.success("✅")
