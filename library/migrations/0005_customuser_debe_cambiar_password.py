from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0004_auditlog_historiallectura_solicitudlibro_favorito_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='debe_cambiar_password',
            field=models.BooleanField(
                default=False,
                help_text='Si es True, el usuario deberá cambiar su contraseña al iniciar sesión.',
            ),
        ),
    ]
