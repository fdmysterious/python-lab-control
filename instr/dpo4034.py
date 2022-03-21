"""
┌───────────────────────────────────────────────────┐
│ Simple control interface for DPO4034 oscilloscope │
└───────────────────────────────────────────────────┘

 Florian Dupeyron
 March 2022
"""

# Enums also inherits from 'str' class: see https://stackoverflow.com/questions/24481852/serialising-an-enum-member-to-json
# This allows the objects to be serializable

import usbtmc
import logging
import numpy as np
import re
import time

from PIL         import Image
from io          import BytesIO

from enum        import Enum
from dataclasses import dataclass, field, InitVar, asdict

from threading   import Event

# ┌────────────────────────────────────────┐
# │ Measurement subsystem                  │
# └────────────────────────────────────────┘
class DPO4034_Measurement_Source(str, Enum):
    CH1       = "CH1"
    CH2       = "CH2"
    CH3       = "CH3"
    CH4       = "CH4"
    MATH      = "MATH"
    D0        = "D0"
    D1        = "D1"
    D2        = "D2"
    D3        = "D3"
    D4        = "D4"
    D5        = "D5"
    D6        = "D6"
    D7        = "D7"
    D8        = "D8"
    D9        = "D9"
    D10       = "D10"
    D11       = "D11"
    D12       = "D12"
    D13       = "D13"
    D14       = "D14"
    D15       = "D15"
    Histogram = "HIS"
    RF_Amp    = "RF_AMP"
    RF_Freq   = "RF_FREQ"
    RF_Phase  = "RF_PHASE"


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
{||||||||
|||||||||
||||||
||||||||
|SIGMA1|SIGMA2|SIGMA3|STDdev|WAVEFORMS}

class DPO4034_Measurement_Type(str, Enum):
    # TODO # Check returned names by oscilloscope

    Disable     = "NONE"

    Amplitude   = "AMP"       # Signal amplitude
    Area        = "AREA"      # Voltage over time → V/s
    Burst       = "BURST"     # Time of a signal burst
    Delay       = "DELAY"     # Measure the time between the middle reference (default = 50%) amplitude point of the source waveform and the destination waveform.
    Frequency   = "FREQ"
    Mean        = "MEAN"
    Period      = "PERIOD"    # Signal period
    Phase       = "PHA"       # Phase difference between two waveforms
    RMS         = "RMS"       # Signal RMS value

    Cycle_Area  = "CAREA"
    Cycle_Mean  = "CMEAN"
    Cycle_RMS   = "CRMS"

    Fall        = "FALL"      # Fall time between 90% and 10% of the first falling edge of the waveform
    Rise        = "RISE"      # Rise time between 10% and 90% of the first rising  edge of the waveform
    High        = "HIGH"      # Measures the high reference (100% level, sometimes called topline) of a waveform.
    Low         = "LOW"       # Measures the low reference (0% level, sometimes called Baseline) of a waveform

    Hits        = "HITS"      # Histogram hits: number of points in or on the histogram box
    Median      = "MEDIAN"    # Histogram median: middle point of the histogram box. Half of all acquired points within or on the histogram box are less than this value and half greater than this value.
    PeakHits    = "PEAKH"     # Number of points in the largest bin of the histogram
    Sigma1      = "SIGMA1"    # Percentage of points in the histogram that are within one standard deviation of the histogram mean
    Sigma2      = "SIGMA2"    # Percentage of points in the histogram that are within two standard deviations of the histogram mean
    Sigma3      = "SIGMA3"    # Percentage of points in the histogram that are within three standard deviations of the histogram mean
    STD_Dev     = "STDDEV"    # Standard deviation (RMS deviation) of all acquired points within or on the histogram box
    Waveforms   = "WAVEFORMS" # Number of waveforms used to calculate the histogram

    Maximum     = "MAXI"
    Minimum     = "MINI"

    PWidth      = "PWIDTH"    # Positive pulse width
    PEdgeCount  = "PEDGEC"    # Count of falling edges
    PDuty       = "PDUTY"     # Positive Duty Cycle → NDUTY = (NWidth/Period) * 100%
    POvershoot  = "POV"       # Positive Overshoot: NOvershoot = ((Low-Minimum)/Amplitude)*100%
    PPulseCount = "PPULSEC"   # Positive pulse count

    NWidth      = "NWIDTH"    # Negative pulse width
    NEdgeCount  = "NEDGEC"    # Count of falling edges
    NDuty       = "NDUTY"     # Negative Duty Cycle → NDUTY = (NWidth/Period) * 100%
    NOvershoot  = "NOV"       # Negative Overshoot: NOvershoot = ((Low-Minimum)/Amplitude)*100%
    NPulseCount = "NPULSEC"   # Negative pulse count

    Peak2Peak   = "PK2PK"

