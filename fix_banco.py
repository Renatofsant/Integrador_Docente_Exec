import psycopg2

# USANDO A PORTA 5432 (SESSION) PARA NÃO DAR TIMEOUT
URI_SESSION = "postgresql://postgres.upjxocjacpsdtdcigqfe:Schrodinger48Rfs2321@aws-1-sa-east-1.pooler.supabase.com:5432/postgres"

try:
    conn = psycopg2.connect(URI_SESSION)
    cursor = conn.cursor()
    print("🚀 Conectado via Porta 5432. Aplicando regra de unicidade...")

    cursor.execute("""
        ALTER TABLE notas_bimestre 
        ADD CONSTRAINT unique_nota_aluno_trimestre_professor 
        UNIQUE (aluno_id, trimestre, professor_username);
    """)

    conn.commit()
    print("✅ SUCESSO TOTAL! A regra foi criada.")
except Exception as e:
    print(f"❌ Erro: {e}")
finally:
    if conn: conn.close()