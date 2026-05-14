import psycopg2
from selenium import webdriver
from selenium.webdriver.common.by import By


# ... (mesmos imports do seu sync_alunos)

def carga_forcada():
    driver = webdriver.Chrome()  # Abre o que já está aberto ou inicia um novo
    # (...) Faça login e vá até a tela da turma manualmente se necessário

    conn = psycopg2.connect(host="localhost", port="5438", database="seeduc_db", user="postgres", password="admin123")
    cursor = conn.cursor()

    # Pega a escola Agripino (ID 1)
    escola_id = 1
    turma_nome = "IF_FC_3001-182444"  # Nome que aparece no topo do seu site

    linhas = driver.find_elements(By.CSS_SELECTOR, "table.table-padrao tbody tr")
    for linha in linhas:
        nome = linha.find_element(By.XPATH, "./td[1]").text.strip()
        situacao = linha.find_element(By.CLASS_NAME, "situacao").text.strip()

        # Insere o aluno e já define a turma para o Streamlit encontrar
        cursor.execute("""
            INSERT INTO alunos (escola_id, nome_completo, turma, status) 
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (escola_id, nome, turma_nome, situacao))

    conn.commit()
    print(f"Carga de {len(linhas)} alunos concluída!")