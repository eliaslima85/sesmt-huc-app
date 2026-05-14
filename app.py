import streamlit as st
from supabase import create_client, Client
import random
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse
from fpdf import FPDF
import requests
from io import BytesIO

# --- CREDENCIAIS SUPABASE ---
# COLOQUE SUAS CHAVES REAIS AQUI
SUPABASE_URL = "https://aatkjhtrafuepwzzlrbm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFhdGtqaHRyYWZ1ZXB3enpscmJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg2Mjg5MTYsImV4cCI6MjA5NDIwNDkxNn0.65izu7Zhc3kUZrVIRXGvVQ5o-Lhk-7PCK9CMg4zIwuk"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="SESMT - HUC Digital", layout="wide", page_icon="🛡️")

# --- FUNÇÕES DE APOIO ---
def obter_config(chave, padrao=""):
    try:
        res = supabase.table("configuracoes").select("valor").eq("chave", chave).execute()
        return res.data[0]['valor'] if res.data else padrao
    except: return padrao

def formatar_data_br(data_str):
    try:
        dt = datetime.strptime(str(data_str).split('T')[0], '%Y-%m-%d')
        return dt.strftime('%d/%m/%Y')
    except: return data_str

def remover_acentos(texto):
    return str(texto).encode('latin-1', 'replace').decode('latin-1')

# --- GERAÇÃO DE PDF (FICHA DE EPI INDIVIDUAL) ---
def gerar_pdf_ficha(f, df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 8, "HOSPITAL UNIVERSITARIO DO CEARA - HUC - ISGH", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, "CNPJ: 05.268.526/0024-67", ln=True, align='C'); pdf.ln(5)
    
    pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, remover_acentos(f" FICHA DE EPI - {f['nome'].upper()}"), ln=True, align='L', fill=True); pdf.ln(2)
    
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(100, 7, f"NOME: {remover_acentos(f['nome'])}", 0); pdf.cell(90, 7, f"MATRICULA: {f['matricula']}", ln=True)
    pdf.cell(100, 7, f"FUNCAO: {remover_acentos(f['funcao'])}", 0); pdf.cell(90, 7, f"ADMISSAO: {formatar_data_br(f['admissao'])}", ln=True)
    pdf.cell(100, 7, f"SETOR: {remover_acentos(f['setor'])}", 0); pdf.cell(90, 7, f"VINCULO: {remover_acentos(f['vinculo'])}", ln=True); pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 7)
    pdf.cell(20, 8, "DATA", 1, 0, 'C', fill=True); pdf.cell(10, 8, "QTD", 1, 0, 'C', fill=True)
    pdf.cell(56, 8, "DESCRICAO DO EPI", 1, 0, 'C', fill=True); pdf.cell(18, 8, "C.A.", 1, 0, 'C', fill=True)
    pdf.cell(22, 8, "VALID. C.A.", 1, 0, 'C', fill=True); pdf.cell(24, 8, "TOKEN", 1, 0, 'C', fill=True)
    pdf.cell(40, 8, "STATUS", 1, ln=True, align='C', fill=True)
    
    pdf.set_font("Arial", size=7)
    for _, r in df.iterrows():
        pdf.cell(20, 8, str(r['data_entrega']), 1, 0, 'C')
        pdf.cell(10, 8, str(r.get('quantidade', 1)), 1, 0, 'C')
        pdf.cell(56, 8, remover_acentos(str(r['epi_nome'])[:35]), 1)
        pdf.cell(18, 8, str(r['ca']), 1, 0, 'C')
        pdf.cell(22, 8, formatar_data_br(r.get('validade_epi', '')), 1, 0, 'C')
        pdf.cell(24, 8, str(r['token']), 1, 0, 'C')
        pdf.cell(40, 8, remover_acentos(str(r['status'])), 1, ln=True, align='C')
    
    pdf.ln(8); pdf.set_font("Arial", 'I', 8)
    texto_legal = obter_config("ficha_descricao", "O empregado declara ter recebido os EPIs...")
    pdf.multi_cell(0, 5, remover_acentos(texto_legal), align='J')
    return pdf.output(dest='S').encode('latin-1')

