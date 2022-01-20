"""
┌───────────────────────────────────────────────────────┐
│ Simple control interface for Tektronix AFG3000 series │
└───────────────────────────────────────────────────────┘

 Florian Dupeyron
 October 2021
"""

import usbtmc
import logging

class AFG3000_Interface:
    def __init__( self, vendor_id=0x0699, product_id=0x0347 ):
        self.dev = usbtmc.Instrument(vendor_id, product_id)
        self.log = logging.getLogger("AFG3000 interface")

    # ┌────────────────────────────────────────┐
    # │ Utilities                              │
    # └────────────────────────────────────────┘

    def __channel_check(self, channel: int):
        if (channel < 1) or (channel > 2):
            raise ValueError(f"Invalid channel {channel}, must be 1 or 2")

    def __write(self, buf: str):
        self.log.debug(f"write: {buf}")
        self.dev.write(buf)

    # ┌────────────────────────────────────────┐
    # │ System commands                        │
    # └────────────────────────────────────────┘
    
    def identity(self):
        return self.dev.ask("*IDN?")


    # ┌────────────────────────────────────────┐
    # │ Source configuration                   │
    # └────────────────────────────────────────┘

    def freq_set(self, channel: int, freq: float):
        channel = int  (channel)
        freq    = float(freq)

        self.__channel_check(channel)
        self.__write(f"SOUR{channel}:FREQ {freq:E}")

    # ┌────────────────────────────────────────┐
    # │ Output state                           │
    # └────────────────────────────────────────┘

    def output_enable(self, channel: int, state: bool):
        channel = int (channel)
        state   = bool(state  )

        self.__channel_check(channel)

        self.__write(f"OUTP{channel} {'ON' if state else 'OFF'}")
