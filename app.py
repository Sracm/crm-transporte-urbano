# -*- coding: utf-8 -*-
"""
CRM & SERVICE DESK OPERACIONAL - TRANSPORTE URBANO
Porta: 5700
Integração de 10 Áreas: Gerente Operacional, Gerente Adm, Diretor de Operações,
Manutenção, RH, Treinamento, Contas a Pagar, Contas a Receber, Garagem, Portaria.
"""

import os
import sqlite3
import calendar
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory

app = Flask(__name__)

@app.template_filter("moeda")
def moeda_filter(val):
    try:
        return f"{float(val or 0.0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00"

@app.template_filter("dec1")
def dec1_filter(val):
    try:
        return f"{float(val or 0.0):.1f}"
    except Exception:
        return "0.0"

@app.template_filter("intformat")
def int_filter(val):
    try:
        return f"{int(float(val or 0)):,}".replace(",", ".")
    except Exception:
        return "0"

DB_PATH = os.path.join(os.path.dirname(__file__), "crm_transporte.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json")

@app.route("/service-worker.js")
def service_worker():
    return send_from_directory("static", "service-worker.js")

@app.route("/mobile")
@app.route("/app")
def mobile_view():
    return redirect(url_for("dashboard"))

@app.route("/cco")
def cco_view():
    linhas_cco = [
        {"linha": "Linha 801", "nome": "Central x Term. Sul", "frota": 32, "intervalo": "4 min", "pontualidade": 99.1, "status": "Normal", "velocidade": "21 km/h", "corredor": "Corredor Sul"},
        {"linha": "Linha 703", "nome": "Bairro Alto x Metrô", "frota": 26, "intervalo": "6 min", "pontualidade": 94.8, "status": "Atenção", "velocidade": "16 km/h", "corredor": "Eixo Radial Leste"},
        {"linha": "Linha 602", "nome": "Circular Hospitais", "frota": 18, "intervalo": "8 min", "pontualidade": 98.2, "status": "Normal", "velocidade": "24 km/h", "corredor": "Anel Viário Central"},
        {"linha": "Linha 504", "nome": "Vila Progresso x Centro", "frota": 24, "intervalo": "5 min", "pontualidade": 97.9, "status": "Normal", "velocidade": "19 km/h", "corredor": "Corredor Norte"},
        {"linha": "Linha 305", "nome": "Expresso Terminal Leste", "frota": 22, "intervalo": "6 min", "pontualidade": 96.5, "status": "Normal", "velocidade": "22 km/h", "corredor": "Pista Exclusiva Leste"},
        {"linha": "Linha 412", "nome": "Interbairros Norte x Oeste", "frota": 20, "intervalo": "7 min", "pontualidade": 97.2, "status": "Normal", "velocidade": "18 km/h", "corredor": "Avenida Perimetral"}
    ]
    return render_template(
        "cco.html",
        linhas=linhas_cco,
        total_em_linha=142,
        total_programado=150,
        pontualidade_geral=98.4
    )

