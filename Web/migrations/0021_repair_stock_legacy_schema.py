from django.db import migrations


REPAIR_SQL = r'''
DO $$
BEGIN
    IF to_regclass('public."Web_stock"') IS NULL THEN
        RETURN;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='Web_stock' AND column_name='created_at'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='Web_stock' AND column_name='Fecha_de_creación'
    ) THEN
        ALTER TABLE "Web_stock" RENAME COLUMN "created_at" TO "Fecha_de_creación";
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='Web_stock' AND column_name='updated_at'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='Web_stock' AND column_name='Ultima_actualización'
    ) THEN
        ALTER TABLE "Web_stock" RENAME COLUMN "updated_at" TO "Ultima_actualización";
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='Web_stock' AND column_name='user_id'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='Web_stock' AND column_name='Usario_id'
    ) THEN
        ALTER TABLE "Web_stock" RENAME COLUMN "user_id" TO "Usario_id";
    END IF;

    ALTER TABLE "Web_stock" ADD COLUMN IF NOT EXISTS "Matricula" varchar(16);
    ALTER TABLE "Web_stock" ADD COLUMN IF NOT EXISTS "VIN" varchar(17);
    ALTER TABLE "Web_stock" ADD COLUMN IF NOT EXISTS "Kilometros" integer;
    ALTER TABLE "Web_stock" ADD COLUMN IF NOT EXISTS "Versión" varchar(80);
    ALTER TABLE "Web_stock" ADD COLUMN IF NOT EXISTS "Carrocería" varchar(50);
    ALTER TABLE "Web_stock" ADD COLUMN IF NOT EXISTS "Puertas" smallint;
    ALTER TABLE "Web_stock" ADD COLUMN IF NOT EXISTS "Tracción" varchar(50);
    ALTER TABLE "Web_stock" ADD COLUMN IF NOT EXISTS "Fecha_matriculación" varchar(30);
    ALTER TABLE "Web_stock" ADD COLUMN IF NOT EXISTS "Foto" varchar(100);
END $$;
'''


def apply_repair_sql(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute(REPAIR_SQL)


class Migration(migrations.Migration):

    dependencies = [
        ('Web', '0020_repair_stock_columns'),
    ]

    operations = [
        migrations.RunPython(apply_repair_sql, migrations.RunPython.noop),
    ]
