# Jupyter MicroPython Kernel

Jupyter kernel to interact with a MicroPython board over its REPL interface.

Also with capabilities to work through the WEBREPL (available on ESP8266 only), 
do Ctrl-C, transfer files and esptools flashing (useful for deployment).
See https://github.com/goatchurchprime/jupyter_micropython_developer_notebooks 
for examples.

## Installation

First install Jupyter: http://jupyter.org/install.html (the Python3 version).

Then install this module:

    pip3 install jupyter_micropython_kernel

Install the kernel into jupyter itself using the shell command:

    python -m mpy_kernel.install

This registers the kernel with Jupyter so it can be selected for use in notebooks

## Running

Now run Jupyter notebooks:

    jupyter notebook

In the notebook click the New notebook button in the upper right, you should see your
MicroPython kernel display name listed.  

The first cell will need to be something like:

    %connect <device> --baudrate=115200 --user='micro' --password='python' --wait=0

eg:

    %connect "USB-SERIAL CH340""
    
or something that matches the serial port that
you connect to your MicroPython/ESP8266 with.

The <port> <args> bit matches the arguments used for the `pyboard.py`:
            
    device can be serial port device or name

    device can start with "exec:"
       "Execute a process and emulate serial connection using its stdin/stdout."

    device can start with "execpty:"
        Execute a process which creates a PTY and prints slave PTY as
        first line of its output, and emulate serial connection using
        this PTY

    device can be an ip address for webrepl communication


You should now be able to execute MicroPython commands by running the cells.

There is a micropythondemo.ipynb file in the directory you could
look at with some of the features shown.

If a cell is taking too long to interrupt, it may respond 
to a "Kernel" -> "Interrupt" command. 

Alternatively hit Escape and then 'i' twice.

To do a soft reboot (when you need to clear out the modules and recover some memory) type:
    
    %reboot

Note: Restarting the kernel does not actually reboot the device.  
Also, pressing the reset button will probably mess things up, because 
this interface relies on the ctrl-A non-echoing paste mode to do its stuff.

You can list all the functions with:
    
    %lsmagic

Thanks to the built in `mprepl` support, when connected to the micropython board the local
working directory jupyter was run from will be available on the micropython board at the
directory `/remote/`

This allows you to copy files to and from micropython to your pc with ease.

A cell can be run in the local python environment instead of the remote kernel by starting a cell with:
    
    %local

This can be useful to work directly with local files for instance. Commands here will be run by the same
python as jupyter notebook, however they're run in an `exec` sandbox to ensure jupyter can't be compromised.

In %local cells, `IPython.display` objects can usually be passed to `print()` to be displayed in graphical
form like in a normal python jupyter notebook, eg:
    
    %local
    from IPython.display import Image
    img = Image(filename='test.png')
    print(img)


## Background

This Jupyter MicroPython Kernel was originally based on the amazing work done on https://github.com/goatchurchprime/jupyter_micropython_kernel.git

Their original custom device connection library has been replaced by pyboard and mprepl to take advantage of proven functionality implemented there. mprepl has since been extended substantially.  
The kernel has also been reworked to extend form the full ipython kernel, so local cells are fully-functional and we can use the ipython display mechanisms for output formatting.
