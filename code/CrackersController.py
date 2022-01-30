import board

import time
import gc
import board
import neopixel
import rotaryio
from digitalio import DigitalInOut, Direction, Pull
import usb_midi
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
from adafruit_midi.control_change import ControlChange
from adafruit_debouncer import Debouncer

class Col:
    
    RED = (255, 0, 0)
    YELLOW = (255, 150, 0)
    GREEN = (0, 255, 0)
    CYAN = (0, 255, 255)
    BLUE = (0, 0, 255)
    MAGENTA = (255, 0, 255)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GREY = (10, 10, 10)
    VIOLET = (127,0,155)
    INDIGO = (75,0,130)
    ORANGE = (255,165,0)
       
    values=(RED, GREEN, BLUE, YELLOW, MAGENTA, CYAN, GREY, WHITE)
    
   
    @staticmethod
    def dim(col):
        return (col[0]/40, col[1]/40, col[2]/40)

class ControllerConfig():
    
    def __init__(self, min_val=0, max_val=127,turns=1.0,init_value=0,
                 controller_value = 0, background_col = Col.BLUE,
                 val_col = Col.RED):
        self.min_val = min_val
        self.max_val = max_val
        self.turns = turns
        self.encoder_value = 0
        self.init_value = init_value
        self.controller_value = init_value
        self.val_col = val_col
        self.background_col = background_col
        
class MidiControllerConfig(ControllerConfig):
    
    def __init__(self, min_val=0, max_val=127,turns=1.0,init_value=0,
                 controller_value = 0, background_col = Col.BLUE,
                 val_col = Col.RED, midi_channel=0,midi_control=1):
        super(MidiControllerConfig,self).__init__(
            min_val, max_val,turns,init_value,
                 controller_value, background_col,
                 val_col)
        self.midi_channel=midi_channel
        self.midi_control = midi_control

class Controller():
    def __init__(self, client, name, encoder_pin1, encoder_pin2, pulses_rev,
                 button_pin, pixel_start, no_of_pixels, pixel_offset, forward,
                 configs
                 ):
        self.name = name
        self.client =  client
        self.encoder= rotaryio.IncrementalEncoder(encoder_pin1, encoder_pin2)
        self.pulses_rev = pulses_rev
        self.last_encoder_position = 0
        tmp_pin = DigitalInOut(button_pin)
        tmp_pin.pull = Pull.UP
        self.button_debounce = Debouncer(tmp_pin,interval=0.01)
        self.pixel_start = pixel_start
        self.no_of_pixels = no_of_pixels
        self.pixel_offset = pixel_offset
        self.forward = forward
        self.first_run = True
        self.configs = configs
        self.active_config_no = 0
        self.active_config = configs[0]
    
    def set_range(self,min_val,max_val,turns,pulses_rev):
        self.min = min_val
        self.max = max_val
        self.turns = turns
        self.pulses_rev = pulses_ref
        
    def draw_cursor(self):
        pixels = self.no_of_pixels
        base = self.pixel_start
        offset = self.pixel_offset
        pulse_limit = int(self.pulses_rev * self.active_config.turns)-1
        turn_amount = self.active_config.encoder_value / pulse_limit
        cursor = int(pixels*turn_amount)
        pos=0
        while pos < pixels:
            pix = base + ((pos+offset) % pixels)
            if pos<=cursor:
                self.client.pixels[pix] = self.active_config.val_col
            else:
                self.client.pixels[pix] = self.active_config.background_col
            pos = pos + 1
                    
    def update_encoder(self):
        new_encoder_position = self.encoder.position
        encoder_change = self.last_encoder_position - new_encoder_position
        
        if encoder_change != 0 or self.first_run:
            if self.forward:
                new_pos = self.active_config.encoder_value - encoder_change
            else:
                new_pos = self.active_config.encoder_value + encoder_change
                
            if new_pos<0:
                new_pos=0
                
            pulse_limit = int(self.pulses_rev * self.active_config.turns)-1
            
            if new_pos>=pulse_limit:
                new_pos=pulse_limit
                 
            if self.active_config.encoder_value != new_pos or self.first_run:
                self.first_run = False
                self.active_config.encoder_value = new_pos
                turn_amount = new_pos / pulse_limit
                val_range = self.active_config.max_val - self.active_config.min_val
                scaled_change = turn_amount * val_range
                self.active_config.controller_value=scaled_change
                self.draw_cursor()
                self.encoder_changed()
                
        self.last_encoder_position = new_encoder_position
        
    def update(self):
        self.button_debounce.update()
        if self.button_debounce.fell:
            self.button_down()
        if self.button_debounce.rose:
            self.button_up()
            
        self.update_encoder()

    def reset(self):
        self.count=0;
        
    def step_controller(self):
        self.active_config_no = (self.active_config_no + 1) % len(self.configs)
        self.active_config = self.configs[self.active_config_no]
        self.draw_cursor()
    
    def button_down(self):
        if self.client.change_all_controllers:
            for controller in self.client.controllers:
                controller.step_controller()
        else:
            self.step_controller()
        
    def button_up(self):
        pass


