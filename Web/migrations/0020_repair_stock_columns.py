from django.db import migrations


def ensure_stock_columns(apps, schema_editor):
    Stock = apps.get_model('Web', 'Stock')
    table_name = Stock._meta.db_table

    with schema_editor.connection.cursor() as cursor:
        existing_columns = {
            column.name for column in schema_editor.connection.introspection.get_table_description(cursor, table_name)
        }

    for field_name in ['Matricula', 'VIN']:
        if field_name in existing_columns:
            continue
        field = Stock._meta.get_field(field_name)
        field.set_attributes_from_name(field_name)
        schema_editor.add_field(Stock, field)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('Web', '0019_favorite'),
    ]

    operations = [
        migrations.RunPython(ensure_stock_columns, noop_reverse),
    ]
