import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URI',
        'mysql+pymysql://root:root@localhost:3306/fund?charset=utf8mb4'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 3600
    CRAWLER_INTERVAL_SECONDS = 0.5
    SCHEDULER_API_ENABLED = True