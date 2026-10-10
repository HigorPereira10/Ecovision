"""
cloud/app/core/emails.py

Envio de email por SMTP, para confirmar cadastro e redefinir senha.

POR QUE SMTP GENERICO, e nao a API de um provedor: SMTP funciona com
Gmail, Outlook, Zoho ou qualquer servico, e trocar de provedor vira
mudanca de variavel de ambiente, sem tocar no codigo. A alternativa
avaliada (Resend) tem plano gratuito generoso, mas sem dominio proprio
verificado ele so entrega para o endereco do dono da conta, o que
inviabilizaria o resto do grupo testar.

DEGRADACAO PROPOSITAL: sem SMTP configurado, enviar() devolve False em
vez de levantar excecao. Quem chama decide o que fazer. Em
app/api/routes/auth.py isso significa criar a conta JA VERIFICADA, com
aviso no log, em vez de deixar o produtor preso numa conta que ele
nunca conseguiria confirmar. Mesma filosofia de app/core/inference.py:
dependencia externa ausente nao derruba o sistema.

O envio e sincrono e bloqueia a requisicao por algumas centenas de
milissegundos. Aceitavel no volume deste projeto (cadastro e
recuperacao de senha sao raros); se virar gargalo, o caminho e uma fila
em segundo plano, nao deixar de enviar.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger("ecovision.cloud.emails")


def enviar(destinatario: str, assunto: str, corpo: str) -> bool:
    """Envia um email em texto puro. Devolve True se saiu, False se o
    SMTP nao esta configurado ou se o envio falhou.

    Nunca levanta excecao: uma falha de email nao pode derrubar a
    requisicao que estava em andamento.
    """
    if not settings.email_configurado:
        logger.warning(
            "SMTP nao configurado: email para %s NAO foi enviado (assunto: %s)",
            destinatario,
            assunto,
        )
        return False

    mensagem = EmailMessage()
    mensagem["From"] = settings.SMTP_REMETENTE or settings.SMTP_USUARIO
    mensagem["To"] = destinatario
    mensagem["Subject"] = assunto
    mensagem.set_content(corpo)

    try:
        contexto = ssl.create_default_context()
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as servidor:
            servidor.starttls(context=contexto)
            servidor.login(settings.SMTP_USUARIO, settings.SMTP_SENHA)
            servidor.send_message(mensagem)
        logger.info("Email enviado para %s (assunto: %s)", destinatario, assunto)
        return True
    except Exception:
        # Inclui credencial errada, servidor fora do ar e limite de envio
        # atingido. O log traz o traceback; quem chama so precisa saber
        # que nao saiu.
        logger.exception("Falha ao enviar email para %s", destinatario)
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
