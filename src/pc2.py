#!/usr/bin/python
from thermistor2temp import therm2temp

import time, signal, sys, math
from Adafruit_ADS1x15 import ADS1x15

import Adafruit_CharLCD as LCD

import RPi.GPIO as GPIO ## Import GPIO library

IO_Solar = 17
IO_Pump = 18
ADC_Pool = 0
ADC_Solar = 1

PoolMaxTemp = 90
SolarPoolDiff = 5
SolarChangeFrequency = 5 * 60
DisplayUpdateFrequency = 5
LogUpdateFrequency = 5 * 60

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM) ## Use board pin numbering
GPIO.setup(IO_Solar, GPIO.OUT)
GPIO.setup(IO_Pump, GPIO.OUT)

def signal_handler(signal, frame):
        print 'You pressed Ctrl+C!'
	f.close()
        sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def ReadTemp(channel):
	volts = adc.readADCSingleEnded(channel, gain, sps) / 1000
	if volts > 3.3:
		volts=3.3
	if volts == 0:
		volts=0.001
	ohms = round(((1/volts)*33000)-10000,0)
	return therm2temp[ohms]

ADS1015 = 0x00  # 12-bit ADC
#ADS1115 = 0x01	# 16-bit ADC
gain = 4096    # +/- 4.096V
sps = 250  # 250 samples per second

# Initialise the ADC using the default mode (use default I2C address)
# Set this to ADS1015 or ADS1115 depending on the ADC you are using!
adc = ADS1x15(ic=ADS1015)

# Initialize the LCD using the pins 
lcd = LCD.Adafruit_CharLCDPlate()
lcd.clear()

# Open a logging file
f = open("/var/log/pool.log", "a+")

LastSolarChange = 0
LastDisplayUpdate = 0
LastLog = "System startup"
LastLogUpdate = 0

print 'Press Ctrl-C to quit.'
while True:
	#
	# Get the data
	#
	Now = time.time()
	PumpStatus = GPIO.input(IO_Pump)
	SolarStatus = GPIO.input(IO_Solar)
	PoolTemp = ReadTemp(ADC_Pool)
	SolarTemp = ReadTemp(ADC_Solar)

	#
	# Control Logic
	#
	if (PumpStatus == 1 and SolarStatus == 1 and PoolTemp > PoolMaxTemp):
		if (Now-LastSolarChange > SolarChangeFrequency):
			LastLog = "Pool at or above target temperature - turning off solar"
			GPIO.output(IO_Solar,False)
			LastSolarChange = Now
	if (PumpStatus == 1 and SolarStatus == 1 and PoolTemp >= SolarTemp):
		if (Now-LastSolarChange > SolarChangeFrequency):
			LastLog = "Pool at or above solar temperature - turning off solar"
			GPIO.output(IO_Solar,False)
			LastSolarChange = Now
	if (PumpStatus == 1 and SolarStatus == 0 and PoolTemp < PoolMaxTemp and SolarTemp-PoolTemp > SolarPoolDiff):
		if (Now-LastSolarChange > SolarChangeFrequency):
			LastLog = "Pool below target temperature and solar differential reached - turning on solar"
			GPIO.output(IO_Solar,True)
			LastSolarChange = Now
	if (PumpStatus == 0 and SolarStatus == 1):
		if (Now-LastSolarChange > SolarChangeFrequency):
			LastLog = "Pool pump off - turning off solar"
			GPIO.output(IO_Solar,False)
			LastSolarChange = Now

	#
	# Display Logic
	#
	if (Now-LastDisplayUpdate > DisplayUpdateFrequency):	
		LCDMessage = "Pool  %3dF\nSolar %3dF" % (PoolTemp,SolarTemp)
		#Pump = "On" if PumpStatus==1 else "Off" 
		#Solar = "On" if SolarStatus==1 else "Off" 
		#print "Pump %s" % Pump
		#print "Solar %s" % Solar
		print LCDMessage
		lcd.clear()
		lcd.message(LCDMessage)
		LastDisplayUpdate = Now

	# Logging Logic
	if (Now-LastLogUpdate > LogUpdateFrequency):
		LogMessage = "%d,%d,%d,%d,%d,%s\n" % (Now,PumpStatus,SolarStatus,PoolTemp,SolarTemp,LastLog)
		f.write(LogMessage)
		f.flush()
		LastLog = ""
		LastLogUpdate = Now

	#
	# Keypad Button Logic
	#
	if lcd.is_pressed(LCD.UP):
		GPIO.output(IO_Pool,True)

	if lcd.is_pressed(LCD.DOWN):
		GPIO.output(IO_Pool,False)

	if lcd.is_pressed(LCD.RIGHT):
		GPIO.output(IO_Solar,True)

	if lcd.is_pressed(LCD.LEFT):
		GPIO.output(IO_Solar,False)
