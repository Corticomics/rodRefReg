from migrations.migrate_settings import migrate_settings
import click

@click.command()
@click.option('--force', is_flag=True, help='Force migration even if already migrated')
def migrate_settings_command(force):
    """Migrate settings from JSON to database"""
    try:
        migrate_settings(force=force)
        click.echo("Settings migration completed successfully")
    except Exception as e:
        click.echo(f"Error during migration: {e}", err=True)
        raise click.Abort() 