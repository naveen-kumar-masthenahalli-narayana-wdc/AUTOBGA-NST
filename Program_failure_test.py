import os
import sys
import re
import subprocess
import time
import configparser
import datetime
import logging

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
    	logger.error("Please check the command")
    	logger.error(e)
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
    logger.info(LBA2Phy_data)
    return LBA2Phy_data


def read_test_config(block, config_file='test_conf.ini'):
    """
    Gets the GBB count from the output
    :param GBB_out: Output of Health Check VUC command to be passed here
    :return: Returns GBB_count
    """
    config = configparser.ConfigParser()
    config.read_file(open(config_file))
    if block == "GBBT":
        logger.info(dict(config.items("GBB_Offset")))
        return dict(config.items("GBB_Offset"))
    elif block == 'LBA2PHY':
        logger.info(dict(config.items("LBA2PHY_Offset")))
        return dict(config.items("LBA2PHY_Offset"))
    elif block == 'ReadERR':
    	logger.info(dict(config.items("Read_Error_Injection_Offset")))
    	return dict(config.items("Read_Error_Injection_Offset"))
    elif block == 'OPCODE':
    	logger.info(dict(config.items("OPCODE")))
    	return dict(config.items("OPCODE"))
    elif block == 'EraseERR':
    	logger.info(dict(config.items("Erase_Error_Injection_Offset")))
    	return dict(config.items("Erase_Error_Injection_Offset"))
    elif block == 'ProgramERR':
    	logger.info(dict(config.items("Program_Error_Injection")))
    	return dict(config.items("Program_Error_Injection"))
    else:
    	logger.error("Invalid section in your Configuration file. Please check!!!")
    	return -1
        
    
        

def error_injection(device, phy_details):
	rERR_conf = read_test_config('ReadERR')
	for key, value in rERR_conf.items():
		print(key, value)
	logger.info("****************************************************")
	cdw12 = hex((int(rERR_conf['injection_level'], 16)<<8) | 0xA0)
	cdw13 = hex((int(phy_details['fpage'],16)<<0x10) | int(phy_details['fblock'],16))
	cdw14 = hex((int(phy_details['die_address'],16)<<0x18) | \
			(int(rERR_conf['injection_length'], 16)<<0x10) | \
			(int(phy_details['plane_address'],16)<<0x8) | \
			int(phy_details['ch'],16)
			)

	error_cmd = f'sudo nvme admin-passthru {device} -o 0xc0 --cdw12={cdw12} --cdw13={cdw13} --cdw14={cdw14} -b -s'
	logger.info(error_cmd)
	
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

def vuc_read_super_page(start_lba, num_of_pages):

	total_bytes = num_of_pages*4*16000*2
	end_lba = start_lba + total_bytes/512
	fio_readwrite('/dev/nvme0n1', 'read', offset=str(start_lba), size=str(total_bytes), pattern="0xdeadface")
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
    	logger.info(f'Reading data from {filename} at offset {offset} of total size={size} and pattern to verify is {pattern}')
    else:
    	logger.info(f'Writing data from {filename} at offset {offset} of total size={size} and pattern to verify is {pattern}')
    	
    if 'verify_pattern'==None:
    	fio_rw = run_command(['sudo', 'fio', '--name=global', '--filename='+filename, '--rw='+ rw, '--size='+size, '--offset='+offset, '--name=job1'])
    else:
    	fio_rw = run_command(['sudo', 'fio', '--name=global', '--filename='+filename, '--rw='+ rw, '--size='+size, '--offset='+offset, '--name=job1', '--verify=pattern', '--verify_pattern='+pattern])
    fio_rw = fio_rw.decode('ascii')
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
    	logger.error(f"FIO {rw} operation is unsuccessful :(")
    	return 0

gbb_opcode = read_test_config('OPCODE')['GBB_Read_From_Drive_Health_Opcode'.lower()]
lba2phy_opcode = read_test_config('OPCODE')['LBA2Phy_Opcode'.lower()]
err_inj_opcode = read_test_config('OPCODE')['Read_ERR_Inj_Opcode'.lower()]
    	
memory_health_command = f"sudo nvme admin-passthru /dev/nvme0n1 -o {gbb_opcode} --cdw10=0x2EE --cdw12=0x01 -s -r -l 0xBB8"

lba2phy_command = f"sudo nvme admin-passthru /dev/nvme0n1 -o {lba2phy_opcode} --cdw10=0x80 --cdw12=0x78 --cdw13=0x0 -s -r -l 0x30"

#err_inj_command = f"sudo nvme admin-passthru /dev/nvme0n1 -o {err_inj_opcode} --cdw10=0x11A --cdw12=0x01 -s -r -l 0x468"
 
#Execution starts from here
if __name__ == "__main__":

	rERR_conf = read_test_config('ReadERR')
	reference_GBB = 0
	start_of_test = True
	l_offset = 0x1000000
	for cycle in range(5):
		logger.info(f"########################## Iteration No : {cycle} #################################")
		#Step: 1
		fio_readwrite('/dev/nvme0n1', 'write', offset=str(l_offset), size='10mB', pattern="0xdeadface")

		#Step: 2
		laddres = (10*1024*1024)/512 - 1 + 0x1000000
		lba2phy_command = f"sudo nvme admin-passthru /dev/nvme0n1 -o {lba2phy_opcode} --cdw10=0x80 --cdw12=0x78 --cdw13={laddres} -s -r -l 0x30"
		l2p = run_command(lba2phy_command.split())
		#import pdb; pdb.set_trace()
		lba2phy = get_LBA2PHY_data(l2p)
		#import pdb; pdb.set_trace()

		#Step: 3
		initial_gbb_data = run_command(memory_health_command.split())
		initial_gbb = int(get_GBB_count(initial_gbb_data, failure_type='program'), 16)
		logger.info(f"Initial GBB count for Iteration {cycle} : {initial_gbb}")
		if start_of_test:
			reference_GBB = initial_gbb
			start_of_test = False

		#Step: 4
		generate_program_fail('/dev/nvme0n1', lba2phy)

		#Step: 5
		fio_readwrite('/dev/nvme0n1', 'write', offset='0x1005000', size='200mB', pattern="0xdeadface")

		#Step: 6
		final_gbb_data = run_command(memory_health_command.split())
		final_gbb = int(get_GBB_count(final_gbb_data, failure_type='program', stage="Final"), 16)
		logger.info(f"Final GBB count for Iteration {cycle} : {final_gbb}")

		if final_gbb == reference_GBB+1:
			logger.info("GBB Pass")
			logger.info("Iteration Passed")
			reference_GBB = reference_GBB + 1
		else:
			logger.error("GBB Fail")
			logger.error("Iteration Failed")
			logger.error("#"*20 + " FAIL " + "#"*20)
			logger.error("GBB count has not increased")
				


		#Step: 7
		try:
			if False:
				logger.info("Disabling the drive")
				run_command(['rmmod', 'nvme'])
				time.sleep(10)
				logger.info("Enabling the drive")
				run_command(['modprobe', 'nvme'])
				time.sleep(10)
			else:
				logger.info("Running command to Reset PCIe bus")
				run_command(['./pcie_reset.sh', '03:00.0'])
				
			time.sleep(5)
		except Exception as e:
			logger.error("Exception occurred, during readback after resets !!!!")
			logger.error(e)
			logger.error("Test Failed")
			break






