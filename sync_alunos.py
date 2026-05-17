import psycopg2
import psycopg2.extras
import customtkinter as ctk
from tkinter import messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import time
import sys
import os
import webbrowser

# --- CONFIGURAÇÕES NUVEM ---
DB_URI = "postgresql://postgres.upjxocjacpsdtdcigqfe:Schrodinger48Rfs2321@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"


def recurso_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# =================================================================
# COMPONENTES DE INTERFACE (U.I. PREMIUM CUSTOMTKINTER)
# =================================================================

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
        ctk.CTkButton(self, text="Confirmar", command=self.confirmar, fg_color="#3b82f6").pack(pady=20)
        self.wait_window()

    def confirmar(self):
        self.resultado = self.entry.get()
        self.destroy()


class CardInstrucao(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Ação Requerida")
        self.geometry("400x380")
        self.attributes("-topmost", True)
        self.configure(fg_color="#1a1a1a")
        self.grab_set()
        ctk.CTkLabel(self, text="⚡ PRÓXIMO PASSO", font=("Urbanist", 20, "bold"), text_color="#3b82f6").pack(
            pady=(30, 20))
        instrucoes = "1. Faça Login Manual no Portal\n2. Resolva o Captcha\n3. Entre na tela da Turma\n\n👉 Clique abaixo quando a lista\nde alunos estiver visível."
        ctk.CTkLabel(self, text=instrucoes, font=("Roboto", 14), justify="left", text_color="#e0e0e0").pack(pady=10,
                                                                                                            padx=40)
        ctk.CTkButton(self, text="ESTOU NA TELA!", command=self.destroy, fg_color="#3b82f6", height=50).pack(pady=30,
                                                                                                             padx=40,
                                                                                                             fill="x")
        self.wait_window()


class CardFinalizacao(ctk.CTkToplevel):
    def __init__(self, master, msg_principal="Deseja lançar outra turma?"):
        super().__init__(master)
        self.title("Sucesso")
        self.geometry("400x320")
        self.attributes("-topmost", True)
        self.configure(fg_color="#1a1a1a")
        self.grab_set()
        self.resultado = False

        ctk.CTkLabel(self, text="🎉", font=("Roboto", 50)).pack(pady=(20, 5))
        ctk.CTkLabel(self, text="MISSÃO CUMPRIDA!", font=("Urbanist", 18, "bold"), text_color="#10b981").pack()
        ctk.CTkLabel(self, text=msg_principal, font=("Roboto", 13), text_color="gray", wraplength=320).pack(pady=10)

        btn_f = ctk.CTkFrame(self, fg_color="transparent")
        btn_f.pack(pady=20)
        ctk.CTkButton(btn_f, text="SIM, OUTRA", command=self.sim, width=120, fg_color="#3b82f6").pack(side="left",
                                                                                                      padx=5)
        ctk.CTkButton(btn_f, text="FECHAR", command=self.nao, width=120, fg_color="#4b5563").pack(side="left", padx=5)
        self.wait_window()

    def sim(self):
        self.resultado = True
        self.destroy()

    def nao(self):
        self.resultado = False
        self.destroy()


# =================================================================
# MOTOR PRINCIPAL (PAINEL SGI COM LOGIN)
# =================================================================

class PainelSGI(ctk.CTk):
    def __init__(self, usuario, escola_id):
        super().__init__()
        self.usuario = usuario
        self.escola_id = escola_id
        self.title(f"Integrador Docente - {self.usuario}")
        self.geometry("500x520")
        ctk.set_appearance_mode("dark")
        self.attributes("-topmost", True)

        self.driver = None

        ctk.CTkLabel(self, text="INTEGRADOR DOCENTE", font=("Urbanist", 24, "bold"), text_color="#3b82f6").pack(
            pady=(30, 20))

        self.btn_iniciar = ctk.CTkButton(self, text="🚀 INICIAR LANÇAMENTO TOTAL",
                                         command=self.executar_fluxo,
                                         height=60, width=380, font=("Roboto", 16, "bold"))
        self.btn_iniciar.pack(pady=10)

        self.f_tools = ctk.CTkFrame(self, fg_color="transparent")
        self.f_tools.pack(pady=20)

        self.btn_sinc = ctk.CTkButton(self.f_tools, text="🔄 Sincronizar Alunos",
                                      command=self.sincronizar_apenas_alunos,
                                      fg_color="#10b981", width=185, height=45)
        self.btn_sinc.pack(side="left", padx=5)

        self.btn_rel = ctk.CTkButton(self.f_tools, text="📊 Gerar Relatório",
                                     command=self.gerar_relatorio_final,
                                     fg_color="#8b5cf6", width=185, height=45)
        self.btn_rel.pack(side="left", padx=5)

        self.status = ctk.CTkLabel(self, text=f"Professor: {self.usuario} | Escola ID: {self.escola_id}",
                                   font=("Roboto", 11),
                                   text_color="gray")
        self.status.pack(side="bottom", pady=20)

        self.protocol("WM_DELETE_WINDOW", self.ao_fechar_painel)

    def ao_fechar_painel(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.destroy()

    def obter_id_vinculo_professor(self, cursor, turma_digitada):
        try:
            turma_limpa = turma_digitada.strip()

            query_busca = """
                SELECT id FROM vinculo_professor_turma 
                WHERE professor_username = %s AND turma = %s AND escola_id = %s
            """
            cursor.execute(query_busca, (self.usuario, turma_limpa, self.escola_id))
            res = cursor.fetchone()

            if res:
                return res[0]

            print(f"📌 Criando novo vínculo automático para {self.usuario} na turma {turma_limpa}...")
            query_insercao = """
                INSERT INTO vinculo_professor_turma (professor_username, escola_id, turma)
                VALUES (%s, %s, %s)
                RETURNING id
            """
            cursor.execute(query_insercao, (self.usuario, self.escola_id, turma_limpa))
            novo_id = cursor.fetchone()[0]

            cursor.connection.commit()
            return novo_id

        except Exception as e:
            try:
                cursor.execute("ROLLBACK;")
            except:
                pass
            print(f"⚠️ Erro na gestão automática de vínculo: {e}")
            return None

    def sincronizar_apenas_alunos(self):
        conn = None
        try:
            self.withdraw()

            if not self.driver:
                self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
                self.driver.get("https://docenteonline.educacao.rj.gov.br/NovoDocente/")
                CardInstrucao(self)

            sufixo_disciplina = ""
            if self.usuario == "ana@leal":
                sufixo_disciplina = " - Matemática"
            elif self.usuario == "carla":
                sufixo_disciplina = " - [Matéria da Carla]"

            while True:
                t_dig = JanelaDialogo("Sincronia", "Mude de pauta no portal e digite o número da turma aqui:",
                                      "Ex: 2004").resultado
                if not t_dig:
                    break

                t = f"{t_dig.strip()}{sufixo_disciplina}" if self.usuario != "renato" else t_dig.strip()

                conn = psycopg2.connect(DB_URI)
                cur = conn.cursor()

                vinculo_id = self.obter_id_vinculo_professor(cur, t)

                if not vinculo_id:
                    messagebox.showwarning("Erro de Vínculo",
                                           f"A turma {t} não pôde ser associada ao perfil {self.usuario}.")
                    conn.close()
                    break

                script_extracao = "let r=[]; document.querySelectorAll('tr').forEach(tr=>{let d=tr.querySelectorAll('td'); if(d.length>=2){let n=d[0].innerText.trim(); let s=d[1]?d[1].innerText.trim():''; if(n.length>5 && !n.includes('Aulas')) r.push({nome:n, status:(s==='Matriculado'||s==='')?'Ativo':'Inativo'});}}); return r;"
                alunos_portal = self.driver.execute_script(script_extracao)

                if not alunos_portal:
                    messagebox.showwarning("Aviso de Carregamento",
                                           "Não foi possível extrair a lista. Certifique-se de estar com a lista de alunos visível na tela.")
                    conn.close()
                    continue

                for a in alunos_portal:
                    cur.execute(
                        """INSERT INTO alunos (escola_id, nome_completo, turma, status, vinculo_turma_id) 
                           VALUES (%s, %s, %s, %s, %s) 
                           ON CONFLICT (escola_id, nome_completo, turma, vinculo_turma_id) 
                           DO UPDATE SET status = EXCLUDED.status""",
                        (self.escola_id, a['nome'], t.strip(), a['status'], vinculo_id))

                conn.commit()
                conn.close()

                if not CardFinalizacao(self,
                                       msg_principal=f"Alunos da turma {t} sincronizados com sucesso! Mude de pauta no portal antes de continuar.").resultado:
                    break

        except Exception as e:
            messagebox.showerror("Erro", str(e))
        finally:
            if conn: conn.close()
            self.deiconify()

    def gerar_relatorio_final(self):
        t = JanelaDialogo("Relatório", "Turma para o relatório:", "Ex: 2005").resultado
        if not t: return
        try:
            conn = psycopg2.connect(DB_URI)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""SELECT a.nome_completo, n.av1, n.av2, n.av3, n.recuperacao, n.faltas FROM alunos a 
                           JOIN notas_bimestre n ON a.id = n.aluno_id WHERE a.turma = %s AND n.professor_username = %s""",
                        (t, self.usuario))
            dados = cur.fetchall()
            conn.close()
            if not dados: messagebox.showwarning("Aviso", "Nenhuma nota encontrada."); return

            html = f"<html><head><style>body{{font-family:sans-serif; padding:20px; background:#f4f7f6;}} .card{{background:white; border-radius:8px; padding:20px; box-shadow:0 2px 5px rgba(0,0,0,0.1);}} table{{width:100%; border-collapse:collapse; margin-top:20px;}} th{{background:#3b82f6; color:white; padding:12px; text-align:left;}} td{{padding:10px; border-bottom:1px solid #eee;}}</style></head><body>"
            html += f"<div class='card'><h2>📊 Relatório de Lançamento - Turma {t}</h2><p>Professor: <b>{self.usuario}</b></p><table><tr><th>Aluno</th><th>AV1</th><th>AV2</th><th>AV3</th><th>Rec</th><th>Faltas</th></tr>"
            for r in dados: html += f"<tr><td>{r['nome_completo']}</td><td>{r['av1'] or '-'}</td><td>{r['av2'] or '-'}</td><td>{r['av3'] or '-'}</td><td>{r['recuperacao'] or '-'}</td><td>{r['faltas'] or '0'}</td></tr>"
            html += "</table><p style='font-size:12px; color:gray; margin-top:20px;'>Gerado por Integrador Docente</p></div></body></html>"

            path = os.path.abspath(f"Relatorio_{t}.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            webbrowser.open(path)
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def executar_fluxo(self):
        conn = None
        try:
            self.withdraw()

            if not self.driver:
                opt = Options()
                opt.add_experimental_option("detach", True)
                opt.add_argument("--start-maximized")
                self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opt)
                self.driver.get("https://docenteonline.educacao.rj.gov.br/NovoDocente/")
                CardInstrucao(self)

            conn = psycopg2.connect(DB_URI)
            cursor = conn.cursor()

            while True:
                turma_digitada = JanelaDialogo("Identificação",
                                               "Informe o número da turma que está aberta no portal:",
                                               "Ex: 2005").resultado
                if not turma_digitada:
                    break

                turma_alvo = turma_digitada.strip()
                vinculo_id = self.obter_id_vinculo_professor(cursor, turma_alvo)

                trimestre_alvo = JanelaDialogo("Trimestre", "Trimestre (1, 2 ou 3):", "1").resultado or "1"
                time.sleep(2)

                script_extracao = "let r=[]; document.querySelectorAll('tr').forEach(tr=>{let d=tr.querySelectorAll('td'); if(d.length>=2){let n=d[0].innerText.trim(); let s=d[1]?d[1].innerText.trim():''; if(n.length>5 && !n.includes('Aulas')) r.push({n:n, s:(s==='Matriculado'||s==='')?'Ativo':'Inativo'});}}); return r;"
                alunos_portal = self.driver.execute_script(script_extracao)

                if not alunos_portal:
                    messagebox.showwarning("Aviso de Carregamento",
                                           "Não li nenhum aluno. Certifique-se de estar com a pauta aberta na tela.")
                    continue

                for aluno in alunos_portal:
                    nome, status = aluno['n'], aluno['s']
                    try:
                        # 💡 ALINHAMENTO COM O CÓDIGO SIMPLES: Força escola_id = 2 fixa para teste igualzinho ao seu código funcional
                        escola_teste = 2

                        cursor.execute("""
                            SELECT id FROM alunos 
                            WHERE escola_id = %s AND nome_completo = %s AND turma = %s
                        """, (escola_teste, nome, turma_alvo))
                        aluno_data = cursor.fetchone()

                        if aluno_data:
                            aluno_id = aluno_data[0]
                            cursor.execute("""
                                UPDATE alunos 
                                SET status = %s, vinculo_turma_id = %s 
                                WHERE id = %s
                            """, (status, vinculo_id, aluno_id))
                        else:
                            cursor.execute("""
                                INSERT INTO alunos (escola_id, nome_completo, turma, status, vinculo_turma_id) 
                                VALUES (%s, %s, %s, %s, %s) 
                                RETURNING id
                            """, (escola_teste, nome, turma_alvo, status, vinculo_id))
                            aluno_id = cursor.fetchone()[0]

                        conn.commit()

                        if status == "Ativo":
                            cursor.execute("""
                                                        SELECT av1, av2, av3, recuperacao, faltas FROM notas_bimestre 
                                                        WHERE aluno_id = %s AND trimestre = %s
                                                    """, (aluno_id, int(trimestre_alvo)))
                            nota_data = cursor.fetchone()

                            if nota_data:
                                v_av1, v_av2, v_av3, v_rec, v_faltas = nota_data
                                somatorio = float(v_av1 or 0) + float(v_av2 or 0) + float(v_av3 or 0)

                                # Localiza a linha e os campos do aluno na SEEDUC
                                xpath_linha = f"//tr[td[contains(text(), '{nome}')]]"
                                linha = self.driver.find_element(By.XPATH, xpath_linha)
                                campo_n = linha.find_element(By.CSS_SELECTOR, "input[name*='.NotaProva']")
                                campo_f = linha.find_element(By.CSS_SELECTOR, "input[name*='.Faltas']")

                                # 1. Sempre lança o somatório original no campo principal
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", campo_n)
                                time.sleep(0.1)
                                campo_n.click()
                                campo_n.clear()
                                campo_n.send_keys(str(round(somatorio, 1)).replace('.', ','))

                                # 2. Condicional da SEEDUC: Se a nota foi baixa, abre e preenche a recuperação
                                if somatorio < 5.0:
                                    try:
                                        try:
                                            WebDriverWait(self.driver, 3).until(EC.alert_is_present())
                                            self.driver.switch_to.alert.accept()
                                            time.sleep(1.0)
                                        except:
                                            pass

                                        # Ativa o checkbox para fazer o portal exibir o campo numérico
                                        self.driver.execute_script("""
                                                                    let linha = arguments[0];
                                                                    let cb = linha.querySelector("input[type='checkbox'][name*='.PossuiRecuperacao']");
                                                                    if (cb && !cb.checked) { cb.click(); }
                                                                """, linha)
                                        time.sleep(1.5)

                                        # Captura o campo de recuperação que apareceu na tela e injeta o valor
                                        campo_rec = linha.find_element(By.CSS_SELECTOR, "input.inputnotarecuperacao")
                                        self.driver.execute_script("arguments[0].value = arguments[1];", campo_rec,
                                                                   str(round(float(v_rec or 0.0), 1)).replace('.', ','))

                                        # Dispara os eventos para o portal da SEEDUC salvar a alteração na linha
                                        self.driver.execute_script("arguments[0].dispatchEvent(new Event('change'));",
                                                                   campo_rec)
                                        self.driver.execute_script("arguments[0].dispatchEvent(new Event('blur'));",
                                                                   campo_rec)

                                        print(f"[OK] Recuperação lançada para {nome}")
                                    except Exception as eRec:
                                        print(f"Aviso: Falha na recuperação de {nome}: {eRec}")

                                # 3. Preenche as Faltas
                                campo_f.click()
                                campo_f.clear()
                                campo_f.send_keys(str(int(v_faltas or 0)))

                    except Exception as e:
                        print(f"Erro ao processar {nome}: {e}")
                        conn.rollback()

                if not CardFinalizacao(self,
                                       msg_principal="Lançamentos concluídos nesta turma. Mude de pauta no portal antes de avançar.").resultado:
                    break

            self.deiconify()
        except Exception as e:
            messagebox.showerror("Erro Crítico", f"Ocorreu uma falha no motor do robô: {e}")
            self.deiconify()
        finally:
            if conn: conn.close()


# =================================================================
# TELA DE LOGIN
# =================================================================

class TelaLogin(ctk.CTk):
    USER_FINAL = None
    ESCOLA_FINAL = None

    def __init__(self):
        super().__init__()
        self.title("🛡️ Acesso Integrador Docente")
        self.geometry("420x620")  # Aumentado ligeiramente para o novo robô se destacar
        self.eval('tk::PlaceWindow . center')
        self.attributes("-topmost", True)
        self.configure(fg_color="#1a1a1a")
        self.usuario_logado = None
        self.grid_columnconfigure(0, weight=1)

        try:
            # 💡 SALVE A IMAGEM COMO "logo_robot.png" NA SUA PASTA DE PROJETO
            img_path = recurso_path("6.png")
            img_original = Image.open(img_path)
            # Tamanho ajustado para 180x180 para dar destaque ao robô com o terminal holográfico
            self.logo_image = ctk.CTkImage(light_image=img_original, dark_image=img_original, size=(180, 180))
            self.logo_label = ctk.CTkLabel(self, text="", image=self.logo_image)
            self.logo_label.grid(row=0, column=0, pady=(30, 5), sticky="ew")
        except Exception as e:
            self.logo_label = ctk.CTkLabel(self, text="[LOGO]", font=("Roboto", 14), text_color="gray")
            self.logo_label.grid(row=0, column=0, pady=(40, 10))

        ctk.CTkLabel(self, text="LOGIN DO DOCENTE", font=("Urbanist", 22, "bold"), text_color="#3b82f6").grid(row=1,
                                                                                                              column=0,
                                                                                                              pady=5,
                                                                                                              sticky="ew")

        self.u = ctk.CTkEntry(self, placeholder_text="Usuário", width=300, height=45)
        self.u.grid(row=2, column=0, pady=10)

        self.p = ctk.CTkEntry(self, placeholder_text="Senha", show="*", width=300, height=45)
        self.p.grid(row=3, column=0, pady=10)

        ctk.CTkButton(self, text="ACESSAR SISTEMA", command=self.logar, fg_color="#3b82f6", height=50, width=300,
                      font=("Roboto", 14, "bold")).grid(row=4, column=0, pady=20)

        t = "Ao acessar, você concorda com os Termos de Uso\ne com a Política de Privacidade do sistema."
        ctk.CTkLabel(self, text=t, font=("Roboto", 11, "bold"), text_color="#cbd5e1", justify="center").grid(row=5,
                                                                                                             column=0,
                                                                                                             pady=10,
                                                                                                             sticky="ew")

        self.msg = ctk.CTkLabel(self, text="", text_color="#ef4444")
        self.msg.grid(row=6, column=0)

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
                self.withdraw()

                # Captura inteligente por nome da escola (SaaS Universal)
                dialogo = JanelaDialogo("Identificação do Colégio",
                                        "Digite o nome (ou parte do nome) da Escola para o lançamento:",
                                        "Ex: Agripino, Nazareth...")
                nome_escola_digitado = dialogo.resultado

                if not nome_escola_digitado or not nome_escola_digitado.strip():
                    messagebox.showwarning("Aviso", "Nome da escola não pode ser vazio. Login cancelado.")
                    self.deiconify()
                    cur.close();
                    conn.close()
                    return

                termo_busca = f"%{nome_escola_digitado.strip()}%"
                cur.execute("SELECT id, nome FROM escolas WHERE nome ILIKE %s LIMIT 1", (termo_busca,))
                escola_data = cur.fetchone()

                if escola_data:
                    id_real_escola = escola_data[0]
                    nome_real_escola = escola_data[1]

                    messagebox.showinfo("Escola Identificada", f"Conectado com sucesso ao:\n{nome_real_escola}")

                    TelaLogin.USER_FINAL = self.usuario_logado
                    TelaLogin.ESCOLA_FINAL = id_real_escola

                    print(
                        f"[SAAS SYSTEM] Lançador pronto para a escola: {nome_real_escola} (ID: {TelaLogin.ESCOLA_FINAL})")

                    cur.close();
                    conn.close()
                    self.quit()
                    self.destroy()
                else:
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
                self.msg.configure(text="Acesso negado ou conta suspensa.")
        except Exception as e:
            self.msg.configure(text=f"Erro de conexão: {str(e)}")


# =================================================================
# INICIALIZAÇÃO DA APLICAÇÃO SAAS
# =================================================================
if __name__ == "__main__":
    login = TelaLogin()
    login.mainloop()

    usuario_final = TelaLogin.USER_FINAL
    escola_final = TelaLogin.ESCOLA_FINAL

    if usuario_final:
        app_painel = PainelSGI(usuario=usuario_final, escola_id=escola_final)
        app_painel.mainloop()
