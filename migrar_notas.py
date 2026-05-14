import os
import psycopg2
from psycopg2 import extras
import time

# --- BLINDAGEM DE AMBIENTE ---
os.environ['PGGSSENCMODE'] = 'disable'

LOCAL_URI = "postgresql://postgres:admin123@localhost:5438/seeduc_db"
SUPABASE_URI = "postgresql://postgres.upjxocjacpsdtdcigqfe:Schrodinger48Rfs2321@aws-1-sa-east-1.pooler.supabase.com:5432/postgres?sslmode=require"


def sincronizar_bancos():
    conn_l = None
    conn_s = None
    ADMIN_USER = "renato"

    try:
        print("\n" + "═" * 75)
        print("🚀 [INTEGRADOR DOCENTE] - MIGRAÇÃO TANQUE DE GUERRA V6.2")
        print("🔗 Sincronizando com Verificação de Colunas Locais")
        print("═" * 75)

        conn_l = psycopg2.connect(LOCAL_URI)
        conn_s = psycopg2.connect(SUPABASE_URI)
        cur_l = conn_l.cursor(cursor_factory=extras.RealDictCursor)
        cur_s = conn_s.cursor(cursor_factory=extras.RealDictCursor)

        # 1. SINCRONISMO DE ALUNOS
        print(f"\n📦 SINCRONIZANDO ALUNOS...")
        cur_l.execute("SELECT * FROM alunos")
        alunos_locais = cur_l.fetchall()

        for r in alunos_locais:
            colunas = list(r.keys())
            conflito = "(escola_id, nome_completo, turma)"
            # Protegemos colunas de identidade
            cols_upd = [c for c in colunas if c not in ['id', 'escola_id', 'nome_completo', 'turma']]
            upd_clause = ", ".join(
                [f"{c} = EXCLUDED.{c}" for c in cols_upd]) if cols_upd else "status = EXCLUDED.status"

            query = f"INSERT INTO alunos ({','.join(colunas)}) VALUES ({','.join(['%s'] * len(colunas))}) ON CONFLICT {conflito} DO UPDATE SET {upd_clause}"
            cur_s.execute(query, list(r.values()))

        conn_s.commit()
        print(f"✅ {len(alunos_locais)} alunos sincronizados.")

        # 2. MAPEAMENTO DE NOTAS (CORREÇÃO DE IDs E COLUNAS)
        print(f"\n📦 PROCESSANDO NOTAS_BIMESTRE...")

        cur_l.execute("""
            SELECT n.*, a.nome_completo, a.escola_id, a.turma 
            FROM notas_bimestre n 
            JOIN alunos a ON n.aluno_id = a.id
        """)
        notas_locais = cur_l.fetchall()

        # Mapa da Nuvem para pegar IDs novos
        cur_s.execute("SELECT id, nome_completo, escola_id, turma FROM alunos")
        mapa_nuvem = {(r['nome_completo'], r['escola_id'], r['turma']): r['id'] for r in cur_s.fetchall()}

        sucesso = 0
        pulas = 0

        for n in notas_locais:
            chave = (n['nome_completo'], n['escola_id'], n['turma'])
            id_nuvem = mapa_nuvem.get(chave)

            if not id_nuvem:
                pulas += 1
                continue

            # Mapeamento explícito das notas conforme seu print do DBeaver
            dados_nota = {
                'aluno_id': id_nuvem,
                'av1': n.get('av1', 0.0),
                'av2': n.get('av2', 0.0),
                'av3': n.get('av3', 0.0),
                'recuperacao': n.get('recuperacao', 0.0),
                'faltas': n.get('faltas', 0),
                'trimestre': n.get('trimestre', 1),
                'professor_username': ADMIN_USER
            }

            cols = list(dados_nota.keys())
            query_nota = f"""
                INSERT INTO notas_bimestre ({','.join(cols)}) 
                VALUES ({','.join(['%s'] * len(cols))})
                ON CONFLICT (aluno_id, trimestre, professor_username) 
                DO UPDATE SET 
                    av1 = EXCLUDED.av1, 
                    av2 = EXCLUDED.av2, 
                    av3 = EXCLUDED.av3, 
                    recuperacao = EXCLUDED.recuperacao, 
                    faltas = EXCLUDED.faltas;
            """

            try:
                cur_s.execute(query_nota, list(dados_nota.values()))
                sucesso += 1
            except Exception as e:
                conn_s.rollback()
                print(f"❌ Erro em {n['nome_completo']}: {e}")
                continue

            if sucesso % 100 == 0:
                conn_s.commit()
                print(f"   ➔ {sucesso} notas integradas...")

        conn_s.commit()
        print(f"\n" + "═" * 75)
        print(f"🏆 SUCESSO TOTAL: {sucesso} notas integradas na nuvem!")
        print("═" * 75)

    except Exception as e:
        print(f"\n❌ FALHA CRÍTICA: {e}")
        if conn_s: conn_s.rollback()
    finally:
        if conn_l: conn_l.close()
        if conn_s: conn_s.close()
        print("\n🔒 Conexões encerradas.")


if __name__ == "__main__":
    sincronizar_bancos()