class MidiController(Controller):
    
    def __init__(self, client, name, encoder_pin1, encoder_pin2, pulses_rev,
                 button_pin, pixel_start, no_of_pixels, pixel_offset, forward,
                 configs):
        super(MidiController,self).__init__(client = client, name = name,
                 encoder_pin1 = encoder_pin1, encoder_pin2 = encoder_pin2,
                 pulses_rev = pulses_rev, button_pin = button_pin,
                 pixel_start = pixel_start, no_of_pixels = no_of_pixels,
                 forward = forward, pixel_offset = pixel_offset,
                 configs=configs)
    
    def encoder_changed(self):
        self.client.midi.send(ControlChange(self.active_config.midi_control,
            round(self.active_config.controller_value)), channel=self.active_config.midi_channel)

class CrackersController:

    def __init__(self):
        print("Rob Miles Crackers Midi Controller 1.0")
        base=20
        
        c1 = [
            MidiControllerConfig(midi_channel=0,midi_control=base+1),
            MidiControllerConfig(midi_channel=0,midi_control=base+5, background_col = Col.YELLOW),
            MidiControllerConfig(midi_channel=0,midi_control=base+9, background_col = Col.GREEN),
            MidiControllerConfig(midi_channel=0,midi_control=base+13, background_col = Col.MAGENTA)
            ]
        
        c2 = [
            MidiControllerConfig(midi_channel=0,midi_control=base+2),
            MidiControllerConfig(midi_channel=0,midi_control=base+6, background_col = Col.YELLOW),
            MidiControllerConfig(midi_channel=0,midi_control=base+10, background_col = Col.GREEN),
            MidiControllerConfig(midi_channel=0,midi_control=base+14, background_col = Col.MAGENTA)
            ]
        c3 = [
            MidiControllerConfig(midi_channel=0,midi_control=base+3),
            MidiControllerConfig(midi_channel=0,midi_control=base+7, background_col = Col.YELLOW),
            MidiControllerConfig(midi_channel=0,midi_control=base+11, background_col = Col.GREEN),
            MidiControllerConfig(midi_channel=0,midi_control=base+15, background_col = Col.MAGENTA)
            ]
        c4 = [
            MidiControllerConfig(midi_channel=0,midi_control=base+4),
            MidiControllerConfig(midi_channel=0,midi_control=base+8, background_col = Col.YELLOW),
            MidiControllerConfig(midi_channel=0,midi_control=base+12, background_col = Col.GREEN),
            MidiControllerConfig(midi_channel=0,midi_control=base+16, background_col = Col.MAGENTA)
            ]
        self.controllers = [
            MidiController(client=self, name="c1", encoder_pin1=board.GP8, encoder_pin2=board.GP9, pulses_rev=20,
                           button_pin=board.GP14, pixel_start=24, no_of_pixels=12, forward=True, pixel_offset=2,
                           configs=c1),
            MidiController(client=self, name="c2", encoder_pin1=board.GP10, encoder_pin2=board.GP11, pulses_rev=20,
                           button_pin=board.GP15, pixel_start=36, no_of_pixels=12, forward=True, pixel_offset=-1,
                           configs=c2),
            MidiController(client=self, name="c3", encoder_pin1=board.GP6, encoder_pin2=board.GP7, pulses_rev=20,
                           button_pin=board.GP17, pixel_start=12, no_of_pixels=12, forward=True, pixel_offset=5,
                           configs=c3),
            MidiController(client=self, name ="c4", encoder_pin1=board.GP4, encoder_pin2=board.GP5, pulses_rev=20,
                           button_pin=board.GP12, pixel_start=0, no_of_pixels=12, forward=False, pixel_offset=8,
                           configs=c4)
            ]
        self.midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)
        no_of_pixels = len(self.controllers)*12
        self.pixels = neopixel.NeoPixel(board.GP13,no_of_pixels,auto_write=False)
        self.pixels.brightness = 0.5
        self.change_all_controllers = True
        
    def button_down(self,controller):
        pass
        
    def button_up(self,controller):
        pass

    def encoder_changed(self, controller, change):
        pass

    def update(self):
        for controller in self.controllers:
            controller.update()
        self.pixels.show()


controller = CrackersController()
while True:
    controller.update()


