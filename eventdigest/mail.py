import os
import smtplib
import email.mime.text


def mail_self(subject, text):
        user = os.environ['USER']
        host = 'localhost'
        addr = user + '@' + host
        msg = email.mime.text.MIMEText(text)
        msg['Subject'] = subject
        msg['From'] = addr
        msg['To'] = addr
        s = smtplib.SMTP('localhost')
        s.sendmail(addr, [addr], msg.as_string())
