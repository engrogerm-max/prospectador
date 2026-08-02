import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import re
import time

st.set_page_config(page_title="Prospectador Uni PRO", page_icon="📍", layout="wide")

# --- FUNÇÃO PARA DETECTAR WHATSAPP ---
def verificar_whatsapp(telefone):
    if not telefone or telefone == "N/A":
        return "N/A", "N/A"
    # Limpa número
    numeros = re.sub(r'\D', '', telefone)
    # Brasil: celular tem 11 dígitos e o 3º dígito é 9
    if len(numeros) >= 10:
        # Se tem 11 dígitos e começa com 9 no celular = alta chance de WhatsApp
        if len(numeros) == 11 and numeros[2] == '9':
            link = f"https://wa.me/55{numeros}?text=Ol%C3%A1%20{telefone}"
            return "✅ Sim - Provável WhatsApp 📱", link
        elif len(numeros) == 10: # Fixo
            link = f"https://wa.me/55{numeros}?text=Ol%C3%A1"
            return "❌ Fixo - Talvez não tenha WhatsApp ☎️", link
        elif len(numeros) == 13 and numeros.startswith("55"): # Já com 55
            if numeros[4] == '9':
                link = f"https://wa.me/{numeros}"
                return "✅ Sim - Provável WhatsApp 📱", link
    return "❓ Indefinido", f"https://wa.me/55{numeros}" if numeros else "N/A"

