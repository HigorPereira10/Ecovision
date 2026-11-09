"""
Envio dos e-mails de confirmação de cadastro e de redefinição de senha.

Dois caminhos, nesta ordem:
1. API HTTP do Brevo, quando BREVO_API_KEY está definida (produção; o
   Railway bloqueia as portas de SMTP nos planos Free, Trial e Hobby);
2. SMTP, quando apenas SMTP_* está definido (desenvolvimento local).

Usa urllib da biblioteca padrão para a chamada HTTP. Sem nenhum caminho
configurado, enviar() devolve False em vez de levantar exceção; o cadastro
cria então a conta já verificada, com aviso no log.
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

# Tempo limite curto: o envio ocorre durante a requisição de cadastro, e o
# aplicativo desiste após 10 segundos.
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
        # O corpo da resposta do Brevo indica a causa (chave inválida,
        # remetente não verificado, cota esgotada).
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
    """Envia um e-mail em texto puro e devolve se o envio foi aceito. Nunca
    levanta exceção, para não interromper a requisição em andamento."""
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
    """Assunto e corpo do e-mail de confirmação de cadastro."""
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
    """Assunto e corpo do e-mail de redefinição de senha."""
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
