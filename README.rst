Jupyter MicroPython Kernel
==========================

Jupyter kernel to interact with a MicroPython board over its REPL
interface.

Typically used with micropython boards over the USB / Serial interface,
however it should also work through the WEBREPL (available on ESP8266
only). Also includes a few advanced features for micorpython project
management; uploading files, running mpy-cross, flashing boards etc. See
https://github.com/goatchurchprime/jupyter_micropython_developer_notebooks
for examples.

Installation
------------

First install python 3.6 or above, ensure it’s available from your
command line.

Then install this module:

::

   pip3 install jupyter_micropython_kernel

Install the kernel into jupyter itself using the shell command:

::

   python -m mpy_kernel.install

This registers the kernel with Jupyter so it can be selected for use in
notebooks

Running
-------

Now run Jupyter notebooks:

::

   jupyter notebook

In the notebook click the New notebook button in the upper right, you
should see your MicroPython kernel display name listed.

The first cell will need to be something like:

::

   %connect <device> --baudrate=115200 --user='micro' --password='python' --wait=0

eg:

::

   %connect "USB-SERIAL CH340""

or something that matches the serial port that you connect to your
MicroPython/ESP8266 with.

The ``<device>`` and args matches the command used to run the standard
``pyboard.py``:

::

   device can be serial port device or name

   device can start with "exec:"
      "Execute a process and emulate serial connection using its stdin/stdout."

   device can start with "execpty:"
       Execute a process which creates a PTY and prints slave PTY as
       first line of its output, and emulate serial connection using
       this PTY

   device can be an ip address for webrepl communication

You should now be able to execute MicroPython commands by running the
cells.

There is a micropythondemo.ipynb file in the directory you could look at
with some of the features shown.

If a cell is taking too long to interrupt, it may respond to a “Kernel”
-> “Interrupt” command.

Alternatively hit Escape and then ‘i’ twice.

To do a soft reboot (when you need to clear out the modules and recover
some memory) type:

::

   %reboot

| Note: Restarting the kernel does not actually reboot the device.
| Also, pressing the reset button will probably mess things up, because
  this interface relies on the ctrl-A non-echoing paste mode to do its
  stuff.

You can list all the functions with:

::

   %lsmagic

Thanks to the built in ``mprepl`` support, when connected to the
micropython board the local working directory jupyter was run from will
be available on the micropython board at the directory ``/remote/``

This allows you to copy files to and from micropython to your pc with
ease.

::

   import os
   print(os.listdir("/remote/")

There is also an injected ``Util`` class with some extra file handling tools,
culminating with a ``sync(source, target, delete=True, include=None, exclude=None)``
which will copy all files/folders from source to target, optionally with include or exclude
regex filters.

::

   Util.sync("/remote/src", "/lib/", delete=True, include=".*\.mpy")

Commands can be run in the local python environment instead of the remote
kernel by starting a cell with:

::

   %local


This can be useful to work directly with local files, use ipywidgets, etc.
Commands here will be run by the standard ipython kernel.

In `%local` cells, a special global function ``remote()`` is available which
will pass a single string argument to the micropython board to be run, returning
any stdout from the command. Eg:

micropython cell

::

   from machine import Pin
   import neopixel
   pixels = neopixel.NeoPixel(Pin(4, Pin.OUT), 1)

   def set_colour(r, g, b):
       pixels[0] = (r, g, b)
       pixels.write()

   set_colour(0xff, 0xff, 0xff)

local cell

::

   %local
   import colorsys
   from ipywidgets import interact, Layout, FloatSlider

   def set_hue(hue):
       r, g, b = (int(p*255) for p in colorsys.hsv_to_rgb(hue, 1.0, 1.0))
       remote(f"set_colour({r}, {g}, {b})")

   slider = FloatSlider(min=0,max=1.0,step=0.01, layout=Layout(width='80%', height='80px'))
   interact(set_hue, hue=slider)

Background
----------

This Jupyter MicroPython Kernel was originally based on the amazing work
done on
https://github.com/goatchurchprime/jupyter_micropython_kernel.git

| Their original custom device connection library has been replaced by
  pyboard and mprepl to take advantage of proven functionality
  implemented there. mprepl has since been extended substantially.
| The kernel has also been reworked to extend form the full ipython
  kernel, so local cells are fully-functional and we can use the ipython
  display mechanisms for output formatting.
