import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
#if not os.environ.get("API_KEY"):
#    raise RuntimeError("API_KEY not set")

def isInteger(n):
    """Return True if argument is a whole number, False if argument has a fractional part.

    Note that for values very close to an integer, this test breaks. During
    superficial testing the closest value to zero that evaluated correctly
    was 9.88131291682e-324. When dividing this number by 10, Python 2.7.1 evaluated
    the result to zero"""

    if n % 2 == 0 or (n+1) % 2 == 0:
        return True
    return False


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    userID = session["user_id"]

    userShares = db.execute('SELECT symbol, shares FROM inventory WHERE user_id = ? AND shares != 0', userID)
    # getting the user cash
    userMoney = db.execute("SELECT cash FROM users WHERE id = ?", userID)
    userMoney = userMoney[0]["cash"]
    # getting all the share related info and appending them into list that correspond each other by index
    print(userShares)
    allSymbols = []
    allShares = []
    allPrices = []
    allNames = []
    for elem in userShares:
        allSymbols.append(elem['symbol'])
        allShares.append(elem['shares'])
    for symbol in allSymbols:
        infoDict = lookup(symbol)
        price = infoDict['price']
        name = infoDict["name"]
        allPrices.append(price)
        allNames.append(name)

    # getting the TOTAL VALUE of each owned share, osea, shares * price y los guardo en una list allTotals
    allTotals = []
    length = len(allShares)
    for i in range(length):
        print(i, length)
        total = float(allShares[i]) * float(allPrices[i])
        allTotals.append(total)

    # suming my share totals + the cash he has to get my REALTOTAL
    realTotal = 0
    for total in allTotals:
        realTotal = realTotal + total
    realTotal = float(realTotal) + float(userMoney)
    realTotal = usd(realTotal)
    userMoney = usd(userMoney)

    # aca lo que hice fue cerar dos listas donde voy a meter los preciso y totales pero formateados con USD, porque no queria modificar las otras listas creadas
    allPricesUSD = []
    allTotalsUSD = []
    for price in allPrices:
        price = usd(price)
        allPricesUSD.append(price)
    for total in allTotals:
        total = usd(total)
        allTotalsUSD.append(total)
    print(allSymbols, allShares, allPrices, allNames)
    print(allTotals)
    print(realTotal)
    print(userMoney)
    return render_template("index.html", allSymbols=allSymbols, allShares=allShares, allPrices=allPricesUSD, allNames=allNames, allTotals=allTotalsUSD, realTotal=realTotal, userMoney=userMoney, length=length)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    # si tengo un get, RENDREO el form, y sino tengo que hacer que puedan comprar y return un flash message exito
    if request.method == "POST":
        # me fijo si el symbol es valido
        # me fijo si la cantidad de shares es positiva
        # me fijo si tiene plata suficiente
        # hago la compra
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        stockInfo = lookup(symbol)
        userID = session["user_id"]
        # checking if symbol and shares are inputed, also, if the symbol is valid
        if not symbol:
            return apology("must provide symbol", 400)
        if not shares:
            return apology("must provide a positive shares quantity", 400)
        # checkfin if shares is a number
        if not shares.isdigit():
            return apology("shares must be a number", 400)
        shares = int(shares)
        if shares <= 0:
            return apology("must provide a positive shares quantity", 400)
        #checking if shares are fractional
        if not isInteger(shares):
            return apology("must provide a positive whole number shares quantity", 400)
        if stockInfo == None:
            return apology("Stock not found", 400)

        # checking if the user has enough money to buy
        stockPrice = stockInfo["price"]
        precio = stockInfo["price"]
        userMoney = db.execute("SELECT cash FROM users WHERE id = ?", userID)
        userMoney = userMoney[0]["cash"]
        total = stockPrice * shares
        precio2 = total
        if total > userMoney:
            return apology("Not enough money!", 403)

        # si llegaste hasta aca quiere decir que está todo bien y la transaccion pasa
        # por ende hay que restar la plata de mi tabla de usuarios
        # y registrar la compra en mi tabla de trans
        # despues tmb tengo que registalre en mi tabla INVENTORY
        # para eso neceiso chequear si ya tiene o no de esa stock
        newMoney = userMoney - total

        #update the users money
        db.execute('UPDATE users SET cash = (?) WHERE id = (?)', newMoney, userID)
        # insert the transaction to the database
        operation = 'buy'
        db.execute('INSERT INTO trans (user_id, symbol, shares, price, type) VALUES (?, ?, ?, ?, ?)',
                   userID, symbol, shares, total, operation)
        print(stockPrice, userMoney)
        newMoney = usd(newMoney)
        datos = [symbol, shares, total, newMoney, stockPrice]

        # cargo tmb en INVENTORY,  si tiene acciones de esa, UPDATEO PARA SUBIRLE AL CANITAD, sino, inserto con la cantiad que compro
        actualShares = db.execute('SELECT shares FROM inventory WHERE symbol = ? AND user_id = ?', symbol, userID)

        print(actualShares)
        if actualShares:
            actualShares = int(actualShares[0]['shares'])
            actualShares = actualShares + shares
            db.execute('UPDATE inventory SET shares = (?) WHERE symbol = (?)', actualShares, symbol)
        else:
            db.execute('INSERT INTO inventory (user_id, symbol, shares) VALUES (?, ?, ?)', userID, symbol, shares)
        return render_template("bought.html", datos=datos, precio=precio, precio2=precio2)

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    userID = session["user_id"]
    trans = db.execute('SELECT symbol, shares, price, time, type FROM trans WHERE user_id = ?', userID)
    print(trans)
    length = len(trans)
    return render_template("history.html", length=length, trans=trans)


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

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # si me llega un GET, muestro las quotes que obtuve, si me llega un POST, busco en la base de datos y madno al info
    if request.method == "POST":
        # busco el SYMBOL y redirecteo a quoted, QUE MUESTRA LA INFO DE LA STOCK QUE NOS DIERON
        if request.form.get('symbol'):
            symbol = request.form.get('symbol')
            print(symbol)
            if lookup(symbol):
                print(symbol)
                stockInfo = lookup(symbol)
                print(stockInfo)
                return render_template("quoted.html", stockInfo = stockInfo)
            else:
                return apology("SOTCK NOT FOUND", 400)
        else:
            return apology("MUST PROVIDE SYMBOL", 400)

    else:
        # rendereo mi QUOTE.HTML SI ES UN GET. QUE ES UN FORM QUE MANDA UN POST A ESTA MISMA RUTA
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # SI RECIBO UN POST REGISTRO EL USUARIO, SINO RENDER REGISTER
    if request.method == "POST":
        # registro usuario
        # chequeo USERNAME
        # chequeo PASSWORD, sino tengo esas dos, return aplogy.
        # si tengo las dos, sumbit el user input via post to register

        username = request.form.get('username')
        password = request.form.get('password')
        password2 = request.form.get('confirmation')
        print(username, password, password2)

        # chequeo que no este el username ya registrado
        existe = db.execute('SELECT username FROM users WHERE username = ?', username)
        if existe:
            return apology("username alredy in use", 400)

        if not username:
            return apology("must provide username", 400)
        elif not password:
            return apology("must provide password", 400)
        elif password != password2:
            return apology("confirmation password error", 400)
        # hasheo el pass para poder guardarlo
        hashPass = generate_password_hash(password)
        # inserto el usernaem y el hashpass en la base de datos
        rows = db.execute('INSERT INTO users (username, hash) VALUES(?, ?)', username, hashPass)
        sucess_message = "Registrado correctamente {username}"
        flash(sucess_message)
        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # voy a recibir en un POST, el SYMBOL y la CANTIDAD que quiere vender el usuario, tengo que tirar error si el usuario NO POSEE esa STOCK, o si no teine la cantidad suficiente
    # si cumple todo, lo que hago es updatear la base de datos en su tabla restando las acciones que tiene y rendereo SOLD que va a decir que vendio en un flash y nada mas, tengo lookup el price
    # SI RECIBO GET, presento la opcion para vender, tengo que buscar que acciones tiene e la base de datos inventory y render el template SELL.html mandandole una lista con los symbosl

    userID = session["user_id"]

    if request.method == "POST":
        symbol = request.form.get('symbol')
        shares = request.form.get('shares')
        print(symbol)

        # error si no elige stock
        if not symbol:
            return apology("must select a stock", 400)

        # query a la data base para ver la canitdad de esa accion que tiene
        userCantidad = db.execute('SELECT shares FROM inventory WHERE user_id = ? AND symbol = ? AND shares != 0', userID, symbol)
        if not shares:
            return apology("must input shares to sell", 400)
        # error si elige una que no tiene somehow
        if not userCantidad:
            return apology("you dont own that stock", 400)
        userCantidad = userCantidad[0]['shares']

        # error si no pone un numero positivo
        if int(shares) <= 0:
            return apology("you must input a positive number", 400)

        # error si pone un numero positivo, pero no tiene tantas acciones
        if int(shares) > int(userCantidad):
            return apology("you dont own that many shares of that stock", 400)

        # si todo esta bien busco el precio actual de la stock
        price = lookup(symbol)
        price = float(price['price'])
        precio = price
        # updateo la base de datos para reflejar la venta, tengo que restar acciones en inventory y sumar plata en users, el PRICE ya lo tengo en price
        # necesito saber cuanta plata tiene ahora, lo busco de la base de datos
        plataActual = db.execute('SELECT cash FROM users WHERE id = ?', userID)
        plataActual = float(plataActual[0]['cash'])
        # calcular cuanta plata gano
        plataNueva = price * float(shares)

        # sum of boths
        plataNueva = plataActual + plataNueva
        # COMANDO PARA UPDATEAR EL CASH
        db.execute('UPDATE users SET cash = ? WHERE id = ?', plataNueva, userID)

        # UPDATE LAS ACCIONES, resto las que tiene con las que quedan
        accionesTotales = int(userCantidad) - int(shares)
        db.execute('UPDATE inventory SET shares = ? WHERE symbol = ? AND user_id = ?', accionesTotales, symbol, userID)
        total = float(plataActual)
        total2 = float(plataNueva)
        cantidad2 = float(shares)

        # CARGO TMB EN LA TABLA DE TRANS
        opType = 'sell'
        db.execute('INSERT INTO trans (user_id, symbol, shares, price, type) VALUES (?, ?, ?, ?, ?)',
                   userID, symbol, shares, price, opType)
        price = usd(price)
        flash("SOLD!")
        return redirect('/')
        # return render_template('sold.html', symbol = symbol, price = price, acciones = shares, precio = precio, total = total, total2 = total2, cantidad = cantidad2)
    else:
        # busco que acciones tiene el usuario

        shares = db.execute('SELECT symbol, shares FROM inventory WHERE user_id = ? AND shares != 0', userID)

        return render_template('sell.html', shares=shares)


