import psycopg2

URI = "postgresql://postgres.upjxocjacpsdtdcigqfe:Schrodinger48Rfs2321@aws-1-sa-east-1.pooler.supabase.com:5432/postgres?sslmode=require"

try:
    conn = psycopg2.connect(URI)
    conn.autocommit = True  # Importante para comandos de estrutura
    cur = conn.cursor()

    print("🧹 Limpando tabela e aplicando regras...")
    cur.execute("TRUNCATE TABLE notas_bimestre RESTART IDENTITY;")
    cur.execute("ALTER TABLE notas_bimestre ADD COLUMN IF NOT EXISTS professor_username TEXT;")
    cur.execute("ALTER TABLE notas_bimestre DROP CONSTRAINT IF EXISTS unique_nota_aluno_trimestre_professor;")
    cur.execute(
        "ALTER TABLE notas_bimestre ADD CONSTRAINT unique_nota_aluno_trimestre_professor UNIQUE (aluno_id, trimestre, professor_username);")

    print("✅ BANCO RESETADO E REGRA CRIADA!")
except Exception as e:
    print(f"❌ Erro: {e}")
finally:
    conn.close()