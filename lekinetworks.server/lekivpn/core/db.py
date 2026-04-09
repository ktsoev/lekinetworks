import os

import aiomysql

from lekivpn.core import config

pool = None


async def init_pool(user, password, db_name):
    global pool
    host = os.getenv("DATABASE_IP", config.DATABASE_IP)
    port = int(os.getenv("DATABASE_PORT", str(config.DATABASE_PORT)))
    pool = await aiomysql.create_pool(
        host=host,
        port=port,
        user=user,
        password=password,
        db=db_name,
        charset=config.DATABASE_CHARSET,
        autocommit=True,
    )

    if pool:
        print("✅ MySQL Pool is ready")


async def close_pool():
    global pool
    if pool:
        pool.close()
        await pool.wait_closed()
        print("✅ Pool closed")
