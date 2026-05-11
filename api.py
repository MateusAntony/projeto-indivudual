from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import psycopg2 
import os
import psycopg2.extras
from typing import Optional
import json
from decimal import Decimal
from fastapi.middleware.cors import CORSMiddleware 

DATABASE_URL = os.environ["DATABASE_URL"]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
def get_conn():
    try:
        return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    except psycopg2.OperationalError as e:
        raise HTTPException(status_code=503, detail=f"Erro ao conectar ao banco: {e}")
 
 
def serializar(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Tipo não serializável: {type(obj)}")

def fetchall(conn, sql: str, params: list = []) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        return json.loads(json.dumps([dict(r) for r in rows], default=serializar))

def fetchone(conn, sql: str, params: list = []) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return json.loads(json.dumps(dict(row), default=serializar)) if row else None
    

#todos os times, filtros opcionais por conferência, situação
@app.get("/standings")
def get_standings(
    conferencia: Optional[str] = Query(None),
    situacao:    Optional[str] = Query(None)
):
    sql = "SELECT * FROM nba_standings WHERE 1=1"
    params =[]

    if conferencia:
        sql += " AND conferencia ILIKE %s"
        params.append(f"%{conferencia}%")
    if situacao:
        sql += " AND situacao ILIKE %s"
        params.append(f"%{situacao}%")
 
    sql += " ORDER BY conferencia, posicao"
 
    with get_conn() as conn:
        rows = fetchall(conn, sql, params)
 
    if not rows:
        raise HTTPException(status_code=404, detail="Nenhum registro encontrado.")
 
    return JSONResponse(content={"total": len(rows), "standings": rows})


# times da conferência
@app.get("/standings/conferencia/{nome}")
def get_por_conferencia(nome: str):
    with get_conn() as conn:
        rows = fetchall(
            conn,
            "SELECT * FROM nba_standings WHERE conferencia ILIKE %s ORDER BY posicao",
            [f"%{nome}%"]
        )
 
    if not rows:
        raise HTTPException(status_code=404, detail=f"Conferência '{nome}' não encontrada.")
 
    return JSONResponse(content={"conferencia": rows[0]["conferencia"], "total": len(rows), "times": rows})

#Pelo nome do time, case-insensitive
@app.get("/standings/time/{nome}" )
def get_time(nome: str):
    with get_conn() as conn:
        rows = fetchall(
            conn,
            "SELECT * FROM nba_standings WHERE time ILIKE %s ORDER BY data_coleta DESC",
            [f"%{nome}%"]
        )
 
    if not rows:
        raise HTTPException(status_code=404, detail=f"Time '{nome}' não encontrado.")
 
    return JSONResponse(content={"total": len(rows), "resultado": rows})

#classificados por playoffs
@app.get("/standings/playoff")
def get_playoff(conferencia: Optional[str]=Query(None)):
    sql="SELECT * FROM nba_standings WHERE posicao BETWEEN 1 AND 6"
    params=[]

    if conferencia:
        sql += " AND conferencia ILIKE %s"
        params.append(f"%{conferencia}%")

    sql += " ORDER BY conferencia, posicao"
    with get_conn() as conn:
        rows = fetchall(conn, sql, params)
    if not rows:
        raise HTTPException(status_code=404, detail="Nenhum time classificado encontrado.")
    return JSONResponse(content={"total": len(rows), "times": rows})

#Eliminados do playoffs
@app.get("/standings/eliminados")
def get_eliminados(conferencia: Optional[str]=Query(None)):
    sql="SELECT * FROM nba_standings WHERE situacao ILIKE %s"
    params=["%Eliminado dos Playoffs%"]

    if conferencia:
        sql += " AND conferencia ILIKE %s"
        params.append(f"%{conferencia}%")

    sql += " ORDER BY conferencia, vitorias DESC"
    with get_conn() as conn:
        rows = fetchall(conn, sql, params)
    if not rows:
        raise HTTPException(status_code=404, detail="Nenhum time eliminado encontrado.")
    return JSONResponse(content={"total": len(rows), "times": rows})

#Em disputa do playin
@app.get("/standings/playin")
def get_playin(conferencia: Optional[str]=Query(None)):
    sql="SELECT * FROM nba_standings WHERE posicao BETWEEN 7 AND 10"
    params=[]

    if conferencia:
        sql += " AND conferencia ILIKE %s"
        params.append(f"%{conferencia}%")

    sql += " ORDER BY conferencia, posicao "
    with get_conn() as conn:
        rows = fetchall(conn, sql, params)
    if not rows:
        raise HTTPException(status_code=404, detail="Nenhum time em disputa encontrado.")
    return JSONResponse(content={"total": len(rows), "times": rows})
#Desempenho em casa
@app.get("/standings/casa")
def get_casa(conferencia: Optional[str]=Query(None)):
    sql="""
        SELECT *,
               CAST(SPLIT_PART(resultado_casa, '-', 1) AS INTEGER) AS vitorias_casa
        FROM nba_standings
        WHERE 1=1
    """
    params=[]

    if conferencia:
        sql += " AND conferencia ILIKE %s"
        params.append(f"%{conferencia}%")

    sql += " ORDER BY vitorias_casa DESC"
    with get_conn() as conn:
        rows = fetchall(conn, sql, params)
    if not rows:
        raise HTTPException(status_code=404, detail="Nenhum time com desempenho em casa encontrado.")
    return JSONResponse(content={"total": len(rows), "ranking_casa": rows})

@app.get("/standings/fora")
def get_ranking_fora(
    conferencia: Optional[str] = Query(None),
):
    """Ranking dos times por número de vitórias fora de casa."""
    sql, params = """
        SELECT *,
               CAST(SPLIT_PART(resultado_fora, '-', 1) AS INTEGER) AS vitorias_fora
        FROM nba_standings
        WHERE 1=1
    """, []
    if conferencia:
        sql += " AND conferencia ILIKE %s"
        params.append(f"%{conferencia}%")
        
    sql += " ORDER BY vitorias_fora DESC"
 
    with get_conn() as conn:
        rows = fetchall(conn, sql, params)
    if not rows:
        raise HTTPException(status_code=404, detail="Nenhum dado encontrado.")
    return JSONResponse(content={"total": len(rows), "ranking_fora": rows})

#Times por divsão
@app.get("/standings/divisao/{nome}")
def get_divisao(
    nome: str,
):
    
    divisoes = {
        "atlantico":   ["Celtics", "Nets", "Knicks", "76ers", "Raptors"],
        "central":    ["Bulls", "Cavaliers", "Pistons", "Pacers", "Bucks"],
        "sudeste":  ["Hawks", "Hornets", "Heat", "Magic", "Wizards"],
        "noroeste":  ["Nuggets", "Timberwolves", "Thunder", "Trail Blazers", "Jazz"],
        "pacifico":    ["Warriors", "Clippers", "Lakers", "Suns", "Kings"],
        "sudoeste":  ["Mavericks", "Rockets", "Grizzlies", "Pelicans", "Spurs"],
    }
 
    chave = nome.lower()
    if chave not in divisoes:
        raise HTTPException(
            status_code=400,
            detail=f"Divisão '{nome}' inválida. Use: {', '.join(divisoes.keys())}"
        )
 
    times = divisoes[chave]
    condicoes = " OR ".join(["time ILIKE %s"] * len(times))
    sql = f"SELECT * FROM nba_standings WHERE ({condicoes})"
    params = []
    for t in times:
        params.append(f"%{t}%") 
    
 
    with get_conn() as conn:
        rows = fetchall(conn, sql, params)
    if not rows:
        raise HTTPException(status_code=404, detail=f"Nenhum time encontrado para a divisão '{nome}'.")
    return JSONResponse(content={"divisao": nome.capitalize(), "total": len(rows), "times": rows})

#melhores ataques
@app.get("/rankings/ataque")
def get_ataque(n:int= Query(30, ge=1, le=30),conferencia: Optional[str] = Query(None)):
    sql = "SELECT * FROM nba_standings WHERE 1=1"
    params =[]

    if conferencia:
        sql += " AND conferencia ILIKE %s"
        params.append(f"%{conferencia}%")
 
    sql += " ORDER BY media_pontos_marcados  DESC LIMIT %s"
    params.append(n)
 
    with get_conn() as conn:
        rows = fetchall(conn, sql, params)
 
    if not rows:
        raise HTTPException(status_code=404, detail="Nenhum registro encontrado.")
 
    return JSONResponse(content={"total": len(rows), "ranking_ataque": rows})

#melhores defesas
@app.get("/rankings/defesa")
def get_defesa(n:int= Query(30, ge=1, le=30),conferencia: Optional[str] = Query(None)):
    sql = "SELECT * FROM nba_standings WHERE 1=1"
    params =[]

    if conferencia:
        sql += " AND conferencia ILIKE %s"
        params.append(f"%{conferencia}%")
 
    sql += " ORDER BY media_pontos_sofridos ASC LIMIT %s"
    params.append(n)
 
    with get_conn() as conn:
        rows = fetchall(conn, sql, params)
 
    if not rows:
        raise HTTPException(status_code=404, detail="Nenhum registro encontrado.")
 
    return JSONResponse(content={"total": len(rows), "ranking_defesa": rows})

#Compara dois times
@app.get("/comparar", summary="Comparar dois times")
def comparar_times(
    time1:  str           = Query(..., description="Nome do primeiro time"),
    time2:  str           = Query(..., description="Nome do segundo time"),
):
    """ /comparar?time1=Lakers&time2=Celtics"""
    def buscar(conn, nome):
        sql = "SELECT * FROM nba_standings WHERE time ILIKE %s"
        params = [f"%{nome}%"]
        
        sql += " ORDER BY data_coleta DESC LIMIT 1"
        return fetchone(conn, sql, params)
 
    with get_conn() as conn:
        t1 = buscar(conn, time1)
        t2 = buscar(conn, time2)
 
    if not t1:
        raise HTTPException(status_code=404, detail=f"Time '{time1}' não encontrado.")
    if not t2:
        raise HTTPException(status_code=404, detail=f"Time '{time2}' não encontrado.")
 
    # Vantagens
    vantagens = {}
    campos = {
        "vitorias":              ("maior", "mais vitórias"),
        "saldo_pontos":          ("maior", "melhor saldo"),
        "media_pontos_marcados": ("maior", "melhor ataque"),
        "media_pontos_sofridos": ("menor", "melhor defesa"),
        "percentual_vitorias":   ("maior", "maior aproveitamento"),
    }
 
    for campo in campos:
        criterio = campos[campo][0]
        descricao = campos[campo][1]

        v1 = t1.get(campo)
        v2 = t2.get(campo)

        if v1 is None or v2 is None:
            continue

        try:
            v1_str = str(v1).replace(",", ".")
            v2_str = str(v2).replace(",", ".")

            f1 = float(v1_str)
            f2 = float(v2_str)

            if criterio == "maior":
                if f1 > f2:
                    vantagens[descricao] = t1["time"]
                elif f2 > f1:
                    vantagens[descricao] = t2["time"]
                else:
                    vantagens[descricao] = "Empate"
            else:
                if f1 < f2:
                    vantagens[descricao] = t1["time"]
                elif f2 < f1:
                    vantagens[descricao] = t2["time"]
                else:
                    vantagens[descricao] = "Empate"

        except Exception:
            pass
 
    return JSONResponse(content={
        time1: t1,
        time2: t2,
        "vantagens": vantagens
    })
