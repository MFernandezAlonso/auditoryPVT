import logging
import datetime
import time

import sounddevice as sd
import pandas as pd
import numpy as np

import pyxid2


#___________________________________________________
# CEDRUS RESPONSE PAD
#___________________________________________________

#_____________________
## connect to Cedrus device
def connectToCedrus():

    # get a list of all attached XID devices
    devices = pyxid2.get_xid_devices()

    if not devices:
        raise ConnectionError(
            "Cedrus response pad not detected. Please close Vizard, connect the device and reopen the program.")

    dev = devices[0]  # get the first device to use

    dev.reset_timer()  # make sure that this works

    return dev


#_____________________
## get Cedrus responses

def waitCedrusResponse(dev, timeout_sec, keyList=[0, 1, 2, 3, 4]):

    keysPressed = []
    responseTimes = []

    dev.flush_serial_buffer()
    dev.clear_response_queue()

    dev.reset_timer()  # restart timer

    endTime = time.perf_counter() + timeout_sec

    while time.perf_counter() <= endTime:

        dev.poll_for_response()

        if dev.has_response():

            response = dev.get_next_response()

            if response['pressed'] and response['key'] in keyList:
                responseTimes.append(response['time'])
                keysPressed.append(response['key'])

    return responseTimes, keysPressed





#___________________________________________________
# AUDITORY PVT
#___________________________________________________

# Generate sequence of random time intervals wihtin limits that add up to total duration

def genRandTimeIntervals(total_s, 
                         min_s,
                         max_s):
    
    movingTotal = 0
    timesArray = []
    
    while movingTotal < total_s:

        # generate random time interval between min and max
        randTime = np.random.uniform(low = min_s, high = max_s, size = 1)[0]

           # would it exceed total duration?
        if sum(timesArray, randTime) > total_s:

                # calculate remaining time
                remainingTime = total_s - movingTotal

                # is it less than minimum time interval?
                if remainingTime < min_s:
                                    
                    # remove previous interval, it will iterate
                    timesArray.pop(-1)
                    movingTotal = sum(timesArray) 
                    

                # if not, then add remaining time to list
                else:
                    timesArray.append(remainingTime) 
                    movingTotal = sum(timesArray)
                    
            # add random time interval to array
        else:
            
            timesArray.append(randTime) 
            movingTotal = sum(timesArray)

    print(timesArray)
    
    return timesArray




# get ID for audio device according to keyword, default is Microsoft's Realtek audio
def getAudioDeviceID(keyword='realtek'):

    deviceFound = False
    listOutputDevices = sd.query_devices()

    for d in listOutputDevices:

        # check if it is an output device
        if d['max_input_channels'] == 0:

            # check if keyword matches name
            if keyword.lower() in d['name'].lower():

                # get device ID
                audioDeviceID = d['index']
                deviceFound = True
                break

    # if no device found, return default output device
    if not deviceFound:
        defDevice = sd.query_devices(kind='output')

        logging.warning('\nNo audio output device found with keyword ' + keyword + '!\n'
                        'Using instead the default audio device:   ' + defDevice['name'])

        audioDeviceID = defDevice['index']

    return audioDeviceID



# create sound waveform
def createPVTSound(frequency=1000, 
                   soundDuration_ms=475):

    # parameters
    rate = 48000  # samples per sec
    T = soundDuration_ms / 1000  # duration_secs
    f = frequency  # frequency Hz

    # compute waveform
    t = np.linspace(0, T, int(T*rate), endpoint=False)
    x = np.sin(2 * np.pi * f * t)

    return x, rate



# Run auditory PVT
def runPVT(cedrusDeviceHandle,
           totalDuration_s,
           minInterval_s=1, maxInterval_s=9,
           resultsFileName='',
           audioDeviceKeyword='realtek',
           soundDuration_ms=375,
           soundFrequency_hz=1000,
           soundVolume=0.09,
           keys=[0, 1, 2, 3, 4]):

    
    if not resultsFileName: # generate filename
        resultsFileName = 'aditoryPVT_' + datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    
    
    # choose audio device
    audioDeviceID = getAudioDeviceID(keyword=audioDeviceKeyword)
    sd.default.device = audioDeviceID
    
    # create sound wave according to input parameters
    [soundArray, soundRate] = createPVTSound(frequency = soundFrequency_hz, 
                                             soundDuration_ms = soundDuration_ms)

    # generate list if random time intervals
    randTimeArray = genRandTimeIntervals(total_s = totalDuration_s, 
                                         min_s = minInterval_s, 
                                         max_s = maxInterval_s)
    
    # to save results
    d_Timestamps = []
    d_IntervalTime = []
    d_RTs = []
    d_Keys = []

    startTime_ms = time.perf_counter_ns() / 1e6
        
    for t in randTimeArray:
        
        # play sound
        sd.play(soundArray, soundRate)
        soundTimestamp_ms = time.perf_counter_ns() / 1e6 - startTime_ms
        sd.wait()
        
        time.sleep(t)
        responseTimes = 0
        keysPressed = 0
        
        # capture all responses during interval
        [responseTimes,keysPressed] = waitCedrusResponse(dev = cedrusDeviceHandle,
                                                         timeout_sec = t,
                                                         keyList = keys)

        # save results
        d_Timestamps.append(soundTimestamp_ms)
        d_IntervalTime.append(t)
        d_RTs.append(responseTimes)
        d_Keys.append(keysPressed)


    # add results to dataframe
    df = pd.DataFrame({'SoundStartTimestamp_ms': d_Timestamps,
                    'IntervalToNextSound_s': d_IntervalTime,
                    'KeysPressed': d_Keys,
                    'ResponseTimes_ms': d_RTs})
    
    df.to_csv(resultsFileName)
    
    return df
