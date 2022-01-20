"""
┌──────────────────────────────────────────────────────┐
│ Simple control interface for TTi QL335P power supply │
└──────────────────────────────────────────────────────┘

 Florian Dupeyron
 December 2021
"""

import logging
import io
import serial
import time
import re

import functools

class QL335P_Interface:
    __RE_VOLTAGE = re.compile(r"([0-9]+\.[0-9]+)V")
    __RE_CURRENT = re.compile(r"([0-9]+\.[0-9]+)A")

    def __init__(self, dev_path):
        self.log = logging.getLogger(f"QLP335P {dev_path}")

        self.dev               = serial.serial_for_url(dev_path, do_not_open=True)
        self.dev.baudrate      = 19200
        self.dev.bytesize      = serial.EIGHTBITS
        self.dev.parity        = serial.PARITY_NONE
        self.dev.stopbits      = serial.STOPBITS_ONE
        self.dev.rtscts        = False

        self.dev.timeout       = 10
        self.dev.write_timeout = 10

        # https://stackoverflow.com/questions/10222788/line-buffered-serial-input
        self.io                = io.TextIOWrapper(
            self.dev,
            encoding       = "ascii",
            newline        = None,
            line_buffering = False
        )
        self.io._CHUNK_SIZE= 1

    def __write(self, *cmds):
        # Append new line terminator to all commands
        txt = "".join( map(lambda x: f"{x}\r\n", cmds) )

        self.log.debug(f"TX: {txt!r}")
        self.io.write(txt)
        self.io.flush()

    def __read(self):
        rx = self.io.readline()
        self.log.debug(f"RX: {rx!r}")

        return rx.strip().split(" ")

    def open(self):
        self.dev.open()

    def close(self):
        self.dev.close()

    # ┌────────────────────────────────────────┐
    # │ Ask for address (useless)              │
    # └────────────────────────────────────────┘
    
    def addr_ask(self):
        self.__write("ADDRESS?")
        resp = self.__read()
        
        return int(resp)

    # ┌────────────────────────────────────────┐
    # │ Voltage control                        │
    # └────────────────────────────────────────┘

    def voltage_get(self):
        self.__write("V1?")
        return float(self.__read()[1])

    def voltage_set(self, voltage: float, verify: bool = True):
        self.log.debug(f"Set voltage to {voltage}, verify = {verify}")
        self.__write(f"V1 {voltage:.3f}")
        if verify: assert self.voltage_get() == voltage

    # ┌────────────────────────────────────────┐
    # │ Current control                        │
    # └────────────────────────────────────────┘
    def current_get(self):
        self.__write("I1?")
        return float(self.__read()[1])

    def current_set(self, current: float, verify: bool = True):
        self.log.debug(f"Set current to {current}, verify = {verify}")
        self.__write(f"I1 {current:.3f}")
        if verify: assert self.current_get() == current

    # ┌────────────────────────────────────────┐
    # │ Output control and status              │
    # └────────────────────────────────────────┘
    def output_voltage(self):
        self.__write(f"V1O?")
        resp = self.__read()[0] # Response is X.XXV
        mt   = self.__RE_VOLTAGE.match(resp)
        if not mt:
            raise ValueError(f"Failed parsing: response is {resp!r}")

        return float(mt.group(1))

    def output_current(self):
        self.__write(f"I1O?")
        resp = self.__read()[0] # Response is X.XXA
        mt   = self.__RE_CURRENT.match(resp)
        if not mt:
            raise ValueError(f"Failed parsing: response is {resp!r}")

        return float(mt.group(1))

    def output_enable(self, state: bool = True):
        """
        Output enable doesn't verify output status!
        You may want to check output_voltage() value against a specific range after
        some time (2-3s for example)
        """
        self.log.debug(f"Set output status to {state}")
        self.__write(f"OP1 {int(state)}")