class DPO4034_Measurement_Unit(str, Enum):
    Indeterminate                      = "?"
    Unknown                            = "unk"    

    Percent                            = "%"
    Inverse_Hertz                      = "/Hz"
    Amperes                            = "A"
    Amperes_Per_Ampere                 = "A/A"
    Amperes_Per_Volt                   = "A/V"
    Amperes_Per_Decibel                = "A/dB"
    Amperes_Per_Second                 = "A/S"
    Amperes_Squared                    = "AA"
    Ampere_Watts                       = "AW"
    Ampere_Decibels                    = "AdB"    
    Ampere_Seconds                     = "As"     
    Bytes                              = "B"      
    Hertz                              = "Hz"     
    Institute_of_radio_engineers_units = "IRE"    
    Samples_Per_Second                 = "S/s"    
    Volts                              = "V"      
    Volts_Per_Ampere                   = "V/A"    
    Volts_Per_volt                     = "V/V"    
    Volts_Per_watt                     = "V/W"    
    Volts_Per_decibel                  = "V/dB"   
    Volts_Per_second                   = "V/s"    
    Volt_Amperes                       = "VA"     
    Volt_Amperes_Resistive             = "VAR"    
    Volts_Squared                      = "VV"     
    Volt_Watts                         = "VW"     
    Volts_Decibels                     = "VdB"    
    Volt_Seconds                       = "Vs"     
    Watts                              = "W"      
    Watts_Per_Ampere                   = "W/A"    
    Watts_Per_Volt                     = "W/V"    
    Watts_Per_watt                     = "W/W"    
    Watt_Per_Decibel                   = "W/dB"   
    Watts_Per_Second                   = "W/s"    
    Watt_Amperes                       = "WA"     
    Watt_Volts                         = "WV"     
    Watts_Squared                      = "WW"     
    Watt_Decibels                      = "WdB"    
    Waveforms                          = "Wfms"   
    Watt_Seconds                       = "Ws"     
    Decibels                           = "dB"     
    Decibels_Per_Ampere                = "dB/A"   
    Decibels_Per_Volt                  = "dB/V"   
    Decibels_Per_Watt                  = "dB/W"   
    Decibels_Per_Decibel               = "dB/dB"  
    Decibel_Amperes                    = "dBA"    
    Decibel_Volts                      = "dBV"    
    Decibel_Watts                      = "dBW"    
    decibels squared                   = "dBdB"   
    Days                               = "day"    
    Degrees                            = "degrees"
    Divisions                          = "div"    
    Edges                              = "edges"  
    Hits                               = "hits"   
    Hours                              = "hr"     
    Joules                             = "joules" 
    Minutes                            = "min"    
    Ohms                               = "ohms"   
    Percent                            = "percent"
    Pulses                             = "pulses" 
    Seconds                            = "s"      

