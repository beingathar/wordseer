import os

from flask import Flask
from flask_wtf.csrf import CsrfProtect

app = Flask(__name__)

app.config.from_object('config')
CsrfProtect(app)

from app.controllers import *
from app.models import *

#TODO: these imports are all over the place
