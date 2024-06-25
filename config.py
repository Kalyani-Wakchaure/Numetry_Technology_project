import os

class Config:
    SECRET_KEY = ""# enter secrete key
    DB_HOST = 'localhost'
    DB_USER = ''#enter username
    DB_PASSWORD = ''#enter password
    DB_NAME = ''#enter database name
    MAIL_SERVER = ''# enter server name
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = ''#enter emailid
    MAIL_PASSWORD = ''  #'your-email-password'
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
