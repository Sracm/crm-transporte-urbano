# -*- coding: utf-8 -*-
"""
BANCO DE DADOS INTEGRADO - CRM & SERVICE DESK TRANSPORTE URBANO
Data: 2026-11-24
60 a 70 Colaboradores nas 10 Áreas Operacionais + Chamados / OS + Ponto Eletrônico + Integração RH x Financeiro
"""

import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(r"c:\Users\amello\OneDrive - MQHAIR\T.I\PROJETOS BI\ANTIGRAVITY\PROJETOS\CRM_TRANSPORTE_URBANO\crm_transporte.db")

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Tabela de Colaboradores / Usuários (60 a 70 usuários)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        matricula TEXT UNIQUE NOT NULL,
        nome TEXT NOT NULL,
        cargo TEXT NOT NULL,
        departamento TEXT NOT NULL,
        email TEXT NOT NULL,
        telefone TEXT NOT NULL,
        status TEXT DEFAULT 'Ativo',
        foto_avatar TEXT,
        perfil_acesso TEXT NOT NULL
    )
    """)
    
    # 2. Tabela de Chamados / Ordens de Serviço (Service Desk & Manutenção)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chamados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        protocolo TEXT UNIQUE NOT NULL,
        titulo TEXT NOT NULL,
        departamento_origem TEXT NOT NULL,
        departamento_destino TEXT NOT NULL,
        solicitante_id INTEGER,
        solicitante_nome TEXT NOT NULL,
        responsavel_id INTEGER,
        responsavel_nome TEXT,
        prioridade TEXT NOT NULL, -- Baixa, Média, Alta, Crítica
        categoria TEXT NOT NULL,  -- Mecânica, Elétrica, Ar Condicionado, Pneu, Bilhetagem, RH/Folha, Infra Garagem, Sinistro
        prefixo_veiculo TEXT,
        linha TEXT,
        descricao TEXT NOT NULL,
        resolucao TEXT,
        status TEXT NOT NULL DEFAULT 'Aberto', -- Aberto, Em Atendimento, Aguardando Peças, Concluído, Cancelado
        data_abertura DATETIME NOT NULL,
        data_previsao DATETIME,
        data_fechamento DATETIME,
        sla_horas INTEGER DEFAULT 24,
        email_abertura_enviado INTEGER DEFAULT 1,
        email_fechamento_enviado INTEGER DEFAULT 0,
        custo_estimado REAL DEFAULT 0.0,
        FOREIGN KEY (solicitante_id) REFERENCES usuarios(id)
    )
    """)
    
    # 3. Tabela de Histórico / Timeline de Chamados
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chamados_historico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chamado_id INTEGER NOT NULL,
        usuario_nome TEXT NOT NULL,
        acao TEXT NOT NULL,
        observacao TEXT,
        data_hora DATETIME NOT NULL,
        FOREIGN KEY (chamado_id) REFERENCES chamados(id)
    )
    """)
    
    # 4. Tabela de Ponto Eletrônico (Gestão de Jornada & Integração RH x Financeiro)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ponto_eletronico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        matricula TEXT NOT NULL,
        nome TEXT NOT NULL,
        departamento TEXT NOT NULL,
        cargo TEXT NOT NULL,
        data_ponto DATE NOT NULL,
        entrada_1 TEXT,
        saida_1 TEXT,
        entrada_2 TEXT,
        saida_2 TEXT,
        total_horas_trabalhadas REAL DEFAULT 8.0,
        horas_extras REAL DEFAULT 0.0,
        horas_falta REAL DEFAULT 0.0,
        status_registro TEXT NOT NULL DEFAULT 'Normal', -- Normal, Hora Extra, Falta, Atestado, DSR, Atraso
        observacao_rh TEXT,
        aprovado_gestor INTEGER DEFAULT 1,
        custo_hora_extra REAL DEFAULT 0.0,
        desconto_falta REAL DEFAULT 0.0,
        visivel_financeiro INTEGER DEFAULT 1,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    )
    """)
    
    # 5. Tabela de Portaria & Movimentação de Garagem (Entradas e Saídas)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS portaria_movimentacao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prefixo_veiculo TEXT NOT NULL,
        linha TEXT NOT NULL,
        motorista_nome TEXT NOT NULL,
        motorista_matricula TEXT NOT NULL,
        porteiro_nome TEXT NOT NULL,
        tipo_movimento TEXT NOT NULL, -- Saída Garagem, Entrada Garagem
        data_hora DATETIME NOT NULL,
        km_registro INTEGER NOT NULL,
        nivel_combustivel TEXT NOT NULL, -- 100%, 75%, 50%, 25%, Reserva
        avaria_apontada TEXT,
        status_liberacao TEXT NOT NULL DEFAULT 'Liberado', -- Liberado, Retido Manutenção, Retido Documento
        os_aberta_id INTEGER
    )
    """)
    
    # 6. Tabela de Integração Financeira (Contas a Pagar e Receber vinculadas às Áreas)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS financeiro_integracao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        origem_area TEXT NOT NULL, -- RH_Folha, Manutenção_Peças, Garagem_Diesel, Receita_Bilhetagem, Receita_Subsidio
        tipo TEXT NOT NULL,        -- Pagar, Receber
        descricao TEXT NOT NULL,
        referencia_documento TEXT,
        valor REAL NOT NULL,
        data_lancamento DATE NOT NULL,
        data_vencimento DATE NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pendente', -- Pendente, Aprovado, Pago, Recebido
        responsavel_aprovacao TEXT
    )
    """)
    
    # 7. Tabela de Logs de E-mails Disparados
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS log_emails (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo_evento TEXT NOT NULL, -- Abertura_OS, Fechamento_OS, Alerta_Ponto, Aviso_Diretoria
        protocolo_ref TEXT,
        destinatario_nome TEXT NOT NULL,
        destinatario_email TEXT NOT NULL,
        assunto TEXT NOT NULL,
        corpo_html TEXT NOT NULL,
        data_envio DATETIME NOT NULL,
        status_envio TEXT DEFAULT 'Enviado com Sucesso'
    )
    """)
    
    conn.commit()
    print("✅ Estrutura de tabelas criada com sucesso!")
    
    # Inserção de dados iniciais realistas
    seed_data(conn)
    conn.close()

def seed_data(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] > 0:
        print("Tabelas já possuem dados. Pulando seed.")
        return

    print("Gerando 65 Colaboradores nas 10 Áreas...")
    
    departamentos_config = [
        ("Diretor de Operações", [
            ("Antonio Carlos de Mello", "Diretor Geral de Operações & BI", "Diretoria"),
            ("Eduardo Paiva", "Diretor Adjunto de Transportes", "Diretoria"),
        ]),
        ("Gerente Operacional", [
            ("Marcos Vinicius Rezende", "Gerente Geral de Tráfego e Escala", "Gestão"),
            ("Claudio Albuquerque", "Gerente Operacional Noturno", "Gestão"),
        ]),
        ("Gerente Administrativo", [
            ("Sandra Helena Costa", "Gerente Administrativa & Facilities", "Gestão"),
            ("Ricardo Penteado", "Coordenador de Suprimentos & Almoxarifado", "Gestão"),
        ]),
        ("Manutenção", [
            ("Carlos Roberto Silva", "Supervisor Geral de Oficina", "Operacional"),
            ("Valdir Guimarães", "Encarregado de Mecânica Diesel", "Operacional"),
            ("Ailton Ferreira de Souza", "Mecânico Socorrista - SOS", "Operacional"),
            ("Rodrigo Mendes Rocha", "Eletricista de Frota & Ar-Condicionado", "Operacional"),
            ("Gilberto Nogueira", "Mecânico de Freios e Suspensão", "Operacional"),
            ("Fábio Cristiano Luz", "Funileiro & Pintor de Carroceria", "Operacional"),
            ("Lucas Tadeu Martins", "Técnico de Telemetria e Validador", "Operacional"),
            ("Paulo Henrique Dias", "Borracheiro de Pátio", "Operacional"),
            ("José Nilson Barbosa", "Mecânico Motor e Câmbio", "Operacional"),
            ("Marcio Silveira", "Auxiliar de Manutenção", "Operacional"),
        ]),
        ("RH", [
            ("Renata Vasconcelos", "Supervisora de Recursos Humanos", "Gestão"),
            ("Juliana Moraes", "Analista de Departamento Pessoal & Ponto", "Administrativo"),
            ("Camila Brandão", "Analista de Benefícios & Atendimento", "Administrativo"),
            ("Patricia Soares", "Assistente de Admissão & Demissão", "Administrativo"),
            ("Tiago Faria", "Assistente de Ponto Eletrônico", "Administrativo"),
            ("Beatriz Alcantara", "Psicóloga Organizacional & Clima", "Administrativo"),
        ]),
        ("Treinamento", [
            ("Sérgio Luiz Fontana", "Coordenador de Treinamento e Segurança", "Gestão"),
            ("Ademir dos Santos", "Instrutor de Direção Defensiva & MOPP", "Operacional"),
            ("Rogério Batista", "Instrutor de Integração & Tecnologia Embarcada", "Operacional"),
            ("Marcio Antunes", "Monitor de Telemetria & Condução Econômica", "Operacional"),
        ]),
        ("Contas a Pagar", [
            ("Mariana Fontes", "Coordenadora de Contas a Pagar", "Financeiro"),
            ("Fernanda Gomes", "Analista de Pagamentos - Diesel & Peças", "Financeiro"),
            ("Leandro Prado", "Analista Financeiro - Contratos & Serviços", "Financeiro"),
            ("Tatiane Ribeiro", "Assistente de Conciliação Bancária", "Financeiro"),
            ("Gabriel Nunes", "Assistente de Contas a Pagar", "Financeiro"),
        ]),
        ("Contas a Receber", [
            ("Luciano Barreto", "Coordenador de Faturamento & Bilhetagem", "Financeiro"),
            ("Aline Castilho", "Analista de Bilhetagem Eletrônica & SPTrans", "Financeiro"),
            ("Viviane Ramos", "Analista de Recebíveis & Fretamento", "Financeiro"),
            ("Danilo Duarte", "Assistente de Conciliação de Tarifas", "Financeiro"),
            ("Amanda Meirelles", "Assistente de Contas a Receber", "Financeiro"),
        ]),
        ("Garagem", [
            ("Wellington Aparecido", "Supervisor de Pátio e Abastecimento", "Operacional"),
            ("Edmilson Ramos", "Manobrista Líder Turno Manhã", "Operacional"),
            ("Sebastião Pereira", "Manobrista Turno Tarde", "Operacional"),
            ("Cleber Moreira", "Manobrista Turno Noite/Madrugada", "Operacional"),
            ("Jonas Vicente", "Operador de Bomba de Combustível (Diesel)", "Operacional"),
            ("Valdemar Simões", "Operador de Lavador Automático de Ônibus", "Operacional"),
            ("Elton John Dias", "Fiscal de Pátio e Liberação", "Operacional"),
            ("Denis Oliveira", "Auxiliar de Pátio", "Operacional"),
            ("Cristiano Viana", "Auxiliar de Abastecimento", "Operacional"),
            ("Moacir da Silva", "Conferente de Higienização de Frota", "Operacional"),
        ]),
        ("Portaria", [
            ("Osvaldo Severino", "Supervisor de Portaria & Segurança Patrimonial", "Operacional"),
            ("Benedito Queiroz", "Porteiro Controlador de Acesso - Portão 1", "Operacional"),
            ("Severino Ramos", "Porteiro Controlador de Acesso - Portão 2", "Operacional"),
            ("Genivaldo Castro", "Porteiro Noturno - Registro de Frota", "Operacional"),
            ("Agenor Rodrigues", "Porteiro Turno B - Escalas e Crachá", "Operacional"),
            ("Waldomiro Santos", "Controlador de Balança e Quilometragem", "Operacional"),
            ("Clodoaldo Lima", "Porteiro Portão Central", "Operacional"),
            ("Reginaldo Peixoto", "Porteiro Noturno Guarita Leste", "Operacional"),
            ("José Carlos Macedo", "Fiscal de Entrada de Colaboradores", "Operacional"),
            ("Vanderlei Correa", "Porteiro de Reserva e Ronda", "Operacional"),
            ("Ariovaldo Pires", "Porteiro Diurno Guarita Norte", "Operacional"),
            ("Claudinei Bueno", "Porteiro Revezamento 12x36", "Operacional"),
            ("Milton Fonseca", "Porteiro Revezamento 12x36", "Operacional"),
            ("Jurandir Alcantara", "Porteiro Noturno Entrada de Peças", "Operacional"),
        ])
    ]
    
    mat_counter = 1001
    users_list = []
    
    for dep, pessoas in departamentos_config:
        for nome, cargo, perfil in pessoas:
            email_slug = nome.lower().replace(" ", ".").replace("ã", "a").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ç", "c")
            email = f"{email_slug}@viacaourbana.com.br"
            telefone = f"(11) 9{random.randint(7000, 9999)}-{random.randint(1000, 9999)}"
            mat = f"VUR-{mat_counter}"
            
            cursor.execute("""
            INSERT INTO usuarios (matricula, nome, cargo, departamento, email, telefone, status, perfil_acesso)
            VALUES (?, ?, ?, ?, ?, ?, 'Ativo', ?)
            """, (mat, nome, cargo, dep, email, telefone, perfil))
            
            users_list.append((cursor.lastrowid, mat, nome, cargo, dep, email))
            mat_counter += 1
            
    print(f"✅ {len(users_list)} usuários cadastrados com sucesso!")
    
    # 2. Seed de Chamados / Ordens de Serviço
    print("Gerando Ordens de Serviço e Chamados...")
    categorias_os = [
        ("Falha no Compressor de Freio Pneumático", "Manutenção", "Portaria", "Crítica", "Mecânica", "5014", "Linha 801 - Term. Central x Term. Sul", 350.0),
        ("Validador de Bilhetagem Travado em Tela Preta", "Manutenção", "Gerente Operacional", "Alta", "Bilhetagem", "5028", "Linha 703 - Bairro Alto x Estação Metrô", 120.0),
        ("Vazamento no Radiador de Arrefecimento Diesel", "Manutenção", "Garagem", "Crítica", "Mecânica", "5045", "Linha 602 - Circular Hospitais", 480.0),
        ("Ar-Condicionado sem Refrigeração (Código E-04)", "Manutenção", "Gerente Operacional", "Média", "Ar Condicionado", "5008", "Linha 805 - Expresso Corredor Norte", 220.0),
        ("Pneu Dianteiro Direito com Desgaste Irregular", "Manutenção", "Portaria", "Alta", "Pneu", "5077", "Linha 504 - Vila Progresso x Centro", 650.0),
        ("Solicitação de Ajuste de Ponto por Falha de Catraca", "RH", "Gerente Operacional", "Média", "RH/Folha", None, None, 0.0),
        ("Substituição de Lâmpada de LED do Pátio Garagem 2", "Gerente Administrativo", "Garagem", "Baixa", "Infra Garagem", None, None, 85.0),
        ("Colisão Leve Retrovisor Esquerdo em Manobra", "Manutenção", "Garagem", "Alta", "Sinistro", "5019", "Linha 701 - Jardim América x Rodoviária", 410.0),
        ("Reciclagem Obrigatória de Direção Defensiva - CNH", "Treinamento", "RH", "Média", "Treinamento", None, None, 150.0),
        ("Divergência de Repasse no Repasse SPTrans de Outubro", "Contas a Receber", "Diretor de Operações", "Alta", "Bilhetagem", None, None, 0.0),
        ("Nota Fiscal de Combustível Diesel S-10 para Pagamento", "Contas a Pagar", "Garagem", "Alta", "Combustível", None, None, 142000.0),
        ("Travamento na Catraca de Entrada de Funcionários", "Gerente Administrativo", "Portaria", "Alta", "Infra Garagem", None, None, 290.0)
    ]
    
    proto_num = 840
    now = datetime.now()
    
    for titulo, dep_dest, dep_orig, prioridade, cat, pref, linha, custo in categorias_os:
        proto = f"OS-2026-{proto_num:04d}"
        proto_num += 1
        
        # Encontra solicitante compatível
        cands_sol = [u for u in users_list if u[4] == dep_orig]
        sol = random.choice(cands_sol) if cands_sol else users_list[0]
        
        # Encontra responsável compatível
        cands_resp = [u for u in users_list if u[4] == dep_dest]
        resp = random.choice(cands_resp) if cands_resp else users_list[1]
        
        status = random.choice(["Aberto", "Em Atendimento", "Concluído", "Em Atendimento"])
        dt_abertura = now - timedelta(hours=random.randint(2, 72))
        dt_prev = dt_abertura + timedelta(hours=24)
        dt_fecha = dt_abertura + timedelta(hours=random.randint(4, 18)) if status == "Concluído" else None
        
        cursor.execute("""
        INSERT INTO chamados (
            protocolo, titulo, departamento_origem, departamento_destino,
            solicitante_id, solicitante_nome, responsavel_id, responsavel_nome,
            prioridade, categoria, prefixo_veiculo, linha, descricao, resolucao,
            status, data_abertura, data_previsao, data_fechamento, sla_horas,
            email_abertura_enviado, email_fechamento_enviado, custo_estimado
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 24, 1, ?, ?)
        """, (
            proto, titulo, dep_orig, dep_dest, sol[0], sol[2], resp[0], resp[2],
            prioridade, cat, pref, linha,
            f"Ocorrência registrada no sistema operacional pelo colaborador {sol[2]} ({dep_orig}). Requer providências imediatas.",
            "Reparo efetuado com substituição preventiva e testes de rodagem aprovados pelo encarregado técnico." if status == "Concluído" else None,
            status, dt_abertura, dt_prev, dt_fecha, 1 if status == "Concluído" else 0, custo
        ))
        chamado_id = cursor.lastrowid
        
        # Insere histórico
        cursor.execute("""
        INSERT INTO chamados_historico (chamado_id, usuario_nome, acao, observacao, data_hora)
        VALUES (?, ?, 'Abertura de Chamado', 'Chamado registrado com disparo automático de e-mail ao setor responsável.', ?)
        """, (chamado_id, sol[2], dt_abertura))
        
        if status in ["Em Atendimento", "Concluído"]:
            cursor.execute("""
            INSERT INTO chamados_historico (chamado_id, usuario_nome, acao, observacao, data_hora)
            VALUES (?, ?, 'Início de Atendimento', 'Equipe técnica alocou recursos e iniciou o diagnóstico na vala/estação.', ?)
            """, (chamado_id, resp[2], dt_abertura + timedelta(hours=1)))
            
        if status == "Concluído":
            cursor.execute("""
            INSERT INTO chamados_historico (chamado_id, usuario_nome, acao, observacao, data_hora)
            VALUES (?, ?, 'Conclusão & Fechamento', 'Serviço finalizado com sucesso. E-mail de encerramento enviado ao solicitante.', ?)
            """, (chamado_id, resp[2], dt_fecha))
            
            # Log de email de fechamento
            cursor.execute("""
            INSERT INTO log_emails (tipo_evento, protocolo_ref, destinatario_nome, destinatario_email, assunto, corpo_html, data_envio)
            VALUES ('Fechamento_OS', ?, ?, ?, ?, ?, ?)
            """, (
                proto, sol[2], sol[5],
                f"[CONCLUÍDO] Ordem de Serviço {proto} - {titulo}",
                f"<p>Prezado(a) {sol[2]},<br>Sua Ordem de Serviço {proto} referente ao veículo {pref or 'Geral'} foi CONCLUÍDA com sucesso.</p>",
                dt_fecha
            ))
            
        # Log de email de abertura
        cursor.execute("""
        INSERT INTO log_emails (tipo_evento, protocolo_ref, destinatario_nome, destinatario_email, assunto, corpo_html, data_envio)
        VALUES ('Abertura_OS', ?, ?, ?, ?, ?, ?)
        """, (
            proto, resp[2], resp[5],
            f"[NOVO CHAMADO] Ordem de Serviço {proto} - Prioridade {prioridade}",
            f"<p>Prezado(a) {resp[2]},<br>Uma nova OS {proto} foi atribuída ao seu setor ({dep_dest}).</p>",
            dt_abertura
        ))

    # 3. Seed de Ponto Eletrônico (Últimos 5 dias para todos os 65 colaboradores)
    print("Gerando Ponto Eletrônico com integração RH x Financeiro...")
    dias_ponto = [now.date() - timedelta(days=i) for i in range(5, -1, -1)]
    
    for u in users_list:
        u_id, mat, nome, cargo, dep, email = u
        
        for dt in dias_ponto:
            # 85% normal, 10% hora extra, 3% atraso/falta, 2% atestado
            rnd = random.random()
            if rnd < 0.85:
                status_p = "Normal"
                e1, s1, e2, s2 = "08:00", "12:00", "13:00", "17:00"
                he, hf = 0.0, 0.0
                obs = "Jornada regular cumprida integralmente"
                custo_he, desc_f = 0.0, 0.0
            elif rnd < 0.95:
                status_p = "Hora Extra"
                he = random.choice([1.5, 2.0, 2.5])
                s2 = f"{17 + int(he):02d}:{int((he % 1) * 60):02d}"
                e1, s1, e2 = "08:00", "12:00", "13:00"
                hf = 0.0
                obs = f"Hora extra autorizada pelo gestor imediato ({he}h)"
                custo_he = round(he * 38.50, 2)
                desc_f = 0.0
            elif rnd < 0.98:
                status_p = "Atraso/Falta"
                hf = random.choice([1.0, 4.0, 8.0])
                if hf == 8.0:
                    e1, s1, e2, s2 = "--:--", "--:--", "--:--", "--:--"
                    obs = "Falta injustificada apurada pelo RH"
                    desc_f = 160.0
                else:
                    e1, s1, e2, s2 = "09:30", "12:00", "13:00", "17:00"
                    obs = "Atraso no início do turno"
                    desc_f = 45.0
                he = 0.0
                custo_he = 0.0
            else:
                status_p = "Atestado Médico"
                e1, s1, e2, s2 = "--:--", "--:--", "--:--", "--:--"
                he, hf = 0.0, 0.0
                obs = "Atestado médico homologado pelo RH (CID homologado)"
                custo_he, desc_f = 0.0, 0.0
                
            cursor.execute("""
            INSERT INTO ponto_eletronico (
                usuario_id, matricula, nome, departamento, cargo, data_ponto,
                entrada_1, saida_1, entrada_2, saida_2,
                total_horas_trabalhadas, horas_extras, horas_falta,
                status_registro, observacao_rh, aprovado_gestor,
                custo_hora_extra, desconto_falta, visivel_financeiro
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, 1)
            """, (
                u_id, mat, nome, dep, cargo, dt.strftime("%Y-%m-%d"),
                e1, s1, e2, s2, 8.0 + he - hf, he, hf,
                status_p, obs, custo_he, desc_f
            ))

    # 4. Seed de Portaria & Garagem
    print("Gerando Movimentações de Portaria e Garagem...")
    prefixos = ["5008", "5014", "5019", "5028", "5045", "5077", "5089", "5102", "5125", "5140"]
    linhas = ["Linha 801 - Central", "Linha 703 - Metrô", "Linha 602 - Hospitais", "Linha 504 - Progresso", "Linha 805 - Corredor"]
    porteiros = [u[2] for u in users_list if u[4] == "Portaria"]
    
    km_base = 145000
    for i in range(25):
        pref = random.choice(prefixos)
        lin = random.choice(linhas)
        porteiro = random.choice(porteiros)
        tipo = random.choice(["Saída Garagem", "Entrada Garagem"])
        km_base += random.randint(30, 180)
        tanque = random.choice(["100%", "85%", "70%", "50%", "30%"])
        avaria = "Pequeno risco lanterna traseira" if random.random() < 0.15 else "Sem avarias visuais"
        dt_mov = now - timedelta(minutes=random.randint(10, 600))
        
        cursor.execute("""
        INSERT INTO portaria_movimentacao (
            prefixo_veiculo, linha, motorista_nome, motorista_matricula,
            porteiro_nome, tipo_movimento, data_hora, km_registro,
            nivel_combustivel, avaria_apontada, status_liberacao
        ) VALUES (?, ?, 'Motorista Operacional', 'MOT-2044', ?, ?, ?, ?, ?, ?, 'Liberado')
        """, (pref, lin, porteiro, tipo, dt_mov, km_base, tanque, avaria))

    # 5. Seed de Integração Financeira
    print("Gerando Lançamentos Financeiros Integrados (Contas a Pagar / Receber)...")
    lancamentos = [
        ("RH_Folha", "Pagar", "Provisão de Horas Extras - Semana Operacional CCO", "FOLHA-HE-NOV26", 18450.00, "Pendente", "Sandra Helena (Ger. Adm)"),
        ("Manutenção_Peças", "Pagar", "Aquisição de Filtros e Óleo Lubrificante Diesel 15W40", "NF-OFICINA-9042", 12380.00, "Aprovado", "Carlos Roberto (Oficina)"),
        ("Garagem_Diesel", "Pagar", "Fornecimento de Combustível Diesel S-10 (20.000 Litros)", "NF-DIESEL-44819", 118400.00, "Pendente", "Eduardo Paiva (Diretoria)"),
        ("Receita_Bilhetagem", "Receber", "Repasse Semanal Bilhetagem Eletrônica SPTrans", "REC-SPTRANS-W47", 348900.00, "Recebido", "Luciano Barreto (Fat.)"),
        ("Receita_Subsidio", "Receber", "Subsídio Municipal por Quilômetro Rodado (Câmara)", "SUB-PREF-11-2026", 285400.00, "Pendente", "Antonio Carlos de Mello (Diretor)")
    ]
    
    for origem, tipo, desc, ref, val, st, resp in lancamentos:
        cursor.execute("""
        INSERT INTO financeiro_integracao (
            origem_area, tipo, descricao, referencia_documento, valor,
            data_lancamento, data_vencimento, status, responsavel_aprovacao
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            origem, tipo, desc, ref, val,
            (now - timedelta(days=2)).strftime("%Y-%m-%d"),
            (now + timedelta(days=5)).strftime("%Y-%m-%d"),
            st, resp
        ))

    conn.commit()
    print("🚀 Base de dados povoada com sucesso!")

if __name__ == "__main__":
    init_database()
