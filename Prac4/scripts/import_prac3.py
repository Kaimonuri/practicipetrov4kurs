from pathlib import Path
import sqlite3, shutil, sys
source = Path(sys.argv[1])
target = Path(__file__).resolve().parents[1]
old = sqlite3.connect(source / 'db.sqlite3')
old.row_factory = sqlite3.Row
new = sqlite3.connect(target / 'dev.db')
new.execute('PRAGMA foreign_keys=ON')

def rows(table): return old.execute('SELECT * FROM ' + table).fetchall()
def cents(v): return round(float(v) * 100)
with new:
    for r in rows('shop_category'):
        new.execute('INSERT OR IGNORE INTO categories(id,name,slug) VALUES(?,?,?)', (r['id'],r['name'],r['slug']))
    for r in rows('shop_product'):
        image = Path(r['image']).name if r['image'] else ''
        if image:
            src = source / 'media' / r['image']
            if src.is_file(): shutil.copy2(src,target / 'public' / 'uploads' / image)
        new.execute('INSERT OR IGNORE INTO products(id,category_id,name,slug,description,price,stock,image,available) VALUES(?,?,?,?,?,?,?,?,?)', (r['id'],r['category_id'],r['name'],r['slug'],r['description'],cents(r['price']),r['stock'],image,int(r['available'])))
    for r in rows('auth_user'):
        if r['username'].lower() == 'lab16': continue
        profile = old.execute('SELECT * FROM accounts_profile WHERE user_id=?',(r['id'],)).fetchone()
        new.execute('INSERT OR IGNORE INTO users(username,password,full_name,phone,email,role) VALUES(?,?,?,?,?,?)',(r['username'],r['password'],profile['full_name'] if profile else '',profile['phone'] if profile else '',r['email'],'customer'))
    for r in rows('shop_coupon'):
        new.execute('INSERT OR IGNORE INTO coupons(id,code,discount_type,value,active,valid_from,valid_until) VALUES(?,?,?,?,?,?,?)',(r['id'],r['code'],r['discount_type'],float(r['value']),int(r['active']),r['valid_from'],r['valid_until']))
    for r in rows('shop_order'):
        username = old.execute('SELECT username FROM auth_user WHERE id=?',(r['user_id'],)).fetchone() if r['user_id'] else None
        user = new.execute('SELECT id FROM users WHERE username=?',(username['username'],)).fetchone() if username else None
        new.execute('INSERT OR IGNORE INTO orders(id,user_id,first_name,last_name,email,address,postal_code,city,delivery_method,delivery_date,payment_method,status,coupon_code,discount_amount,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(r['id'],user[0] if user else None,r['first_name'],r['last_name'],r['email'],r['address'],r['postal_code'],r['city'],r['delivery_method'],r['delivery_date'] or '2026-09-21',r['payment_method'],r['status'],r['coupon_code'],cents(r['discount_amount']),r['created']))
    for r in rows('shop_orderitem'):
        new.execute('INSERT OR IGNORE INTO order_items(id,order_id,product_id,price,quantity) VALUES(?,?,?,?,?)',(r['id'],r['order_id'],r['product_id'],cents(r['price']),r['quantity']))
    for r in rows('shop_review'):
        username = old.execute('SELECT username FROM auth_user WHERE id=?',(r['user_id'],)).fetchone()
        user = new.execute('SELECT id FROM users WHERE username=?',(username['username'],)).fetchone() if username else None
        if user: new.execute('INSERT OR IGNORE INTO reviews(product_id,user_id,rating,comment,created_at) VALUES(?,?,?,?,?)',(r['product_id'],user[0],r['rating'],r['comment'],r['created_at']))
    for r in rows('shop_wishlistitem'):
        username = old.execute('SELECT username FROM auth_user WHERE id=?',(r['user_id'],)).fetchone()
        user = new.execute('SELECT id FROM users WHERE username=?',(username['username'],)).fetchone() if username else None
        if user: new.execute('INSERT OR IGNORE INTO wishlist(user_id,product_id) VALUES(?,?)',(user[0],r['product_id']))
print('Imported catalog, accounts, orders, coupons, reviews and wishlist')
