import psycopg2
import customtkinter as ctk
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from tkinter import messagebox

# --- CONFIGURAÇÕES CRÍTICAS (Padrão Tanque de Guerra) ---
# DB_URI mantida conforme sua infraestrutura Supabase
DB_URI = "postgresql://postgres.upjxocjacpsdtdcigqfe:Schrodinger48Rfs2321@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"


class AppInterface:
    """Interface Moderna e Elegante com a identidade Projetta"""

    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

    def avisar(self, titulo, mensagem):
        janela = ctk.CTk()
        janela.attributes("-topmost", True)
        janela.withdraw()
        messagebox.showinfo(titulo, f"📝 {mensagem}")
        janela.destroy()

    def perguntar(self, titulo, mensagem):
        self.resposta = None
        janela = ctk.CTk()
        janela.attributes("-topmost", True)
        janela.withdraw()

        pergunta = ctk.CTkToplevel(janela)
        pergunta.title(titulo)
        pergunta.geometry("420x200")
        pergunta.attributes("-topmost", True)

        ctk.CTkLabel(pergunta, text=f"❓ {mensagem}", font=("Roboto", 14), wraplength=380).pack(expand=True, padx=20,
                                                                                               pady=10)

        def set_resp(valor):
            self.resposta = valor
            pergunta.destroy()

        btn_frame = ctk.CTkFrame(pergunta, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)
        ctk.CTkButton(btn_frame, text="SIM", width=120, command=lambda: set_resp(True)).pack(side="left", padx=10,
                                                                                             expand=True)
        ctk.CTkButton(btn_frame, text="NÃO", width=120, fg_color="gray", command=lambda: set_resp(False)).pack(
            side="right", padx=10, expand=True)

        pergunta.grab_set()
        janela.wait_window(pergunta)
        janela.destroy()
        return self.resposta

    def solicitar_entrada(self, titulo, prompt):
        dialog = ctk.CTkInputDialog(text=prompt, title=titulo)
        return dialog.get_input()


def iniciar_driver():
    """Inicia o Chrome com blindagem contra detecção e otimização de tela"""
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)
    chrome_options.add_argument("--start-maximized")
    # Impede que o site detecte que é um robô
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)


def selecionar_vinculo_automatico(driver, nome_escola):
    """
    LÓGICA TANQUE DE GUERRA: Seleciona o vínculo correto (ex: /3 ou /4)
    baseado no nome da escola vindo do SGI.
    """
    try:
        # Aguarda 3 segundos para a tela de múltiplos vínculos (se houver)
        time.sleep(3)
        # O robô procura o link que contém o nome da escola selecionada no SGI
        elemento_escola = driver.find_element(By.PARTIAL_LINK_TEXT, nome_escola.upper())
        elemento_escola.click()
        print(f"✅ Vínculo '{nome_escola}' identificado e selecionado automaticamente.")
        return True
    except:
        # Se a tela de escolha não aparecer, o robô entende que entrou direto
        return False


