"""
cloud/app/core/emails.py

Envio de email para confirmar cadastro e redefinir senha.

DOIS CAMINHOS, e a ordem importa:

1. API HTTP do Brevo, quando BREVO_API_KEY existe. É o que funciona em
   PRODUÇÃO.
2. SMTP, quando BREVO_API_KEY não existe mas SMTP_* sim. Útil em
   desenvolvimento local.

POR QUE SMTP NÃO SERVE EM PRODUÇÃO: o Railway BLOQUEIA as portas de
email (25, 465, 587, 2525) nos planos Free, Trial e Hobby, para impedir
que spammers abusem dos IPs do datacenter. O projeto está no Hobby,
então SMTP de lá nunca vai funcionar, por melhor que seja a
configuração. Isso custou um diagnóstico: o envio funcionava na máquina
de desenvolvimento e falhava em produção, sempre estourando o tempo de
conexão. A própria documentação do Railway indica serviços com API HTTP
como alternativa, porque usam a porta 443, que não é bloqueada.

POR QUE BREVO E NÃO RESEND: os planos gratuitos costumam exigir um
domínio verificado para enviar a terceiros. Sem domínio, o Resend só
entrega no endereço do dono da conta, o que impediria o resto do grupo
de receber. O Brevo aceita verificar apenas um endereço REMETENTE e
enviar para qualquer destinatário, com 300 emails por dia no plano
gratuito.

Usa urllib da biblioteca padrão em vez de `requests` de propósito: o
Blueprint é restritivo com dependências no deploy, e uma única chamada
HTTP não justifica um pacote novo.

DEGRADAÇÃO PROPOSITAL: sem nenhum caminho configurado, enviar() devolve
False em vez de levantar exceção. Quem chama decide o que fazer. Em
app/api/routes/auth.py isso significa criar a conta JÁ VERIFICADA, com
aviso no log, em vez de prender o produtor numa conta que ele nunca
conseguiria confirmar.
"""

import json
import logging
import smtplib
import ssl
import urllib.error
import urllib.request
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger("ecovision.cloud.emails")

_BREVO_URL = "https://api.brevo.com/v3/smtp/email"

# Curto de propósito. O envio acontece DENTRO da requisição de cadastro,
# e o app desiste em 10 segundos (EXPO_PUBLIC_API_TIMEOUT). Com o limite
# antigo de 20s, uma porta bloqueada pendurava o cadastro além do tempo
# do app e o produtor via "fetch failed" sem entender nada. Melhor
# desistir rápido do email e liberar a conta.
_TIMEOUT_SEGUNDOS = 8


def _enviar_por_brevo(destinatario: str, assunto: str, corpo: str) -> bool:
    payload = json.dumps(
        {
            "sender": {"name": "EcoVision", "email": settings.remetente},
            "to": [{"email": destinatario}],
            "subject": assunto,
            "textContent": corpo,
        }
    ).encode("utf-8")

    requisicao = urllib.request.Request(
        _BREVO_URL,
        data=payload,
        headers={
            "api-key": settings.BREVO_API_KEY,
            "content-type": "application/json",
            "accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(requisicao, timeout=_TIMEOUT_SEGUNDOS) as resposta:
            logger.info(
                "Email enviado via Brevo para %s (HTTP %s, assunto: %s)",
                destinatario,
                resposta.status,
                assunto,
            )
            return True
    except urllib.error.HTTPError as erro:
        # O corpo do erro do Brevo diz a causa (chave inválida,
        # remetente não verificado, cota estourada). Sem ele no log,
        # descobrir o motivo vira adivinhação.
        detalhe = erro.read().decode("utf-8", "replace")[:300]
        logger.error(
            "Brevo recusou o envio para %s: HTTP %s %s", destinatario, erro.code, detalhe
        )
        return False
    except Exception:
        logger.exception("Falha de rede ao enviar email para %s via Brevo", destinatario)
        return False


def _enviar_por_smtp(destinatario: str, assunto: str, corpo: str) -> bool:
    mensagem = EmailMessage()
    mensagem["From"] = settings.remetente
    mensagem["To"] = destinatario
    mensagem["Subject"] = assunto
    mensagem.set_content(corpo)

    try:
        contexto = ssl.create_default_context()
        with smtplib.SMTP(
            settings.SMTP_HOST, settings.SMTP_PORT, timeout=_TIMEOUT_SEGUNDOS
        ) as servidor:
            servidor.starttls(context=contexto)
            servidor.login(settings.SMTP_USUARIO, settings.SMTP_SENHA)
            servidor.send_message(mensagem)
        logger.info("Email enviado via SMTP para %s (assunto: %s)", destinatario, assunto)
        return True
    except Exception:
        logger.exception("Falha ao enviar email para %s via SMTP", destinatario)
        return False


def enviar(destinatario: str, assunto: str, corpo: str) -> bool:
    """Envia um email em texto puro. Devolve True se saiu, False caso
    contrário. Nunca levanta exceção: uma falha de email não pode
    derrubar a requisição que estava em andamento."""
    if settings.BREVO_API_KEY and settings.remetente:
        return _enviar_por_brevo(destinatario, assunto, corpo)

    if settings.smtp_configurado:
        return _enviar_por_smtp(destinatario, assunto, corpo)

    logger.warning(
        "Nenhum caminho de email configurado: mensagem para %s NAO foi enviada "
        "(assunto: %s)",
        destinatario,
        assunto,
    )
    return False


def montar_email_verificacao(nome: str, codigo: str) -> tuple[str, str]:
    """Assunto e corpo do email de confirmacao de cadastro."""
    corpo = (
        f"Olá, {nome}.\n\n"
        f"Seu código de confirmação do EcoVision é:\n\n"
        f"    {codigo}\n\n"
        f"Ele vale por 15 minutos. Digite-o no aplicativo para ativar sua conta.\n\n"
        f"Se não foi você quem se cadastrou, ignore esta mensagem: "
        f"sem o código, a conta não é ativada.\n\n"
        f"EcoVision"
    )
    return "Confirme seu cadastro no EcoVision", corpo


def montar_email_recuperacao(codigo: str) -> tuple[str, str]:
    """Assunto e corpo do email de redefinicao de senha."""
    corpo = (
        f"Recebemos um pedido para redefinir a senha da sua conta EcoVision.\n\n"
        f"Seu código é:\n\n"
        f"    {codigo}\n\n"
        f"Ele vale por 15 minutos e só pode ser usado uma vez.\n\n"
        f"Se não foi você quem pediu, ignore esta mensagem e NÃO compartilhe "
        f"este código com ninguém. Sua senha atual continua valendo.\n\n"
        f"EcoVision"
    )
    return "Redefinir sua senha do EcoVision", corpo
