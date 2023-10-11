import os
import sys
import re
import subprocess
import time
import configparser
import logging
import datetime

date_str = datetime.datetime.now().strftime('%b_%d_%Y_%H_%M_%S')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

c_handler = logging.StreamHandler()
f_handler = logging.FileHandler(f'{date_str}.log')

c_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

c_handler.setFormatter(c_format)
f_handler.setFormatter(f_format)

logger.addHandler(c_handler)
logger.addHandler(f_handler)

def run_command(command):
    """
    Gets the GBB count from the output
    :param GBB_out: Output of Health Check VUC command to be passed here
    :return: Returns GBB_count
    """
    try:	
    	sp = subprocess.Popen(command, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    	a = sp.stdout.read()
    	#sp.communicate(input="AutoBGA123")
    	return a
    except Exception as e:
    	print("Please check the command")
    	print(e)
    	return -1
    	
def get_GBB_count(GBB_out, failure_type="read", stage='Initial'):
    """
    Gets the GBB count from the output
    :param GBB_out: Output of Health Check VUC command to be passed here
    :return: Returns GBB_count
    """    
    gbb_conf = read_test_config('GBBT')
    gbb_list = []
    #import pdb; pdb.set_trace()
    gbb_data = GBB_out.decode('ascii').split('\n')
    for line in gbb_data:
        match = re.search('([0-9]|[a-f])+:', line)
        if match:
            key, val = line.split(' "')[0].split(":")
            gbb_list.extend(val.lstrip().split())
    #import pdb; pdb.set_trace()
    width = ''
    if failure_type == 'program':
    	GBB_offset = int(gbb_conf['total_program_failure_block_count'])
    	width = int(gbb_conf['total_program_failure_block_count_width'])
    elif failure_type == 'read':
    	GBB_offset = int(gbb_conf['total_read_failure_block_count'])
    	width = int(gbb_conf['total_read_failure_block_count_width'])
    elif failure_type == 'erase':
    	GBB_offset = int(gbb_conf['total_erase_failure_block_count'])
    	width = int(gbb_conf['total_erase_failure_block_count_width'])
    else:
    	return -1
    GBB_count = ''
    GBB_count = gbb_list[GBB_offset : GBB_offset+width]
    GBB_count.reverse()
    GBB_count = "".join(GBB_count)
    logger.info(f"{stage} count is : {GBB_count}")
    return GBB_count

def get_LBA2PHY_data(LBA2PHY_out):
    """
    Gets the GBB count from the output
    :param GBB_out: Output of Health Check VUC command to be passed here
    :return: Returns GBB_count
    """
    raw_data = {}
    LBA2Phy_data = {}
    gbb_data = LBA2PHY_out.decode('ascii').split('\n')
    gbb_conf = read_test_config('LBA2PHY')
    #with open(LBA2PHY_out, 'rb') as gbb_data:
    for line in gbb_data:
        match = re.search('([0-9]|[a-f])+:', line)
        if match:
            key, val = line.split(' "')[0].split(":")
            raw_data[int(key,16)] = val.lstrip().split()
    #import pdb; pdb.set_trace()
    
    for key, multiplier in gbb_conf.items():
        offset = (4*int(multiplier))%16
        LBA2Phy_data[key] = ''
        if int(multiplier) in [0,1,2,3]:
            for i in range(4):
                LBA2Phy_data[key] = raw_data[0][offset+i] + LBA2Phy_data[key]
        elif int(multiplier) in [4,5,6,7]:
            for i in range(4):
                LBA2Phy_data[key] = (raw_data[16][offset+i]) + LBA2Phy_data[key]
        else:
            for i in range(4):
                LBA2Phy_data[key] = (raw_data[32][offset+i]) + LBA2Phy_data[key]
    print(LBA2Phy_data)
    return LBA2Phy_data


def read_test_config(block, config_file='test_conf.ini'):
    """
    Gets the GBB count from the output
    :param GBB_out: Output of Health Check VUC command to be passed here
    :return: Returns GBB_count
    """
    config = configparser.ConfigParser()
    config.read_file(open(config_file))
    logger.debug(f"{block} config params")
    if block == "GBBT":
        logger.debug(dict(config.items("GBB_Offset")))
        return dict(config.items("GBB_Offset"))
    elif block == 'LBA2PHY':
        logger.debug(dict(config.items("LBA2PHY_Offset")))
        return dict(config.items("LBA2PHY_Offset"))
    elif block == 'ReadERR':
    	logger.debug(dict(config.items("Read_Error_Injection_Offset")))
    	return dict(config.items("Read_Error_Injection_Offset"))
    elif block == 'OPCODE':
    	logger.debug(dict(config.items("OPCODE")))
    	return dict(config.items("OPCODE"))
    elif block == 'EraseERR':
    	logger.debug(dict(config.items("Erase_Error_Injection_Offset")))
    	return dict(config.items("Erase_Error_Injection_Offset"))
    elif block == 'Generic':
    	logger.debug(dict(config.items("Generic")))
    	return dict(config.items("Generic"))
    else:
    	logger.error("Invalid section in your Configuration file. Please check!!!")
    	return -1
        
    
        

def error_injection(device, phy_details):
	rERR_conf = read_test_config('ReadERR')
	for key, value in rERR_conf.items():
		print(key, value)
	print("****************************************************")
	cdw12 = hex((int(rERR_conf['injection_level'], 16)<<8) | 0xA0)
	cdw13 = hex((int(phy_details['fpage'],16)<<0x10) | int(phy_details['fblock'],16))
	cdw14 = hex((int(phy_details['die_address'],16)<<0x18) | \
			(int(rERR_conf['injection_length'], 16)<<0x10) | \
			(int(phy_details['plane_address'],16)<<0x8) | \
			int(phy_details['ch'],16)
			)

	error_cmd = f'sudo nvme admin-passthru {device} -o 0xc0 --cdw12={cdw12} --cdw13={cdw13} --cdw14={cdw14} -b -s'
	print(error_cmd)
	
	error_inj = run_command(error_cmd.split())
	

def vuc_write_lba(lba):
	pass	

def vuc_read_lba(lba):
	pass

def vuc_write_super_page(start_lba, num_of_pages):

	total_bytes = num_of_pages*4*16000*2
	end_lba = start_lba + total_bytes/512
	fio_readwrite('/dev/nvme0n1', 'write', offset=str(start_lba), size=str(total_bytes), pattern="0xdeadface")
	return end_lba
	
def fio_read_write_inMB(device, start_lba, size_in_MB, rw='read'):
	logger.info(f"Start LBA of the r/w operation is : {start_lba}")
	total_bytes = size_in_MB*1048576
	end_lba = start_lba + total_bytes/512 - 1
	fio_readwrite(device, rw, offset=str(start_lba), size=str(total_bytes), pattern="0xdeadface")
	logger.info(f"Last LBA of the r/w operation is : {end_lba}")
	return end_lba

def vuc_read_super_page(device, start_lba, num_of_pages):

	total_bytes = num_of_pages*4*16000*2
	end_lba = start_lba + total_bytes/512
	fio_readwrite(device, 'read', offset=str(start_lba), size=str(total_bytes), pattern="0xdeadface")
	return end_lba	

def generate_erase_fail(device, phy_details):
	eERR_conf = read_test_config('EraseERR')

	cdw12 = 0xA1
	cdw13 = hex((int(eERR_conf['type'], 16)<<0x10) | int(phy_details['fblock'],16)+1)
	cdw14 = hex((int(phy_details['die_address'],16)<<0x18) | int(phy_details['plane_address'],16)<<0x08 | int(phy_details['ch'],16))
	cdw15 = eERR_conf['ch_fail_status_bit']
	error_cmd = f'sudo nvme admin-passthru {device} -o 0xc0 --cdw12={cdw12} --cdw13={cdw13} --cdw14={cdw14} --cdw15={cdw15} -b -s'
	logger.debug(f"Generate EF cmd : error_cmd")
	run_command(error_cmd.split())

	
def generate_program_fail(device, phy_details):
	pERR_conf = read_test_config('ProgramERR')

	cdw12 = hex((int(pERR_conf['type'], 16)<<0x08) | 0xA2)
	cdw13 = hex((int(phy_details['fpage'],16)<<0x10) | int(phy_details['fblock'],16)+1)
	cdw14 = hex(int(phy_details['die_address'],16)<<0x18 | int(phy_details['plane_address'],16)<<0x08 | int(phy_details['ch'],16))

	error_cmd = f'sudo nvme admin-passthru {device} -o 0xc0 --cdw12={cdw12} --cdw13={cdw13} --cdw14={cdw14} -b -s'
	logger.info(error_cmd)
	run_command(error_cmd.split())
	logger.info("Error injected successfully")


def fio_readwrite(filename, rw, offset='0', size=None, runtime=None, pattern=None, logfile=None):
    """
    Gets the GBB count from the output
    :param GBB_out: Output of Health Check VUC command to be passed here
    :return: Returns GBB_count
    """
    if logfile == None:
    	logfile = os.path.join(os.getcwd(), "fio_log")
    if rw == 'read':
    	print(f'Reading data from {filename} at offset {offset} of total size={size} and pattern to verify is {pattern}')
    else:
    	print(f'Writing data from {filename} at offset {offset} of total size={size} and pattern to verify is {pattern}')
    logger.info(" ".join(['sudo', 'fio', '--name=global', '--filename='+filename, '--rw='+ rw, '--size='+size, '--offset='+offset, '--name=job1', '--verify=pattern', '--verify_pattern='+pattern]))
    fio_rw = run_command(['sudo', 'fio', '--name=global', '--filename='+filename, '--rw='+ rw, '--size='+size, '--offset='+offset, '--name=job1', '--verify=pattern', '--verify_pattern='+pattern, '--verify_dump=1'])
    fio_rw = fio_rw.decode('ascii')
    logger.info("------------- FIO Execution Summary Start--------------------")
    #logger.info(fio_rw)
    logger.info("------------- FIO Execution Summary End--------------------") 
    success = False
    
    for line in fio_rw.split('\n'):
    	if "job" in line and "err" in line:
    		match = re.search("err= (\d+)", line)
    		try:
    			if match.group(1) == "0":
    				success = True
    			else:
    				success = False
    		except:
    			success = False
    if success == True:
    	logger.info(f"FIO {rw} operation is successful :)")
    	return 1
    else:
    	logger.info(f"FIO {rw} operation is unsuccessful :(")
    	return 0



#err_inj_command = f"sudo nvme admin-passthru /dev/nvme0n1 -o {err_inj_opcode} --cdw10=0x11A --cdw12=0x01 -s -r -l 0x468"
 
#Execution starts from here
if __name__ == "__main__":

	rERR_conf = read_test_config('ReadERR')
	dev = read_test_config('Generic')['device']
	pat = read_test_config('Generic')['pattern']
	iterations = int(read_test_config('Generic')['iterations'])
	levels = rERR_conf['injection_level'].split(',')
	logger.info(f"Device Under Test(DUT) 	: {dev}")
	logger.info(f"Pattern for Write 		: {pat}")
	logger.info(f"Number of iterations 		: {iterations}")
	
	gbb_opcode = read_test_config('OPCODE')['GBB_Read_From_Drive_Health_Opcode'.lower()]
	lba2phy_opcode = read_test_config('OPCODE')['LBA2Phy_Opcode'.lower()]
	err_inj_opcode = read_test_config('OPCODE')['Read_ERR_Inj_Opcode'.lower()]
			
	memory_health_command = f"sudo nvme admin-passthru {dev} -o {gbb_opcode} --cdw10=0x180 --cdw12=0x01 -s -r -l 0x600"
	reference_GBB = 0
	start_of_test = True
	for cycle in range(iterations):
		logger.info(f"########################## Iteration No : {cycle} #################################")
		#Step: 1
		last_lba = fio_read_write_inMB(dev, 0,1,'write')
		lba2phy_command = f"sudo nvme admin-passthru {dev} -o {lba2phy_opcode} --cdw10=0x80 --cdw12=0x78 --cdw13={last_lba} -s -r -l 0x30"
		logger.debug(f"LBA2PHY cmd : {lba2phy_command}")
		#Step: 2
		l2p = run_command(lba2phy_command.split())
		#import pdb; pdb.set_trace()
		lba2phy = get_LBA2PHY_data(l2p)
		#import pdb; pdb.set_trace()

		#Step: 3
		logger.debug(f"Memory health cmd : {memory_health_command}")
		initial_gbb_data = run_command(memory_health_command.split())
		#import pdb; pdb.set_trace()
		initial_gbb = int(get_GBB_count(initial_gbb_data, failure_type="erase", stage='Initial'), 16)
		if start_of_test:
			reference_GBB = initial_gbb
			start_of_test = False

		#Step: 4
		#generate_erase_fail(dev, lba2phy)

		#Step: 5
		last_lba_200 = fio_read_write_inMB(dev, last_lba+1,200,'write')

		#Step: 6
		last_lba_200 = fio_read_write_inMB(dev, 0,201,'read')

		final_gbb_data = run_command(memory_health_command.split())
		final_gbb = int(get_GBB_count(final_gbb_data, failure_type="erase", stage='Final'), 16)

		if final_gbb == reference_GBB + 1 :
			logger.info("GBB Pass")
			reference_GBB = reference_GBB + 1
		
		else:
			logger.info("GBB Fail")
			logger.info(f"Previous GBB count {reference_GBB} Current GBB count {final_gbb} ")
			break	







