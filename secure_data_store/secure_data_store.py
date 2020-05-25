# -*- coding: utf-8 -*-

"""Convenience methods for using GoCryptFS from the commandline"""

import subprocess as sp
from pathlib import Path
import string
import random
from collections import namedtuple
from shutil import chown, which
from platform import system
from os.path import expandvars

import toml

# Config data class
Config = namedtuple('Config', ['gocryptfs',
                               'gocryptfs_xray',
                               'passroot',
                               'groupname',
                               'passlength',
                               'dataroot',
                               'mountpoints',
                               'mount',
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

def get_path(s):
    return Path(expandvars(s)).expanduser().resolve(),

def read_config(configpath):
    """Read config from path"""
    try:
        configpath = get_path(configpath)
        raw = toml.load(configpath)
        if system() == 'Linux':
            raw['umount'] = which('fusermount')
            raw['umountopts'] = ['-u']
        elif system() == 'Darwin':
            raw['umount'] = which('umount')
            raw['umountopts'] = []
        else:
            raise ConfigError('Unknown system type')
        raw['mount'] = which('mount')
        result = Config(gocryptfs=get_path(raw['gocryptfs']),
                        gocryptfs_xray=get_path(raw['gocryptfs_xray']),
                        passroot=get_path(raw['passroot']),
                        groupname=raw['groupname'],
                        passlength=64,
                        dataroot=get_path(raw['dataroot']),
                        umount=get_path(raw['umount']),
                        mount=get_path(raw['mount']),
                        umountopts=raw['umountopts'],
                        mountpoints=[get_path(mnt) for mnt in raw['mountpoints']])
        return result
    except (TypeError, toml.TomlDecodeError, IOError) as err:
        raise ConfigError("Could not parse config file {}: {}".format(configpath, err))

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

def mounted(config):
    """Get active mounts"""
    exe = config.mount
    result = sp.run([exe], stdout=sp.PIPE, stderr=sp.PIPE, check=True)
    active = [ln.strip().decode('ascii').split(' ')
              for ln in result.stdout.split(b'\n')
              if ln.strip()]
    return {Path(mnt[0]): Path(mnt[2]) for mnt in active}

def find_mount(config):
    """Find first free mountpoint"""
    mounts = mounted(config).values()
    for mnt in config.mountpoints:
        if not mnt in mounts:
            return mnt
    return None

def check_mount(config, name):
    """Check if FS is already mounted"""
    container = datastore(config, name)
    mounts = mounted(config)
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
        raise GCFSError("Could not find GoCryptFS. Maybe load module?")
    try:
        exe, version = result.stdout.decode('ascii').split(';')[0].split(' ')[:2]
        version = version.split('-')[0]
        major, minor, tiny = map(int, version[1:].split('.'))
    except:
        raise GCFSError("GoCryptFS could not determine GoCryptFS version, executable is {}, version {}".format(gcfs, version))
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
    try:
        gcfs = config.gocryptfs
        result = sp.run([gcfs, '-passfile', passfile, '-init', container],
                        check=True,
                        stdout=sp.DEVNULL)
        print("Created container in", container)
    except sp.CalledProcessError:
        raise GCFSError("Could not create container.")
    try:
        xray = config.gocryptfs_xray
        proc = sp.run('cat {} | {} -dumpmasterkey {}'.format(passfile, xray,  container / 'gocryptfs.conf'),
                      check=True,
                      shell=True,
                      stdout=sp.PIPE)
        mkey = proc.stdout
        print("This is your master key:", mkey.decode('ascii').strip())
    except Exception as e:
        print("Could not extract master key, you can still use the container, but no recovery possible.")

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
