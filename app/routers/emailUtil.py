from typing import List
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from ..config import settings
from jinja2 import Environment, select_autoescape, PackageLoader
from ..enums import EmailTemplate
from fastapi import UploadFile
from io import BytesIO

conf = ConnectionConfig(
    MAIL_USERNAME = settings.mail_username,
    MAIL_PASSWORD = settings.mail_password,
    MAIL_FROM     = settings.mail_from,   
    MAIL_PORT     = 587,                
    MAIL_SERVER   = settings.mail_server,
    MAIL_STARTTLS = True,                
    MAIL_SSL_TLS  = False,          
    USE_CREDENTIALS = True,
    VALIDATE_CERTS  = True,
)
env = Environment(
    loader=PackageLoader('app', 'templates'),
    autoescape=select_autoescape(['html', 'xml'])
)

file_per_template = {
    EmailTemplate.ResetPassword: 'reset_pass_mail.html',
    EmailTemplate.ConfirmAccount: 'confirm_mail.html',
    EmailTemplate.PayslipsMail: 'payslip_mail.html',
}

async def send_email(subject: str, recipients: List, email_template: EmailTemplate, email: str, code: str, attachments: list[dict] = [], msg: str = ""):
    template = env.get_template(file_per_template[email_template])
    html = template.render(
        name=email,
        code=code,
        subject=subject,
        message = msg
    )
    upload_files = [
        UploadFile(
            filename=attachment["filename"],
            file=BytesIO(attachment["content"]),
            content_type=attachment["content_type"]
        )
        for attachment in attachments
    ]

    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        html=html,
        subtype="html",
        attachments=upload_files,
    )

    fm = FastMail(conf)
    await fm.send_message(message)
