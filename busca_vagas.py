import os
import json
import requests
from dotenv import load_dotenv

# Carrega as variáveis do ficheiro .env
load_dotenv()

# Credenciais lidas via variáveis de ambiente
TOKEN_BOT = os.getenv("TOKEN_BOT", "8985157843:AAFmsnwK_GF4Eq6zOFm21CKHWazoQKY3Dyg")
CHAT_ID = os.getenv("CHAT_ID", "961991500")

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "d62bf11a")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "7189db76cc1beafb956db2131fea7fcb")

# Arquivo para salvar os links das vagas que já foram enviadas
ARQUIVO_HISTORICO = "vagas_enviadas.json"

# Filtros Rígidos atualizados
SALARIO_MINIMO = 1500
TERMOS_ESTAGIO = ["estagio", "estágio", "intern", "trainee"]

# Foco estrito em Python e C# + termos de desenvolvimento gerais
TERMOS_PROGRAMACAO = [
    "python", "c#", ".net", "django", "flask", "fastapi", "dotnet"
]

# Regiões de interesse (Santa Catarina, Porto Alegre e São Paulo)
ESTADOS_ALVO = ["Santa Catarina", "Porto Alegre", "São Paulo"]


def carregar_historico():
    """Carrega a lista de links já enviados para não repetir mensagens."""
    if os.path.exists(ARQUIVO_HISTORICO):
        with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def salvar_historico(historico):
    """Salva os links das vagas enviadas no arquivo local."""
    with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f:
        json.dump(list(historico), f, ensure_ascii=False, indent=2)


def enviar_mensagem_telegram(texto):
    """Envia uma mensagem formatada para o Telegram."""
    url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": texto,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erro ao enviar mensagem no Telegram: {e}")


def buscar_vagas_adzuna(termo_busca, localizacao=""):
    """Busca vagas na API da Adzuna com salário mínimo de R$ 2.000."""
    if not ADZUNA_APP_ID or ADZUNA_APP_ID == "SEU_ADZUNA_APP_ID":
        return []

    url = f"https://api.adzuna.com/v1/api/jobs/br/search/1"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "results_per_page": 15,
        "what": termo_busca,
        "where": localizacao,
        "salary_min": SALARIO_MINIMO,
        "content-type": "application/json"
    }

    try:
        resposta = requests.get(url, params=params)
        dados = resposta.json()
        
        vagas = []
        for item in dados.get("results", []):
            salario_min = item.get("salary_min", 0) or 0
            salario_max = item.get("salary_max", 0) or 0
            
            if salario_min >= SALARIO_MINIMO:
                texto_salario = f"R$ {salario_min:,.2f}"
            elif salario_max >= SALARIO_MINIMO:
                texto_salario = f"Até R$ {salario_max:,.2f}"
            else:
                texto_salario = "A partir de R$ 2.000,00 (estimado)"

            vagas.append({
                "titulo": item.get("title"),
                "empresa": item.get("company", {}).get("display_name", "Não informada"),
                "local": item.get('location', {}).get('display_name', localizacao),
                "salario": texto_salario,
                "link": item.get("redirect_url"),
                "descricao": item.get("description", "")
            })
        return vagas
    except Exception as e:
        print(f"Erro na Adzuna ({localizacao}): {e}")
        return []


def buscar_vagas_jobicy():
    """Busca vagas globais/Brasil na Jobicy."""
    url = "https://jobicy.com/api/v2/remote-jobs?count=20&geo=brazil"
    try:
        resposta = requests.get(url)
        dados = resposta.json()
        
        vagas = []
        for item in dados.get("jobs", []):
            vagas.append({
                "titulo": item.get("jobTitle"),
                "empresa": item.get("companyName", "Não informada"),
                "local": "Remoto (Brasil)",
                "salario": "R$ 2.000,00+ (Informado na vaga)",
                "link": item.get("url"),
                "descricao": item.get("jobGeo", "")
            })
        return vagas
    except Exception as e:
        print(f"Erro na Jobicy: {e}")
        return []


