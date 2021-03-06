=================================================
Secure Data Store -- Convenience around GoCryptFS
=================================================

This project wraps GoCryptFS into an easily accessible CLI interface aimed at
data storage encrypted at-rest for scientific use. Passwords are stored inside a
file that is readable by a UNIX group specified at creation of the filesystem.

Installation
------------
.. code:: bash
   # Have go > 1.11 in your PATH (from https://github.com/rfjakob/gocryptfs)
   go get -d github.com/rfjakob/gocryptfs
   cd $(go env GOPATH)/src/github.com/rfjakob/gocryptfs
   ./build.bash	  
   # Create virtual environment
   python -mvenv sds
   # Enter virtual environment
   source sds/bin/activate
   # Install package
   pip install git+http://github.com/HumanBrainProject/secure-data-store#egg=secure-data-store
   # Leave virtual environment
   deactivate

Usage
-----
.. code:: bash

   # Assuming you run on HPC systems, bring Python and GoCryptFS into scope
   # This is for Piz Daint
   module load cray-python/3.6.5.7 gocryptfs
   # Enter virtual environment
   source sds/bin/activate
   # Create filesystem, at first use, this will also setup the tool's workspace.
   # Data inside a filesystem is encrypted, unless mounted as below.
   # Each container has a random password, stored in a directory only readable
   # by your UNIX group. This will also print the masterkey, which you should
   # stored (physically) in a secure location.
   sds create my-container
   # Open filesystem (mount) at one of a list of predefined locations.
   # Subsequent open operations will return the same mountpoint.
   sds open my-container
     /mnt/sds/00
   # Use /mnt/sds as a normal un-encrypted filesystem
   # ...
   # Unmount filesystem
   sds close my-container
   # Leave virtual environment
   deactivate

Configuration
-------------
All configuration is handled via a single file (defaults to `$HOME/.sdsrc`) in
TOML syntax.

.. code:: bash

  # User configuration ###########################################################
  # This can -- and should -- be changed by users

  # GocryptFS binaries, see section on installation.
  gocryptfs      = "~/go/src/github.com/rfjakob/gocryptfs/gocryptfs"
  gocryptfs_xray = "~/go/src/github.com/rfjakob/gocryptfs/gocryptfs-xray/gocryptfs-xray"

  # Unix group associated with your project
  groupname = "******"
  # Path to your encrypted data sets
  dataroot  = "/gpfs/project/sds/containers"
  # Path to password files
  # This should be identical for all members of a group.
  # Ensure that the path is accessible (rx) for all members and writeable for
  # all member intended to create datasets (rxw).
  passroot  = "~groupleader/.sds/passfiles"
  # List of mountpoints to use
  # Piz Daint
  #  * must be under `/tmp`
  #  * add as many as you like
  mountpoints = ["/tmp/sds/00", "/tmp/sds/01", "/tmp/sds/02"]
  # ##############################################################################

Please ensure that `dataroot` and `passroot` reside on different filesystems for
minimal isolation.

Acknowledgements
----------------

This open source software code was developed in part or in whole in the Human Brain Project, funded from the European Union’s Horizon 2020 Framework Programme for Research and Innovation under the Specific Grant Agreement No. 720270 (Human Brain Project SGA1) and No. 785907 (Human Brain Project SGA2).

The python package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
