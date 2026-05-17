from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class FundCategory(db.Model):
    __tablename__ = 'fund_categories'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    funds = db.relationship('Fund', backref='category', lazy='dynamic')


class Fund(db.Model):
    __tablename__ = 'funds'
    code = db.Column(db.String(6), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('fund_categories.id'))


class FundNav(db.Model):
    __tablename__ = 'fund_nav'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fund_code = db.Column(db.String(6), db.ForeignKey('funds.code'), nullable=False)
    nav_date = db.Column(db.Date, nullable=False)
    nav = db.Column(db.Numeric(10, 4), nullable=False)
    acc_nav = db.Column(db.Numeric(10, 4), nullable=False)
    __table_args__ = (db.UniqueConstraint('fund_code', 'nav_date'),)


class FundWeekly(db.Model):
    __tablename__ = 'fund_weekly'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fund_code = db.Column(db.String(6), db.ForeignKey('funds.code'), nullable=False)
    week_start = db.Column(db.Date, nullable=False)
    week_end = db.Column(db.Date, nullable=False)
    change_pct = db.Column(db.Numeric(8, 4), nullable=False)
    __table_args__ = (db.UniqueConstraint('fund_code', 'week_start'),)