# --- PDF: CONSUMO POR SETOR ---
def gerar_pdf_consumo(setor, df_consumo, inicio, fim):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"RELATORIO DE CONSUMO - SETOR: {setor.upper()}", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, f"Periodo: {inicio} a {fim}", ln=True, align='C'); pdf.ln(10)
    pdf.set_fill_color(200, 200, 200); pdf.set_font("Arial", 'B', 10)
    pdf.cell(120, 8, "DESCRICAO DO EPI", 1, 0, 'C', fill=True)
    pdf.cell(40, 8, "QUANTIDADE", 1, ln=True, align='C', fill=True)
    pdf.set_font("Arial", '', 10)
    for _, r in df_consumo.iterrows():
        pdf.cell(120, 8, remover_acentos(r['epi_nome']), 1)
        pdf.cell(40, 8, str(r['quantidade']), 1, ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1')

# --- LOGIN SEGURO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.markdown('<h1 style="text-align:center;">🛡️ SESMT HUC</h1>', unsafe_allow_html=True)
    senha_input = st.text_input("Senha de Acesso", type="password")
    senha_db = obter_config("app_password", "1234")
    if st.button("Entrar"):
        if senha_input == senha_db:
            st.session_state.logado = True; st.rerun()
        else: st.error("Senha incorreta!")
    st.stop()

# --- MENU LATERAL ---
url_base = obter_config("url_sistema", "https://sesmt-huc-app.streamlit.app")
menu = st.sidebar.radio("MENU", ["📊 Dashboard", "🚀 Entregar EPI", "👥 Funcionários", "📦 Catálogo", "📄 Ficha de EPI", "📈 Consumo", "⚙️ Configurações"])

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.markdown("### 📊 Indicadores SESMT")
    t_f = len(supabase.table("oficiais").select("id").not_.eq("matricula", "URL_SISTEMA").execute().data)
    t_e = len(supabase.table("entregas").select("id").execute().data)
    pend = len(supabase.table("entregas").select("id").eq("status", "Pendente ⏳").execute().data)
    conf = len(supabase.table("entregas").select("id").eq("status", "Confirmado ✅").execute().data)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Funcionários", t_f)
    k2.metric("Total Entregas", t_e)
    k3.metric("Pendentes", pend, delta=pend, delta_color="inverse")
    k4.metric("Confirmados", conf)
    st.divider()
    res = supabase.table("entregas").select("*, oficiais(nome, whatsapp), ep(nome)").order("id", desc=True).limit(10).execute()
    if res.data:
        for row in res.data:
            c1, c2 = st.columns([4, 1])
            status = row['status']
            cor = "🔴" if "Pendente" in status else "🟢"
            c1.write(f"{cor} **{row['oficiais']['nome']}** | {row['ep']['nome']} | {status}")
            if "Pendente" in status:
                link = f"{url_base}/?confirmar={row['token']}"
                msg = urllib.parse.quote(f"🛡️ *SESMT HUC*\nAssinatura pendente: {row['ep']['nome']}\nLink: {link}")
                c2.markdown(f'<a href="https://api.whatsapp.com/send?phone=55{row["oficiais"]["whatsapp"]}&text={msg}" target="_blank"><button style="background-color:#25D366; color:white; border:none; border-radius:5px; padding:5px; cursor:pointer; width:100%;">📲 REENVIAR</button></a>', unsafe_allow_html=True)

# --- ENTREGAR EPI ---
elif menu == "🚀 Entregar EPI":
    st.markdown("### 🚀 Registrar Entrega")
    df_f = pd.DataFrame(supabase.table("oficiais").select("*").not_.eq("matricula", "URL_SISTEMA").execute().data)
    df_e = pd.DataFrame(supabase.table("ep").select("*").execute().data)
    if df_f.empty or df_e.empty:
        st.warning("⚠️ Cadastre Funcionários e EPIs primeiro.")
    else:
        colab = st.selectbox("Colaborador", df_f['matricula'] + " - " + df_f['nome'])
        sel_items = st.multiselect("Selecione os EPIs", options=df_e['nome'])
        quantidades = {}
        for item in sel_items:
            validade = df_e[df_e['nome'] == item].iloc[0]['validade']
            if validade and datetime.strptime(validade, '%Y-%m-%d').date() < datetime.now().date():
                st.error(f"⚠️ BLOQUEADO: O C.A. do item '{item}' venceu em {formatar_data_br(validade)}!")
                st.stop()
            quantidades[item] = st.number_input(f"Qtd: {item}", min_value=1, value=1)
        if st.button("Enviar para WhatsApp"):
            tk = str(random.randint(100000, 999999))
            f_d = df_f[df_f['matricula'] == colab.split(" - ")[0]].iloc[0]
            detalhes = []
            for item in sel_items:
                e_id = df_e[df_e['nome'] == item].iloc[0]['id']
                qtd = quantidades[item]
                detalhes.append(f"{qtd}x {item}")
                supabase.table("entregas").insert({"id_func": int(f_d['id']), "id_epi": int(e_id), "token": tk, "quantidade": qtd}).execute()
            link = f"{url_base}/?confirmar={tk}"
            msg = urllib.parse.quote(f"🛡️ *SESMT HUC*\nAssine o EPI: {', '.join(detalhes)}\nLink: {link}")
            st.markdown(f'<a href="https://api.whatsapp.com/send?phone=55{f_d["whatsapp"]}&text={msg}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:15px; border-radius:5px; font-weight:bold;">📲 ENVIAR AGORA</button></a>', unsafe_allow_html=True)

# --- FUNCIONÁRIOS ---
elif menu == "👥 Funcionários":
    st.markdown("### 👥 Gestão de Colaboradores")
    t1, t2 = st.tabs(["➕ Novo Cadastro", "🔧 Gerenciar"])
    with t1:
        with st.form("cad_f", clear_on_submit=True):
            n, m, s = st.text_input("Nome"), st.text_input("Matricula"), st.text_input("Setor")
            f, adm, w = st.text_input("Função"), st.date_input("Admissão"), st.text_input("WhatsApp (Ex: 85988887777)")
            v = st.selectbox("Vínculo", ["ISGH", "Cooperado", "Terceirizado"])
            if st.form_submit_button("Salvar"):
                supabase.table("oficiais").insert({"nome": n, "matricula": m, "setor": s, "funcao": f, "admissao": str(adm), "vinculo": v, "whatsapp": w}).execute()
                st.success("Cadastrado com sucesso!"); st.rerun()
    with t2:
        res_f = supabase.table("oficiais").select("*").not_.eq("matricula", "URL_SISTEMA").execute()
        if res_f.data:
            st.data_editor(pd.DataFrame(res_f.data), num_rows="dynamic", use_container_width=True)

# --- CATÁLOGO ---
elif menu == "📦 Catálogo":
    st.markdown("### 📦 Cadastro de EPIs")
    t1, t2 = st.tabs(["➕ Novo EPI", "🔧 Gerenciar"])
    with t1:
        with st.form("cad_e", clear_on_submit=True):
            n_epi, ca_epi, val_epi = st.text_input("Nome do EPI"), st.text_input("C.A."), st.date_input("Validade C.A.")
            if st.form_submit_button("Salvar"):
                supabase.table("ep").upsert({"nome": n_epi, "ca": ca_epi, "validade": str(val_epi)}, on_conflict="nome").execute()
                st.success("EPI Atualizado!"); st.rerun()
    with t2:
        res_e = supabase.table("ep").select("*").execute()
        if res_e.data:
            st.data_editor(pd.DataFrame(res_e.data), num_rows="dynamic", use_container_width=True)

# --- FICHA DE EPI ---
elif menu == "📄 Ficha de EPI":
    st.markdown("### 📄 Ficha de Entrega de EPI")
    df_f = pd.DataFrame(supabase.table("oficiais").select("*").not_.eq("matricula", "URL_SISTEMA").execute().data)
    if not df_f.empty:
        sel = st.selectbox("Escolher Colaborador", df_f['matricula'] + " - " + df_f['nome'])
        f_d = df_f[df_f['matricula'] == sel.split(" - ")[0]].iloc[0]
        h_res = supabase.table("entregas").select("data_entrega, token, status, quantidade, ep(nome, ca, validade)").eq("id_func", int(f_d['id'])).execute()
        if h_res.data:
            h_data = [{"data_entrega": r['data_entrega'], "quantidade": r.get('quantidade', 1), "epi_nome": r['ep']['nome'], "ca": r['ep']['ca'], "validade_epi": r['ep']['validade'], "token": r['token'], "status": r['status']} for r in h_res.data]
            df_h = pd.DataFrame(h_data)
            st.dataframe(df_h, use_container_width=True)
            if st.button("📥 Baixar PDF"):
                st.download_button("Clique aqui", gerar_pdf_ficha(f_d, df_h), f"Ficha_{f_d['nome']}.pdf")

# --- CONSUMO ---
elif menu == "📈 Consumo":
    st.markdown("### 📈 Relatório por Setor")
    res_s = supabase.table("oficiais").select("setor").execute()
    if res_s.data:
        setores = sorted(list(set([r['setor'] for r in res_s.data if r['setor']])))
        setor_sel = st.selectbox("Setor", setores)
        d1, d2 = st.date_input("Início", datetime.now()-timedelta(days=7)), st.date_input("Fim", datetime.now())
        if st.button("📊 Gerar Relatório"):
            res = supabase.table("entregas").select("quantidade, ep(nome), oficiais!inner(setor)").eq("oficiais.setor", setor_sel).gte("data_entrega", str(d1)).lte("data_entrega", str(d2)).execute()
            if res.data:
                dados = pd.DataFrame([{"epi_nome": r['ep']['nome'], "quantidade": r['quantidade']} for r in res.data]).groupby("epi_nome")["quantidade"].sum().reset_index()
                st.table(dados)
                st.download_button("Baixar PDF", gerar_pdf_consumo(setor_sel, dados, d1, d2), f"Consumo_{setor_sel}.pdf")

# --- CONFIGURAÇÕES ---
elif menu == "⚙️ Configurações":
    st.markdown("### ⚙️ Ajustes")
    tab1, tab2 = st.tabs(["🔗 Sistema", "🔑 Senha"])
    with tab1:
        nova_url = st.text_input("URL do App", url_base)
        termo = st.text_area("Termo NR-06", obter_config("ficha_descricao"))
        if st.button("Salvar Ajustes"):
            supabase.table("configuracoes").upsert({"chave": "url_sistema", "valor": nova_url}).execute()
            supabase.table("configuracoes").upsert({"chave": "ficha_descricao", "valor": termo}).execute()
            st.success("Salvo!")
    with tab2:
        n_senha = st.text_input("Nova Senha", type="password")
        if st.button("Mudar Senha"):
            supabase.table("configuracoes").upsert({"chave": "app_password", "valor": n_senha}).execute()
            st.success("Senha alterada!")

# --- LÓGICA DE ASSINATURA (TOKEN) ---
if "confirmar" in st.query_params:
    tk = st.query_params["confirmar"]
    supabase.table("entregas").update({"status": "Confirmado ✅"}).eq("token", tk).execute()
    st.balloons(); st.success("🛡️ RECEBIMENTO CONFIRMADO!"); st.stop()