@dataclass
class DPO4034_Measurement:
    dev:  InitVar[usbtmc.Instrument]           # USBTMC handle
    id:   InitVar[str]                         # Measurement id: not represented in settings

    source: DPO4034_Measurement_Source = None
    type:   DPO4034_Measurement_Type   = None

    def __post_init__(self, dev, id):
        self.dev = dev
        self.id  = id
        self.log = logging.getLogger(f"DPO4034 Measure {self.id}")

    # ┌────────────────────────────────────────┐
    # │ Update config from dict                │
    # └────────────────────────────────────────┘

    def settings_load(self, data):
        if data.get("source", None) is not None: self.source = DPO4034_Measurement_Source (data["source"])
        if data.get("type",   None) is not None: self.type   = DPO4034_Measurement_Type   (data["type"]  )


    # ┌────────────────────────────────────────┐
    # │ Read/Write resource                    │
    # └────────────────────────────────────────┘

    def settings_read(self):
        self.log.debug("Read settings")

        # Read Source
        self.source = DPO4034_Measurement_Source(
            self.dev.ask(f"MEASU:{self.id}:SOURCE?")
        )

        # Read Type
        self.type   = DPO4034_Measurement_Type(
            self.dev.ask(f"MEASU:{self.id}:TYPE?")
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
        return DPO4034_Measurement_Unit(
            self.dev.ask(f"MEASU:{self.id}:UNIT?").replace("\"","") # Remove quotes
        )

    # ┌────────────────────────────────────────┐
    # │ Value read                             │
    # └────────────────────────────────────────┘

    def value(self):
        return float(self.dev.ask(f"MEASU:{self.id}:VALUE?"))

# ┌────────────────────────────────────────┐
# │ Channel parmaeters                     │
# └────────────────────────────────────────┘
#class DPO4034_Channel_Coupling(str, Enum):
#    AC  = "AC"
#    DC  = "DC"
#    GND = "GND"
#
#@dataclass
#class DPO4034_Channel_Parameters:
#    dev:  InitVar[usbtmc.Instrument]           # USBTMC handle
#    chan: InitVar[int]                         # Channel number (0-3): not represented in dict data
#    
#    bw_filter: bool                     = None # Enable bandwidth filter? (20MHz or 200MHz)
#    coupling: DPO4034_Channel_Coupling = None # Channel coupling mode
#
#    invert: bool                        = None # Enable inversion?
#    position: float                     = None # Vertical position
#    attenuation: int                    = None # Probe attenuation factor (x1, x10, x20, x50, x100, x500, x1000)
#
#    scale: float                        = None # V/div scale
#
#    on: bool                            = None # Channel is enabled?
#
#    def __post_init__(self, dev, chan):
#        self.dev  = dev
#        self.chan = chan
#        self.log  = logging.getLogger(f"DPO4034 Channel CH{self.chan}")
#
#    # ┌────────────────────────────────────────┐
#    # │ Update config from dict                │
#    # └────────────────────────────────────────┘
#    
#    def settings_load(self, data):
#        if data.get("bw_filter"  , None) is not None: self.bw_filter   = bool(data["bw_filter"])
#        if data.get("coupling"   , None) is not None: self.coupling    = DPO4034_Channel_Coupling(data["coupling"])
#        if data.get("invert"     , None) is not None: self.invert      = bool(data["invert"])
#        if data.get("position"   , None) is not None: self.position    = float(data["position"])
#        if data.get("attenuation", None) is not None: self.attenuation = int(data["attenuation"])
#        if data.get("scale"      , None) is not None: self.scale       = float(data["scale"])
#        if data.get("on"         , None) is not None: self.on          = bool(data["on"])
#
#    # ┌────────────────────────────────────────┐
#    # │ Read / Write resource                  │
#    # └────────────────────────────────────────┘
#
#    def settings_read(self):
#        self.log.debug("Read settings")
#
#        self.bw_filter   = True if self.dev.ask(f"CH{self.chan}:BANDWIDTH?") == "ON" else False
#        self.coupling    = DPO4034_Channel_Coupling( self.dev.ask(f"CH{self.chan}:COUPLING?") )
#        self.invert      = True if self.dev.ask(f"CH{self.chan}:INVERT?") == "ON" else False
#        self.position    = float(self.dev.ask(f"CH{self.chan}:POS?"))
#        self.attenuation = float(self.dev.ask(f"CH{self.chan}:PROBE?"))
#        self.scale       = float(self.dev.ask(f"CH{self.chan}:SCALE?"))
#        self.on          = bool(int(self.dev.ask(f"SELECT:CH{self.chan}?")))
#
#
#    def settings_write(self):
#        self.log.debug("Write settings")
#
#        if self.bw_filter   is not None: self.dev.write(f"CH{self.chan}:BANDWIDTH %s" % ("ON" if self.bw_filter else "OFF"))
#        if self.coupling    is not None: self.dev.write(f"CH{self.chan}:COUPLING {self.coupling.value}")
#        if self.invert      is not None: self.dev.write(f"CH{self.chan}:INVERT %s" % ("ON" if self.invert else "OFF"))
#        if self.position    is not None: self.dev.write(f"CH{self.chan}:POS {self.position:E}")
#        if self.attenuation is not None: self.dev.write(f"CH{self.chan}:PROBE {self.attenuation:E}")
#        if self.scale       is not None: self.dev.write(f"CH{self.chan}:SCALE {self.scale:E}")
#        if self.on          is not None: self.dev.write(f"SELECT:CH{self.chan} {int(self.on)}")
#
#    # ┌────────────────────────────────────────┐
#    # │ Enable/Disable                         │
#    # └────────────────────────────────────────┘
#
#    def enable(self):
#        self.log.info("--> Enable channel")
#        self.dev.write(f"SELECT:CH{self.chan} ON")
#
#    def disable(self):
#        self.log.info("--> Disable channel")
#        self.dev.write(f"SELECT:CH{self.chan} OFF")
#
## ┌────────────────────────────────────────┐
## │ Horizontal parameters                  │
## └────────────────────────────────────────┘
#
#@dataclass
#class DPO4034_Horizontal_Parameters:
#    dev: InitVar[usbtmc.Instrument]
#    id:  InitVar[str]    # Name of the horizontal scale: not represented in dict data
#
#    pos: float   = None # Horizontal position
#    scale: float = None # s/div scale
#
#    def __post_init__(self, dev, id):
#        self.dev = dev
#        self.id  = id
#        self.log = logging.getLogger(f"DPO4034 horizontal {self.id} scale")
#
#    # ┌────────────────────────────────────────┐
#    # │ Update from dict                       │
#    # └────────────────────────────────────────┘
#    
#    def settings_load(self, data):
#        if data.get("pos",   None) is not None: self.pos   = float(data["pos"])
#        if data.get("scale", None) is not None: self.scale = float(data["scale"])
#    
#
#    # ┌────────────────────────────────────────┐
#    # │ Settings read/write                    │
#    # └────────────────────────────────────────┘
#
#    def settings_read(self):
#        self.log.debug("Read settings")
#
#        self.pos   = float(self.dev.ask(f"HOR:{self.id}:POS?"))
#        self.scale = float(self.dev.ask(f"HOR:{self.id}:SCALE?"))
#
#    def settings_write(self):
#        self.log.debug("Write settings")
#
#        if self.pos   is not None: self.dev.write(f"HOR:{self.id}:POS {self.pos:E}"    )
#        if self.scale is not None: self.dev.write(f"HOR:{self.id}:SCALE {self.scale:E}")
#    
## ┌────────────────────────────────────────┐
## │ Trigger parameters                     │
## └────────────────────────────────────────┘
#
#class DPO4034_Trigger_Type(str, Enum):
#    Edge    = "EDGE"
#    Video   = "VID"
#    Pulse   = "PUL"
#
#class DPO4034_Trigger_Mode(str, Enum):
#    Auto    = "AUTO"
#    Normal  = "NORMAL"
#
#class DPO4034_Trigger_State(str, Enum):
#    Armed   = "ARMED"
#    Ready   = "READY"
#    Trigger = "TRIGGER"
#    Auto    = "AUTO"
#    Save    = "SAVE"
#    Scan    = "SCAN"
#    
## ────────── Edge trigger defs. ────────── #
#
#class DPO4034_Trigger_Edge_Coupling(str, Enum):
#    AC           = "AC"
#    DC           = "DC"
#    HF_Reject    = "HFREJ"
#    LF_Reject    = "LFREJ"
#    Noise_Reject = "NOISEREJ"
#
#class DPO4034_Trigger_Edge_Slope(str, Enum):
#    Fall = "FALL"
#    Rise = "RISE"
#
#class DPO4034_Trigger_Edge_Source(str, Enum):
#    CH1   = "CH1"
#    CH2   = "CH2"
#    CH3   = "CH3"
#    CH4   = "CH4"
#
#    Ext   = "EXT"    # Ext. trigger
#    Ext5  = "EXT5"   # Ext. trigger, 5x  attenuation
#    Ext10 = "EXT10"  # Ext. trigger, 10x attenuation
#
#    Line  = "LINE"   # Power line
#
#@dataclass
#class DPO4034_Trigger_Parameters:
#    dev: InitVar[usbtmc.Instrument]
#    id : InitVar[str] # Name of trigger: not represented in dict data
#
#    # ──────────── Global settings ─────────── #
#
#    type: DPO4034_Trigger_Type = None
#    mode: DPO4034_Trigger_Mode = None
#    level: float                = None
#
#
#    # ────── Settings for video trigger ────── #
#
#    # NOT IMPLEMENTED
#
#
#    # ─────── Settings for edge trigger ────── #
#
#    edge_coupling: DPO4034_Trigger_Edge_Coupling = None
#    edge_slope:    DPO4034_Trigger_Edge_Slope    = None
#    edge_source:   DPO4034_Trigger_Edge_Source   = None
#
#
#    # ────── Settings for pulse trigger ────── #
#
#    # NOT IMPLEMENTED
#
#    # ───────────────── Misc. ──────────────── #
#
#    def __post_init__(self, dev, id):
#        self.dev = dev
#        self.id  = id
#        self.log = logging.getLogger(f"DPO4034 Trigger {self.id}")
#
#    # ─────── Update config from dict. ─────── #
#
#    def settings_load(self, data):
#        if data.get("type"         , None) is not None: self.type          = DPO4034_Trigger_Type(data["type"])
#        if data.get("mode"         , None) is not None: self.mode          = DPO4034_Trigger_Mode(data["mode"])
#        if data.get("edge_coupling", None) is not None: self.edge_coupling = DPO4034_Trigger_Edge_Coupling(data["edge_coupling"])
#        if data.get("edge_slope"   , None) is not None: self.edge_slope    = DPO4034_Trigger_Edge_Slope(data["edge_slope"])
#        if data.get("edge_source"  , None) is not None: self.edge_source   = DPO4034_Trigger_Edge_Source(data["edge_source"])
#    
#
#    # ────────────── Properties ────────────── #
#    def frequency(self):
#        return float( self.dev.ask(f"TRIG:{self.id}:FREQ?"))
#
#    def state(self):
#        return DPO4034_Trigger_State(self.dev.ask(f"TRIG:{self.id}:STATE"))
#
#
#    # ────────── Settings read/write ───────── #
#    def settings_read(self):
#        self.log.debug("Read settings")
#
#        # Main settings
#        self.type          = DPO4034_Trigger_Type(self.dev.ask(f"TRIG:{self.id}:TYPE?"))
#        self.mode          = DPO4034_Trigger_Mode(self.dev.ask(f"TRIG:{self.id}:MODE?"))
#        self.level         = float(self.dev.ask(f"TRIG:{self.id}:LEVEL?"))
#
#        # Edge settings
#        self.edge_coupling = DPO4034_Trigger_Edge_Coupling(self.dev.ask(f"TRIG:{self.id}:EDGE:COUPLING?"))
#        self.edge_slope    = DPO4034_Trigger_Edge_Slope   (self.dev.ask(f"TRIG:{self.id}:EDGE:SLOPE?"))
#        self.edge_source   = DPO4034_Trigger_Edge_Source  (self.dev.ask(f"TRIG:{self.id}:EDGE:SOURCE?"))
#
#    def settings_write(self):
#        self.log.debug("Write settings")
#
#        # Main settings
#        if self.type  is not None: self.dev.write(f"TRIG:{self.id}:TYPE {self.type.value}")
#        if self.mode  is not None: self.dev.write(f"TRIG:{self.id}:MODE {self.mode.value}")
#        if self.level is not None: self.dev.write(f"TRIG:{self.id}:LEVEL {self.level:G}")
#        
#        # Edge settings
#        if self.edge_coupling is not None: self.dev.write(f"TRIG:{self.id}:EDGE:COUPLING {self.edge_coupling.value}")
#        if self.edge_slope    is not None: self.dev.write(f"TRIG:{self.id}:EDGE:SLOPE {self.edge_slope.value}")
#        if self.edge_source   is not None: self.dev.write(f"TRIG:{self.id}:EDGE:SOURCE {self.edge_source.value}")

# ┌────────────────────────────────────────┐
# │ Interface class                        │
# └────────────────────────────────────────┘

class DPO4034_Interface:
    def __init__(self, vendor_id=0x699, product_id=0x0401):
        """
        Main interface to the DPO4034 oscilloscope using USB TMC bus

        Some various notes :

        - the synchronized event can be used to ensure all the settings has been read from the scope
        at least one time. For example:

        .. code:: python
            
            if not scope.synchronized.is_set():
                scope.state_sync() # Blocking function, no need to wait for the flag to be set


        - The recommended usage to use the scope is to read the settings you want to modify, set
        them, and then send them to the scope. Here is a full example:

        .. code:: python

                osc = DPO4034_Interface()

                # Set channel parameters
                def chan_conf(i):
                    osc.ch[i].bw_filter = False                        # 200 MHz bandwidth
                    osc.ch[i].scale     = 1.0                          # V/div
                    osc.ch[i].coupling  = DPO4034_Channel_Coupling.DC # DC coupling
                    osc.ch[i].position  = 0                            # Center channel on scope

                    osc.ch[i].settings_write()
                    osc.ch[i].enable()

                def chan_hide(i):
                    osc.ch[i].disable()

                chan_conf(0)
                chan_conf(1)
                chan_conf(2)
                chan_hide(3)

                # Set time trigger parameters
                osc.trigger.type          = DPO4034_Trigger_Type.Edge
                osc.trigger.mode          = DPO4034_Trigger_Mode.Auto
                osc.trigger.level         = 2.0 # V
                osc.trigger.edge_coupling = DPO4034_Trigger_Edge_Coupling.DC
                osc.trigger.edge_slope    = DPO4034_Trigger_Edge_Slope.Fall
                osc.trigger.edge_source   = DPO4034_Trigger_Edge_Source.CH1

                osc.trigger.settings_write()

                # Set horizontal time settings
                osc.horizontal_main.pos   = 0.0    # Center
                osc.horizontal_main.scale = 250e-6 # s

                osc.horizontal_main.settings_write()
                
                # Set immediate measurement settings
                osc.mes_imm.source         = DPO4034_Measurement_Source.CH1
                osc.mes_imm.type           = DPO4034_Measurement_Type.Period

                osc.mes_imm.settings_write()
                
                # Set measurement settings
                osc.mes[0].source         = DPO4034_Measurement_Source.CH1
                osc.mes[0].type           = DPO4034_Measurement_Type.NWidth # Negative pulse width
                osc.mes[1].source         = DPO4034_Measurement_Source.CH2
                osc.mes[1].type           = DPO4034_Measurement_Type.NWidth # Negative pulse width
                osc.mes[2].source         = DPO4034_Measurement_Source.CH3
                osc.mes[2].type           = DPO4034_Measurement_Type.NWidth # Negative pulse width

                osc.mes[0].settings_write()
                osc.mes[1].settings_write()
                osc.mes[2].settings_write()

        """

        self.dev = usbtmc.Instrument(vendor_id, product_id)
        self.synchronized = Event()
        self.synchronized.clear()

        # Change the default timeout
        self.dev.timeout = 10 
        self.log = logging.getLogger("DPO4034 Interface")

        # Disable headers for query responses
        self.dev.write("HEADER OFF")

        # Trigger settings
        #self.trigger          = DPO4034_Trigger_Parameters(self.dev, "MAIN")

        ## Horizontal handles
        #self.horizontal_main  = DPO4034_Horizontal_Parameters(self.dev, "MAIN" )
        #self.horizontal_delay = DPO4034_Horizontal_Parameters(self.dev, "DELAY")

        ## Channel handles
        #self.ch      = [DPO4034_Channel_Parameters(self.dev, i) for i in range(1,5)]

        ## Measurements handles
        #self.mes     = [DPO4034_Measurement(self.dev, f"MEAS{i}") for i in range(1,6)]

        # Immediate measure is the same as classic measures,
        # except it is not displayed on the scope, and thus is
        # faster to run
        self.mes_imm = DPO4034_Measurement(self.dev, "IMM")
  

    def settings_read(self):
        # Init resources status
        self.log.info("Read all settings")

        #self.trigger.settings_read()
        #self.horizontal_main.settings_read()
        #self.horizontal_delay.settings_read()

        #for c   in self.ch:  c.settings_read()
        #for mes in self.mes: mes.settings_read()
        self.mes_imm.settings_read()

        self.synchronized.set()

    def settings_write(self):
        # Init resources status
        self.log.info("Write all settings")
        #self.trigger.settings_write()
        #self.horizontal_main.settings_write()
        #self.horizontal_delay.settings_write()

        #for c   in self.ch:  c.settings_write()
        #for mes in self.mes: mes.settings_write()
        self.mes_imm.settings_write()

        self.synchronized.set()


    # ┌────────────────────────────────────────┐
    # │ System commands                        │
    # └────────────────────────────────────────┘
    
    def identity(self):
        return self.dev.ask("*IDN?")


    # ┌────────────────────────────────────────┐
    # │ Config dump/load                       │
    # └────────────────────────────────────────┘

    def settings_dump(self):
        """
        Dumps the config in dict format
        """

        return {
            #"trigger"         : asdict(self.trigger),
            #"horizontal_main" : asdict(self.horizontal_main),
            #"horizontal_delay": asdict(self.horizontal_delay),
            #"ch1"             : asdict(self.ch[0]),
            #"ch2"             : asdict(self.ch[1]),
            #"ch3"             : asdict(self.ch[2]),
            #"ch4"             : asdict(self.ch[3]),
            #"mes1"            : asdict(self.mes[0]),
            #"mes2"            : asdict(self.mes[1]),
            #"mes3"            : asdict(self.mes[2]),
            #"mes4"            : asdict(self.mes[3]),
            "mes_imm"         : asdict(self.mes_imm)
        }

    def settings_load(self, data):
        """
        Load config from dict data
        """


        #if "trigger" in data:
        #    self.log.info("Load trigger config")
        #    self.trigger.settings_load(data["trigger"])

        #if "horizontal_main" in data:
        #    self.log.info("Load main horizontal settings")
        #    self.horizontal_main.settings_load(data["horizontal_main"])

        #if "horizontal_delay" in data:
        #    self.log.info("Load delay horizontal settings")
        #    self.horizontal_main.settings_load(data["horizontal_delay"])
    
        #if "ch" in data:
        #    for i in range(4):
        #        if f"ch{i+1}" in data:
        #            self.log.info(f"Load channel settings for channel {i+1}")
        #            self.ch[i].settings_load(data[f"ch{i+1}"])

        #    for i in range(4):
        #        if f"mes{i+1}" in data:
        #            self.log.info(f"Load measure settings for measure {i+1}")
        #            self.mes[i].settings_load(data[f"mes{i+1}"])

        if "mes_imm" in data:
            self.log.info("Load immediate measure settings")
            self.mes_imm.settings_load(data["mes_imm"])