def povoar_supabase(cpf_manual=None, senha_manual=None):
    """
    Versão SaaS Robusta: Povoa o banco com alunos e turmas.
    Agora aceita credenciais externas para processar professores convidados.
    """
    ui = AppInterface()

    # Define as chaves de acesso (Dinamismo Total)
    cpf_final = cpf_manual if cpf_manual else "08163149779"
    senha_final = senha_manual if senha_manual else "08163149779"

    try:
        conn = psycopg2.connect(DB_URI)
        cursor = conn.cursor()
    except Exception as e:
        ui.avisar("Erro Crítico", f"Falha na conexão Cloud: {e}")
        return

    try:
        # 1. BUSCA AS ESCOLAS CADASTRADAS NO SUPABASE
        cursor.execute("SELECT id, nome, vinculo_login FROM escolas ORDER BY nome")
        escolas = cursor.fetchall()

        driver = iniciar_driver()
        url_portal = "https://docenteonline.educacao.rj.gov.br/NovoDocente/"

        for escola_id, nome_escola, vinculo in escolas:
            if not ui.perguntar("Povoar Banco", f"Deseja extrair alunos de:\n{nome_escola}?"):
                continue

            driver.get(url_portal)
            wait = WebDriverWait(driver, 20)

            # --- FLUXO DE LOGIN AUTOMATIZADO ---
            try:
                # Preenche Matrícula/Vínculo
                wait.until(EC.element_to_be_clickable((By.ID, "LoginMatricula"))).send_keys(vinculo)
                # Preenche Senha (CPF)
                driver.find_element(By.ID, "LoginSenha").send_keys(senha_final)
                # Clica em Entrar
                driver.find_element(By.ID, "btnEntrar").click()

                # --- SELEÇÃO DE VÍNCULO AUTOMÁTICA ---
                # Resolve o problema das múltiplas matrículas (/3, /4...)
                selecionar_vinculo_automatico(driver, nome_escola)

                ui.avisar("Ação Requerida",
                          f"Login pronto para {nome_escola}.\nEntre na TURMA correta e clique em SIM no próximo aviso.")
            except Exception as e:
                print(f"⚠️ Aviso no Login: {e}")
                pass

            # --- LOOP DE CAPTURA DE TURMAS ---
            while True:
                if not ui.perguntar("Capturar Alunos", f"A lista de alunos de '{nome_escola}' está visível?"):
                    break

                turma_label = ui.solicitar_entrada("Identificação",
                                                   "Digite o número/nome da turma (ex: 1001 ou EJAIV):")
                if not turma_label: break

                print(f"🔍 Extraindo alunos da turma {turma_label}...")

                # EXTRAÇÃO VIA JAVASCRIPT (Performance Superior e Blindada)
                script_extracao = """
                let resultados = [];
                let linhas = document.querySelectorAll('tr');
                linhas.forEach(tr => {
                    let colunas = tr.querySelectorAll('td');
                    if (colunas.length >= 2) {
                        let nome = colunas[0].innerText.trim();
                        let situacao = colunas[1] ? colunas[1].innerText.trim() : "";
                        if (nome.length > 5 && !nome.includes("Aulas") && !nome.includes("Matrícula")) {
                            resultados.push({ 
                                nome: nome, 
                                status: (situacao.includes("Matriculado") || situacao === "") ? "Ativo" : "Inativo" 
                            });
                        }
                    }
                });
                return resultados;
                """
                alunos_portal = driver.execute_script(script_extracao)

                if not alunos_portal:
                    print("⚠️ Nenhum aluno encontrado na extração JS. Verifique a tela.")
                    continue

                # 2. INSERÇÃO NO BANCO COM LÓGICA DE UPSERT
                for aluno in alunos_portal:
                    try:
                        cursor.execute("""
                            INSERT INTO alunos (escola_id, nome_completo, turma, status)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (escola_id, nome_completo) 
                            DO UPDATE SET turma = EXCLUDED.turma, status = EXCLUDED.status;
                        """, (escola_id, aluno['nome'], turma_label, aluno['status']))
                    except Exception as e:
                        print(f"  ⚠️ Erro ao inserir {aluno['nome']}: {e}")
                        conn.rollback()
                        continue

                conn.commit()
                print(f"✅ {len(alunos_portal)} alunos da Turma {turma_label} sincronizados no Supabase.")
                ui.avisar("Sucesso", f"Turma {turma_label} salva com sucesso!")

                if not ui.perguntar("Próxima", "Deseja capturar outra turma nesta mesma escola?"):
                    break

        ui.avisar("Concluído", "O povoamento do banco foi finalizado com sucesso!")

    except Exception as e:
        ui.avisar("Erro Crítico", f"Ocorreu um erro inesperado no processo: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        # driver.quit() # Mantemos aberto para conferência se desejar


if __name__ == "__main__":
    # Quando rodado localmente, usa as credenciais padrão do Renato
    povoar_supabase()