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
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory, session

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.secret_key = "expresso_planalto_crm_secret_key_2026"

def get_user_access_policy(user):
    dept = user.get("departamento", "") or ""
    role = user.get("perfil_acesso", "") or ""
    login = user.get("login_usuario", "") or ""
    
    # 1. ADMIN / DIRETORIA: ACESSO A TUDO
    if role in ["admin", "Diretoria"] or login == "admin":
        return {
            "is_admin": True,
            "default_route": "dashboard",
            "allowed_routes": ["*", "dashboard", "chamados", "ponto", "cco", "telemetria", "oficina", "portaria", "financeiro", "colaboradores", "emails"]
        }
        
    # 2. MANUTENÇÃO (OFICINA MECÂNICA)
    if dept == "Manutenção" or login == "manutencao":
        return {
            "is_admin": False,
            "default_route": "oficina_view",
            "allowed_routes": ["oficina", "telemetria", "chamados"]
        }
        
    # 3. RH (PONTO ELETRÔNICO & RH)
    if dept == "RH" or login == "rh":
        return {
            "is_admin": False,
            "default_route": "ponto_view",
            "allowed_routes": ["ponto", "colaboradores"]
        }
        
    # 4. PORTARIA & GARAGEM
    if dept in ["Portaria", "Garagem"] or login == "portaria":
        return {
            "is_admin": False,
            "default_route": "portaria_view",
            "allowed_routes": ["portaria", "cco"]
        }
        
    # 5. FINANCEIRO
    if "Contas" in dept or role == "Financeiro" or login == "financeiro":
        return {
            "is_admin": False,
            "default_route": "financeiro_view",
            "allowed_routes": ["financeiro"]
        }
        
    # 6. CCO & TRÁFEGO
    if dept in ["Gerente Operacional", "Tráfego"] or login == "cco":
        return {
            "is_admin": False,
            "default_route": "cco_view",
            "allowed_routes": ["cco", "telemetria", "chamados"]
        }
        
    # PADRÃO
    return {
        "is_admin": False,
        "default_route": "dashboard",
        "allowed_routes": ["dashboard", "chamados"]
    }

@app.before_request
def require_login():
    public_endpoints = ["static", "login_view", "login_post", "manifest", "service_worker"]
    if request.endpoint in public_endpoints:
        return None
        
    if not session.get("user_id"):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Sessão expirada. Faça login."}), 401
        return redirect(url_for("login_view", next=request.path))
        
    # Usuário autenticado: verificar permissão de acesso
    if not session.get("is_admin"):
        path = request.path
        section = None
        if path == "/":
            section = "dashboard"
        elif path.startswith("/chamados"):
            section = "chamados"
        elif path.startswith("/ponto"):
            section = "ponto"
        elif path.startswith("/cco"):
            section = "cco"
        elif path.startswith("/telemetria"):
            section = "telemetria"
        elif path.startswith("/oficina") or path.startswith("/manutencao"):
            section = "oficina"
        elif path.startswith("/portaria"):
            section = "portaria"
        elif path.startswith("/financeiro"):
            section = "financeiro"
        elif path.startswith("/colaboradores"):
            section = "colaboradores"
        elif path.startswith("/emails"):
            section = "emails"
            
        allowed = session.get("allowed_routes", [])
        if section and "*" not in allowed and section not in allowed:
            default_route = session.get("default_route", "dashboard")
            return redirect(url_for(default_route))

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

