
import streamlit as st
from supabase import create_client, Client
import random
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse
from fpdf import FPDF

# --- CREDENCIAIS SUPABASE ---
SUPABASE_URL = "aatkjhtrafuepwzzlrbm"
SUPABASE_KEY = "SeyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFhdGtqaHRyYWZ1ZXB3enpscmJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg2Mjg5MTYsImV4cCI6MjA5NDIwNDkxNn0.65izu7Zhc3kUZrVIRXGvVQ5o-Lhk-7PCK9CMg4zIwuk"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="SESMT - HUC Digital", layout="wide", page_icon="🛡️")

def formatar_data_br(data_str):
    try:
        dt = datetime.strptime(str(data_str).split('T')[0], '%Y-%m-%d')
        return dt.strftime('%d/%m/%Y')
    except: return data_str

def remover_acentos(texto):
    return str(texto).encode('latin-1', 'replace').decode('latin-1')

# --- PDF: FICHA DE EPI INDIVIDUAL ---
def gerar_pdf_ficha(f, df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 8, "HOSPITAL UNIVERSITARIO DO CEARA - HUC - ISGH", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    
    # CORREÇÃO SOLICITADA: APENAS CNPJ
    pdf.cell(0, 6, "CNPJ: 05.268.526/0024-67", ln=True, align='C') 
    pdf.ln(5)
    
    # TÍTULO COM NOME DO FUNCIONÁRIO
    pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", 'B', 11)
    titulo_ficha = f" FICHA DE EPI - {f['nome'].upper()}"
    pdf.cell(0, 10, remover_acentos(titulo_ficha), ln=True, align='L', fill=True); pdf.ln(2)
    
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(100, 7, f"NOME: {remover_acentos(f['nome'])}", 0)
    pdf.cell(90, 7, f"MATRICULA: {f['matricula']}", ln=True)
    pdf.cell(100, 7, f"FUNCAO: {remover_acentos(f['funcao'])}", 0)
    pdf.cell(90, 7, f"ADMISSAO: {formatar_data_br(f['admissao'])}", ln=True)
    pdf.cell(100, 7, f"SETOR: {remover_acentos(f['setor'])}", 0)
    pdf.cell(90, 7, f"VINCULO: {remover_acentos(f['vinculo'])}", ln=True); pdf.ln(5)
    
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
    texto_nr6 = 'Em conformidade com o item 6.5.1 alínea d da NR 6, que dispõe que cabe à organização, quanto ao EPI:\n"d) registrar o seu fornecimento ao empregado, podendo ser adotados livros, fichas ou sistema eletrônico, inclusive, por sistema biométrico;"'
    pdf.multi_cell(0, 5, remover_acentos(texto_nr6), align='J')
    return pdf.output(dest='S').encode('latin-1')

# --- PDF: RELATÓRIO DE CONSUMO POR SETOR ---
def gerar_pdf_consumo(setor, df_consumo, inicio, fim):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"RELATORIO DE CONSUMO - SETOR: {setor.upper()}", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, f"Periodo: {inicio} a {fim}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_fill_color(200, 200, 200); pdf.set_font("Arial", 'B', 10)
    pdf.cell(120, 8, "DESCRICAO DO EPI", 1, 0, 'C', fill=True)
    pdf.cell(40, 8, "QUANTIDADE", 1, ln=True, align='C', fill=True)
    
    pdf.set_font("Arial", '', 10)
    for _, r in df_consumo.iterrows():
        pdf.cell(120, 8, remover_acentos(r['epi_nome']), 1)
        pdf.cell(40, 8, str(r['quantidade']), 1, ln=True, align='C')
    
    return pdf.output(dest='S').encode('latin-1')

# --- LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.markdown('<h1 style="text-align:center;">🛡️ SESMT HUC</h1>', unsafe_allow_html=True)
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if senha == "1234": st.session_state.logado = True; st.rerun()
    st.stop()

res_url = supabase.table("oficiais").select("whatsapp").eq("matricula", "URL_SISTEMA").execute()
url_base = res_url.data[0]['whatsapp'] if res_url.data else "https://sesmt-huc-app.streamlit.app"

menu = st.sidebar.radio("MENU", ["📊 Dashboard", "🚀 Entregar EPI", "👥 Funcionários", "📦 Catálogo", "📄 Ficha de EPI", "📈 Consumo por Setor", "⚙️ Configurações"])

# --- DASHBOARD (COM REENVIAR) ---
if menu == "📊 Dashboard":
    st.markdown("### 📊 Monitoramento de Entregas")
    res = supabase.table("entregas").select("*, oficiais(nome, whatsapp), ep(nome)").order("id", desc=True).limit(15).execute()
    if res.data:
        for row in res.data:
            c1, c2 = st.columns([4, 1])
            status_txt = row['status']
            status_cor = "🔴" if "Pendente" in status_txt else "🟢"
            c1.write(f"{status_cor} **{row['oficiais']['nome']}** | {row.get('quantidade', 1)}x {row['ep']['nome']} | {status_txt}")
            if "Pendente" in status_txt:
                link = f"{url_base}/?confirmar={row['token']}"
                msg = urllib.parse.quote(f"🛡️ *SESMT HUC*\nAssinatura pendente: {row['ep']['nome']}\nLink: {link}")
                c2.markdown(f'<a href="https://api.whatsapp.com/send?phone=55{row["oficiais"]["whatsapp"]}&text={msg}" target="_blank"><button style="background-color:#25D366; color:white; border:none; padding:5px; border-radius:5px; cursor:pointer; width:100%;">📲 REENVIAR</button></a>', unsafe_allow_html=True)

# --- CONSUMO POR SETOR (NOVO) ---
elif menu == "📈 Consumo por Setor":
    st.markdown("### 📈 Relatório de Consumo por Setor")
    res_setores = supabase.table("oficiais").select("setor").execute()
    setores = sorted(list(set([r['setor'] for r in res_setores.data if r['setor']])))
    
    setor_sel = st.selectbox("Escolha o Setor", setores)
    data_inicio = st.date_input("Data Início", datetime.now() - timedelta(days=7))
    data_fim = st.date_input("Data Fim", datetime.now())
    
    if st.button("📊 Gerar Relatório de Consumo"):
        # Busca entregas do setor no intervalo
        res = supabase.table("entregas").select("quantidade, ep(nome), oficiais!inner(setor)").eq("oficiais.setor", setor_sel).gte("data_entrega", str(data_inicio)).lte("data_entrega", str(data_fim)).execute()
        
        if res.data:
            dados = [{"epi_nome": r['ep']['nome'], "quantidade": r['quantidade']} for r in res.data]
            df_c = pd.DataFrame(dados).groupby("epi_nome")["quantidade"].sum().reset_index()
            st.table(df_c)
            st.download_button("📥 Baixar PDF de Consumo", gerar_pdf_consumo(setor_sel, df_c, data_inicio, data_fim), f"Consumo_{setor_sel}.pdf")
        else:
            st.warning("Nenhum consumo registrado para este setor no período.")

# --- FICHA DE EPI ---
elif menu == "📄 Ficha de EPI":
    st.markdown("### 📄 Ficha de Entrega de EPI")
    df_f = pd.DataFrame(supabase.table("oficiais").select("*").not_.eq("matricula", "URL_SISTEMA").execute().data)
    if not df_f.empty:
        sel = st.selectbox("Selecione o Colaborador", df_f['matricula'] + " - " + df_f['nome'])
        f_d = df_f[df_f['matricula'] == sel.split(" - ")[0]].iloc[0]
        h_res = supabase.table("entregas").select("data_entrega, token, status, quantidade, ep(nome, ca, validade)").eq("id_func", int(f_d['id'])).execute()
        if h_res.data:
            h_data = [{"data_entrega": r['data_entrega'], "quantidade": r.get('quantidade', 1), "epi_nome": r['ep']['nome'], "ca": r['ep']['ca'], "validade_epi": r['ep']['validade'], "token": r['token'], "status": r['status']} for r in h_res.data]
            df_h = pd.DataFrame(h_data)
            if st.button(f"📥 Gerar Ficha de {f_d['nome']}"):
                st.download_button("Baixar Agora", gerar_pdf_ficha(f_d, df_h), f"Ficha_{f_d['nome']}.pdf")

# (O resto do código de Cadastro e Configurações continua igual)
