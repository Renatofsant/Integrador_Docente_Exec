import streamlit as st
import psycopg2
import pandas as pd
from psycopg2.extras import RealDictCursor

# --- CONFIGURAÇÕES DE CONEXÃO ---
DB_URI = "postgresql://postgres.upjxocjacpsdtdcigqfe:Schrodinger48Rfs2321@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"


def get_connection():
    return psycopg2.connect(DB_URI)


# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Projetta Admin - Gestão SaaS", layout="wide")

st.title("🛡️ Integrador Docente - Painel de Controle")
st.markdown("---")

# Barra Lateral para Adicionar Usuário
st.sidebar.header("Novo Cliente")
with st.sidebar.form("form_novo_usuario"):
    new_user = st.text_input("Username (Login)")
    new_pass = st.text_input("Senha Inicial", type="password")
    new_nome = st.text_input("Nome do Professor")
    submit = st.form_submit_button("Cadastrar Docente")

    if submit:
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO usuarios_integrador (username, senha, nome_professor) VALUES (%s, %s, %s)",
                (new_user.lower().strip(), new_pass, new_nome)
            )
            conn.commit()
            st.sidebar.success(f"Usuário {new_user} criado!")
            cur.close();
            conn.close()
        except Exception as e:
            st.sidebar.error(f"Erro: {e}")

# Aba Principal: Gestão de Clientes Ativos
st.subheader("👥 Gestão de Clientes")

try:
    conn = get_connection()
    query = "SELECT id, username, nome_professor, ativo, data_cadastro FROM usuarios_integrador ORDER BY data_cadastro DESC"
    df = pd.read_sql(query, conn)

    # Criar colunas para exibição
    for index, row in df.iterrows():
        col1, col2, col3, col4 = st.columns([1, 2, 1, 1])

        with col1:
            st.write(f"**{row['username']}**")
        with col2:
            st.write(row['nome_professor'])
        with col3:
            status = "✅ Ativo" if row['ativo'] else "🚫 Bloqueado"
            st.write(status)
        with col4:
            if st.button("Alternar Status", key=f"btn_{row['id']}"):
                cur = conn.cursor()
                cur.execute("UPDATE usuarios_integrador SET ativo = %s WHERE id = %s", (not row['ativo'], row['id']))
                conn.commit()
                st.rerun()

    conn.close()
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")

st.markdown("---")

# Aba de Métricas Rápidas
st.subheader("📈 Métricas de Uso")
try:
    conn = get_connection()
    cur = conn.cursor()

    # Total de Alunos Sincronizados
    cur.execute("SELECT COUNT(*) FROM alunos")
    total_alunos = cur.fetchone()[0]

    # Total de Notas Lançadas
    cur.execute("SELECT COUNT(*) FROM notas_bimestre")
    total_notas = cur.fetchone()[0]

    m1, m2 = st.columns(2)
    m1.metric("Alunos na Nuvem", total_alunos)
    m2.metric("Notas Processadas", total_notas)

    cur.close();
    conn.close()
except:
    pass