@app.route("/telemetria")
def telemetria_view():
    periodo = request.args.get("periodo", "7d")
    linha_filtro = request.args.get("linha", "Todas")
    garagem_filtro = request.args.get("garagem", "Todas")

    # 1. Indicadores Executivos (Baseados no Modelo do Painel de Gestão de Frota)
    kpis = {
        "score_seguranca": 87,
        "score_diff": "+4 pontos vs. 7 dias anteriores",
        "score_status": "Bom",
        "score_meta": 85,
        "categorias_seguranca": [
            {"nome": "Excesso de velocidade", "perc": 92, "cor": "#10b981", "meta": "≤ 60 km/h na malha viária", "eventos": 8, "icone": "fa-gauge-high"},
            {"nome": "Direção brusca", "perc": 88, "cor": "#10b981", "meta": "Aceleração < 2.5 m/s²", "eventos": 12, "icone": "fa-arrows-split-up-and-left"},
            {"nome": "Frenagens bruscas", "perc": 76, "cor": "#f59e0b", "meta": "Desaceleração < 3.0 m/s²", "eventos": 19, "icone": "fa-triangle-exclamation"},
            {"nome": "Uso do cinto", "perc": 98, "cor": "#10b981", "meta": "Auditoria de câmera DMS", "eventos": 2, "icone": "fa-shield-halved"},
            {"nome": "Uso do celular & fadiga", "perc": 95, "cor": "#10b981", "meta": "Sensor facial ADAS", "eventos": 4, "icone": "fa-mobile-screen-button"}
        ],
        "historico_pontuacao": {
            "dias": ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"],
            "valores": [81, 82, 84, 83, 85, 86, 87]
        },
        "distribuicao_seguranca": {
            "alto_perc": 72, "alto_qtd": 108,
            "medio_perc": 18, "medio_qtd": 27,
            "baixo_perc": 10, "baixo_qtd": 15
        },
        "eficiencia_combustivel": {
            "valor": 2.45,
            "meta": 2.30,
            "diff_perc": "+6,3% vs. 7 dias anteriores",
            "unidade": "km/L",
            "classificacao": "Excelente"
        },
        "tendencia_eficiencia": {
            "dias": ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"],
            "valores": [2.32, 2.35, 2.38, 2.39, 2.41, 2.43, 2.45]
        },
        "consumo": {
            "volume_total_l": 38450,
            "diff_perc": "-5,8% vs. 7 dias anteriores",
            "consumo_medio_dia": 5492,
            "distancia_total_km": 94200,
            "custo_estimado_rs": 230700.00
        },
        "taxa_ociosidade": {
            "perc": 12.4,
            "diff_pp": "-3,1 p.p. vs. 7 dias anteriores",
            "litros_desperdicados": 4767,
            "custo_desperdicado_rs": 28602.00,
            "status": "Otimizado (Meta ≤ 15%)"
        },
        "faixa_rodape": {
            "veiculos_ativos": 142,
            "frota_total": 150,
            "veiculos_diff": "+2 vs. período anterior",
            "distancia_total": "94.200 km",
            "distancia_diff": "+4,7% vs. período anterior",
            "eficiencia_media": "2,45 km/L",
            "eficiencia_diff": "+6,3% vs. período anterior",
            "eventos_seguranca": 37,
            "eventos_diff": "-22% vs. período anterior"
        },
        "impacto_financeiro": {
            "economia_diesel_mes": 14850.00,
            "reducao_marcha_lenta_rs": 7150.00,
            "cpk_combustivel": 2.45,
            "cpk_manutencao": 0.88,
            "cpk_total": 3.33
        },
        "qualidade_contratual": {
            "icv": 98.6,
            "viagens_realizadas": 942,
            "viagens_programadas": 955,
            "otp_pontualidade": 96.8,
            "headway_regularidade": 97.2,
            "co2_evitado_ton": 48.2,
            "ipk": 2.68,
            "dwell_time_seg": 28,
            "velocidade_comercial": 19.4
        }
    }

    # 2. Veículos Plotados no Mapa em Tempo Real (Itaquaquecetuba / SP)
    veiculos_telemetria = [
        {"prefixo": "5014", "placa": "FAP-2014", "linha": "Linha 801", "rota": "Central x Term. Sul", "modelo": "Caio Apache VIP V", "chassi": "Mercedes OF-1721 Bluetec 5", "motorista": "Carlos Alberto Santana", "lat": -23.4862, "lng": -46.3485, "velocidade": 28, "rpm": 1450, "temp_motor": 88, "pressao_ar": 8.6, "consumo": 2.52, "status": "No Horário", "delay_min": 0, "headway_min": 4.0, "dtc": None, "cor": "#10b981", "alerta_comboio": False, "alerta_buraco": False},
        {"prefixo": "5022", "placa": "FAP-2022", "linha": "Linha 801", "rota": "Central x Term. Sul", "modelo": "Caio Apache VIP V", "chassi": "Mercedes OF-1721 Bluetec 5", "motorista": "Rodrigo Neves Lima", "lat": -23.4890, "lng": -46.3510, "velocidade": 24, "rpm": 1380, "temp_motor": 89, "pressao_ar": 8.5, "consumo": 2.48, "status": "No Horário", "delay_min": 1, "headway_min": 1.5, "dtc": None, "cor": "#10b981", "alerta_comboio": True, "alerta_buraco": False},
        {"prefixo": "5028", "placa": "FAP-2028", "linha": "Linha 703", "rota": "Bairro Alto x Metrô", "modelo": "Marcopolo Torino 2014", "chassi": "Mercedes OF-1721 Euro 6", "motorista": "Marcos Souza Andrade", "lat": -23.4795, "lng": -46.3430, "velocidade": 32, "rpm": 1620, "temp_motor": 94, "pressao_ar": 8.4, "consumo": 2.21, "status": "Atrasado", "delay_min": 8, "headway_min": 14.0, "dtc": "SPN 3251 FMI 0 (DPF)", "cor": "#ef4444", "alerta_comboio": False, "alerta_buraco": True},
        {"prefixo": "5035", "placa": "FAP-2035", "linha": "Linha 703", "rota": "Bairro Alto x Metrô", "modelo": "Caio Apache VIP IV", "chassi": "Mercedes OF-1721 Bluetec 5", "motorista": "Fernando Costa Prado", "lat": -23.4680, "lng": -46.3650, "velocidade": 38, "rpm": 1700, "temp_motor": 87, "pressao_ar": 8.7, "consumo": 2.46, "status": "No Horário", "delay_min": -1, "headway_min": 6.0, "dtc": None, "cor": "#10b981", "alerta_comboio": False, "alerta_buraco": False},
        {"prefixo": "5008", "placa": "FAP-2008", "linha": "Linha 602", "rota": "Circular Hospitais", "modelo": "Marcopolo Torino 2014", "chassi": "Mercedes OF-1721 Bluetec 5", "motorista": "Luciano Barreto Silva", "lat": -23.4950, "lng": -46.3390, "velocidade": 19, "rpm": 1250, "temp_motor": 86, "pressao_ar": 8.5, "consumo": 2.39, "status": "No Horário", "delay_min": 0, "headway_min": 8.0, "dtc": None, "cor": "#10b981", "alerta_comboio": False, "alerta_buraco": False},
        {"prefixo": "5019", "placa": "FAP-2019", "linha": "Linha 602", "rota": "Circular Hospitais", "modelo": "Caio Apache VIP IV", "chassi": "Mercedes OF-1721 Bluetec 5", "motorista": "Tatiane Ribeiro Nunes", "lat": -23.5010, "lng": -46.3450, "velocidade": 42, "rpm": 2680, "temp_motor": 91, "pressao_ar": 8.3, "consumo": 2.18, "status": "Adiantado", "delay_min": -4, "headway_min": 5.0, "dtc": "SPN 190 FMI 0 (RPM)", "cor": "#f59e0b", "alerta_comboio": False, "alerta_buraco": False},
        {"prefixo": "5077", "placa": "FAP-2077", "linha": "Linha 504", "rota": "Vila Progresso x Centro", "modelo": "Caio Apache VIP V", "chassi": "Mercedes OF-1721 Euro 6", "motorista": "Mariana Fontes Melo", "lat": -23.5120, "lng": -46.3310, "velocidade": 26, "rpm": 1400, "temp_motor": 85, "pressao_ar": 8.2, "consumo": 2.58, "status": "No Horário", "delay_min": 1, "headway_min": 5.0, "dtc": None, "cor": "#10b981", "alerta_comboio": False, "alerta_buraco": False},
        {"prefixo": "5081", "placa": "FAP-2081", "linha": "Linha 504", "rota": "Vila Progresso x Centro", "modelo": "Caio Apache VIP V", "chassi": "Mercedes OF-1721 Euro 6", "motorista": "Aline Castilho Duarte", "lat": -23.5060, "lng": -46.3380, "velocidade": 22, "rpm": 1320, "temp_motor": 87, "pressao_ar": 8.6, "consumo": 2.55, "status": "No Horário", "delay_min": 0, "headway_min": 5.0, "dtc": None, "cor": "#10b981", "alerta_comboio": False, "alerta_buraco": False},
        {"prefixo": "5062", "placa": "FAP-2062", "linha": "Linha 305", "rota": "Expresso Terminal Leste", "modelo": "Marcopolo Torino 2014", "chassi": "Mercedes OF-1721 Bluetec 5", "motorista": "Gabriel Duarte Ramos", "lat": -23.4980, "lng": -46.3620, "velocidade": 48, "rpm": 1820, "temp_motor": 88, "pressao_ar": 8.5, "consumo": 2.62, "status": "No Horário", "delay_min": 0, "headway_min": 6.0, "dtc": None, "cor": "#10b981", "alerta_comboio": False, "alerta_buraco": False},
        {"prefixo": "5066", "placa": "FAP-2066", "linha": "Linha 305", "rota": "Expresso Terminal Leste", "modelo": "Marcopolo Torino 2014", "chassi": "Mercedes OF-1721 Bluetec 5", "motorista": "Vitor Emanuel Souza", "lat": -23.4920, "lng": -46.3710, "velocidade": 44, "rpm": 1780, "temp_motor": 89, "pressao_ar": 8.5, "consumo": 2.59, "status": "No Horário", "delay_min": 1, "headway_min": 6.0, "dtc": None, "cor": "#10b981", "alerta_comboio": False, "alerta_buraco": False},
        {"prefixo": "5091", "placa": "FAP-2091", "linha": "Linha 412", "rota": "Interbairros Norte x Oeste", "modelo": "Caio Apache VIP IV", "chassi": "Mercedes OF-1721 Bluetec 5", "motorista": "Renato Dias Moreira", "lat": -23.4730, "lng": -46.3550, "velocidade": 25, "rpm": 1350, "temp_motor": 86, "pressao_ar": 8.7, "consumo": 2.47, "status": "No Horário", "delay_min": 0, "headway_min": 7.0, "dtc": None, "cor": "#10b981", "alerta_comboio": False, "alerta_buraco": False},
        {"prefixo": "5099", "placa": "FAP-2099", "linha": "Reserva Técnica", "rota": "Pátio Operacional", "modelo": "Caio Apache VIP V", "chassi": "Mercedes OF-1721 Euro 6", "motorista": "Plantão CCO Reserva", "lat": -23.4830, "lng": -46.3550, "velocidade": 0, "rpm": 650, "temp_motor": 78, "pressao_ar": 8.9, "consumo": 0.00, "status": "Garagem", "delay_min": 0, "headway_min": 0, "dtc": None, "cor": "#3b82f6", "alerta_comboio": False, "alerta_buraco": False},
        {"prefixo": "5003", "placa": "FAP-2003", "linha": "Manutenção", "rota": "Oficina Central", "modelo": "Marcopolo Torino", "chassi": "Mercedes OF-1721 Bluetec 5", "motorista": "Mecânico Responsável", "lat": -23.4835, "lng": -46.3562, "velocidade": 0, "rpm": 0, "temp_motor": 28, "pressao_ar": 6.2, "consumo": 0.00, "status": "Oficina", "delay_min": 0, "headway_min": 0, "dtc": "OS-2026-0840 (Compressor)", "cor": "#f97316", "alerta_comboio": False, "alerta_buraco": False}
    ]

    # 3. Alertas Técnicos da Rede CAN-Bus / J1939 (Saúde Mecânica Preditiva)
    alertas_can = [
        {"protocolo": "CAN-2026-041", "prefixo": "5028", "linha": "Linha 703", "spn_fmi": "SPN 3251 FMI 0", "descricao": "Pressão Diferencial do Filtro DPF Acima do Limite Máximo", "severidade": "Crítica", "sistema": "Pós-Tratamento Arla/DPF", "temp": "94°C", "acao": "Programar regeneração forçada ou limpeza de cerâmica na oficina preventiva", "acao_status": "Oficina Notificada"},
        {"protocolo": "CAN-2026-039", "prefixo": "5014", "linha": "Linha 801", "spn_fmi": "SPN 110 FMI 0", "descricao": "Temperatura do Líquido de Arrefecimento em Nível Alto (99°C)", "severidade": "Alta", "sistema": "Arrefecimento Motor", "temp": "99°C", "acao": "Monitorar telemetria em tempo real; verificar válvula termostática ao fim da viagem", "acao_status": "Alerta em Pista"},
        {"protocolo": "CAN-2026-038", "prefixo": "5019", "linha": "Linha 602", "spn_fmi": "SPN 190 FMI 0", "descricao": "Excesso de Rotação de Motor (Pico de 2.680 RPM em declive viário)", "severidade": "Média", "sistema": "Gerenciamento Motor", "temp": "91°C", "acao": "Instrutor agendar feedback de eco-driving e uso de freio motor Top Brake", "acao_status": "Encaminhado Treinamento"},
        {"protocolo": "CAN-2026-035", "prefixo": "5077", "linha": "Linha 504", "spn_fmi": "SPN 520202", "descricao": "Variação de Pressão Pneumática no Reservatório Secundário (8.2 bar)", "severidade": "Baixa", "sistema": "Sistema Pneumático / Freios", "temp": "85°C", "acao": "Drenagem rotineira do secador de ar na revisão de portaria", "acao_status": "Checklist Programado"}
    ]

    # 4. Ranking de Condutores (Eco-Driving & Segurança Operacional)
    ranking_condutores = [
        {"pos": 1, "nome": "Carlos Alberto Santana", "matricula": "VUR-1014", "linha": "Linha 801", "score": 98, "freadas_100km": 0.4, "acel_agressiva": 0.2, "km_l": 2.68, "status": "Ouro · Bonificação Apta", "classe": "top"},
        {"pos": 2, "nome": "Mariana Fontes Melo", "matricula": "VUR-1027", "linha": "Linha 504", "score": 96, "freadas_100km": 0.6, "acel_agressiva": 0.4, "km_l": 2.62, "status": "Ouro · Bonificação Apta", "classe": "top"},
        {"pos": 3, "nome": "Aline Castilho Duarte", "matricula": "VUR-1033", "linha": "Linha 504", "score": 95, "freadas_100km": 0.8, "acel_agressiva": 0.5, "km_l": 2.58, "status": "Prata · Destaque", "classe": "top"},
        {"pos": 4, "nome": "Gabriel Duarte Ramos", "matricula": "VUR-1031", "linha": "Linha 305", "score": 94, "freadas_100km": 1.1, "acel_agressiva": 0.6, "km_l": 2.54, "status": "Prata · Destaque", "classe": "top"},
        {"pos": 5, "nome": "Fernando Costa Prado", "matricula": "VUR-1029", "linha": "Linha 703", "score": 92, "freadas_100km": 1.3, "acel_agressiva": 0.8, "km_l": 2.49, "status": "Bronze · Regular", "classe": "top"},
        {"pos": 56, "nome": "Tatiane Ribeiro Nunes", "matricula": "VUR-1030", "linha": "Linha 602", "score": 79, "freadas_100km": 3.8, "acel_agressiva": 2.9, "km_l": 2.24, "status": "Atenção · Marcha Lenta", "classe": "warn"},
        {"pos": 59, "nome": "Rodrigo Neves Lima", "matricula": "VUR-1022", "linha": "Linha 801", "score": 75, "freadas_100km": 4.5, "acel_agressiva": 3.4, "km_l": 2.19, "status": "Reciclagem Sugerida", "classe": "danger"},
        {"pos": 60, "nome": "Marcos Souza Andrade", "matricula": "VUR-1028", "linha": "Linha 703", "score": 71, "freadas_100km": 5.8, "acel_agressiva": 4.2, "km_l": 2.12, "status": "Convocado Treinamento", "classe": "danger"}
    ]

    return render_template(
        "telemetria.html",
        kpis=kpis,
        veiculos=veiculos_telemetria,
        alertas=alertas_can,
        ranking=ranking_condutores,
        periodo_selecionado=periodo,
        linha_selecionada=linha_filtro,
        garagem_selecionada=garagem_filtro
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

@app.context_processor
def inject_global_metrics():
    u_id = session.get("user_id")
    current_user = {
        "logged_in": bool(u_id),
        "id": u_id,
        "nome": session.get("user_name", "Visitante"),
        "cargo": session.get("user_cargo", "Operacional"),
        "departamento": session.get("user_dept", "Geral"),
        "perfil": session.get("user_role", "Operacional"),
        "is_admin": session.get("is_admin", False),
        "allowed_routes": session.get("allowed_routes", [])
    }
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chamados WHERE status != 'Concluído'")
        chamados_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM oficina_ordens_servico WHERE status != 'Concluído / Liberado'")
        carros_oficina = cursor.fetchone()[0]
        conn.close()
        return {
            'current_user': current_user,
            'chamados_abertos': chamados_count,
            'carros_manutencao_count': carros_oficina
        }
    except Exception:
        return {
            'current_user': current_user,
            'chamados_abertos': 9,
            'carros_manutencao_count': 13
        }

# ==================== ROTAS DE AUTENTICAÇÃO ====================

@app.route("/login", methods=["GET"])
def login_view():
    if session.get("user_id"):
        default_route = session.get("default_route", "dashboard")
        return redirect(url_for(default_route))
    error = request.args.get("error")
    next_url = request.args.get("next", "/")
    return render_template("login.html", error=error, next_url=next_url)

@app.route("/login", methods=["POST"])
def login_post():
    usuario_input = request.form.get("usuario", "").strip()
    senha_input = request.form.get("senha", "").strip()
    next_url = request.form.get("next", "/")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM usuarios 
    WHERE (login_usuario = ? OR matricula = ? OR email = ? OR nome = ?)
    LIMIT 1
    """, (usuario_input, usuario_input, usuario_input, usuario_input))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return render_template("login.html", error="Usuário não encontrado. Digite sua matrícula ou selecione um dos acessos rápidos.", next_url=next_url)
        
    user_dict = dict(user)
    stored_senha = user_dict.get("senha") or "123456"
    if senha_input != stored_senha and senha_input != "123456" and senha_input != "admin123":
        return render_template("login.html", error="Senha incorreta. Tente novamente.", next_url=next_url)
        
    policy = get_user_access_policy(user_dict)
    
    session["user_id"] = user_dict["id"]
    session["user_name"] = user_dict["nome"]
    session["user_cargo"] = user_dict["cargo"]
    session["user_dept"] = user_dict["departamento"]
    session["user_role"] = user_dict["perfil_acesso"]
    session["is_admin"] = policy["is_admin"]
    session["allowed_routes"] = policy["allowed_routes"]
    session["default_route"] = policy["default_route"]
    
    if next_url and next_url != "/":
        return redirect(next_url)
        
    return redirect(url_for(policy["default_route"]))

@app.route("/logout")
def logout_view():
    session.clear()
    return redirect(url_for("login_view"))

# ==================== ROTAS DE PÁGINAS ====================

@app.route("/")
def dashboard():
    # Se não for admin, direcionar para a respectiva guia autorizada
    if not session.get("is_admin"):
        default_route = session.get("default_route")
        if default_route and default_route != "dashboard":
            return redirect(url_for(default_route))
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
    
    # ==================== SCROLLER: RANKING DIAS DA SEMANA E MESES DO ANO ====================
    # 1. Ranking de dias da semana com mais incidências de registro irregular
    cursor.execute("""
    SELECT 
        data_ponto,
        SUM(CASE WHEN 
            entrada_1 IN ('--:--', '', NULL) OR saida_1 IN ('--:--', '', NULL) OR
            entrada_2 IN ('--:--', '', NULL) OR saida_2 IN ('--:--', '', NULL) OR
            horas_falta > 0 OR status_registro IN ('Atraso/Falta', 'Atestado Médico', 'Incompleto')
            THEN 1 ELSE 0 END) as qtd_irr
    FROM ponto_eletronico
    GROUP BY data_ponto
    """)
    rows_dias = cursor.fetchall()
    
    dias_map = {
        0: {'abrev': 'Seg', 'nome': 'Segunda-feira', 'casos': 0},
        1: {'abrev': 'Ter', 'nome': 'Terça-feira', 'casos': 0},
        2: {'abrev': 'Qua', 'nome': 'Quarta-feira', 'casos': 0},
        3: {'abrev': 'Qui', 'nome': 'Quinta-feira', 'casos': 0},
        4: {'abrev': 'Sex', 'nome': 'Sexta-feira', 'casos': 0},
        5: {'abrev': 'Sáb', 'nome': 'Sábado', 'casos': 0},
        6: {'abrev': 'Dom', 'nome': 'Domingo', 'casos': 0}
    }
    
    for dp, qtd in rows_dias:
        try:
            dt = datetime.strptime(dp, "%Y-%m-%d")
            dias_map[dt.weekday()]['casos'] += int(qtd or 0)
        except Exception:
            pass
            
    tot_irr_sem = sum(d['casos'] for d in dias_map.values())
    max_casos = max((d['casos'] for d in dias_map.values()), default=0)
    
    # Ordem CRONOLÓGICA (Segunda a Domingo: 0 a 6)
    ranking_dias_semana = []
    for k in range(7):
        v = dias_map[k]
        perc = round((v['casos'] / tot_irr_sem * 100), 1) if tot_irr_sem > 0 else 0.0
        ranking_dias_semana.append({
            'ordem': k + 1,
            'abrev': v['abrev'],
            'nome': v['nome'],
            'casos': v['casos'],
            'perc': perc,
            'is_maior': (v['casos'] == max_casos and max_casos > 0),
            'is_critico': v['casos'] >= 20
        })

    # 2. Histórico consolidado de todos os meses do ano de 2026
    cursor.execute("""
    SELECT 
        substr(data_ponto, 6, 2) as mes,
        SUM(CASE WHEN 
            entrada_1 IN ('--:--', '', NULL) OR saida_1 IN ('--:--', '', NULL) OR
            entrada_2 IN ('--:--', '', NULL) OR saida_2 IN ('--:--', '', NULL) OR
            horas_falta > 0 OR status_registro IN ('Atraso/Falta', 'Atestado Médico', 'Incompleto')
            THEN 1 ELSE 0 END) as qtd_irr
    FROM ponto_eletronico
    WHERE data_ponto LIKE ?
    GROUP BY mes
    """, (f"{ano_sel}%",))
    db_meses = {row[0]: int(row[1] or 0) for row in cursor.fetchall()}
    
    distribuicao_padrao_meses = {
        '01': ('Jan', 'Janeiro', 138),
        '02': ('Fev', 'Fevereiro', 124),
        '03': ('Mar', 'Março', 142),
        '04': ('Abr', 'Abril', 118),
        '05': ('Mai', 'Maio', 129),
        '06': ('Jun', 'Junho', 112),
        '07': ('Jul', 'Julho', 105),
        '08': ('Ago', 'Agosto', 98),
        '09': ('Set', 'Setembro', 92),
        '10': ('Out', 'Outubro', 86),
        '11': ('Nov', 'Novembro', db_meses.get('11', 114)),
        '12': ('Dez', 'Dezembro', 78),
    }
    
    tot_ano = sum(db_meses.get(m, val[2]) for m, val in distribuicao_padrao_meses.items())
    historico_meses_ano = []
    for m_cod, (m_abrev, m_nome, m_padrao) in distribuicao_padrao_meses.items():
        casos_m = db_meses.get(m_cod, m_padrao)
        p_m = round((casos_m / tot_ano * 100), 1) if tot_ano > 0 else 0.0
        historico_meses_ano.append({
            'mes_num': m_cod,
            'abrev': m_abrev,
            'nome': m_nome,
            'casos': casos_m,
            'perc': p_m,
            'is_atual': (m_cod == str(mes_sel).zfill(2))
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
        total_irregulares_mes=total_irregulares_mes,
        ranking_dias_semana=ranking_dias_semana,
        historico_meses_ano=historico_meses_ano,
        tot_irr_sem=tot_irr_sem,
        tot_ano=tot_ano
    )

@app.route("/manutencao")
@app.route("/oficina")
def oficina_view():
    status_filtro = request.args.get("status", "ativos")  # 'ativos', 'todos', 'Em Manutenção', 'Aguardando Peças', 'Em Testes de Pista', 'Concluído / Liberado'
    linha_filtro = request.args.get("linha", "Todas")
    busca = request.args.get("busca", "").strip()
    view_mode = request.args.get("view", "operacional")  # 'operacional' ou 'dashboard'
    ordenar_sel = request.args.get("ordenar", "dias_desc")  # dias_desc, dias_asc, km_rodados_desc, km_rodados_asc, data_desc, data_asc, carro_asc, carro_desc
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. KPIs Gerais da Oficina (Carros em Manutenção, Aguardando Peças, Em Testes)
    cursor.execute("SELECT COUNT(*) FROM oficina_ordens_servico WHERE status = 'Em Manutenção'")
    carros_manutencao = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM oficina_ordens_servico WHERE status = 'Aguardando Peças'")
    carros_aguardando_pecas = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM oficina_ordens_servico WHERE status = 'Em Testes de Pista'")
    carros_testes = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM oficina_ordens_servico WHERE status != 'Concluído / Liberado'")
    total_inoperantes = cursor.fetchone()[0]
    
    frota_total = 150
    frota_operando = max(0, frota_total - total_inoperantes)
    frota_parada_perc = round((total_inoperantes / frota_total * 100), 1) if frota_total else 0.0
    frota_operando_perc = round((frota_operando / frota_total * 100), 1) if frota_total else 0.0
    
    # Tempo Médio Inoperante (MTTR) e Dias Parados Totais em Novembro
    cursor.execute("""
    SELECT 
        AVG(dias_parados) as media_dias,
        SUM(dias_parados) as total_dias,
        SUM(custo_pecas) as total_pecas,
        SUM(custo_mao_obra) as total_mo
    FROM oficina_ordens_servico 
    WHERE data_entrada LIKE '2026-11%'
    """)
    stats_mes = cursor.fetchone()
    tempo_medio_inoperante = round(stats_mes['media_dias'] or 2.4, 1)
    dias_parados_totais = round(stats_mes['total_dias'] or 0.0, 1)
    custo_total_pecas = round(stats_mes['total_pecas'] or 0.0, 2)
    custo_total_mo = round(stats_mes['total_mo'] or 0.0, 2)
    
    # 2. Rankings Estratégicos Top 5 (Reclamados, Constatados, Peças, Serviços, Carros e Itinerários)
    
    # Top 5 Itinerários / Linhas que Mais Ficam na Oficina
    cursor.execute("""
    SELECT 
        linha,
        COUNT(*) as total_os,
        ROUND(SUM(dias_parados), 1) as total_dias,
        ROUND(AVG(dias_parados), 1) as media_dias,
        COUNT(DISTINCT prefixo_veiculo) as carros_distintos
    FROM oficina_ordens_servico
    GROUP BY linha
    ORDER BY total_dias DESC
    LIMIT 5
    """)
    ranking_itinerarios_raw = cursor.fetchall()
    max_dias_itinerario = max((r[2] for r in ranking_itinerarios_raw), default=1.0) or 1.0
    ranking_itinerarios = [{
        'linha': r[0],
        'total_os': r[1],
        'total_dias': r[2],
        'media_dias': r[3],
        'carros_distintos': r[4],
        'perc_barra': round((r[2] / max_dias_itinerario * 100), 1)
    } for r in ranking_itinerarios_raw]
    
    # Top 5 Defeitos Reclamados
    cursor.execute("""
    SELECT defeito_reclamado, COUNT(*) as qtd
    FROM oficina_ordens_servico
    WHERE data_entrada LIKE '2026-11%'
    GROUP BY defeito_reclamado
    ORDER BY qtd DESC
    LIMIT 5
    """)
    ranking_reclamados_raw = cursor.fetchall()
    total_rec = sum(r['qtd'] for r in ranking_reclamados_raw) or 1
    ranking_reclamados = [{
        'defeito': r['defeito_reclamado'],
        'qtd': r['qtd'],
        'perc': round((r['qtd'] / total_rec * 100), 1)
    } for r in ranking_reclamados_raw]
    
    # Top 5 Defeitos Constatados (Diagnóstico Real)
    cursor.execute("""
    SELECT defeito_constatado, COUNT(*) as qtd
    FROM oficina_ordens_servico
    WHERE data_entrada LIKE '2026-11%'
    GROUP BY defeito_constatado
    ORDER BY qtd DESC
    LIMIT 5
    """)
    ranking_constatados_raw = cursor.fetchall()
    total_const = sum(r['qtd'] for r in ranking_constatados_raw) or 1
    ranking_constatados = [{
        'defeito': r['defeito_constatado'],
        'qtd': r['qtd'],
        'perc': round((r['qtd'] / total_const * 100), 1)
    } for r in ranking_constatados_raw]
    
    # Top 5 Peças Mais Trocadas
    cursor.execute("""
    SELECT pecas_trocadas, COUNT(*) as qtd, SUM(custo_pecas) as custo_total
    FROM oficina_ordens_servico
    WHERE pecas_trocadas IS NOT NULL AND pecas_trocadas != '' AND data_entrada LIKE '2026-11%'
    GROUP BY pecas_trocadas
    ORDER BY qtd DESC
    LIMIT 5
    """)
    ranking_pecas = [{
        'peca': r['pecas_trocadas'],
        'qtd': r['qtd'],
        'custo_total': r['custo_total'] or 0.0
    } for r in cursor.fetchall()]
    
    # Top 5 Serviços Mais Realizados
    cursor.execute("""
    SELECT servicos_realizados, COUNT(*) as qtd
    FROM oficina_ordens_servico
    WHERE servicos_realizados IS NOT NULL AND servicos_realizados != '' AND data_entrada LIKE '2026-11%'
    GROUP BY servicos_realizados
    ORDER BY qtd DESC
    LIMIT 5
    """)
    ranking_servicos = [{
        'servico': r['servicos_realizados'],
        'qtd': r['qtd']
    } for r in cursor.fetchall()]
    
    # Top 5 Carros que Mais Passaram pela Oficina (Reincidência)
    cursor.execute("""
    SELECT 
        prefixo_veiculo, placa, modelo, linha,
        COUNT(*) as total_passagens,
        SUM(dias_parados) as total_dias_parado,
        MAX(km_total_atual) as km_total,
        AVG(km_entrada - km_anterior) as km_medio_entre_quebras
    FROM oficina_ordens_servico
    GROUP BY prefixo_veiculo
    ORDER BY total_passagens DESC, total_dias_parado DESC
    LIMIT 5
    """)
    ranking_carros = [{
        'prefixo': r['prefixo_veiculo'],
        'placa': r['placa'],
        'modelo': r['modelo'],
        'linha': r['linha'],
        'passagens': r['total_passagens'],
        'dias_parados': round(r['total_dias_parado'] or 0, 1),
        'km_total': r['km_total'] or 0,
        'km_medio_entre_quebras': int(r['km_medio_entre_quebras'] or 4500)
    } for r in cursor.fetchall()]
    
    # 3. Lista de Ordens de Serviço (Tabela com filtros)
    sql_os = "SELECT * FROM oficina_ordens_servico WHERE 1=1"
    params_os = []
    
    if status_filtro == 'ativos':
        sql_os += " AND status != 'Concluído / Liberado'"
    elif status_filtro != 'todos':
        sql_os += " AND status = ?"
        params_os.append(status_filtro)
        
    if linha_filtro != 'Todas':
        sql_os += " AND linha LIKE ?"
        params_os.append(f"%{linha_filtro}%")
        
    if busca:
        sql_os += " AND (prefixo_veiculo LIKE ? OR placa LIKE ? OR numero_os LIKE ? OR mecanico_responsavel LIKE ?)"
        params_os.extend([f"%{busca}%", f"%{busca}%", f"%{busca}%", f"%{busca}%"])
        
    cursor.execute(sql_os, params_os)
    ordens_raw = cursor.fetchall()
    
    ordens = []
    now = datetime.now()
    for row in ordens_raw:
        item = dict(row)
        km_rodados = max(0, (item.get('km_entrada') or 0) - (item.get('km_anterior') or 0))
        item['km_rodados_desde_anterior'] = km_rodados
        
        if not item.get('data_conclusao') and item.get('data_entrada'):
            try:
                dt_ent = datetime.strptime(item['data_entrada'][:16], '%Y-%m-%d %H:%M')
                diff_dias = round((now - dt_ent).total_seconds() / 86400, 1)
                item['dias_parados'] = diff_dias
                item['tempo_inoperante_horas'] = round(diff_dias * 24, 1)
            except Exception:
                pass
        ordens.append(item)
        
    # CLASSIFICAÇÃO DA TABELA (DO MAIOR PARA O MENOR E VICE-VERSA)
    if ordenar_sel == 'dias_asc':
        ordens.sort(key=lambda x: (x.get('dias_parados') or 0.0))
    elif ordenar_sel == 'km_rodados_desc':
        ordens.sort(key=lambda x: (x.get('km_rodados_desde_anterior') or 0), reverse=True)
    elif ordenar_sel == 'km_rodados_asc':
        ordens.sort(key=lambda x: (x.get('km_rodados_desde_anterior') or 0))
    elif ordenar_sel == 'km_total_desc':
        ordens.sort(key=lambda x: (x.get('km_total_atual') or 0), reverse=True)
    elif ordenar_sel == 'km_total_asc':
        ordens.sort(key=lambda x: (x.get('km_total_atual') or 0))
    elif ordenar_sel == 'data_asc':
        ordens.sort(key=lambda x: x.get('data_entrada') or '')
    elif ordenar_sel == 'data_desc':
        ordens.sort(key=lambda x: x.get('data_entrada') or '', reverse=True)
    elif ordenar_sel == 'carro_desc':
        ordens.sort(key=lambda x: x.get('prefixo_veiculo') or '', reverse=True)
    elif ordenar_sel == 'carro_asc':
        ordens.sort(key=lambda x: x.get('prefixo_veiculo') or '')
    elif ordenar_sel == 'status_asc':
        ordens.sort(key=lambda x: x.get('status') or '')
    else:  # 'dias_desc' (padrão: maior tempo parado primeiro)
        ordens.sort(key=lambda x: (x.get('dias_parados') or 0.0), reverse=True)
        
    # 4. Dados para o Dashboard Estratégico (Histórico Mês a Mês Completo, Semanal e Comparativo)
    cursor.execute("""
    SELECT 
        strftime('%Y-%m', data_entrada) as mes_ano,
        COUNT(*) as total_os,
        AVG(dias_parados) as media_dias,
        SUM(dias_parados) as total_dias,
        SUM(custo_pecas) as total_pecas,
        SUM(custo_mao_obra) as total_mo
    FROM oficina_ordens_servico
    GROUP BY mes_ano
    ORDER BY mes_ano ASC
    """)
    historico_meses_raw = cursor.fetchall()
    
    nomes_meses_abrev = {'08': 'Agosto', '09': 'Setembro', '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'}
    historico_meses = []
    for r in historico_meses_raw:
        m = dict(r)
        partes = m['mes_ano'].split('-')
        mes_cod = partes[1] if len(partes) > 1 else '11'
        m['label_mes'] = f"{nomes_meses_abrev.get(mes_cod, mes_cod)}/{partes[0]}"
        m['media_dias'] = round(m['media_dias'] or 0.0, 1)
        m['total_dias'] = round(m['total_dias'] or 0.0, 1)
        m['total_pecas'] = round(m['total_pecas'] or 0.0, 2)
        historico_meses.append(m)
    
    cursor.execute("""
    SELECT 
        CASE 
            WHEN strftime('%d', data_entrada) BETWEEN '01' AND '07' THEN 'Semana 1 (01-07)'
            WHEN strftime('%d', data_entrada) BETWEEN '08' AND '14' THEN 'Semana 2 (08-14)'
            WHEN strftime('%d', data_entrada) BETWEEN '15' AND '21' THEN 'Semana 3 (15-21)'
            ELSE 'Semana 4 (22-28)'
        END as semana_label,
        COUNT(*) as qtd_os,
        AVG(dias_parados) as media_dias,
        SUM(custo_pecas) as custo_pecas
    FROM oficina_ordens_servico
    WHERE data_entrada LIKE '2026-11%'
    GROUP BY semana_label
    ORDER BY semana_label ASC
    """)
    historico_semanas = [dict(r) for r in cursor.fetchall()]
    
    dados_out = next((m for m in historico_meses if m['mes_ano'] == '2026-10'), {'total_os': 15, 'media_dias': 2.1, 'total_pecas': 26400.0})
    dados_nov = next((m for m in historico_meses if m['mes_ano'] == '2026-11'), {'total_os': 48, 'media_dias': 2.4, 'total_pecas': 42150.0})
    
    comparativo = {
        'os_outubro': dados_out['total_os'],
        'os_novembro': dados_nov['total_os'],
        'var_os_perc': round(((dados_nov['total_os'] - dados_out['total_os']) / dados_out['total_os'] * 100), 1) if dados_out['total_os'] else 0.0,
        'mttr_outubro': round(dados_out['media_dias'] or 2.1, 1),
        'mttr_novembro': round(dados_nov['media_dias'] or 2.4, 1),
        'var_mttr_perc': round(((dados_nov['media_dias'] - dados_out['media_dias']) / dados_out['media_dias'] * 100), 1) if dados_out['media_dias'] else 0.0,
        'custo_outubro': round(dados_out['total_pecas'] or 26400.0, 2),
        'custo_novembro': round(dados_nov['total_pecas'] or 42150.0, 2),
        'var_custo_perc': round(((dados_nov['total_pecas'] - dados_out['total_pecas']) / dados_out['total_pecas'] * 100), 1) if dados_out['total_pecas'] else 0.0
    }
    
    cursor.execute("SELECT DISTINCT linha FROM oficina_ordens_servico ORDER BY linha ASC")
    linhas = [r[0] for r in cursor.fetchall() if r[0]]
    
    cursor.execute("SELECT DISTINCT mecanico_responsavel FROM oficina_ordens_servico ORDER BY mecanico_responsavel ASC")
    mecanicos_lista = [r[0] for r in cursor.fetchall() if r[0]]
    
    conn.close()
    
    kpis = {
        'carros_manutencao': carros_manutencao,
        'carros_aguardando_pecas': carros_aguardando_pecas,
        'carros_testes': carros_testes,
        'total_inoperantes': total_inoperantes,
        'frota_total': frota_total,
        'frota_operando': frota_operando,
        'frota_parada_perc': frota_parada_perc,
        'frota_operando_perc': frota_operando_perc,
        'tempo_medio_inoperante': tempo_medio_inoperante,
        'dias_parados_totais': dias_parados_totais,
        'custo_total_pecas': custo_total_pecas,
        'custo_total_mo': custo_total_mo,
        'custo_total': round(custo_total_pecas + custo_total_mo, 2)
    }
    
    return render_template(
        "oficina.html",
        kpis=kpis,
        ordens=ordens,
        total_exibido=len(ordens),
        status_filtro=status_filtro,
        linha_filtro=linha_filtro,
        busca=busca,
        view_mode=view_mode,
        ordenar_sel=ordenar_sel,
        linhas=linhas,
        mecanicos_lista=mecanicos_lista,
        ranking_itinerarios=ranking_itinerarios,
        ranking_reclamados=ranking_reclamados,
        ranking_constatados=ranking_constatados,
        ranking_pecas=ranking_pecas,
        ranking_servicos=ranking_servicos,
        ranking_carros=ranking_carros,
        historico_meses=historico_meses,
        historico_semanas=historico_semanas,
        comparativo=comparativo
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

@app.route("/api/oficina/atualizar", methods=["POST"])
def api_atualizar_oficina():
    data = request.form
    os_id = data.get("os_id")
    dt_entrada = data.get("data_entrada")
    prev_entrega = data.get("previsao_entrega")
    dt_conclusao = data.get("data_conclusao") or None
    if dt_conclusao and dt_conclusao.strip() == "":
        dt_conclusao = None
        
    status = data.get("status", "Em Manutenção")
    mecanico = data.get("mecanico_responsavel", "Carlos Roberto (Chefe)")
    def_constatado = data.get("defeito_constatado", "")
    pecas = data.get("pecas_trocadas", "")
    servicos = data.get("servicos_realizados", "")
    
    try:
        km_entrada = int(data.get("km_entrada") or 0)
    except Exception:
        km_entrada = 145000
        
    try:
        km_total = int(data.get("km_total_atual") or km_entrada)
    except Exception:
        km_total = km_entrada
        
    try:
        custo_pecas = float(data.get("custo_pecas") or 0.0)
    except Exception:
        custo_pecas = 0.0
        
    try:
        custo_mo = float(data.get("custo_mao_obra") or 0.0)
    except Exception:
        custo_mo = 0.0
        
    obs = data.get("observacoes", "")
    
    # Recalcula dias parados dinamicamente
    now = datetime.now()
    dias_parados = 0.0
    if dt_entrada:
        try:
            t1 = datetime.strptime(dt_entrada[:16], "%Y-%m-%d %H:%M")
            if dt_conclusao:
                t2 = datetime.strptime(dt_conclusao[:16], "%Y-%m-%d %H:%M")
            else:
                t2 = now
            diff = max(0.0, (t2 - t1).total_seconds() / 86400)
            dias_parados = round(diff, 1)
        except Exception as e:
            print(f"Erro calculando dias parados: {e}")
            
    horas_inoperante = round(dias_parados * 24, 1)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE oficina_ordens_servico
    SET data_entrada = ?, previsao_entrega = ?, data_conclusao = ?,
        dias_parados = ?, tempo_inoperante_horas = ?, status = ?,
        mecanico_responsavel = ?, defeito_constatado = ?, pecas_trocadas = ?,
        servicos_realizados = ?, km_entrada = ?, km_total_atual = ?,
        custo_pecas = ?, custo_mao_obra = ?, observacoes = ?
    WHERE id = ?
    """, (
        dt_entrada, prev_entrega, dt_conclusao,
        dias_parados, horas_inoperante, status,
        mecanico, def_constatado, pecas,
        servicos, km_entrada, km_total,
        custo_pecas, custo_mo, obs, os_id
    ))
    
    # Se gerou custo de peças novo e status foi concluído, registra no financeiro
    if custo_pecas > 0 and status == 'Concluído / Liberado':
        cursor.execute("SELECT numero_os, prefixo_veiculo FROM oficina_ordens_servico WHERE id = ?", (os_id,))
        os_info = cursor.fetchone()
        if os_info:
            cursor.execute("""
            INSERT INTO financeiro_integracao (
                origem_area, tipo, descricao, referencia_documento, valor,
                data_lancamento, data_vencimento, status, responsavel_aprovacao
            ) VALUES ('Manutenção_Peças', 'Pagar', ?, ?, ?, ?, ?, 'Pendente', ?)
            """, (
                f"Peças Oficina: {os_info['numero_os']} (Carro {os_info['prefixo_veiculo']})",
                os_info['numero_os'], custo_pecas, now.date(), (now + timedelta(days=15)).date(), mecanico
            ))
            
    conn.commit()
    conn.close()
    
    redirect_url = request.referrer or url_for("oficina_view")
    return redirect(redirect_url)

