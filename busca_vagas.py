import os
import json
import requests
from dotenv import load_dotenv

# Carrega as variáveis do ficheiro .env
load_dotenv()

TOKEN_BOT = os.getenv("TOKEN_BOT")
CHAT_ID = os.getenv("CHAT_ID")
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")

# --- CONFIGURAÇÕES ---
TOKEN_BOT = "8985157843:AAFmsnwK_GF4Eq6zOFm21CKHWazoQKY3Dyg"
CHAT_ID = "961991500"

# Credenciais da Adzuna
ADZUNA_APP_ID = "d62bf11a"
ADZUNA_APP_KEY = "7189db76cc1beafb956db2131fea7fcb"

# Arquivo para salvar os links das vagas que já foram enviadas
ARQUIVO_HISTORICO = "vagas_enviadas.json"

# Filtros Rígidos
SALARIO_MINIMO = 2000
TERMOS_ESTAGIO = ["estagio", "estágio", "intern", "trainee"]
TERMOS_PROGRAMACAO = ["programacao", "programação", "desenvolvimento", "developer", "dev", "software", "c#", "python", "java", "javascript", "typescript", ".net", "backend", "frontend", "fullstack"]
TERMOS_REMOTO = ["remoto", "home office", "teletrabalho", "remote"]

# Regiões de interesse para a Adzuna
ESTADOS_ALVO = ["Rio Grande do Sul", "Santa Catarina", "São Paulo"]


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


def buscar_vagas_adzuna(termo_busca="estagio desenvolvimento remoto", localizacao=""):
    """Busca vagas na API da Adzuna com salário mínimo de R$ 2.000."""
    if not ADZUNA_APP_ID or ADZUNA_APP_ID == "SEU_ADZUNA_APP_ID":
        return []

    url = "https://api.adzuna.com/v1/api/jobs/br/search/1"
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
                "local": f"{item.get('location', {}).get('display_name', localizacao or 'Brasil')} (Remoto)",
                "salario": texto_salario,
                "link": item.get("redirect_url"),
                "descricao": item.get("description", "")
            })
        return vagas
    except Exception as e:
        print(f"Erro na Adzuna ({localizacao}): {e}")
        return []


def buscar_vagas_jobicy():
    """Busca vagas remotas na Jobicy."""
    url = "https://jobicy.com/api/v2/remote-jobs?count=15&geo=brazil"
    try:
        resposta = requests.get(url)
        dados = resposta.json()
        
        vagas = []
        for item in dados.get("jobs", []):
            vagas.append({
                "titulo": item.get("jobTitle"),
                "empresa": item.get("companyName", "Não informada"),
                "local": "Remoto",
                "salario": "R$ 2.000,00+ (Remoto Internacional/Nacional)",
                "link": item.get("url"),
                "descricao": item.get("jobGeo", "")
            })
        return vagas
    except Exception as e:
        print(f"Erro na Jobicy: {e}")
        return []


def filtrar_vagas(lista_vagas):
    """Filtra rigorosamente por Estágio + Programação + Remoto."""
    vagas_filtradas = []
    
    for vaga in lista_vagas:
        texto_completo = f"{vaga['titulo']} {vaga.get('descricao', '')}".lower()
        
        eh_estagio = any(termo in texto_completo for termo in TERMOS_ESTAGIO)
        eh_programacao = any(tech in texto_completo for tech in TERMOS_PROGRAMACAO)
        eh_remoto = "remoto" in vaga["local"].lower() or any(term in texto_completo for term in TERMOS_REMOTO)
        
        if eh_estagio and eh_programacao and eh_remoto:
            vagas_filtradas.append(vaga)
            
    return vagas_filtradas


def main():
    print("Iniciando busca rigorosa de vagas (Estágio Remoto em Programação >= R$ 2.000)...")
    historico = carregar_historico()
    todas_vagas = []
    
    # 1. Jobicy (Vagas remotas)
    todas_vagas.extend(buscar_vagas_jobicy())
    
    # 2. Adzuna - Remoto + Programação por Estado Alvo
    for estado in ESTADOS_ALVO:
        print(f"Buscando vagas em: {estado}...")
        todas_vagas.extend(buscar_vagas_adzuna("estagio desenvolvimento remoto", localizacao=estado))
        todas_vagas.extend(buscar_vagas_adzuna("estagio python remoto", localizacao=estado))
        todas_vagas.extend(buscar_vagas_adzuna("estagio c# remoto", localizacao=estado))

    vagas_relevantes = filtrar_vagas(todas_vagas)
    
    novas_vagas = [v for v in vagas_relevantes if v["link"] not in historico]
    
    if not novas_vagas:
        print("Nenhuma nova vaga encontrada no momento.")
        return

    # LIMITE DE SEGURANÇA: Envia no máximo 5 vagas por execução para evitar acúmulo no Telegram
    LIMITE_VAGAS = 10
    vagas_para_enviar = novas_vagas[:LIMITE_VAGAS]

    enviar_mensagem_telegram(f"🎯 **{len(vagas_para_enviar)} nova(s) vaga(s) de Estágio Remoto em Programação (R$ 2.000+)!**\n")
    
    for vaga in vagas_para_enviar:
        mensagem = (
            f"📌 *{vaga['titulo']}*\n"
            f"🏢 *Empresa:* {vaga['empresa']}\n"
            f"📍 *Local:* {vaga['local']}\n"
            f"💰 *Bolsa/Salário:* {vaga['salario']}\n"
            f"🔗 [Candidatar-se na Vaga]({vaga['link']})\n"
        )
        enviar_mensagem_telegram(mensagem)
        historico.add(vaga["link"])

    salvar_historico(historico)
    print(f"Sucesso! {len(vagas_para_enviar)} vagas enviadas e histórico atualizado.")


if __name__ == "__main__":
    main()