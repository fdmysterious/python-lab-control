"""
┌─────────────────────────────────────────────────┐
│ Simple control interface for Tektronix TDS2024B │
└─────────────────────────────────────────────────┘

 Please keep in mind this is dumb and unoptimized.

 Florian Dupeyron
 December 2021
"""

import usbtmc
import logging
import numpy as np
import re
import time

from PIL         import Image
from io          import BytesIO

from enum        import Enum
from dataclasses import dataclass, field

from threading   import Event

# ┌────────────────────────────────────────┐
# │ Measurement subsystem                  │
# └────────────────────────────────────────┘
class TDS2024B_Measurement_Source(Enum):
    CH1       = "CH1"
    CH2       = "CH2"
    CH3       = "CH3"
    CH4       = "CH4"
    MATH      = "MATH"


    @classmethod
    def channel(cls, i):
        """
        Returns the corresponding source according to
        the index i
        """

        __chan_idx = {
            0: cls.CH1,
            1: cls.CH2,
            2: cls.CH3,
            3: cls.CH4,
        }

        return __chan_idx[i]

class TDS2024B_Measurement_Type(Enum):
    Disable   = "NONE"
    Cycle_RMS = "CRMS"

    Fall      = "FALL"   # Fall time between 90% and 10% of the first falling edge of the waveform
    Rise      = "RISE"   # Rise time between 10% and 90% of the first rising  edge of the waveform

    Maximum   = "MAXI"
    Minimum   = "MINI"

    Period    = "PERIOD" # Signal period

    NWidth    = "NWIDTH" # Negative pulse width
    PWidth    = "PWIDTH" # Positive pulse width

    Peak2Peak = "PK2PK"

class TDS2024B_Measurement_Unit(Enum):
    Volts     = "V"
    Seconds   = "s"
    Hertz     = "Hz"

class TDS2024B_Measurement:
    def __init__(
        self,
        dev,
        id_,

        source  = None,
        type_   = None
    ):
        self.log  = logging.getLogger(f"TDS2024B Measure {id_}")
        self.dev  = dev

        self.id     = id_
        self.source = source
        self.type   = type_

    # ┌────────────────────────────────────────┐
    # │ Read/Write resource                    │
    # └────────────────────────────────────────┘

    def settings_read(self):
        self.log.debug("Read settings")

        # Read Source
        self.source = TDS2024B_Measurement_Source(
            self.dev.ask(f"MEASU:{self.id}:SOURCE?").split(" ")[1]
        )

        # Read Type
        self.type   = TDS2024B_Measurement_Type(
            self.dev.ask(f"MEASU:{self.id}:TYPE?").split(" ")[1]
        )
    

    def settings_write(self):
        self.log.debug("Write settings")

        # Write source
        self.dev.write(f"MEASU:{self.id}:SOURCE {self.source.value}")
        
        # Write type
        self.dev.write(f"MEASU:{self.id}:TYPE {self.type.value}")

    # ┌────────────────────────────────────────┐
    # │ Properties                             │
    # └────────────────────────────────────────┘
    
    @property
    def unit(self):
        return TDS2024B_Measurement_Unit(
            self.dev.ask(f"MEASU:{self.id}:UNIT?").split(" ")[1].replace("\"","") # Remove quotes
        )

    # ┌────────────────────────────────────────┐
    # │ Value read                             │
    # └────────────────────────────────────────┘

    def value(self):
        return float(self.dev.ask(f"MEASU:{self.id}:VALUE?").split(" ")[1])

# ┌────────────────────────────────────────┐
# │ Channel parmaeters                     │
# └────────────────────────────────────────┘
class TDS2024B_Channel_Coupling(Enum):
    AC  = "AC"
    DC  = "DC"
    GND = "GND"

