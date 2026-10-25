import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Party profiles keep only the party's own name; senators get the year their term ends; two new tables."""

    dependencies = [
        ('geo', '0012_alter_undernourishmentcountryyear_value'),
        ('politics', '0003_partyprofile_logo_on_dark'),
    ]

    operations = [
        # The English name goes, and the party's own name takes its place.
        migrations.RemoveField(model_name='partyprofile', name='name'),
        migrations.RenameField(model_name='partyprofile', old_name='name_original', new_name='name'),
        migrations.AlterField(
            model_name='partyprofile',
            name='name',
            field=models.CharField(help_text="The party's own name, in its country's language; party names are never translated.", max_length=200),
        ),
        # Every row is reloaded by the next ETL run; 0 only fills the column until then.
        migrations.AddField(
            model_name='senator',
            name='term_ends',
            field=models.PositiveSmallIntegerField(default=0, help_text="The year the seat's term ends, e.g. 2031: a senator sits for eight years."),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='deputy',
            name='party',
            field=models.CharField(help_text="The party's code in the source's data, e.g. PL; empty for none.", max_length=30),
        ),
        migrations.AlterField(
            model_name='senator',
            name='party',
            field=models.CharField(help_text="The party's code in the source's data, e.g. PL; empty for none.", max_length=30),
        ),
        migrations.AlterField(
            model_name='deputy',
            name='member_id',
            field=models.CharField(help_text="The source's own id for the member.", max_length=20),
        ),
        migrations.AlterField(
            model_name='senator',
            name='member_id',
            field=models.CharField(help_text="The source's own id for the member.", max_length=20),
        ),
        migrations.CreateModel(
            name='Elected',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('member_id', models.CharField(help_text="The source's own id for the member.", max_length=20)),
                ('name', models.CharField(max_length=200)),
                ('party', models.CharField(help_text="The party's code in the source's data, e.g. PL; empty for none.", max_length=30)),
                ('state', models.CharField(help_text='The state the member represents, e.g. SP.', max_length=2)),
                ('house', models.CharField(help_text='A key of politics.congress.HOUSES.', max_length=10)),
                ('elected_on', models.DateField()),
                ('country', models.ForeignKey(db_column='iso3', on_delete=django.db.models.deletion.CASCADE, related_name='+', to='geo.country')),
            ],
            options={
                'verbose_name_plural': 'elected',
                'db_table': 'pol_elected',
                'ordering': ['country', 'name'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PartyLeftRight',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.FloatField(help_text='The mean of the experts who placed the party.')),
                ('experts', models.PositiveIntegerField(help_text='How many experts placed it; for a merger, the fewest behind its parties.')),
                ('inferred_from', models.CharField(blank=True, help_text='For a party formed after the survey by a merger, the parties whose average it takes, e.g. PTB, Patriota.', max_length=100)),
                ('party', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='left_right', to='politics.partyprofile')),
            ],
            options={
                'db_table': 'pol_party_left_right',
                'ordering': ['score'],
            },
        ),
    ]
