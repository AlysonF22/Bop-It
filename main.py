
#Libraries for Potentiometer
from machine import ADC, Pin
import time

import random

#Libraries For LCD
from machine import I2C, Pin
from time import sleep
from pico_i2c_lcd import I2cLcd

##POT FUNCTION
# Define a function to map a value from one range to another
def map_value(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def initial_Volume_value():
    
    DO_NOT_CRANK= False
    DO_NOT_KILL = False
    
    # Retrieve analog value from pin A0:
    adc_value = adc.read_u16() >> 4  # Convert 16-bit to 12-bit by right shifting 4 bits
    # Convert the analog value to a voltage (0-3.3V range):
    voltage = map_value(adc_value, 0, 4095, 0, 3.3)
    print("initial Voltage: ",voltage)
    if voltage >= 3:
        DO_NOT_CRANK = True
    if voltage <= .03:
        DO_NOT_KILL = True
        
   
    return voltage, DO_NOT_CRANK, DO_NOT_KILL



def random_exclude(exclude, start, end):
    numbers = list(range(start, end + 1))
    numbers.remove(exclude)
    return random.choice(numbers)



## SPEAKER FUNCTION
# DF PLAYER MINI
class DFPlayer:
    def __init__(self,uart_id,tx_pin_id=None,rx_pin_id=None):
        self.uart_id=uart_id
        #init with given baudrate
        self.uart = machine.UART(uart_id, 9600)  
                
        #not all boards can set the pins for the uart channel
        if tx_pin_id or rx_pin_id:
            self.uart.init(9600, bits=8, parity=None, stop=1, tx=tx_pin_id, rx=rx_pin_id)
        else:
            self.uart.init(9600, bits=8, parity=None, stop=1)
        
    def flush(self):
        self.uart.flush()
        if self.uart.any():
            self.uart.read()
        
    def send_query(self,cmd,param1=0,param2=0):
        retry=True
        while (retry):
            self.flush()
            self.send_cmd(cmd,param1,param2)
            time.sleep(0.05)
            in_bytes = self.uart.read()
            if not in_bytes: #timeout
                return -1
            if len(in_bytes)==10 and in_bytes[1]==255 and in_bytes[9]==239:
                retry=False
        return in_bytes
    
    def send_cmd(self,cmd,param1=0,param2=0):
        out_bytes = bytearray(10)
        out_bytes[0]=126
        out_bytes[1]=255
        out_bytes[2]=6
        out_bytes[3]=cmd
        out_bytes[4]=0
        out_bytes[5]=param1
        out_bytes[6]=param2
        out_bytes[9]=239
        checksum = 0
        for i in range(1,7):
            checksum=checksum+out_bytes[i]
        out_bytes[7]=(checksum>>7)-1
        out_bytes[7]=~out_bytes[7]
        out_bytes[8]=checksum-1
        out_bytes[8]=~out_bytes[8]
        self.uart.write(out_bytes)

    def stop(self):
        self.send_cmd(22,0,0)
        
    def play(self,folder,file):
        self.stop()
        time.sleep(0.05)
        self.send_cmd(15,folder,file)
        
    def volume(self,vol):
        self.send_cmd(6,0,vol)
        
    def volume_up(self):
        self.send_cmd(4,0,0)

    def volume_down(self):
        self.send_cmd(5,0,0)
    
    def reset(self):
        self.send_cmd(12,0,1)
        
    def is_playing(self):
        in_bytes = self.send_query(66)
        if in_bytes==-1 or in_bytes[5]!=2:
            return -1
        return in_bytes[6]
    
    def get_volume(self):
        in_bytes = self.send_query(67)
        if in_bytes==-1 or in_bytes[3]!=67:
            return -1
        return in_bytes[6]

    def get_files_in_folder(self,folder):
        in_bytes = self.send_query(78,0,folder)
        if in_bytes==-1:
            return -1
        if in_bytes[3]!=78:
            return 0
        return in_bytes[6]
    
    

    
SCORE =0
Initial_SwitchState =0
Final_SwitchState =0
#PINOUT OF Controller

##SWITCH (GPIO pins INPUT, 18,19,20,21,22)
Pickup1 = machine.Pin(18,machine.Pin.IN,machine.Pin.PULL_DOWN)
Pickup2 = machine.Pin(19,machine.Pin.IN,machine.Pin.PULL_DOWN)
Pickup3 = machine.Pin(20,machine.Pin.IN,machine.Pin.PULL_DOWN)
Pickup4 = machine.Pin(21,machine.Pin.IN,machine.Pin.PULL_DOWN)
Pickup5 = machine.Pin(22,machine.Pin.IN,machine.Pin.PULL_DOWN)

##BUTTON
Butt = machine.Pin(16,machine.Pin.IN,machine.Pin.PULL_DOWN)

##SPEAKER
df=DFPlayer(uart_id=0,tx_pin_id=0,rx_pin_id=1)
#wait some time till the DFPlayer is ready
time.sleep(0.2)
#change the volume (0-30). The DFPlayer doesn't remember these settings
df.volume(30)
time.sleep(0.2)

## VOLUME POTENTIOMETER
# Initialize the analog pin for reading
adc = ADC(Pin(26))  # Corresponds to GP26, which is ADC0 on the Pico

##TONE POTENTIOMETER
adc1 = ADC(Pin(27))


##LCD
# Create Object to communicate with LCD using sda, scl via GPIO ports
i2c = I2C(1, sda=Pin(2), scl=Pin(3), freq=400000)

##LCD
#Store first I2C address, only one device so first in array [0]
I2C_ADDR = i2c.scan()[0]

##LCD
#Create Object lcd for communication between library
lcd = I2cLcd(i2c, I2C_ADDR, 2, 16)

#Loop until game is started
while True:
    
    if Butt.value() == True:
        break
    



#GAME START
lcd.clear()
lcd.putstr("Game will Start in...4")
sleep(1)
lcd.clear()
lcd.putstr("Game will Start in...3")
sleep(1)
lcd.clear()
lcd.putstr("Game will Start in...2")
sleep(1)
lcd.clear()
lcd.putstr("Game will Start in...1")
sleep(1)
lcd.clear()
Task =0
for i in range(3):
    
    
    #For Tone Pot
    initial_voltage, DO_NOT_CRANK, DO_NOT_KILL = initial_Volume_value()
    print(DO_NOT_CRANK)
    print(DO_NOT_KILL)
    #Volume is already near max
    if DO_NOT_CRANK == True:
        Task = random_exclude(1,1,4)
        
    #Volume is already near min
    elif DO_NOT_KILL == True:
        Task == random_exclude(2,1,4)
        
    else:
        Task = random.randint(1,4)
        
    print("Task: ",Task)

    #Crank_it! - 1 / Kill_it! - 2
    if Task == 1 or Task == 2:
        
        lcd.putstr("Round "+str(i+1))
        sleep(1.5)
        lcd.clear()
        
        
        if Task == 1:
            lcd.putstr("CRANK IT!")
        elif Task == 2:
            lcd.putstr("KILL IT!")
        sleep(.7)
        lcd.clear()
        
        #User Period to change Pot
        for j in range(50):
        
            # Retrieve analog value from pin A0:
            adc_value = adc.read_u16() >> 4  # Convert 16-bit to 12-bit by right shifting 4 bits
            # Convert the analog value to a voltage (0-3.3V range):
            voltage = map_value(adc_value, 0, 4095, 0, 3.3)
            print("Test Voltage: ",voltage)
        
            time.sleep(.1)
            
        Final_voltage = voltage
        print("Final Voltage: ",Final_voltage)
        lcd.putstr("Round "+str(i+1)+" done...\n")
        sleep(5)
        lcd.clear()
        
        if Task == 1:
            lcd.putstr("Did the volume\nincrease?")
        elif Task ==2:
            lcd.putstr("Did the volume\ndecrease?")
        
        sleep(5)
        lcd.clear()
        
        # Volume is supposed to increased
        if Task == 1:
            if (Final_voltage <= (1.03 * initial_voltage)):
                lcd.putstr("NO, LOSER!!!")
                sleep(3)
                lcd.clear()
                lcd.putstr(" -1 point, idiot :)")
                sleep(3)
                SCORE = SCORE -1
                lcd.clear()
            else:
                lcd.putstr("YES, YAYYYYYYY!!!!")
                sleep(3)
                lcd.clear()
                lcd.putstr(" +1 point,\n smartypants")
                df.play(1,3)
                time.sleep(.2)
                while True:
                    
                    if df.is_playing() == False:
                        break;
                SCORE = SCORE +1
                lcd.clear()
            
        # Volume is supposed to decreased
        else:
            if (Final_voltage >= (.97 * initial_voltage)):
                lcd.putstr("NO, LOSER!!!")
                sleep(3)
                lcd.clear()
                lcd.putstr(" -1 point, idiot :)")
                sleep(3)
                SCORE = SCORE -1
                lcd.clear()
            else:
                lcd.putstr("YES, YAYYYYYYY!!!!")
                sleep(3)
                lcd.clear()
                lcd.putstr(" +1 point,\n smartypants")
                
  
                df.play(1,3)
                time.sleep(.2)
                while True:
                    
                    if df.is_playing() == False:
                        break;
                        
            
                SCORE = SCORE +1
                lcd.clear()
            
        
        
    #Flip_it!
    elif Task == 3:
        
       #Check initial state of the switch before task
        if Pickup1.value()== True:
            Initial_SwitchState= 1
        elif Pickup2.value() == True:
            Initial_SwitchState = 2
        elif Pickup3.value() == True:
            Initial_SwitchState = 3
        elif Pickup4.value() == True:
            Initial_SwitchState = 4
        elif Pickup5.value() == True:
            Initial_SwitchState = 5
            
        
        print("initial state: ",Initial_SwitchState)
            
        lcd.putstr("Round "+str(i+1))
        sleep(1.5)
        lcd.clear()
        lcd.putstr("FLIP IT!")
        sleep(.7)
        lcd.clear()
        
        
        #User period to complete the task    
        for j in range(10):
            if Pickup1.value() == True:
                Final_SwitchState = 1
            elif Pickup2.value() == True:
                Final_SwitchState = 2
            elif Pickup3.value() == True:
                Final_SwitchState = 3
            elif Pickup4.value() == True:
                Final_SwitchState = 4
            elif Pickup5.value() == True:
                Final_SwitchState = 5
        
            time.sleep(.5)
        print("final state: ",Final_SwitchState)    
        lcd.putstr("Round "+str(i+1)+" done...\n")
        sleep(5)
        lcd.clear()
        lcd.putstr("Did the switch\nchange?")
        sleep(5)
        lcd.clear() 
        
        if (Initial_SwitchState == Final_SwitchState):
            lcd.putstr("NO, LOSER!!!")
            sleep(3)
            lcd.clear()
            lcd.putstr(" -1 point, idiot :)")
            sleep(3)
            SCORE = SCORE -1
            lcd.clear()
        else:
            lcd.putstr("YES, YAYYYYYYY!!!!")
            sleep(3)
            lcd.clear()
            lcd.putstr(" +1 point,\n smartypants")
            df.play(1,3)
            time.sleep(.2)
            while True:
                    
                if df.is_playing() == False:
                    break
                
            SCORE = SCORE +1
            lcd.clear()
   
   #TONE IT!
    else:
       
        lcd.putstr("Round "+str(i+1))
        sleep(1.5)
        lcd.clear()
        
        
        lcd.putstr("TONE IT!")
        sleep(.7)
        lcd.clear()
       
       
        #User Period to change Pot
        for j in range(50):
        
            # Retrieve analog value from pin A0:
            adc_value = adc.read_u16() >> 4  # Convert 16-bit to 12-bit by right shifting 4 bits
            # Convert the analog value to a voltage (0-3.3V range):
            voltage = map_value(adc_value, 0, 4095, 0, 3.3)
            print("Test Voltage: ",voltage)
        
            time.sleep(.1)
            
        Final_voltage = voltage
        print("Final Voltage: ",Final_voltage)
        lcd.putstr("Round "+str(i+1)+" done...\n")
        sleep(5)
        lcd.clear()
        

        
        lcd.putstr("Did the Tone Change?")
        sleep(5)
        lcd.clear()
        
        # Volume is supposed to increased
    
        if Final_voltage <= 1.10 * initial_voltage and Final_voltage >= .90 * initial_voltage :
            lcd.putstr("NO, LOSER!!!")
            sleep(3)
            lcd.clear()
            lcd.putstr(" -1 point, idiot :)")
            sleep(3)
            SCORE = SCORE -1
            lcd.clear()
        else:
            lcd.putstr("YES, YAYYYYYYY!!!!")
            sleep(3)
            lcd.clear()
            lcd.putstr(" +1 point,\n smartypants")
            df.play(1,3)
            time.sleep(.2)
            while True:
                    
                if df.is_playing() == False:
                    break;
                
            SCORE = SCORE +1
            lcd.clear()
        
        

    
lcd.putstr("Game over")
sleep(3)
lcd.clear()
lcd.putstr("Final score: " + str(SCORE))
sleep(5)
lcd.clear()

if SCORE == -3:

    df.play(1,8)
    time.sleep(.2)
    time.sleep(10.7)
    df.stop()
    
print("end")    
    
    
    
    
    
    
    



    
    
    