@dataclass
class TDS2024B_Channel_Parameters:
    dev:  usbtmc.Instrument                    # USBTMC handle
    chan: int                                  # Channel number (0-3)
    
    bw_filter: bool                     = None # Enable bandwidth filter? (20MHz or 200MHz)
    coupling: TDS2024B_Channel_Coupling = None # Channel coupling mode

    invert: bool                        = None # Enable inversion?
    position: float                     = None # Vertical position
    attenuation: int                    = None # Probe attenuation factor (x1, x10, x20, x50, x100, x500, x1000)

    scale: float                        = None # V/div scale

    on: bool                            = None # Channel is enabled?

    log: logging.Logger = field(init=False)

    def __post_init__(self):
        self.log = logging.getLogger(f"TDS2024B Channel CH{self.chan}")

    def settings_read(self):
        self.log.debug("Read settings")

        self.bw_filter   = True if self.dev.ask(f"CH{self.chan}:BANDWIDTH?").split(" ")[1] == "ON" else False
        self.coupling    = TDS2024B_Channel_Coupling( self.dev.ask(f"CH{self.chan}:COUPLING?").split(" ")[1] )
        self.invert      = True if self.dev.ask(f"CH{self.chan}:INVERT?").split(" ")[1] == "ON" else False
        self.position    = float(self.dev.ask(f"CH{self.chan}:POS?").split(" ")[1])
        self.attenuation = float(self.dev.ask(f"CH{self.chan}:PROBE?").split(" ")[1])
        self.scale       = float(self.dev.ask(f"CH{self.chan}:SCALE?").split(" ")[1])

    def settings_write(self):
        self.log.debug("Write settings")

        if self.bw_filter   is not None: self.dev.write(f"CH{self.chan}:BANDWIDTH %s" % ("ON" if self.bw_filter else "OFF"))
        if self.coupling    is not None: self.dev.write(f"CH{self.chan}:COUPLING {self.coupling.value}")
        if self.invert      is not None: self.dev.write(f"CH{self.chan}:INVERT %s" % ("ON" if self.invert else "OFF"))
        if self.position    is not None: self.dev.write(f"CH{self.chan}:POS {self.position:E}")
        if self.attenuation is not None: self.dev.write(f"CH{self.chan}:PROBE {self.attenuation:E}")
        if self.scale       is not None: self.dev.write(f"CH{self.chan}:SCALE {self.scale:E}")

    # ──────────── Enable/disable ──────────── #
    def enable(self):
        self.log.info("--> Enable channel")
        self.dev.write(f"SELECT:CH{self.chan} ON")

    def disable(self):
        self.log.info("--> Disable channel")
        self.dev.write(f"SELECT:CH{self.chan} OFF")

# ┌────────────────────────────────────────┐
# │ Horizontal parameters                  │
# └────────────────────────────────────────┘

@dataclass
class TDS2024B_Horizontal_Parameters:
    dev: usbtmc.Instrument
    id: str             # Name of the horizontal scale

    pos: float   = None # Horizontal position
    scale: float = None # s/div scale

    log: logging.Logger = field(init=False)

    def __post_init__(self):
        self.log = logging.getLogger(f"TDS2024B horizontal {self.id} scale")

    def settings_read(self):
        self.log.debug("Read settings")

        self.pos   = float( self.dev.ask(f"HOR:{self.id}:POS?").split(" ")[1]   )
        self.scale = float( self.dev.ask(f"HOR:{self.id}:SCALE?").split(" ")[1] )

    def settings_write(self):
        self.log.debug("Write settings")

        if self.pos   is not None: self.dev.write(f"HOR:{self.id}:POS {self.pos:E}"    )
        if self.scale is not None: self.dev.write(f"HOR:{self.id}:SCALE {self.scale:E}")
    
# ┌────────────────────────────────────────┐
# │ Trigger parameters                     │
# └────────────────────────────────────────┘

class TDS2024B_Trigger_Type(Enum):
    Edge    = "EDGE"
    Video   = "VID"
    Pulse   = "PUL"

class TDS2024B_Trigger_Mode(Enum):
    Auto    = "AUTO"
    Normal  = "NORMAL"

class TDS2024B_Trigger_State(Enum):
    Armed   = "ARMED"
    Ready   = "READY"
    Trigger = "TRIGGER"
    Auto    = "AUTO"
    Save    = "SAVE"
    Scan    = "SCAN"
    
# ────────── Edge trigger defs. ────────── #

class TDS2024B_Trigger_Edge_Coupling(Enum):
    AC           = "AC"
    DC           = "DC"
    HF_Reject    = "HFREJ"
    LF_Reject    = "LFREJ"
    Noise_Reject = "NOISEREJ"

class TDS2024B_Trigger_Edge_Slope(Enum):
    Fall = "FALL"
    Rise = "RISE"

class TDS2024B_Trigger_Edge_Source(Enum):
    CH1   = "CH1"
    CH2   = "CH2"
    CH3   = "CH3"
    CH4   = "CH4"

    Ext   = "EXT"    # Ext. trigger
    Ext5  = "EXT5"   # Ext. trigger, 5x  attenuation
    Ext10 = "EXT10"  # Ext. trigger, 10x attenuation

    Line  = "LINE"   # Power line

