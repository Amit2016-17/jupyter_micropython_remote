# Jupyter MicroPython Kernel

Jupyter kernel to interact with a MicroPython board over its REPL interface.

Also with capabilities to work through the WEBREPL (available on ESP8266 only), 
do Ctrl-C, transfer files and esptools flashing (useful for deployment).
See https://github.com/goatchurchprime/jupyter_micropython_developer_notebooks 
for examples.

## Installation

First install Jupyter: http://jupyter.org/install.html (the Python3 version).

Then install this module:

    pip3 install -e git+https://github.com/andrewleech/jupyter_micropython_kernel#egg=jupyter_micropython_kernel


Install the kernel into jupyter itself using the shell command:

    python -m jupyter_micropython_kernel.install

(This creates the small file ".local/share/jupyter/kernels/micropython/kernel.json" 
that jupyter uses to reference it's kernels

If you're interested, you can find out where your kernelspecs are stored by typing:

    jupyter kernelspec list


## Running

Now run Jupyter notebooks:

    jupyter notebook

In the notebook click the New notebook button in the upper right, you should see your
MicroPython kernel display name listed.  

The first cell will need to be something like:

    %connect <device> <args>

eg:

    %connect "USB-SERIAL CH340""
    
or something that matches the serial port that
you connect to your MicroPython/ESP8266 with.

The <port> <args> bit matches the arguments used for the `pyboard.py`:

    <device> --baudrate=115200 --user='micro' --password='python' --wait=0
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

Their original custom device connection library has been replaced by pyboard and mprepl to take advantage of functionality already implemented there.

This had been proposed as an enhancement to webrepl with the idea of a jupyter-like
interface to webrepl rather than their faithful emulation of a command line: https://github.com/micropython/webrepl/issues/32

My first implementation operated a spawned-process asyncronous sub-kernel that handled the serial connection. 
Ascync technology requires the whole program to work this way, or none of it.  
So my next iteration was going to do it using standard python threads to handle the blocking 
of the serial connections.  

However, further review proved that this was unnecessarily complex if you consider the whole 
kernel itself to be operating asyncronously with the front end notebook UI.  In particular, 
if the notebook can independently issue Ctrl-C KeyboardInterrupt signals into the kernel, there is no longer 
a need to worry about what happens when it hangs waiting for input from a serial connection.  

Other known projects that have implemented a Jupyter Micropython kernel are:
* https://github.com/adafruit/jupyter_micropython_kernel
* https://github.com/willingc/circuitpython_kernel
* https://github.com/TDAbboud/mpkernel
* https://github.com/takluyver/ubit_kernel
* https://github.com/jneines/nodemcu_kernel

In my defence, this is not an effect of not-invented-here syndrome; I did not discover most of these 
other projects until I had mostly written this one.  

I do think that for robustness it is important to expose the full processes 
of making connections and But for my purposes, this is more robust and contains debugging (of the 
serial connections) capability.

Other known projects to have made Jupyter-like or secondary interfaces to Micropython:
* https://github.com/nickzoic/mpy-webpad
* https://github.com/BetaRavener/uPyLoader

The general approach of all of these is to make use of the Ctrl-A 
paste mode with its Ctrl-D end of message signals.  
The problem with this mode is it was actually designed for 
automatic testing rather than supporting an interactive REPL (Read Execute Print Loop) system
(citation required), so there can be reliability issues to do with 
accidentally escaping from this mode or not being able to detect the state 
of being in it.  

For example, you can't safely do a Ctrl-B to leave the paste mode and then a 
Ctrl-A to re-enter paste mode cleanly, because a Ctrl-B in the non-paste mode 
will reboot the device.  


