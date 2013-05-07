import time

import os 
import sys
import procpy
import logging

log = logging.getLogger('mcpu')

hldr = logging.FileHandler('/var/log/mcpu.log')
form = logging.Formatter('%(asctime)s  %(message)s')
hldr.setFormatter(form)
log.addHandler(hldr)

from optparse import OptionParser

parser = OptionParser()
parser.add_option("-w", "--cpu_warn_threshold", default=10, help="warning threshold: cpu usage percent. default: 10")
parser.add_option("-e", "--cpu_error_threshold", default=80, help="error threshold: cpu usage percent. default: 80")
parser.add_option("-W", "--cpu_warn_hits", default=5, help="warning hits: warning time limit. default: 5")
parser.add_option("-E", "--cpu_error_hits", default=1, help="error hits: error time limit. default: 1")

parser.add_option("-m", "--memory_error_threshold", default=10, help="error threshold: memory usage percent. default: 10")
parser.add_option("-M", "--memory_error_hits", default=1, help="error hits: memory usage percent. default: 1")
parser.add_option("-d", "--delay", default=60, help="delay: time period between checks in seconds. default: 60 seconds")

(config, _ ) = parser.parse_args()

tics_sec = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
secs = int(time.time()) 
oldsecs = secs
procs = procpy.Proc()
oldprocs = {}



def read_procfs( procs, oldprocs, tics_per_sec, seconds_pass):
	global config, log

	for pid in procs.pids:
		current = procs.pidinfo(pid)
		if current['ruid'] < 1000 or current['ruid'] >= 65534:
			continue
		
		try:
			old = oldprocs[pid]
			if (current['start_time'] / 10) != (old['start_time'] / 10):
				raise Exception
		except:
			log.warning("Init new process %d " % pid)
			current['cpu_warn_hits'] = 0
			current['cpu_error_hits'] = 0
                        current['memory_error_hits'] = 0
			oldprocs[pid] = current
			continue

		curtime = current['stime'] + current['utime']
		oldtime = old['stime'] + old['utime']
		used = int((curtime - oldtime) * 100 / (tics_sec * seconds_pass)) 
		

		log.warning("Check process %s, Usage %s" % (pid, used))
		
		if used >= int(config.cpu_warn_threshold):
			if used >= int(config.cpu_error_threshold):
				old['cpu_error_hits'] += 1
				if old['cpu_error_hits'] >= int(config.cpu_error_hits):
					log.error("Error kill %s %s" % (pid, old['cpu_error_hits']))
					os.system("kill %d " % pid)
					del oldprocs[pid]
			old['cpu_warn_hits'] += 1
			os.system('renice -n 19 -p %d 2> /dev/null > /dev/null' % pid)
			if old['cpu_warn_hits'] >= int(config.cpu_warn_hits):
				log.warning("Warning kill %s %s" % (pid, old['cpu_warn_hits']))
				os.system("kill %d " % pid)
				del oldprocs[pid]
		
		if int(current['pmemstr'].split('.')[0]) >= int(config.memory_error_threshold):
			old['memory_error_hits'] += 1
			if old['memory_error_hits'] >= int(config.memory_error_hits):
				log.error("Error memory kill %s %s" % (pid, old['memory_error_hits']))
				os.system("kill %d " % pid)

if os.fork() > 0:
	sys.exit()

while True:
	time.sleep(float(config.delay))
	procs.update()
	secs = int(time.time())
	read_procfs(procs, oldprocs, tics_sec, secs - oldsecs)
	oldsecs = secs;
