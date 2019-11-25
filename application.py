#API Key = P82FZXGPGDWO4M1I

import os
import csv
import urllib.request

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from flask.exthook import ExtDeprecationWarning
from warnings import simplefilter
simplefilter("ignore", ExtDeprecationWarning)
from flask_autoindex import AutoIndex

from helpers import apology, login_required, lookup, usd

# Ensure environment variable is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    for stock in db.execute("SELECT * FROM transactions WHERE username =:name", name = username):
        try:
            db.execute("UPDATE transactions SET Total = :Total WHERE Symbol = :Symbol", Total = stock["Shares"] * lookup(stock["Symbol"])["price"], Symbol = stock["Symbol"])
        except:
            apology("API Error", 403)
    try:
        sum = round(db.execute("SELECT sum(Total) FROM transactions WHERE Username = :name", name=username)[0]["sum(Total)"], 2)
    except:
        sum = 0
    cash = round(db.execute("SELECT * FROM users WHERE username = :name", name=username)[0]["cash"], 2)
    if not cash:
        cash = 0
    transactions = db.execute("SELECT * FROM transactions WHERE username = :name", name=username)

    return render_template("bought.html", transactions = transactions, cash = cash, total = sum + cash)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if(request.method == "GET"):
        return render_template("buy.html")
    elif(request.method == "POST"):

        """check fields entered"""
        if not request.form.get("shares") or not request.form.get("symbol"):
            return apology("All fields must be filled", 403)

        if int(request.form.get("shares")) <= 0:
            return apology("Must be greater than zero")

        stock = lookup(request.form.get("symbol"))

        """check valid stock symbol"""
        if not stock:
            return apology("Stock not valid", 403)

        cash = db.execute("SELECT * FROM users WHERE username = :name", name = username)[0]["cash"] - stock["price"] * float(request.form.get("shares"))

        """check has enough money"""
        if cash < 0:
            cash += stock["price"] * float(request.form.get("shares"))
            return apology("Not enough money", 403)

        db.execute("UPDATE users SET cash = :cash WHERE username = :username", username = username, cash = cash)

        """if symbol is already in database stack"""
        if db.execute("SELECT * FROM transactions WHERE Symbol = :Symbol", Symbol=stock["symbol"]):
            db.execute("UPDATE transactions SET Shares = :shares WHERE Symbol =:Symbol", Symbol = stock["symbol"], shares = db.execute("SELECT * FROM transactions WHERE Symbol = :Symbol", Symbol = stock["symbol"])[0]["Shares"] + int(request.form.get("shares")))
        else:
            db.execute("INSERT INTO transactions (Symbol, Shares, Price, Total, Username) VALUES(:symbol, :shares, :price, :total, :usernamee)", symbol=stock["symbol"], shares = request.form.get("shares"), price = stock["price"], total = stock["price"] * float(request.form.get("shares")), usernamee = username)

        return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        global username
        username = request.form.get("username")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :name",
                          name=username)

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote")
@login_required
def quote():
    return render_template("quote.html")


@app.route("/getquote")
@login_required
def getquote():
    symbol = request.args.get("symbol")
    dictionary = lookup(symbol)

    if not symbol:
        return apology("Stock not valid", 403)

    print(symbol + "hello")
    return jsonify(dictionary)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    elif request.method == "POST":

        """search through usernames for repeat"""
        accounts = db.execute("SELECT * FROM users")
        for account in accounts:
            if account["username"] == request.form.get("username"):
                return apology("Username taken", 403)

        """check for empty fields"""
        if not request.form.get("username") or not request.form.get("password") or not request.form.get("password2"):
            return apology("All fields must be filled", 403)

        """check for passwords not matching"""
        if not request.form.get("password") == request.form.get("password2"):
            return apology("Passwords do not match", 403)

        """add to database, all clear"""
        db.execute("INSERT INTO users (username, hash, cash) VALUES(:username, :hash, :cash)", username=request.form["username"], hash=generate_password_hash(request.form["password"]), cash=10000)

        return redirect("/login")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "GET":
        return render_template("sell.html", stocks = db.execute("SELECT * FROM transactions WHERE Username=:Username", Username=username))
    elif request.method == "POST":

        """check if fields filled"""
        if not request.form.get("shares") or not request.form.get("symbol"):
            return apology("All fields must be filled", 403)
        if int(request.form.get("shares")) <= 0:
            return apology("Must be greater than zero", 403)
        """check if has enough shares"""
        stock = db.execute("SELECT * FROM transactions WHERE symbol=:symbol", symbol = request.form.get("symbol"))
        if stock and stock[0]["Shares"] < int(request.form.get("shares")):
            return apology("Not enough shares", 403)
        """update stocks after selling"""
        cash = db.execute("SELECT * FROM users WHERE username = :username", username = username)[0]["cash"] + stock[0]["Total"]
        db.execute("UPDATE users SET cash = :cash WHERE username = :username", username = username, cash = cash)

        """delete from database if no stocks left"""
        if stock[0]["Shares"] == int(request.form.get("shares")):
            db.execute("DELETE FROM transactions WHERE Symbol = :Symbol", Symbol = request.form.get("symbol"))
        else:
            db.execute("UPDATE transactions SET Shares = :Shares WHERE Symbol = :Symbol", Shares = stock[0]["Shares"] - int(request.form.get("shares")), Symbol = request.form.get("symbol"))

        return redirect("/")

def updateStockPrice(stock):
      db.execute("UPDATE transactions SET Price = :Price WHERE Symbol = :Symbol", Price = stock["Shares"] - request.form.get("shares"), Symbol = request.form.get("symbol"))
      db.execute("UPDATE transactions SET Price = :Price WHERE Symbol = :Symbol", Price = stock["Shares"] - request.form.get("shares"), Symbol = request.form.get("symbol"))

# def errorhandler(e):
#    """Handle error"""
#    print(e)
#    return apology(e.name, e.code)


# listen for errors
#for code in default_exceptions:
#    app.errorhandler(code)(errorhandler)