def send_simulated_email(tipo_evento, protocolo_ref, dest_nome, dest_email, assunto, corpo_html):
    """Registra disparo de e-mail no banco de dados e simula envio automático"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO log_emails (tipo_evento, protocolo_ref, destinatario_nome, destinatario_email, assunto, corpo_html, data_envio, status_envio)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Enviado com Sucesso')
        """, (tipo_evento, protocolo_ref, dest_nome, dest_email, assunto, corpo_html, datetime.now()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro registrando e-mail: {e}")
        return False

# ==================== ROTAS DE PÁGINAS ====================

@app.route("/")
def dashboard():
    departamento = request.args.get("dept", "Todos")
    conn = get_db()
    cursor = conn.cursor()
    
    # KPIs Gerais
    cursor.execute("SELECT COUNT(*) FROM chamados WHERE status != 'Concluído'")
    chamados_abertos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM chamados WHERE prioridade = 'Crítica' AND status != 'Concluído'")
    chamados_criticos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE status = 'Ativo'")
    total_usuarios = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(custo_hora_extra) FROM ponto_eletronico WHERE strftime('%Y-%m', data_ponto) = strftime('%Y-%m', 'now')")
    total_horas_extras = cursor.fetchone()[0] or 0.0
    
    cursor.execute("SELECT COUNT(*) FROM portaria_movimentacao WHERE date(data_hora) = date('now')")
    mov_portaria_hoje = cursor.fetchone()[0]
    
    # Chamados Recentes
    if departamento != "Todos":
        cursor.execute("SELECT * FROM chamados WHERE departamento_destino = ? OR departamento_origem = ? ORDER BY data_abertura DESC LIMIT 10", (departamento, departamento))
    else:
        cursor.execute("SELECT * FROM chamados ORDER BY data_abertura DESC LIMIT 10")
    chamados_recentes = cursor.fetchall()
    
    # Colaboradores por Departamento
    cursor.execute("SELECT departamento, COUNT(*) as total FROM usuarios GROUP BY departamento ORDER BY total DESC")
    dept_stats = cursor.fetchall()
    
    # Histórico de Atividades / Feed Geral
    cursor.execute("""
    SELECT h.id, h.chamado_id, c.protocolo, c.titulo, h.usuario_nome, h.acao, h.observacao, h.data_hora
    FROM chamados_historico h
    JOIN chamados c ON h.chamado_id = c.id
    ORDER BY h.data_hora DESC LIMIT 8
    """)
    atividades_recentes = cursor.fetchall()
    
    # Resumo Financeiro Integrado
    cursor.execute("SELECT SUM(valor) FROM financeiro_integracao WHERE tipo = 'Pagar' AND status = 'Pendente'")
    total_a_pagar = cursor.fetchone()[0] or 0.0
    
    cursor.execute("SELECT SUM(valor) FROM financeiro_integracao WHERE tipo = 'Receber' AND status = 'Pendente'")
    total_a_receber = cursor.fetchone()[0] or 0.0

    conn.close()
    
    return render_template(
        "index.html",
        chamados_abertos=chamados_abertos,
        chamados_criticos=chamados_criticos,
        total_usuarios=total_usuarios,
        total_horas_extras=total_horas_extras,
        mov_portaria_hoje=mov_portaria_hoje,
        chamados_recentes=chamados_recentes,
        dept_stats=dept_stats,
        atividades_recentes=atividades_recentes,
        total_a_pagar=total_a_pagar,
        total_a_receber=total_a_receber,
        departamento_atual=departamento
    )

@app.route("/chamados")
def chamados_view():
    status_filter = request.args.get("status", "Todos")
    dept_filter = request.args.get("dept", "Todos")
    
    conn = get_db()
    cursor = conn.cursor()
    
    query = "SELECT * FROM chamados WHERE 1=1"
    params = []
    
    if status_filter != "Todos":
        query += " AND status = ?"
        params.append(status_filter)
        
    if dept_filter != "Todos":
        query += " AND (departamento_destino = ? OR departamento_origem = ?)"
        params.extend([dept_filter, dept_filter])
        
    query += " ORDER BY CASE prioridade WHEN 'Crítica' THEN 1 WHEN 'Alta' THEN 2 WHEN 'Média' THEN 3 ELSE 4 END, data_abertura DESC"
    cursor.execute(query, params)
    chamados = cursor.fetchall()
    
    # Lista de usuários para o formulário de abertura
    cursor.execute("SELECT id, nome, departamento, email FROM usuarios ORDER BY nome ASC")
    usuarios = cursor.fetchall()
    
    conn.close()
    return render_template("chamados.html", chamados=chamados, usuarios=usuarios, status_atual=status_filter, dept_atual=dept_filter)

@app.route("/ponto")
def ponto_view():
    ano_sel = request.args.get("ano", "2026")
    mes_sel = request.args.get("mes", "11")
    dia_sel = request.args.get("dia", "24")
    dept_sel = request.args.get("dept", "Todos")
    status_filtro = request.args.get("status_filtro", "todos")  # todos, irregular, regular
    ordenar_sel = request.args.get("ordenar", "nome_asc")      # nome_asc, nome_desc, horas_desc, horas_asc, extras_desc
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Determina filtro de data
    if dia_sel != "Todos":
        data_sel = f"{ano_sel}-{int(mes_sel):02d}-{int(dia_sel):02d}"
        query = "SELECT * FROM ponto_eletronico WHERE data_ponto = ?"
        params = [data_sel]
    else:
        data_sel = f"{ano_sel}-{int(mes_sel):02d}"
        query = "SELECT * FROM ponto_eletronico WHERE data_ponto LIKE ?"
        params = [f"{data_sel}%"]
        
    if dept_sel != "Todos":
        query += " AND departamento = ?"
        params.append(dept_sel)
        
    cursor.execute(query, params)
    raw_rows = cursor.fetchall()
    
    # Mapeia registros e identifica irregularidades
    todos_registros = []
    for r in raw_rows:
        item = dict(r)
        
        # Condições de irregularidade:
        # 1. Qualquer batida vazia ou '--:--'
        # 2. Status 'Atraso/Falta', 'Atestado Médico', 'Incompleto'
        # 3. horas_falta > 0
        batidas = [item.get('entrada_1'), item.get('saida_1'), item.get('entrada_2'), item.get('saida_2')]
        falta_batida = any(b in ('--:--', '', None) for b in batidas)
        tem_falta_status = (item.get('horas_falta') or 0.0) > 0 or item.get('status_registro') in ('Atraso/Falta', 'Atestado Médico', 'Incompleto')
        
        item['is_irregular'] = falta_batida or tem_falta_status
        todos_registros.append(item)
        
    total_colab = len(todos_registros)
    qtd_irregulares = sum(1 for r in todos_registros if r['is_irregular'])
    qtd_regulares = total_colab - qtd_irregulares
    perc_irregulares = round((qtd_irregulares / total_colab * 100), 1) if total_colab > 0 else 0.0
    perc_regulares = round((qtd_regulares / total_colab * 100), 1) if total_colab > 0 else 0.0
    
    total_he = sum((r.get('horas_extras') or 0.0) for r in todos_registros)
    custo_he = sum((r.get('custo_hora_extra') or 0.0) for r in todos_registros)
    total_faltas = sum((r.get('horas_falta') or 0.0) for r in todos_registros)
    total_desconto = sum((r.get('desconto_falta') or 0.0) for r in todos_registros)
    
    # Aplica filtro de status rápido
    if status_filtro == 'irregular':
        registros_exibir = [r for r in todos_registros if r['is_irregular']]
    elif status_filtro == 'regular':
        registros_exibir = [r for r in todos_registros if not r['is_irregular']]
    else:
        registros_exibir = todos_registros
        
    # Aplica ordenação
    if ordenar_sel == 'horas_desc':
        registros_exibir.sort(key=lambda x: (x.get('total_horas_trabalhadas') or 0.0), reverse=True)
    elif ordenar_sel == 'horas_asc':
        registros_exibir.sort(key=lambda x: (x.get('total_horas_trabalhadas') or 0.0))
    elif ordenar_sel == 'extras_desc':
        registros_exibir.sort(key=lambda x: (x.get('horas_extras') or 0.0), reverse=True)
    elif ordenar_sel == 'nome_desc':
        registros_exibir.sort(key=lambda x: x.get('nome', '').lower(), reverse=True)
    else: # nome_asc
        registros_exibir.sort(key=lambda x: x.get('nome', '').lower())
        
    # Resumo para os Cards
    resumo = {
        'total_colab': total_colab,
        'qtd_irregulares': qtd_irregulares,
        'perc_irregulares': perc_irregulares,
        'qtd_regulares': qtd_regulares,
        'perc_regulares': perc_regulares,
        'total_he': total_he,
        'custo_he': custo_he,
        'total_faltas': total_faltas,
        'total_desconto': total_desconto
    }
    
    # ==================== ESTEIRA DE DIAS DO MÊS (CALENDÁRIO HORIZONTAL) ====================
    num_dias_mes = calendar.monthrange(int(ano_sel), int(mes_sel))[1]
    
    # Consulta a contagem de irregularidades por dia para todo o mês selecionado
    cursor.execute("""
    SELECT 
        data_ponto,
        COUNT(*) as total_dia,
        SUM(CASE WHEN 
            entrada_1 IN ('--:--', '', NULL) OR saida_1 IN ('--:--', '', NULL) OR
            entrada_2 IN ('--:--', '', NULL) OR saida_2 IN ('--:--', '', NULL) OR
            horas_falta > 0 OR status_registro IN ('Atraso/Falta', 'Atestado Médico', 'Incompleto')
            THEN 1 ELSE 0 END) as qtd_irregulares
    FROM ponto_eletronico
    WHERE data_ponto LIKE ?
    GROUP BY data_ponto
    """, (f"{ano_sel}-{int(mes_sel):02d}%",))
    
    dados_dias_mes = {row[0]: {'total_dia': row[1], 'qtd_irregulares': row[2]} for row in cursor.fetchall()}
    
    nomes_meses = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    nome_mes_sel = nomes_meses.get(int(mes_sel), "Novembro")
    dias_semana_abrev = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
    
    esteira_dias = []
    total_irregulares_mes = 0
    
    for d in range(1, num_dias_mes + 1):
        data_iso_d = f"{ano_sel}-{int(mes_sel):02d}-{d:02d}"
        try:
            dt_d = datetime(int(ano_sel), int(mes_sel), d)
            dia_sem = dias_semana_abrev[dt_d.weekday()]
            is_fds = dt_d.weekday() in (5, 6)
        except Exception:
            dia_sem = "--"
            is_fds = False
            
        info = dados_dias_mes.get(data_iso_d)
        if info:
            qtd_irr = int(info['qtd_irregulares'] or 0)
            total_d = int(info['total_dia'] or 0)
            tem_dados = True
            total_irregulares_mes += qtd_irr
        else:
            qtd_irr = 0
            total_d = 0
            tem_dados = False
            
        is_sel = (str(dia_sel) == str(d) or str(dia_sel) == f"{d:02d}")
        
        esteira_dias.append({
            'dia_num': d,
            'dia_str': f"{d:02d}",
            'data_iso': data_iso_d,
            'dia_semana': dia_sem,
            'is_fim_de_semana': is_fds,
            'qtd_irregulares': qtd_irr,
            'total_dia': total_d,
            'tem_dados': tem_dados,
            'is_selecionado': is_sel
        })
    
    # Lista de departamentos únicos
    cursor.execute("SELECT DISTINCT departamento FROM usuarios ORDER BY departamento ASC")
    departamentos = [row[0] for row in cursor.fetchall() if row[0]]
    
    conn.close()
    
    return render_template(
        "ponto.html",
        registros=registros_exibir,
        total_exibido=len(registros_exibir),
        resumo=resumo,
        ano_sel=ano_sel,
        mes_sel=mes_sel,
        dia_sel=dia_sel,
        dept_sel=dept_sel,
        status_filtro=status_filtro,
        ordenar_sel=ordenar_sel,
        departamentos=departamentos,
        data_sel=data_sel,
        esteira_dias=esteira_dias,
        num_dias_mes=num_dias_mes,
        nome_mes_sel=nome_mes_sel,
        total_irregulares_mes=total_irregulares_mes
    )

@app.route("/portaria")
def portaria_view():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM portaria_movimentacao ORDER BY data_hora DESC LIMIT 50")
    movimentacoes = cursor.fetchall()
    
    cursor.execute("SELECT id, nome FROM usuarios WHERE departamento = 'Portaria'")
    porteiros = cursor.fetchall()
    
    conn.close()
    return render_template("portaria.html", movimentacoes=movimentacoes, porteiros=porteiros)

@app.route("/financeiro")
def financeiro_view():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM financeiro_integracao ORDER BY data_vencimento ASC")
    lancamentos = cursor.fetchall()
    
    cursor.execute("""
    SELECT origem_area, tipo, SUM(valor) as total 
    FROM financeiro_integracao 
    GROUP BY origem_area, tipo
    """)
    totais_por_origem = cursor.fetchall()
    
    conn.close()
    return render_template("financeiro.html", lancamentos=lancamentos, totais=totais_por_origem)

@app.route("/emails")
def emails_view():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM log_emails ORDER BY data_envio DESC LIMIT 50")
    emails = cursor.fetchall()
    conn.close()
    return render_template("emails.html", emails=emails)

@app.route("/colaboradores")
def colaboradores_view():
    conn = get_db()
    cursor = conn.cursor()
    dept = request.args.get("dept", "Todos")
    
    if dept != "Todos":
        cursor.execute("SELECT * FROM usuarios WHERE departamento = ? ORDER BY nome ASC", (dept,))
    else:
        cursor.execute("SELECT * FROM usuarios ORDER BY departamento ASC, nome ASC")
    colaboradores = cursor.fetchall()
    conn.close()
    return render_template("colaboradores.html", colaboradores=colaboradores, dept_sel=dept)

# ==================== ENDPOINTS DE API (AÇÕES) ====================

@app.route("/api/chamados/abrir", methods=["POST"])
def api_abrir_chamado():
    data = request.form
    conn = get_db()
    cursor = conn.cursor()
    
    # Gera protocolo único
    cursor.execute("SELECT COUNT(*) FROM chamados")
    total = cursor.fetchone()[0] + 1
    protocolo = f"OS-{datetime.now().year}-{total:04d}"
    
    titulo = data.get("titulo")
    dep_origem = data.get("departamento_origem")
    dep_destino = data.get("departamento_destino")
    solicitante_id = data.get("solicitante_id")
    prioridade = data.get("prioridade", "Média")
    categoria = data.get("categoria", "Geral")
    prefixo = data.get("prefixo_veiculo")
    linha = data.get("linha")
    descricao = data.get("descricao")
    
    # Busca dados do solicitante
    cursor.execute("SELECT nome, email FROM usuarios WHERE id = ?", (solicitante_id,))
    solic = cursor.fetchone()
    solic_nome = solic["nome"] if solic else "Colaborador Operacional"
    solic_email = solic["email"] if solic else "operacao@viacaourbana.com.br"
    
    # Atribui automaticamente a um responsável do departamento de destino
    cursor.execute("SELECT id, nome, email FROM usuarios WHERE departamento = ? LIMIT 1", (dep_destino,))
    resp = cursor.fetchone()
    resp_id = resp["id"] if resp else None
    resp_nome = resp["nome"] if resp else "Equipe de Atendimento"
    resp_email = resp["email"] if resp else "suporte@viacaourbana.com.br"
    
    now = datetime.now()
    prev = now + timedelta(hours=24)
    
    cursor.execute("""
    INSERT INTO chamados (
        protocolo, titulo, departamento_origem, departamento_destino,
        solicitante_id, solicitante_nome, responsavel_id, responsavel_nome,
        prioridade, categoria, prefixo_veiculo, linha, descricao,
        status, data_abertura, data_previsao, sla_horas, email_abertura_enviado
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Aberto', ?, ?, 24, 1)
    """, (
        protocolo, titulo, dep_origem, dep_destino,
        solicitante_id, solic_nome, resp_id, resp_nome,
        prioridade, categoria, prefixo, linha, descricao,
        now, prev
    ))
    chamado_id = cursor.lastrowid
    
    # Histórico
    cursor.execute("""
    INSERT INTO chamados_historico (chamado_id, usuario_nome, acao, observacao, data_hora)
    VALUES (?, ?, 'Abertura de Chamado', 'Chamado aberto no sistema. E-mail de notificação gerado para a equipe de destino.', ?)
    """, (chamado_id, solic_nome, now))
    
    conn.commit()
    conn.close()
    
    # Dispara e-mail de notificação de ABERTURA
    corpo_email = f"""
    <div style="font-family: Arial, sans-serif; background-color: #0d1424; color: #fff; padding: 20px; border-radius: 8px;">
      <h2 style="color: #38bdf8; margin-top: 0;">🚀 Nova Ordem de Serviço Aberta: {protocolo}</h2>
      <p>Olá <strong>{resp_nome}</strong>,</p>
      <p>Uma nova solicitação foi atribuída ao seu departamento (<strong>{dep_destino}</strong>).</p>
      <div style="background: rgba(255,255,255,0.08); padding: 15px; border-radius: 6px; border-left: 4px solid #38bdf8;">
        <p><strong>Título:</strong> {titulo}</p>
        <p><strong>Solicitante:</strong> {solic_nome} ({dep_origem})</p>
        <p><strong>Prioridade:</strong> <span style="color: {'#ef4444' if prioridade == 'Crítica' else '#f59e0b'}; font-weight: bold;">{prioridade}</span></p>
        <p><strong>Prefixo / Linha:</strong> {prefixo or 'N/A'} - {linha or 'N/A'}</p>
        <p><strong>Descrição:</strong> {descricao}</p>
      </div>
      <p style="font-size: 12px; color: #94a3b8; margin-top: 20px;">CCO Transporte Urbano | Sistema de Service Desk Integrado</p>
    </div>
    """
    send_simulated_email("Abertura_OS", protocolo, resp_nome, resp_email, f"[NOVA OS] {protocolo} - {titulo} ({prioridade})", corpo_email)
    
    return redirect(url_for("chamados_view"))

@app.route("/api/chamados/fechar", methods=["POST"])
def api_fechar_chamado():
    data = request.form
    chamado_id = data.get("chamado_id")
    resolucao = data.get("resolucao", "Serviço realizado conforme padrão operacional.")
    custo = float(data.get("custo_estimado", 0.0) or 0.0)
    usuario_nome = data.get("usuario_nome", "Responsável Técnico")
    
    conn = get_db()
    cursor = conn.cursor()
    
    now = datetime.now()
    cursor.execute("""
    UPDATE chamados 
    SET status = 'Concluído', resolucao = ?, data_fechamento = ?, custo_estimado = ?, email_fechamento_enviado = 1
    WHERE id = ?
    """, (resolucao, now, custo, chamado_id))
    
    cursor.execute("SELECT * FROM chamados WHERE id = ?", (chamado_id,))
    chamado = cursor.fetchone()
    
    # Histórico
    cursor.execute("""
    INSERT INTO chamados_historico (chamado_id, usuario_nome, acao, observacao, data_hora)
    VALUES (?, ?, 'Conclusão & Fechamento', ?, ?)
    """, (chamado_id, usuario_nome, f"OS finalizada. Parecer: {resolucao}", now))
    
    # Se gerou custo de peças, cria pendência automática no Contas a Pagar!
    if custo > 0:
        cursor.execute("""
        INSERT INTO financeiro_integracao (
            origem_area, tipo, descricao, referencia_documento, valor,
            data_lancamento, data_vencimento, status, responsavel_aprovacao
        ) VALUES ('Manutenção_Peças', 'Pagar', ?, ?, ?, ?, ?, 'Pendente', ?)
        """, (
            f"Peças utilizadas na {chamado['protocolo']} ({chamado['prefixo_veiculo'] or 'Geral'})",
            chamado['protocolo'], custo, now.date(), (now + timedelta(days=15)).date(), usuario_nome
        ))
        
    conn.commit()
    conn.close()
    
    # Dispara e-mail de notificação de FECHAMENTO para o solicitante
    if chamado:
        corpo_email = f"""
        <div style="font-family: Arial, sans-serif; background-color: #0d1424; color: #fff; padding: 20px; border-radius: 8px;">
          <h2 style="color: #10b981; margin-top: 0;">✅ Chamado Finalizado: {chamado['protocolo']}</h2>
          <p>Olá <strong>{chamado['solicitante_nome']}</strong>,</p>
          <p>Informamos que sua Ordem de Serviço foi <strong>CONCLUÍDA</strong> com sucesso.</p>
          <div style="background: rgba(255,255,255,0.08); padding: 15px; border-radius: 6px; border-left: 4px solid #10b981;">
            <p><strong>Título:</strong> {chamado['titulo']}</p>
            <p><strong>Veículo / Linha:</strong> {chamado['prefixo_veiculo'] or 'N/A'}</p>
            <p><strong>Resolução Técnica:</strong> {resolucao}</p>
            <p><strong>Data de Conclusão:</strong> {now.strftime('%d/%m/%Y %H:%M')}</p>
            {f"<p><strong>Custo Apropriado:</strong> R$ {custo:,.2f}</p>" if custo > 0 else ""}
          </div>
          <p style="font-size: 12px; color: #94a3b8; margin-top: 20px;">CCO Transporte Urbano | Sistema de Service Desk Integrado</p>
        </div>
        """
        send_simulated_email("Fechamento_OS", chamado['protocolo'], chamado['solicitante_nome'], "solicitante@viacaourbana.com.br", f"[FECHADO] {chamado['protocolo']} - {chamado['titulo']}", corpo_email)
        
    return redirect(url_for("chamados_view"))

@app.route("/api/ponto/ajustar", methods=["POST"])
def api_ajustar_ponto():
    data = request.form
    ponto_id = data.get("ponto_id")
    e1 = (data.get("entrada_1") or "").strip() or "--:--"
    s1 = (data.get("saida_1") or "").strip() or "--:--"
    e2 = (data.get("entrada_2") or "").strip() or "--:--"
    s2 = (data.get("saida_2") or "").strip() or "--:--"
    status_reg = data.get("status_registro", "Normal")
    
    try:
        total_horas = float(data.get("total_horas", 8.0) or 8.0)
    except:
        total_horas = 8.0
        
    try:
        he = float(data.get("horas_extras", 0.0) or 0.0)
    except:
        he = 0.0
        
    try:
        faltas = float(data.get("horas_falta", 0.0) or 0.0)
    except:
        faltas = 0.0
        
    obs = data.get("observacao_rh", "")
    custo_he = round(he * 38.50, 2)
    desconto_falta = round(faltas * 25.00, 2)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE ponto_eletronico
    SET entrada_1 = ?, saida_1 = ?, entrada_2 = ?, saida_2 = ?,
        total_horas_trabalhadas = ?, horas_extras = ?, horas_falta = ?,
        status_registro = ?, custo_hora_extra = ?, desconto_falta = ?,
        observacao_rh = ?
    WHERE id = ?
    """, (e1, s1, e2, s2, total_horas, he, faltas, status_reg, custo_he, desconto_falta, obs, ponto_id))
    
    conn.commit()
    conn.close()
    
    # Redireciona de volta para a mesma URL com os filtros ativos
    redirect_url = request.referrer or url_for("ponto_view")
    return redirect(redirect_url)

@app.route("/api/portaria/registrar", methods=["POST"])
def api_portaria_registrar():
    data = request.form
    prefixo = data.get("prefixo_veiculo")
    linha = data.get("linha")
    motorista = data.get("motorista_nome", "Motorista de Escala")
    porteiro = data.get("porteiro_nome", "Porteiro Plantão")
    tipo = data.get("tipo_movimento", "Saída Garagem")
    km = int(data.get("km_registro", 145000) or 145000)
    combustivel = data.get("nivel_combustivel", "100%")
    avaria = data.get("avaria_apontada", "Sem avarias visuais")
    abrir_os = data.get("abrir_os_automatica") == "on"
    
    conn = get_db()
    cursor = conn.cursor()
    
    now = datetime.now()
    os_id = None
    
    if abrir_os and avaria and avaria != "Sem avarias visuais":
        # Gera OS automática para a Manutenção
        cursor.execute("SELECT COUNT(*) FROM chamados")
        total = cursor.fetchone()[0] + 1
        protocolo = f"OS-{now.year}-{total:04d}"
        
        cursor.execute("""
        INSERT INTO chamados (
            protocolo, titulo, departamento_origem, departamento_destino,
            solicitante_nome, prioridade, categoria, prefixo_veiculo, linha, descricao,
            status, data_abertura, data_previsao, sla_horas, email_abertura_enviado
        ) VALUES (?, ?, 'Portaria', 'Manutenção', ?, 'Alta', 'Mecânica', ?, ?, ?, 'Aberto', ?, ?, 24, 1)
        """, (
            protocolo, f"Avaria Identificada na Portaria ({tipo})",
            porteiro, prefixo, linha, f"Avaria registrada na portaria: {avaria}. Veículo {prefixo} encaminhado para avaliação técnica na oficina.",
            now, now + timedelta(hours=24)
        ))
        os_id = cursor.lastrowid
        
        # Log de e-mail automático
        send_simulated_email(
            "Abertura_OS", protocolo, "Carlos Roberto (Oficina)", "oficina@viacaourbana.com.br",
            f"[ALERTA PORTARIA] {protocolo} - Avaria Veículo {prefixo}",
            f"<p>Atenção Manutenção: O veículo {prefixo} deu entrada na portaria com avaria: <strong>{avaria}</strong>. OS {protocolo} gerada automaticamente.</p>"
        )

    cursor.execute("""
    INSERT INTO portaria_movimentacao (
        prefixo_veiculo, linha, motorista_nome, motorista_matricula,
        porteiro_nome, tipo_movimento, data_hora, km_registro,
        nivel_combustivel, avaria_apontada, status_liberacao, os_aberta_id
    ) VALUES (?, ?, ?, 'MOT-2044', ?, ?, ?, ?, ?, ?, 'Liberado', ?)
    """, (prefixo, linha, motorista, porteiro, tipo, now, km, combustivel, avaria, os_id))
    
    conn.commit()
    conn.close()
    return redirect(url_for("portaria_view"))

if __name__ == "__main__":
    print("🚀 Iniciando CRM & Service Desk Transporte Urbano na porta 5700...")
    app.run(host="0.0.0.0", port=5700, debug=False, threaded=True)
