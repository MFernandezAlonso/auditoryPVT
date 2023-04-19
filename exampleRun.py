
import apvt

# connect to Cedrus
cedrus = apvt.connectToCedrus()


# run PVT
apvt.runPVT(cedrusDeviceHandle = cedrus, 
			totalDuration_s = 30, 
			minInterval_s = 1, maxInterval_s = 9,
            resultsFileName ='testAPVT.csv',)