st.markdown("""
<style>
.stApp {background-color: #f8fafc;}
.big-title {font-size:30px; font-weight:900; color:#111827;}
.badge-whats {background:#dcfce7; color:#166534; padding:4px 10px; border-radius:20px; font-weight:700; font-size:12px;}
.badge-fixo {background:#fee2e2; color:#991b1b; padding:4px 10px; border-radius:20px; font-weight:700; font-size:12px;}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-title">📍 Prospectador Uni PRO - Busca Precisa</p>', unsafe_allow_html=True)
st.caption("Agora com filtro EXATO + Detector de WhatsApp")

with st.sidebar:
    st.header("🔑 1º Passo - Sua Chave")
    api_key = st.text_input("Google Places API Key", type="password")
    st.markdown("[Como pegar a chave? Clique aqui](https://console.cloud.google.com/apis/library/places-backend.googleapis.com)")
    
    st.divider()
    st.header("🎯 2º Passo - Filtros de Precisão")
    raio = st.slider("Raio de busca (metros)", 1000, 50000, 10000, step=1000)
    nota_min = st.slider("Avaliação mínima", 0.0, 5.0, 0.0, step=0.5)
    apenas_aberto = st.checkbox("Apenas comércios ABERTOS agora")
    
    st.divider()
    st.header("🚀 3º Passo - Por no Ar")
    st.markdown("""
    **Para leigo, passo a passo:**
    1. Crie conta no **github.com** (grátis)
    2. Crie repositório chamado `prospectador`
    3. Faça upload do arquivo `prospectador_web_v2.py`
    4. Vá em **streamlit.io/cloud** e clique em `New App`
    5. Selecione seu repositório e clique em `Deploy`
    6. Pronto! Link no ar.
    
    **Vídeo:** No YouTube pesquise `como hospedar streamlit github`
    """)

col1, col2 = st.columns([1,1])
with col1:
    busca = st.text_input("O QUE buscar? (EXATO)", "pizzaria", help="Digite exatamente o que quer. Ex: 'pizzaria', 'dentista 24h', 'oficina de motos honda'")
with col2:
    localidade = st.text_input("ONDE? Localidade exata", "São José do Rio Preto, SP", help="Seja específico: 'Centro, São José do Rio Preto, SP' é melhor que só 'Rio Preto'")

col3, col4 = st.columns([1,1])
with col3:
    termo_obrigatorio = st.text_input("Palavra que TEM QUE ter no nome (opcional)", "", help="Ex: Se buscar 'mercado', coloque 'atacadão' para filtrar só atacadões. Deixe vazio se não quiser.")
with col4:
    excluir = st.text_input("Excluir quem tem no nome (opcional)", "", help="Ex: 'fechado, falido'")

buscar = st.button("🔍 BUSCAR COM PRECISÃO AGORA", type="primary", use_container_width=True)

if buscar:
    if not api_key:
        st.error("⚠️ Cole sua API Key na barra lateral esquerda.")
        st.stop()

    with st.status(f"🔎 Procurando '{busca}' em '{localidade}' com precisão...", expanded=True) as status:
        # 1. Geocodifica a localidade para pegar lat/lng
        st.write(f"📍 Localizando '{localidade}' no mapa...")
        geo_url = "https://maps.googleapis.com/maps/api/geocode/json"
        geo_resp = requests.get(geo_url, params={"address": localidade, "key": api_key}).json()
        if not geo_resp.get("results"):
            st.error(f"Não achei a localidade '{localidade}'. Tente ser mais específico: ex: 'Centro, São José do Rio Preto, SP'")
            st.stop()
        lat = geo_resp["results"][0]["geometry"]["location"]["lat"]
        lng = geo_resp["results"][0]["geometry"]["location"]["lng"]
        st.write(f"✅ Local encontrado: {lat}, {lng}")

        # 2. Busca precisa com Nearby Search
        st.write(f"🎯 Buscando '{busca}' em raio de {raio}m...")
        resultados = []
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            "location": f"{lat},{lng}",
            "radius": raio,
            "keyword": busca, # keyword é mais preciso que query
            "key": api_key,
            "language": "pt-BR"
        }
        if apenas_aberto:
            params["opennow"] = True

        for pagina in range(3):
            resp = requests.get(url, params=params, timeout=20).json()
            if resp.get("status") not in ["OK", "ZERO_RESULTS"]:
                st.error(f"Erro API: {resp.get('status')} - {resp.get('error_message','')}")
                break
            
            for place in resp.get("results", []):
                nome = place.get("name","")
                # FILTRO DE PRECISÃO 1: nome contém termo?
                if termo_obrigatorio and termo_obrigatorio.lower() not in nome.lower():
                    continue
                if excluir and excluir.lower() in nome.lower():
                    continue
                # FILTRO DE PRECISÃO 2: avaliação
                rating = place.get("rating", 0)
                if rating < nota_min:
                    continue

                place_id = place.get("place_id")
                # Pega telefone
                telefone = "N/A"
                try:
                    details = requests.get("https://maps.googleapis.com/maps/api/place/details/json",
                        params={"place_id": place_id, "fields": "formatted_phone_number,formatted_address,website", "key": api_key, "language": "pt-BR"}, timeout=10).json()
                    telefone = details.get("result", {}).get("formatted_phone_number", "N/A")
                except:
                    pass

                eh_whats, link_whats = verificar_whatsapp(telefone)

                resultados.append({
                    "Nome": nome,
                    "Endereço": place.get("vicinity") or details.get("result", {}).get("formatted_address",""),
                    "Telefone": telefone,
                    "É WhatsApp?": eh_whats,
                    "Link WhatsApp": link_whats,
                    "Avaliação": rating,
                    "Total Avaliações": place.get("user_ratings_total",0),
                    "Link Maps": f"https://www.google.com/maps/place/?q=place_id:{place_id}",
                    "Aberto Agora": "Sim" if place.get("opening_hours", {}).get("open_now") else "Não / N/A"
                })

            token = resp.get("next_page_token")
            if not token:
                break
            params["pagetoken"] = token
            time.sleep(2.5)

        status.update(label=f"✅ Busca finalizada! {len(resultados)} resultados precisos", state="complete")

    if resultados:
        st.success(f"Encontrei {len(resultados)} resultados que batem EXATAMENTE com '{busca}'")
        df = pd.DataFrame(resultados)
        
        # Mostra tabela com cores
        st.dataframe(
            df,
            use_container_width=True,
            height=450,
            column_config={
                "Link Maps": st.column_config.LinkColumn("📍 Localizar"),
                "Link WhatsApp": st.column_config.LinkColumn("💬 Abrir WhatsApp"),
            }
        )

        # Excel com nome empresa + localidade
        nome_arquivo = f"{busca.replace(' ','_')}_{localidade.replace(' ','_').replace(',','')}_{datetime.now().strftime('%d%m%Y')}.xlsx"
        df.to_excel(nome_arquivo, index=False)
        with open(nome_arquivo, "rb") as f:
            st.download_button(f"💾 BAIXAR EXCEL: {nome_arquivo}", f, file_name=nome_arquivo, type="primary", use_container_width=True)

        st.markdown("### 📊 Resumo de WhatsApp")
        qtd_whats = len([r for r in resultados if "Sim" in r["É WhatsApp?"]])
        st.metric("Números que são provavelmente WhatsApp", f"{qtd_whats} de {len(resultados)}")

    else:
        st.warning("Nenhum resultado com esses filtros precisos. Tente aumentar o raio ou tirar o filtro de avaliação.")
        st.info("Dica: Use localidade mais específica. Ex: 'Rua XV de Novembro, Centro, São José do Rio Preto, SP' funciona melhor que só 'Rio Preto'.")

# PASSO A PASSO PARA LEIGO
st.divider()
st.header("📖 PASSO A PASSO COMPLETO PARA POR NO AR (LEIGO)")
st.markdown("""
#### **OPÇÃO 1 - MAIS FÁCIL (2 minutos, sem código):**
1. Acesse **https://streamlit.io/cloud** e clique em `Sign up` com seu Google
2. Baixe o arquivo `prospectador_web_v2.py` aqui embaixo
3. No Streamlit Cloud, clique em `New app` > `Upload file` > selecione o arquivo
4. Cole sua API Key quando pedir
5. Clique em `Deploy` - Pronto, seu link será `https://seu-nome.streamlit.app`

#### **OPÇÃO 2 - PROFISSIONAL (com domínio próprio):**
1. Crie conta no **github.com**
2. Crie novo repositório `meu-prospectador`
3. Envie o arquivo `prospectador_web_v2.py` e um arquivo `requirements.txt` com:
   ```
   streamlit
   requests
   pandas
   openpyxl
   ```
4. Vá no Streamlit Cloud e conecte seu GitHub
5. Seu site fica no ar 24h por dia grátis!

#### **O que mudou nessa versão PRO:**
- ✅ Busca por LAT/LNG (muito mais precisa)
- ✅ Filtro de raio (ex: só 5km do centro)
- ✅ Filtro de avaliação mínima
- ✅ Filtro de palavra obrigatória no nome
- ✅ Detector automático de WhatsApp (celular com 9º dígito)
- ✅ Link direto para abrir no WhatsApp
- ✅ Botão Localizar no Maps funcionando
- ✅ Excel salvo com nome da empresa + localidade
""")