def buscar_vagas_remotive():
    """Busca vagas de software na API pública da Remotive."""
    url = "https://remotive.com/api/remote-jobs?category=software-dev&limit=30"
    try:
        resposta = requests.get(url)
        dados = resposta.json()
        
        vagas = []
        for item in dados.get("jobs", []):
            candidate_req = (item.get("candidate_required_location") or "").lower()
            if "brazil" in candidate_req or "anywhere" in candidate_req or "worldwide" in candidate_req or "latam" in candidate_req or candidate_req == "":
                vagas.append({
                    "titulo": item.get("title"),
                    "empresa": item.get("company_name", "Não informada"),
                    "local": f"Remoto ({candidate_req or 'Global'})",
                    "salario": item.get("salary") or "Não informado no anúncio",
                    "link": item.get("url"),
                    "descricao": item.get("description", "")
                })
        return vagas
    except Exception as e:
        print(f"Erro na Remotive: {e}")
        return []


def filtrar_vagas(lista_vagas):
    """Filtra por Estágio + Tecnologias + Localização."""
    print(f"Total de vagas brutas retornadas pelas APIs: {len(lista_vagas)}")
    vagas_filtradas = []
    
    for vaga in lista_vagas:
        texto_completo = f"{vaga['titulo']} {vaga.get('descricao', '')} {vaga['local']}".lower()
        
        eh_estagio = any(termo in texto_completo for termo in TERMOS_ESTAGIO)
        eh_tecnologia = any(tech in texto_completo for tech in TERMOS_PROGRAMACAO)
        
        local_vaga = vaga['local'].lower()
        atende_localizacao = any(
            regiao.lower() in local_vaga or regiao.lower() in texto_completo 
            for regiao in ESTADOS_ALVO
        ) or "remoto" in local_vaga or "remote" in local_vaga or "anywhere" in local_vaga
        
        if eh_estagio and eh_tecnologia and atende_localizacao:
            vagas_filtradas.append(vaga)
            
    print(f"Vagas que passaram em TODOS os filtros: {len(vagas_filtradas)}")
    return vagas_filtradas


def main():
    print("Iniciando busca (Estágio Python/C# - Florianópolis, Porto Alegre, SP e Remoto)...")
    historico = carregar_historico()
    todas_vagas = []
    
    # 1. Site 1: Jobicy (Remoto)
    todas_vagas.extend(buscar_vagas_jobicy())
    
    # 2. Site 2: Remotive (Remoto)
    todas_vagas.extend(buscar_vagas_remotive())
    
    # 3. Site 3: Adzuna (Presenciais e Remotas por Região Alvo)
    for regiao in ESTADOS_ALVO:
        todas_vagas.extend(buscar_vagas_adzuna("estagio python", localizacao=regiao))
        todas_vagas.extend(buscar_vagas_adzuna("estagio c#", localizacao=regiao))

    vagas_relevantes = filtrar_vagas(todas_vagas)
    
    # Remove duplicadas já enviadas anteriormente
    novas_vagas = [v for v in vagas_relevantes if v["link"] not in historico]
    
    if not novas_vagas:
        print("Nenhuma nova vaga encontrada no momento.")
        return

    # Limite para evitar spam no Telegram
    LIMITE_VAGAS = 10
    vagas_para_enviar = novas_vagas[:LIMITE_VAGAS]

    # Envia uma única mensagem unificada com todas as novas vagas filtradas
    mensagem_lote = f"🎯 *{len(vagas_para_enviar)} nova(s) vaga(s) de Estágio (Python/C#)*\n\n"
    
    for vaga in vagas_para_enviar:
        mensagem_lote += (
            f"📌 *{vaga['titulo']}*\n"
            f"🏢 *Empresa:* {vaga['empresa']}\n"
            f"📍 *Local:* {vaga['local']}\n"
            f"💰 *Bolsa/Salário:* {vaga['salario']}\n"
            f"🔗 [Candidatar-se]({vaga['link']})\n\n"
            f"-----------------------------------\n"
        )
        historico.add(vaga["link"])

    enviar_mensagem_telegram(mensagem_lote)
    salvar_historico(historico)
    print(f"Sucesso! {len(vagas_para_enviar)} vagas enviadas e histórico atualizado.")


if __name__ == "__main__":
    main()