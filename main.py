from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import psycopg2 
import os
import psycopg2.extras
from typing import Optional
import json
from decimal import Decimal

DATABASE_URL = os.environ["DATABASE_URL"]

app = FastAPI()

#melhor defesa,melhor ataque, 

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
    

#todos os times
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

#Pelo nome do time
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

#Resumo
@app.get("/stats/resumo")
def get_resumo(coleta: Optional[str] = Query(None)):
    where  = "WHERE data_coleta = %s" if coleta else ""
    params = [coleta] if coleta else []
 
    with get_conn() as conn:
        mais_v   = fetchone(conn, f"SELECT * FROM nba_standings {where} ORDER BY vitorias DESC LIMIT 1",     params)
        menos_v  = fetchone(conn, f"SELECT * FROM nba_standings {where} ORDER BY vitorias ASC  LIMIT 1",     params)
        melhor   = fetchone(conn, f"SELECT * FROM nba_standings {where} ORDER BY saldo_pontos DESC LIMIT 1", params)
        pior     = fetchone(conn, f"SELECT * FROM nba_standings {where} ORDER BY saldo_pontos ASC  LIMIT 1", params)
        total    = fetchone(conn, f"SELECT COUNT(*) AS c FROM nba_standings {where}", params)
        por_conf = fetchall(conn, f"SELECT conferencia, COUNT(*) AS total FROM nba_standings {where} GROUP BY conferencia", params)
 
    return JSONResponse(content={
        "mais_vitorias":   mais_v,
        "menos_vitorias":  menos_v,
        "melhor_saldo":    melhor,
        "pior_saldo":      pior,
        "total_registros": total["c"] if total else 0,
        "por_conferencia": por_conf
    })
