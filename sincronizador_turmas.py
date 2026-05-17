import psycopg2
import customtkinter as ctk
from tkinter import messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import time
import sys
import os

DB_URI = "postgresql://postgres.upjxocjacpsdtdcigqfe:Schrodinger48Rfs2321@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"


def recurso_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class JanelaDialogo(ctk.CTkToplevel):
    def __init__(self, titulo, prompt, placeholder=""):
        super().__init__()
        self.title(titulo)
        self.geometry("380x220")
        self.attributes("-topmost", True)
        self.resultado = None
        ctk.CTkLabel(self, text=prompt, font=("Roboto", 14), wraplength=300).pack(pady=20)
        self.entry = ctk.CTkEntry(self, placeholder_text=placeholder, width=280)
        self.entry.pack(pady=5)
        self.entry.focus()
        ctk.CTkButton(self, text="Confirmar", command=self.confirmar, fg_color="#10b981").pack(pady=20)
        self.wait_window()

    def confirmar(self):
        self.resultado = self.entry.get()
        self.destroy()


class CardInstrucao(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Sincronizador - Próximo Passo")
        self.geometry("400x380")
        self.attributes("-topmost", True)
        self.configure(fg_color="#1a1a1a")
        self.grab_set()
        ctk.CTkLabel(self, text="🔄 CAPTURA DE ALUNOS", font=("Urbanist", 20, "bold"), text_color="#10b981").pack(
            pady=(30, 20))
        instrucoes = "1. Faça Login Manual no Portal\n2. Resolva o Captcha se houver\n3. Abra a Pauta da Turma desejada\n\n👉 Clique abaixo APENAS quando a lista\nde alunos estiver visível na tela."
        ctk.CTkLabel(self, text=instrucoes, font=("Roboto", 14), justify="left", text_color="#e0e0e0").pack(pady=10,
                                                                                                            padx=40)
        ctk.CTkButton(self, text="ESTOU NA TELA DA TURMA!", command=self.destroy, fg_color="#10b981", height=50,
                      font=("Roboto", 14, "bold")).pack(pady=30, padx=40, fill="x")
        self.wait_window()


class CardFinalizacao(ctk.CTkToplevel):
    def __init__(self, master, msg_principal):
        super().__init__(master)
        self.title("Sincronia Concluída")
        self.geometry("400x320")
        self.attributes("-topmost", True)
        self.configure(fg_color="#1a1a1a")
        self.grab_set()
        self.resultado = False
        ctk.CTkLabel(self, text="✅", font=("Roboto", 50)).pack(pady=(20, 5))
        ctk.CTkLabel(self, text="MIGRAÇÃO COM SUCESSO", font=("Urbanist", 18, "bold"), text_color="#10b981").pack()
        ctk.CTkLabel(self, text=msg_principal, font=("Roboto", 13), text_color="gray", wraplength=320).pack(pady=10)
        btn_f = ctk.CTkFrame(self, fg_color="transparent")
        btn_f.pack(pady=20)
        ctk.CTkButton(btn_f, text="SINCRONIZAR OUTRA", command=self.sim, width=150, fg_color="#10b981").pack(
            side="left", padx=5)
        ctk.CTkButton(btn_f, text="FECHAR PAINEL", command=self.nao, width=120, fg_color="#4b5563").pack(side="left",
                                                                                                         padx=5)
        self.wait_window()

    def sim(self): self.resultado = True; self.destroy()

    def nao(self): self.resultado = False; self.destroy()


class PainelSincronizador(ctk.CTk):
    def __init__(self, usuario, escola_id):
        super().__init__()
        self.usuario = usuario
        self.escola_id = escola_id
        self.title(f"Sincronizador de Alunos SGI - {self.usuario}")
        self.geometry("500x400")
        ctk.set_appearance_mode("dark")
        self.attributes("-topmost", True)
        self.driver = None

        ctk.CTkLabel(self, text="MOTOR DE SINCRONIA SAAS", font=("Urbanist", 24, "bold"), text_color="#10b981").pack(
            pady=(40, 20))
        ctk.CTkLabel(self,
                     text="Use este painel exclusivamente para importar\nou atualizar as listas de alunos do portal da SEEDUC.",
                     font=("Roboto", 13), text_color="gray", justify="center").pack(pady=5)

        self.btn_sinc = ctk.CTkButton(self, text="🔄 INICIAR CAPTURA E MAPEAMENTO",
                                      command=self.sincronizar_alunos_escola,
                                      fg_color="#10b981", hover_color="#059669", height=60, width=380,
                                      font=("Roboto", 15, "bold"))
        self.btn_sinc.pack(pady=40)

        self.status = ctk.CTkLabel(self, text=f"Sessão ativa para: {self.usuario} | Escola ID Atual: {self.escola_id}",
                                   font=("Roboto", 11), text_color="gray")
        self.status.pack(side="bottom", pady=20)

    def sincronizar_alunos_escola(self):
        conn = None
        try:
            self.withdraw()
            if not self.driver:
                self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
                self.driver.get("https://docenteonline.educacao.rj.gov.br/NovoDocente/")
                CardInstrucao(self)

            while True:
                turma_digitada = JanelaDialogo("Mapeamento",
                                               "Digite EXATAMENTE o número da turma aberta na tela (Ex: 3001):",
                                               "3001").resultado
                if not turma_digitada: break

                t_limpa = turma_digitada.strip()

                conn = psycopg2.connect(DB_URI)
                cur = conn.cursor()

                # 💡 LOG DE SEGURANÇA: Mostra no terminal o ID exato que o robô está usando
                print(f"[CONEXÃO] Sincronizando Turma: {t_limpa} | Para o ID da Escola: {self.escola_id}")

                # Busca ou cria o vínculo garantindo a separação estrita por escola_id
                cur.execute("""
                    SELECT id FROM vinculo_professor_turma 
                    WHERE professor_username = %s AND turma = %s AND esco_id = %s
                """, (self.usuario, t_limpa, self.escola_id)) if False else cur.execute("""
                    SELECT id FROM vinculo_professor_turma 
                    WHERE professor_username = %s AND turma = %s AND escola_id = %s
                """, (self.usuario, t_limpa, self.escola_id))

                vinc_res = cur.fetchone()

                if vinc_res:
                    vinculo_id = vinc_res[0]
                else:
                    cur.execute("""
                        INSERT INTO vinculo_professor_turma (professor_username, escola_id, turma) 
                        VALUES (%s, %s, %s) RETURNING id
                    """, (self.usuario, self.escola_id, t_limpa))
                    vinculo_id = cur.fetchone()[0]
                    conn.commit()

                script_extracao = "let r=[]; document.querySelectorAll('tr').forEach(tr=>{let d=tr.querySelectorAll('td'); if(d.length>=2){let n=d[0].innerText.trim(); let s=d[1]?d[1].innerText.trim():''; if(n.length>5 && !n.includes('Aulas')) r.push({nome:n, status:(s==='Matriculado'||s==='')?'Ativo':'Inativo'});}}); return r;"
                alunos_portal = self.driver.execute_script(script_extracao)

                if not alunos_portal:
                    messagebox.showwarning("Aviso", "Nenhum aluno localizado na página. Verifique a tela da SEEDUC.")
                    cur.close();
                    conn.close()
                    continue

                for a in alunos_portal:
                    # 🔒 TRAVA MÁXIMA: Só mexe no aluno se bater Escola, Nome e Turma
                    cur.execute("""
                        SELECT id FROM alunos 
                        WHERE escola_id = %s AND nome_completo = %s AND turma = %s
                    """, (self.escola_id, a['nome'], t_limpa))
                    existe = cur.fetchone()

                    if existe:
                        cur.execute("""
                            UPDATE alunos 
                            SET status = %s, vinculo_turma_id = %s 
                            WHERE id = %s
                        """, (a['status'], vinculo_id, existe[0]))
                    else:
                        cur.execute("""
                            INSERT INTO alunos (escola_id, nome_completo, turma, status, vinculo_turma_id) 
                            VALUES (%s, %s, %s, %s, %s)
                        """, (self.escola_id, a['nome'], t_limpa, a['status'], vinculo_id))

                conn.commit()
                cur.close();
                conn.close()
                print(
                    f"[OK] Turma {t_limpa} e seus {len(alunos_portal)} alunos foram salvos com sucesso na escola ID {self.escola_id}!")

                if not CardFinalizacao(self,
                                       msg_principal=f"Alunos da turma {t_limpa} processados com sucesso no banco de dados!").resultado:
                    break

        except Exception as e:
            messagebox.showerror("Erro de Sincronia", str(e))
        finally:
            if conn: conn.close()
            self.deiconify()


class TelaLogin(ctk.CTk):
    USER_FINAL = None
    ESCOLA_FINAL = None

    def __init__(self):
        super().__init__()
        self.title("🛡️ Login Sincronizador")
        self.geometry("420x520")
        self.eval('tk::PlaceWindow . center')
        self.attributes("-topmost", True)
        self.configure(fg_color="#1a1a1a")
        self.usuario_logado = None
        self.grid_columnconfigure(0, weight=1)

        try:
            img_path = recurso_path("logo_robot.png")
            img_original = Image.open(img_path)
            self.logo_image = ctk.CTkImage(light_image=img_original, dark_image=img_original, size=(90, 90))
            self.logo_label = ctk.CTkLabel(self, text="", image=self.logo_image)
            self.logo_label.grid(row=0, column=0, pady=(30, 10), sticky="ew")
        except Exception as e:
            self.logo_label = ctk.CTkLabel(self, text="[LOGO]", font=("Roboto", 14), text_color="gray")
            self.logo_label.grid(row=0, column=0, pady=(30, 10))

        ctk.CTkLabel(self, text="SINCRO ALUNOS - SGI", font=("Urbanist", 22, "bold"), text_color="#10b981").grid(row=1,
                                                                                                                 column=0,
                                                                                                                 pady=5,
                                                                                                                 sticky="ew")

        self.u = ctk.CTkEntry(self, placeholder_text="Usuário", width=300, height=45)
        self.u.grid(row=2, column=0, pady=10)

        self.p = ctk.CTkEntry(self, placeholder_text="Senha", show="*", width=300, height=45)
        self.p.grid(row=3, column=0, pady=10)

        ctk.CTkButton(self, text="ACESSAR SISTEMA", command=self.logar, fg_color="#10b981", hover_color="#059669",
                      height=50, width=300, font=("Roboto", 14, "bold")).grid(row=4, column=0, pady=20)

        self.msg = ctk.CTkLabel(self, text="", text_color="#ef4444")
        self.msg.grid(row=5, column=0)

    def logar(self):
        user = self.u.get().lower().strip()
        senha = self.p.get()

        try:
            conn = psycopg2.connect(DB_URI)
            cur = conn.cursor()
            cur.execute("SELECT username FROM usuarios_integrador WHERE username=%s AND senha=%s AND ativo=TRUE",
                        (user, senha))
            res = cur.fetchone()

            if res:
                self.usuario_logado = res[0]

                # Oculta a tela de login temporariamente
                self.withdraw()

                # 💡 CAPTURA INTELIGENTE POR NOME DA ESCOLA
                dialogo = JanelaDialogo("Identificação do Colégio", "Digite o nome (ou parte do nome) da sua Escola:",
                                        "Ex: Agripino, Nazareth...")
                nome_escola_digitado = dialogo.resultado

                if not nome_escola_digitado or not nome_escola_digitado.strip():
                    messagebox.showwarning("Aviso", "Nome da escola não pode ser vazio. Login cancelado.")
                    self.deiconify()
                    cur.close();
                    conn.close()
                    return

                # Busca no banco de dados a escola que contém o termo digitado (ignora maiúsculas/minúsculas)
                termo_busca = f"%{nome_escola_digitado.strip()}%"
                cur.execute("SELECT id, nome FROM escolas WHERE nome ILIKE %s LIMIT 1", (termo_busca,))
                escola_data = cur.fetchone()

                if escola_data:
                    id_real_escola = escola_data[0]
                    nome_real_escola = escola_data[1]

                    # Confirmação visual para o professor saber que o robô achou o colégio certo
                    messagebox.showinfo("Escola Identificada", f"Conectado com sucesso ao:\n{nome_real_escola}")

                    TelaLogin.USER_FINAL = self.usuario_logado
                    TelaLogin.ESCOLA_FINAL = id_real_escola

                    print(
                        f"[SAAS SYSTEM] Professor {TelaLogin.USER_FINAL} conectado à escola: {nome_real_escola} (ID: {TelaLogin.ESCOLA_FINAL})")

                    cur.close();
                    conn.close()
                    self.quit()
                    self.destroy()
                else:
                    # Se não achar nada, avisa o professor o que está cadastrado no banco de dados para ajudá-lo
                    cur.execute("SELECT nome FROM escolas ORDER BY nome ASC")
                    todas_escolas = cur.fetchall()
                    lista_nomes = "\n".join([f"- {e[0]}" for e in todas_escolas])

                    messagebox.showerror("Erro de Identificação",
                                         f"Não encontramos nenhuma escola com o termo '{nome_escola_digitado}'.\n\nEscolas disponíveis no sistema:\n{lista_nomes}")
                    self.deiconify()
                    cur.close();
                    conn.close()
                    return
            else:
                conn.close()
                self.msg.configure(text="Acesso negado. Usuário ou senha inválidos.")
        except Exception as e:
            self.msg.configure(text=f"Erro de conexão: {str(e)}")


if __name__ == "__main__":
    login = TelaLogin()
    login.mainloop()
    usuario_final = TelaLogin.USER_FINAL
    escola_final = TelaLogin.ESCOLA_FINAL
    if usuario_final:
        app_painel = PainelSincronizador(usuario=usuario_final, escola_id=escola_final)
        app_painel.mainloop()