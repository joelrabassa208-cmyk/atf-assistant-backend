from alembic import context

from app.db.database import get_engine

# Las migraciones se escriben a mano (op.create_table, op.add_column...).
# La URL sale de DATABASE_URL vía app.config; no hace falta ponerla en alembic.ini.
target_metadata = None


def run_migrations_offline():
    from app.config import DATABASE_URL

    context.configure(url=DATABASE_URL, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    with get_engine().connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