@app.route("/changepass", methods=["GET", "POST"])
@login_required
def changepass():
    # si es un get pongo tres input para cambiar pass, el viejo y el nuevo confirmar, si es un post chequeo que el pass este bieny updateo la tabla users
    if request.method == "POST":
        # check
        # update table
        userID = session["user_id"]
        currentPassword = request.form.get('oldPassword')
        newPassword = request.form.get('newPassword')
        newPassword2 = request.form.get('newPassword2')
        currentHash = db.execute("SELECT hash FROM users WHERE id = ?", userID)
        currentHash = currentHash[0]["hash"]
        print(currentHash)
        # chequeo que haya puesto todo en el post
        if not currentPassword:
            return apology("you must enter your password", 403)
        if not newPassword:
            return apology("you must enter a new password", 403)
        if not newPassword2:
            return apology("you must confirm your new password", 403)
        # chequeo que el password que me dio sea el correcto
        if not check_password_hash(currentHash, currentPassword):
            return apology("wrong current password", 403)
        # chequeo que los dos nuevos passwrod sean iguales
        if newPassword != newPassword2:
            return apology("new password dont match", 403)

        # ya si todo salio bien updateo el hash
        newHash = generate_password_hash(newPassword)
        db.execute("UPDATE users SET hash = ? WHERE id = ?", newHash, userID)
        return render_template("changedpass.html")
    else:
        return render_template("changepass.html")