from os import urandom
from flask_sqlalchemy import SQLAlchemy
from flask import Flask,render_template,request,flash,get_flashed_messages,redirect,url_for
from datetime import datetime
from flask_bcrypt import Bcrypt,check_password_hash
from flask_login import LoginManager,login_required,login_user,current_user,logout_user
import sqlalchemy
from datetime import datetime

app = Flask(__name__)
app.secret_key = urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.sqlite3'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
db.init_app(app)
app.app_context().push()

from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id=db.Column(db.Integer(),primary_key=True,autoincrement=True)
    username=db.Column(db.String(20),nullable=False,unique=True)
    password_hashed=db.Column(db.String(20),nullable=False)
    cart=db.relationship('Cart',backref='users')
    orders=db.relationship('Order',backref='owned')

    @property
    def password(self):
        return self.password
    
    @password.setter
    def password(self, password_text):
        self.password_hashed = bcrypt.generate_password_hash(password_text).decode('utf-8')

class Category(db.Model):
    category_id=db.Column(db.Integer(),primary_key=True,autoincrement=True)
    category_name=db.Column(db.String(20),nullable=False,unique=True)
    products=db.relationship('Product',backref='items')

class Product(db.Model):
    product_id=db.Column(db.Integer(),primary_key=True,autoincrement=True)
    product_name=db.Column(db.String(20),nullable=False,unique=True)
    unit=db.Column(db.String(20),nullable=False)
    price=db.Column(db.Integer(),nullable=False)
    quantity=db.Column(db.Integer(),nullable=False)
    category=db.Column(db.Integer(),db.ForeignKey('category.category_id'),nullable=False)
    expiry_date=db.Column(db.Date())