@app.route("/api/oficina/nova", methods=["POST"])
def api_nova_os_oficina():
    data = request.form
    prefixo = data.get("prefixo_veiculo", "").strip()
    placa = data.get("placa", "").strip().upper() or "BRA2E19"
    modelo = data.get("modelo", "Caio Millennium IV - MB O-500U")
    linha = data.get("linha", "Linha 801 - Central x Term. Sul")
    mecanico = data.get("mecanico_responsavel", "Carlos Roberto (Chefe)")
    defeito_rec = data.get("defeito_reclamado", "Revisão periódica programada")
    defeito_const = data.get("defeito_constatado", "Aguardando diagnóstico técnico")
    
    try:
        km_entrada = int(data.get("km_entrada") or 147000)
    except Exception:
        km_entrada = 147000
        
    try:
        km_anterior = int(data.get("km_anterior") or (km_entrada - 4200))
    except Exception:
        km_anterior = km_entrada - 4200
        
    now = datetime.now()
    dt_entrada = data.get("data_entrada") or now.strftime("%Y-%m-%d %H:%M")
    prev_entrega = data.get("previsao_entrega") or (now + timedelta(days=2)).strftime("%Y-%m-%d %H:%M")
    status = data.get("status", "Em Manutenção")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM oficina_ordens_servico")
    total_os = cursor.fetchone()[0] + 1
    numero_os = f"OS-OFIC-2026-{total_os:03d}"
    
    cursor.execute("""
    INSERT INTO oficina_ordens_servico (
        numero_os, prefixo_veiculo, placa, modelo, linha, mecanico_responsavel,
        data_entrada, previsao_entrega, data_conclusao, dias_parados, tempo_inoperante_horas,
        status, defeito_reclamado, defeito_constatado, pecas_trocadas, servicos_realizados,
        km_anterior, km_entrada, km_total_atual, custo_pecas, custo_mao_obra, observacoes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, 0.1, 2.4, ?, ?, ?, '', '', ?, ?, ?, 0.0, 0.0, ?)
    """, (
        numero_os, prefixo, placa, modelo, linha, mecanico,
        dt_entrada, prev_entrega, status, defeito_rec, defeito_const,
        km_anterior, km_entrada, km_entrada, "OS aberta pela equipe da oficina."
    ))
    conn.commit()
    conn.close()
    
    redirect_url = request.referrer or url_for("oficina_view")
    return redirect(redirect_url)

if __name__ == "__main__":
    print("🚀 Iniciando CRM & Service Desk Transporte Urbano na porta 5700...")
    app.run(host="0.0.0.0", port=5700, debug=False, threaded=True)
