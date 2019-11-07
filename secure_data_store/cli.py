# -*- coding: utf-8 -*-
"""Console script for secure_data_store."""
import click
import secure_data_store as sds

CONFIG='~/.sdsrc'

@click.group()
def main():
    """Wrapper for GoCryptFS"""

@main.command()
@click.argument('name')
@click.option('--config', help='Path to config file', default='~/.sdsrc')
def create(name, config=None):
    """Create a new secure data container NAME."""
    try:
        config = sds.read_config(config)
        sds.create(config, name)
    except (sds.ContainerError, sds.GCFSError, FileExistsError, sds.ConfigError) as err:
        print(err)

@main.command()
@click.argument('name')
@click.option('--config', help='Path to config file', default='~/.sdsrc')
def open(name, config=None):
    """Open an existing secure data container NAME.

    Will print path to the opened, clear-text container."""
    try:
        config = sds.read_config(config)
        sds.mount(config, name)
    except (sds.ContainerError, sds.GCFSError, sds.ConfigError, sds.MountError) as err:
        print(err)

@main.command()
@click.argument('name')
@click.option('--config', help='Path to config file', default='~/.sdsrc')
def close(name, config=None):
    """Close an opend data container NAME."""
    try:
        config = sds.read_config(config)
        sds.unmount(config, name)
    except (sds.ContainerError, sds.GCFSError, sds.ConfigError) as err:
        print(err)

main()
