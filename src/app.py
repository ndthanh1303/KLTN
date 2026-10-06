import os

import pymysql
from flask import Flask, flash, redirect, render_template, url_for
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash
from wtforms import EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import (
    DataRequired, Email, EqualTo, InputRequired, Length, Optional, Regexp,
)

# db.py đọc .env khi được import.
from db import get_db_connection, lay_du_lieu_trang_chu

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]


def clean_text(value):
    return (value or "").strip()


@app.route("/")
def trang_chu():
    return render_template(
        "home.html",
        home_data=lay_du_lieu_trang_chu(),
    )


if __name__ == "__main__":
    app.run(debug=True)