class Cart(db.Model):
    id=db.Column(db.Integer(),primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer(), db.ForeignKey('product.product_id'),unique=True, nullable=False)
    quantity = db.Column(db.Integer(), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_items = db.relationship('OrderItem', backref='order')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

db.create_all()

@app.route('/',methods=['GET'])
@app.route('/home',methods=['GET'])
def index():
    return render_template('home.html')

@app.route('/adminlogin',methods=['GET','POST'])
def adminlogin():
    admin='admin'
    password='1234'
    if request.method == "POST":
        username=request.form['username']
        password=request.form['password']
        if username==admin and password==password:
            flash(f'Success! You are logged in.',category='success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password',category='danger')
            return render_template('adminlogin.html')
    else:
        return render_template('adminlogin.html')

@app.route('/add_category',methods=['POST','GET'])
def add_category():
    if request.method == 'POST':
        try:
            category=request.form['category']
            cat=Category(category_name=category)
            db.session.add(cat)
            db.session.commit()
        except sqlalchemy.exc.IntegrityError:
            flash(f'Category named { category } already exists',category='danger')
            return render_template('add_category.html')
        return redirect(url_for('admin_dashboard'))
    else:
        return render_template('add_category.html')
    


@app.route('/<category>/add_product',methods=['POST','GET'])
def add_product(category):
    if request.method=='POST':
        name=request.form['prod_name']
        unit=request.form['unit']
        price=request.form['price']
        quantity=request.form['quantity']
        try:
            cat=Category.query.filter_by(category_name=category).first()
            prod= Product(product_name=name,unit=unit,price=price,quantity=quantity,category=cat.category_id)
            db.session.add(prod)
            db.session.commit()
        except sqlalchemy.exc.IntegrityError:
            flash(f'Product named { name } already exists',category='danger')
            return render_template('add_product.html')
        return redirect(url_for('admin_dashboard'))
    else:
        return render_template('add_product.html',category=category)

@app.route('/admin_dashboard',methods=['GET'])
def admin_dashboard():
    cat=db.session.query(Category).all()
    return render_template('admin_dashboard.html',categories=cat)

@app.route('/<category>/edit',methods=['GET','POST'])
def edit_category(category):
    if request.method=='POST':
        try:
            cat_name=request.form['category']
            cat=Category.query.filter_by(category_name=category).first()
            cat.category_name=cat_name
            db.session.add(cat)
            db.session.commit()
        except sqlalchemy.exc.IntegrityError:
            flash(f'Category named { category } already exists',category='danger')
            return redirect(url_for('edit_category'))
        return redirect(url_for('admin_dashboard'))
    elif request.method=="GET":
        return render_template('edit_category.html',category=category)

@app.route('/<category>/delete',methods=['GET','POST'])
def delete_category(category):
    cat=Category.query.filter_by(category_name=category).first()
    prod_list=Product.query.filter_by(category=cat.category_id).all
    for i in prod_list:
        db.session.delete(i)
    db.session.delete(cat)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/<category>/<product>/actions',methods=['GET','POST'])
def actions_product(category,product):
    if request.method=='GET':
        prod=Product.query.filter_by(product_name=product).first()
        return render_template('edit_product.html',prod=prod,category=category)
    elif request.method=='POST':
        try:
            prod=Product.query.filter_by(product_name=product).first()
            prod.name=request.form['prod_name']
            prod.unit=request.form['unit']
            prod.price=request.form['price']
            prod.quantity=request.form['quantity']
            db.session.add(prod)
            db.session.commit()
        except sqlalchemy.exc.IntegrityError:
            flash(f'Category named { category } already exists',category='danger')
            return redirect(url_for(actions_product))
        return redirect(url_for('admin_dashboard'))


@app.route('/user_registration',methods=['GET','POST'])
def user_registration():
    if request.method=='POST':
        try:
            username=request.form['username']
            password=request.form['password']
            user = User(username=username,password=password)
            db.session.add(user)
            db.session.commit()
        except sqlalchemy.exc.IntegrityError:
            flash(f'{ username } alraedy exists',category='info')
            return redirect(url_for('user_registration'))
        return redirect(url_for('userlogin'))
    else:
        return render_template('user_registration.html')

@app.route('/userlogin',methods=['GET','POST'])
def userlogin():
    if request.method=='POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hashed, password):
            login_user(user)
            flash(f'Success! You are logged in as : { current_user.username }',category='success')
            return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid username or password',category='danger')
            return render_template('userlogin.html')
    else:
        return render_template('userlogin.html')

@app.route('/user_dashboard',methods=['GET','POST'])
@login_required
def user_dashboard():
    if request.method=='POST':
        return render_template('user_dashboard.html')
    else:
        cat=db.session.query(Category).all()
        return render_template('user_dashboard.html',categories=cat)
    
@app.route('/add_to_cart/<product>',methods=['GET','POST'])
@login_required
def add_to_cart(product):
    quan=request.form['quantity']
    prod=Product.query.filter_by(product_name=product).first()
    cart=Cart.query.filter_by(user_id=current_user.id,product_id=prod.product_id).first()
    if cart:
        cart.quantity=quan
        db.session.add(cart)
        db.session.commit()
        return redirect(url_for('user_dashboard'))
    else:
        car=Cart(user_id=current_user.id,product_id=prod.product_id,quantity=quan)
        db.session.add(car)
        db.session.commit()
        return redirect(url_for('user_dashboard'))

@app.route('/cart',methods=['GET','POST'])
@login_required
def cart():
    uid=current_user.id
    user=User.query.filter_by(id=uid).first()
    items=user.cart
    sum=0
    products=[]
    categories=[]
    for i in items :
        prod=Product.query.filter_by(product_id=i.product_id).first()
        products.append(prod)
        cat=Category.query.filter_by(category_id=prod.category).first()
        categories.append(cat)
        sum+=prod.price*i.quantity
    return render_template('cart.html',cart_total=sum,product=products,category=categories,cart=items)

@app.route('/cart_remove/<product>',methods=['POST'])
@login_required
def remove(product):
    id=current_user.id
    prod_id=Product.query.filter_by(product_name=product).first()
    car=Cart.query.filter_by(user_id=id,product_id=prod_id.product_id).first()
    db.session.delete(car)
    db.session.commit()
    return redirect(url_for('cart'))

@app.route('/place_order',methods=['POST'])
@login_required
def place_order():
    order=Order(user_id=current_user.id)
    db.session.add(order)
    db.session.flush()
    cart=Cart.query.filter_by(user_id=current_user.id).all()
    for i in cart:
        order_items=OrderItem(order_id=order.id,product_id=i.product_id,quantity=i.quantity)
        prod=Product.query.filter_by(product_id=i.product_id).first()
        prod.quantity-=i.quantity
        db.session.add(prod)
        db.session.add(order_items)
        db.session.delete(i)
    db.session.commit()
    return render_template('order_placed.html')

@app.route('/logout',methods=['GET'])
@login_required
def logout():
    logout_user()
    return render_template('home.html')

if __name__=='__main__':
    app.run(debug=True)