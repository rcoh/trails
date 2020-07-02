from django.db import connection, transaction

cursor = connection.cursor()

import djclick as click


@click.command()
def vacuum():
    cursor.execute("vacuum")
    transaction.commit()