@dataclass
class TDS2024B_Trigger_Parameters:
    dev: usbtmc.Instrument
    id : str

    # ──────────── Global settings ─────────── #

    type: TDS2024B_Trigger_Type = None
    mode: TDS2024B_Trigger_Mode = None
    level: float                = None


    # ────── Settings for video trigger ────── #

    # NOT IMPLEMENTED


    # ─────── Settings for edge trigger ────── #

    edge_coupling: TDS2024B_Trigger_Edge_Coupling = None
    edge_slope:    TDS2024B_Trigger_Edge_Slope    = None
    edge_source:   TDS2024B_Trigger_Edge_Source   = None


    # ────── Settings for pulse trigger ────── #

    # NOT IMPLEMENTED

    # ───────────────── Misc. ──────────────── #

    log: logging.Logger = field(init=False)

    def __post_init__(self):
        self.log = logging.getLogger(f"TDS2024B Trigger {self.id}")

    # ────────────── Properties ────────────── #
    def frequency(self):
        return float( self.dev.ask(f"TRIG:{self.id}:FREQ?").split(" ")[1] )

    def state(self):
        return TDS2024B_Trigger_State(self.dev.ask(f"TRIG:{self.id}:STATE"))

    # ────────── Settings read/write ───────── #
    def settings_read(self):
        self.log.debug("Read settings")

        # Main settings
        self.type          = TDS2024B_Trigger_Type(self.dev.ask(f"TRIG:{self.id}:TYPE?").split(" ")[1])
        self.mode          = TDS2024B_Trigger_Mode(self.dev.ask(f"TRIG:{self.id}:MODE?").split(" ")[1])
        self.level         = float(self.dev.ask(f"TRIG:{self.id}:LEVEL?").split(" ")[1])

        # Edge settings
        self.edge_coupling = TDS2024B_Trigger_Edge_Coupling(self.dev.ask(f"TRIG:{self.id}:EDGE:COUPLING?").split(" ")[1])
        self.edge_slope    = TDS2024B_Trigger_Edge_Slope   (self.dev.ask(f"TRIG:{self.id}:EDGE:SLOPE?").split(" ")[1])
        self.edge_source   = TDS2024B_Trigger_Edge_Source  (self.dev.ask(f"TRIG:{self.id}:EDGE:SOURCE?").split(" ")[1])

    def settings_write(self):
        self.log.debug("Write settings")

        # Main settings
        if self.type  is not None: self.dev.write(f"TRIG:{self.id}:TYPE {self.type.value}")
        if self.mode  is not None: self.dev.write(f"TRIG:{self.id}:MODE {self.mode.value}")
        if self.level is not None: self.dev.write(f"TRIG:{self.id}:LEVEL {self.level:G}")
        
        # Edge settings
        if self.edge_coupling is not None: self.dev.write(f"TRIG:{self.id}:EDGE:COUPLING {self.edge_coupling.value}")
        if self.edge_slope    is not None: self.dev.write(f"TRIG:{self.id}:EDGE:SLOPE {self.edge_slope.value}")
        if self.edge_source   is not None: self.dev.write(f"TRIG:{self.id}:EDGE:SOURCE {self.edge_source.value}")

# ┌────────────────────────────────────────┐
# │ Interface class                        │
# └────────────────────────────────────────┘

class TDS2024B_Interface:
    def __init__(self, vendor_id=0x699, product_id=0x036A):
        self.dev = usbtmc.Instrument(vendor_id, product_id)
        self.synchronized = Event()
        self.synchronized.clear()

        # Change the default timeout
        self.dev.timeout = 10 

        self.log = logging.getLogger("TDS2024B Interface")

        # Trigger settings
        self.trigger          = TDS2024B_Trigger_Parameters(self.dev, "MAIN")

        # Horizontal handles
        self.horizontal_main  = TDS2024B_Horizontal_Parameters(self.dev, "MAIN" )
        self.horizontal_delay = TDS2024B_Horizontal_Parameters(self.dev, "DELAY")

        # Channel handles
        self.ch      = [TDS2024B_Channel_Parameters(self.dev, i) for i in range(1,5)]

        # Measurements handles
        self.mes     = [TDS2024B_Measurement(self.dev, f"MEAS{i}") for i in range(1,6)]

        # Immediate measure is the same as classic measures,
        # except it is not displayed on the scope, and thus is
        # faster to run
        self.mes_imm = TDS2024B_Measurement(self.dev, "IMM")

    def state_sync(self):
        # Init resources status
        self.log.info("Synchronize resource status")

        self.trigger.settings_read()
        self.horizontal_main.settings_read()
        self.horizontal_delay.settings_read()

        for c   in self.ch:  c.settings_read()
        for mes in self.mes: mes.settings_read()
        self.mes_imm.settings_read()

        self.synchronized.set()

    # ┌────────────────────────────────────────┐
    # │ System commands                        │
    # └────────────────────────────────────────┘
    
    def identity(self):
        return self.dev.ask("*IDN?")

    # ┌────────────────────────────────────────┐
    # │ Hardcopy                               │
    # └────────────────────────────────────────┘
    
    def capture(self):
        """
        Captures the screen. Returns a Pillow image.
        """

        self.log.info("Capture image from scope")

        # Sets the port to USB and the format to BMP
        self.dev.write("HARDC:PORT USB;FORMAT BMP")

        # Reads the hardcopy image
        self.dev.write("HARDC START")
        img_bytes = self.dev.read_raw()
        img_handle = BytesIO(img_bytes)
        img        = Image.open(img_handle)

        img.load() # Load the data from the buffer

        # Do some palette transformation to turn into DARK MODE >:)
        img_palette = np.resize(img.getpalette(), (256,3))
        
        # --> Change background color (index 80)
        img_palette[80] = np.array([17,16,20])

        # --> Outer background (index 81)
        img_palette[81] = np.array([50, 47, 59])

        # --> Text (index 95)
        img_palette[95] = np.array([255,255,255])

        # --> Put palette
        self.log.info(len(img_palette.flatten()))
        img.putpalette(img_palette.flatten().tolist(), rawmode="RGB")

        return img # Return the loaded BMP image
