# 🚍 CRM & Service Desk Operacional - Transporte Urbano

Sistema integrado de CRM Operacional, Helpdesk, Service Desk de Ordens de Serviço (OS) com envio automático de e-mails, Acompanhamento de Ponto Eletrônico e Integração direta entre RH, Garagem, Portaria e Financeiro (Contas a Pagar e Receber).

## 🚀 Tecnologias
- **Backend:** Python / Flask
- **Banco de Dados:** SQLite (`crm_transporte.db`)
- **Frontend:** HTML5, CSS3 Moderno (Dark Transit Cockpit), JavaScript Vanilla, FontAwesome 6, Google Fonts (Montserrat & Inter)
- **Porta Padrão:** `5700`

## 👥 10 Áreas Conectadas (60 a 70 Colaboradores)
1. Diretor de Operações
2. Gerente Operacional
3. Gerente Administrativo
4. Manutenção (Oficina Diesel & Valas)
5. RH (Recursos Humanos)
6. Treinamento & Segurança
7. Contas a Pagar
8. Contas a Receber
9. Garagem (Pátio & Abastecimento)
10. Portaria (Guarita 24/7)

## 📦 Como Rodar
```bash
pip install flask
python init_db.py
python app.py
```
Acesse no navegador: `http://localhost:5700`
