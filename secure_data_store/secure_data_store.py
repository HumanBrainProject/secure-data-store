# -*- coding: utf-8 -*-

"""Convenience methods for using GoCryptFS from the commandline"""

import subprocess as sp
from pathlib import Path
import string
import random
from collections import namedtuple
import toml
from shutil import chown

# Config data class
Config = namedtuple('Config', ['gocryptfs',
                               'passroot',
                               'groupname',
                               'passlength',
                               'dataroot',
                               'mountpoints',
                               'umount',
                               'umountopts',])

# Exceptions
class ContainerError(Exception):
    """Container"""

class MountError(Exception):
    """Mountpoints"""

class GCFSError(Exception):
    """GoCryptFS"""

class ConfigError(Exception):
    """Configuration"""

# Utilities
def datastore(config, name):
    """Get container name"""
    return config.dataroot / name / 'FS'

def passstore(config, name):
    """Get password file"""
    return config.passroot / name

def read_config(configpath):
    """Read config from path"""
    try:
        configpath = Path(configpath).expanduser().resolve()
        raw = toml.load(configpath)
        result = Config(gocryptfs=Path(raw['gocryptfs']).resolve(),
                        passroot=Path(raw['passroot']).expanduser().resolve(),
                        groupname=raw['groupname'],
                        passlength=raw['passlength'],
                        dataroot=Path(raw['dataroot']).expanduser().resolve(),
                        umount=Path(ra=['umount']).resolve(),
                        umountopts=raw['umountopts'],
                        mountpoints=[Path(mnt).resolve() for mnt in raw['mountpoints']])
        return result
    except (TypeError, toml.TomlDecodeError, IOError) as err:
        raise ConfigError("Could not parse config: {}".format(err))

def set_password(config, name):
    """Store random password to disk"""
    passfile = passstore(config, name)
    chars = string.ascii_letters + string.digits
    length = config.passlength
    password = ''.join(random.choice(chars) for i in range(length))
    with open(passfile, 'w') as fd:
        fd.write(password)
    passfile.chmod(0o440)

def get_password(config, name):
    """Read password"""
    passfile = config.passstore / name
    with open(passfile, 'r') as fd:
        return fd.read()

def mounted():
    """Get active mounts"""
    result = sp.run(['/sbin/mount'], stdout=sp.PIPE, stderr=sp.PIPE, check=True)
    active = [ln.strip().decode('ascii').split(' ')
              for ln in result.stdout.split(b'\n')
              if ln.strip()]
    return {Path(mnt[0]): Path(mnt[2]) for mnt in active}

def find_mount(config):
    """Find first free mountpoint"""
    mounts = mounted().values()
    for mnt in config.mountpoints:
        if not mnt in mounts:
            return mnt
    return None

def check_mount(config, name):
    """Check if FS is already mounted"""
    container = datastore(config, name)
    mounts = mounted()
    return mounts.get(container, None)

# UX
def setup(config):
    """Set up private area, check for GoCryptFS availability, ..."""
    # Set up working areas
    group = config.groupname
    for path in [config.dataroot, config.passroot]:
        for part in reversed(path.parents):
            if not part.exists():
                part.mkdir()
                part.chmod(0o770)
                chown(part, group=group)
        if not path.exists():
            path.mkdir()
            path.chmod(0o770)
            chown(path, group=group)

    gcfs = config.gocryptfs
    try:
        result = sp.run([gcfs, '-version'], stdout=sp.PIPE, check=True)
    except sp.CalledProcessError:
        raise GCFSError("Could not find GoCryptFS")
    exe, version = result.stdout.decode('ascii').split(';')[0].split(' ')[:2]
    major, minor, tiny = map(int, version[1:-1].split('.'))
    if exe != 'gocryptfs' or (major < 1 and minor < 7 and tiny < 1):
        raise GCFSError("GoCryptFS has insufficient version: {} {}".format(exe, version))

def create(config, name):
    """Create a new container"""
    setup(config)
    # Before anything else try to create the container
    # if this fails, someone else already started, so
    # this is effectively a lock! Note, that we do not
    # test existence here, which is not atomic!
    container = datastore(config, name)
    try:
        container.mkdir(parents=True)
        container.chmod(0o770)
    except FileExistsError:
        raise ContainerError("Container already present: {}".format(name))
    set_password(config, name)
    passfile = passstore(config, name)
    gcfs = config.gocryptfs
    try:
        result = sp.run([gcfs, '-passfile', passfile, '-init', container],
                        check=True,
                        stdout=sp.DEVNULL)
    except sp.CalledProcessError:
        raise GCFSError("Could not create container.")

def mount(config, name):
    """Open (mount) an existing container"""
    setup(config)
    container = datastore(config, name)
    passfile = passstore(config, name)
    if not (container.exists() and passfile.exists()):
        raise ContainerError("No such container: {}".format(name))
    previous = check_mount(config, name)
    if previous:
        mountpoint = previous
    else:
        mountpoint = find_mount(config)
        if not mountpoint:
            raise MountError("No available mountpoints.")
        if not mountpoint.exists():
            try:
                mountpoint.mkdir(parents=True, exist_ok=True)
            except:
                raise MountError("No available mountpoints.")
        gcfs = config.gocryptfs
        try:
            sp.run([gcfs, '-passfile', passfile, container, mountpoint],
                   check=True,
                   stdout=sp.DEVNULL)
        except sp.CalledProcessError:
            raise GCFSError("Could not open Container.")
    print(mountpoint)
    return mountpoint

def unmount(config, name):
    """Close open container"""
    setup(config)
    previous = check_mount(config, name)
    umount = config.umount
    option = config.umountopts
    if previous:
        try:
            sp.run([umount, *option, previous], check=True)
        except sp.CalledProcessError:
            raise GCFSError("Could not close Container.")

def delete(config, name):
    """Remove a closed container"""
    setup(config)
    container = datastore(config, name)
    passfile = passstore(config, name)
    if not (container.exists() and passfile.exists()):
        raise ContainerError("No such container: {}".format(name))
    previous = check_mount(config, name)
    if previous:
        raise ContainerError("Cannot remove mounted container.")
