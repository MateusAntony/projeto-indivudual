import urllib.request
import os
import psycopg2
import psycopg2.extras
from bs4 import BeautifulSoup
import datetime


DATABASE_URL = os.environ["DATABASE_URL"]
agora = datetime.datetime.now()
data_formatada = agora.strftime("%d/%m/%Y %H:%M")

print(f"    Coletado em: {data_formatada}")


def get_connect():
    return psycopg2.connect(DATABASE_URL)

def init_db(connect):
    with connect.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS nba_standings (
                id SERIAL PRIMARY KEY,
                conferencia TEXT,
                posicao TEXT,
                time TEXT,
                situacao TEXT,
                vitorias INTEGER,
                derrotas INTEGER,
                percentual_vitorias TEXT,
                jogos_atras_lider TEXT,
                resultado_casa TEXT,
                resultado_fora TEXT,
                resultado_divisao TEXT,
                resultado_conferencia TEXT,
                media_pontos_marcados NUMERIC,
                media_pontos_sofridos NUMERIC,
                saldo_pontos NUMERIC,
                sequencia_atual TEXT,
                ultimos_10_jogos TEXT,
                data_coleta TEXT
            );
        """)
    connect.commit()

def insert_data(connect,linhas):
    with connect.cursor() as cur:
        psycopg2.extras.execute_batch(cur, """
            INSERT INTO nba_standings (
                conferencia, posicao, time, situacao, vitorias, derrotas, percentual_vitorias,
                jogos_atras_lider, resultado_casa, resultado_fora, resultado_divisao,
                resultado_conferencia, media_pontos_marcados, media_pontos_sofridos,
                saldo_pontos, sequencia_atual, ultimos_10_jogos, data_coleta
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s,%s, %s, %s,%s, %s, %s,%s
            );
        """, linhas)
    connect.commit()



url = "https://www.espn.com/nba/standings"
page = urllib.request.urlopen(url)
html = page.read().decode("utf-8")
soup = BeautifulSoup(html, "lxml")

conferencias = soup.find_all("div", class_="standings__table")

colunas = ["Conferencia","Posicao","Time","Situacao","Vitorias","Derrotas","Percentual_Vitorias","Jogos_Atras_Lider","Resultado_Casa","Resultado_Fora","Resultado_Divisao","Resultado_Conferencia","Media_Pontos_Marcados","Media_Pontos_Sofridos","Saldo_Pontos","Sequencia_Atual","Ultimos_10_Jogos", "Data_Coleta"]

situacao_dic = {"x --": "Classificado para Playoffs","y --": "Campeao da Divisao","e --": "Eliminado dos Playoffs","z --": " Melhor campanha","-": "Em disputa"}

linhas = []
print(f"\n{'POS':<3} {'TIME':<22} {'SITUAÇÃO':<27} {'V':>3} {'D':>3} {'%':>6} {'JD':>5} {'CASA':>7} {'FORA':>7} {'DIV':>7} {'CONF':>7} {'PPG':>6} {'OPP':>6} {'SALD':>5} {'SEQ':>5} {'U10':>6} ")
print("-" * 135)
for conferencia in conferencias:
    titulo = conferencia.find("div", class_="Table__Title")
    nome_conferencia = titulo.text.strip() 
    linhas_times = conferencia.find("table", class_="Table--fixed-left").find_all("tr", class_="Table__TR--sm")
    linhas_estatisticas = conferencia.find("div", class_="Table__Scroller").find_all("tr", class_="Table__TR--sm")

    for linha_time, linha_estatistica in zip(linhas_times, linhas_estatisticas):
        nome_franquia = linha_time.find("span", class_="hide-mobile")
        nome = nome_franquia.text.strip()

        posicao_franquia = linha_time.find("span", class_="team-position")
        if posicao_franquia:
            posicao = posicao_franquia.text.strip()
        else:
                posicao = "-"

        classificacao_franquia = linha_time.find("span", class_="dib")
        if classificacao_franquia:
            sigla_classificacao = classificacao_franquia.text.strip()
        else:
            sigla_classificacao = ""
            
        situacao = situacao_dic.get(sigla_classificacao,"Em disputa")

        estatisticas = []

        elementos_estatistica = linha_estatistica.find_all("span", class_="stat-cell")

        for elemento in elementos_estatistica:
            estatisticas.append(elemento.text.strip())

        vitorias = estatisticas[0]
        derrotas = estatisticas[1]
        porcentagem_vitoria = estatisticas[2]
        jogos_atras = estatisticas[3]
        casa = estatisticas[4]
        fora = estatisticas[5]
        divisao = estatisticas[6]
        conferencia = estatisticas[7]
        pontos_por_jogo = estatisticas[8]
        pontos_adversario = estatisticas[9]
        saldo = estatisticas[10]
        sequencia = estatisticas[11]
        ultimos_10 = estatisticas[12]

        print(f"{posicao:<3} {nome:<22} {situacao:<27} {vitorias:>3} {derrotas:>3} {porcentagem_vitoria:>6} {jogos_atras:>5} {casa:>7} {fora:>7} {divisao:>7} {conferencia:>7} {pontos_por_jogo:>6} {pontos_adversario:>6} {saldo:>5} {sequencia:>5} {ultimos_10:>6}")
        linhas.append([nome_conferencia,posicao,nome,situacao,int(vitorias),int(derrotas),porcentagem_vitoria,jogos_atras,casa,fora,divisao,conferencia,float(pontos_por_jogo),float(pontos_adversario),float(saldo),sequencia,ultimos_10,data_formatada])

connect= get_connect()
init_db(connect)
insert_data(connect,linhas)
connect.close()
