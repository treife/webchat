from argon2 import PasswordHasher

from app.db import SessionLocal, engine
from app import models


def init():
    models.Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        if db.query(models.Config).count() > 0:
            print('The database has already been populated. No work is needed.')
            return

        ph = PasswordHasher()
        master_passwd_hash = ph.hash('changeme')
        db.add(models.Config(key='master_password', value=master_passwd_hash))
        db.add(models.Channel(name='general'))

        db.commit()


if __name__ == "__main__":
    init()
