=================
Secure Data Store -- Convenience around GoCryptFS
=================

This project wraps GoCryptFS into an easily accessible CLI interface aimed at
data storage encrypted at-rest for scientific use. Passwords are stored inside a
file that is readable by a UNIX group specified at creation of the filesystem.

Usage example:

.. code:: bash

   # Create filesystem, at first use, this will also setup the tool's workspace.
   # Data inside a filesystem is encrypted, unless mounted as below.
   # Each container has a random password, stored in a directory only readable
   # by your UNIX group
   sds create my-container
   # Open filesystem (mount) at one of a list of predefined locations.
   # Subsequent open operations will return the same mountpoint.
   sds open my-container
     /mnt/sds/00
   # Use /mnt/sds as a normal un-encrypted filesystem
   # ...
   # Unmount filesystem
   sds close my-container


All configuration is handled via a single file (defaults to `$HOME/.sdsrc`) in
TOML syntax. Example

.. code:: bash

  # User configuration ###########################################################
  # This can -- and should -- be changed by users

  # Unix group associated with your project
  groupname = "******"
  # Path to your encrypted data sets
  dataroot  = "/gpfs/project/sds/containers"
  # Path to password files
  # !!! Must reside in a different filesystem than `dataroot`
  # !!! Ensure that the path upto `passroot` has rxw permision for your group
  passroot  = "~groupleader/.sds/passfiles"

  # Site configuration ###########################################################
  # Site specific configuration, do not change!

  # Length of random password
  passlength  = 64
  # Path to gocryptfs binary
  gocryptfs   = "/path/to/gocryptfs"
  # Which umount to use
  umount      = "/user/bin/fusermount"
  # Options, if any, to pass
  umountopts  = ['-u']
  # List of available mountpoints
  mountpoints = ["/tmp/sds/00", "/tmp/sds/01", "/tmp/sds/02"]
  # ##############################################################################

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
