import os
import sys
import re
import subprocess
import time
import configparser
import logging
import datetime

date_str = datetime.datetime.now().strftime('%b_%d_%Y_%H_%M_%S')
NUM_OF_LBAs_PER_ITER = 0

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not os.path.exists(os.path.join(os.getcwd(), 'results')):
	os.mkdir(os.path.join(os.getcwd(), 'results'))



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
    gbb_data = GBB_out.decode('latin-1').split('\n')
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
    logger.info(f"{stage} GBB count : {GBB_count}")
    return GBB_count

def get_LBA2PHY_data(LBA2PHY_out):
    """
    Gets the GBB count from the output
    :param GBB_out: Output of Health Check VUC command to be passed here
    :return: Returns GBB_count
    """
    raw_data = {}
    LBA2Phy_data = {}
    gbb_data = LBA2PHY_out.decode('latin-1').split('\n')
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
    logger.info(f"Physical location is identified as below")
    for key in LBA2Phy_data.keys():
    	logger.info(f"{key} : {LBA2Phy_data[key]}")
    
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
        
    
        

def error_injection(device, phy_details, injection_level):
	rERR_conf = read_test_config('ReadERR')

	logger.info("****************************************************")
	cdw12 = hex((injection_level <<8) | 0xA0)
	cdw13 = hex((int(phy_details['fpage'],16)<<0x10) | int(phy_details['fblock'],16))
	cdw14 = hex((int(phy_details['die_address'],16)<<0x18) | \
			(int(rERR_conf['injection_length'], 16)<<0x10) | \
			(int(phy_details['plane_address'],16)<<0x8) | \
			int(phy_details['ch'],16)
			)

	error_cmd = f'sudo nvme admin-passthru {device} -o 0xc0 --cdw12={cdw12} --cdw13={cdw13} --cdw14={cdw14} -b -s'
	logger.info(f"Read error command executed : {error_cmd}")
	
	error_inj = run_command(error_cmd.split())
	

def vuc_write_lba(lba):
	pass	

def vuc_read_lba(lba):
	pass

def fio_readwrite_super_page(device, drive_capacity, rw, start_lba, num_of_pages):
	drive_capacity = int(drive_capacity)
	num_of_dies = 0
	if drive_capacity == 256:
		num_of_dies = 4
	elif drive_capacity == 512:
		num_of_dies = 8
	elif drive_capacity == 1024:
		num_of_dies = 16
	else:
		num_of_dies = None
		logger.error("Choose the correct drive capacity!!!")
		logger.error(f"You can choose only the capacities 256/512/1024 and you have choosen : {drive_capacity}")
		sys.exit()

	total_bytes = num_of_pages * num_of_dies *16000*2 #No of planes in demeter=2, 1 Plane size=16KB
	end_lba = int(start_lba) + (total_bytes/512)
	if rw=='write':
		status = fio_readwrite(device, 'write', offset=str(start_lba), size=str(total_bytes)+'B', pattern=pat)
	else:
		status = fio_readwrite(device, 'read', offset=str(start_lba), size=str(total_bytes)+'B', pattern=pat)
	logger.info(f"End LBA after read/write : {end_lba-1}")
	return end_lba-1, status

	

def generate_erase_fail(device, phy_details):
	eERR_conf = read_test_config('EraseERR')
	cdw12 = 0xA1
	cdw13 = hex((int(rERR_conf['Type'], 16)<<0x10) | int(phy_details['fblock'],16))
	cdw14 = hex((int(phy_details['die_address'],16)<<0x18) | int(phy_details['plane_address'],16)<<0x08 | int(phy_details['ch'],16))
	cdw15 = rERR_conf['Ch_Fail_Status_Bit']
	error_cmd = f'sudo nvme admin-passthru {device} -o 0xc0 --cdw12={cdw12} --cdw13={cdw13} --cdw14={cdw14} --cdw15={cdw15} -b -s'
	logger.info(error_cmd)
	
def generate_program_fail(device, phy_details):
	eERR_conf = read_test_config('EraseERR')
	cdw12 = 0xA1
	cdw13 = hex((int(rERR_conf['Type'], 16)<<0x10) | int(phy_details['fblock'],16))
	cdw14 = hex((int(phy_details['die_address'],16)<<0x18) | int(phy_details['plane_address'],16)<<0x08 | int(phy_details['ch'],16))
	cdw15 = rERR_conf['Ch_Fail_Status_Bit']
	error_cmd = f'sudo nvme admin-passthru {device} -o 0xc0 --cdw12={cdw12} --cdw13={cdw13} --cdw14={cdw14} --cdw15={cdw15} -b -s'
	logger.info(f"Generate Program Fail Command Executed : {error_cmd}")

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
    fio_rw = run_command(['sudo', 'fio', '--name=global', '--filename='+filename, '--filesize=10mb', '--rw='+ rw, '--size='+size, '--offset='+offset, '--name=job1', '--verify=pattern', '--verify_pattern='+pattern])
    fio_rw = fio_rw.decode('latin-1')
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
    	
def validate_lba(lba):
	drive_total_lba


gbb_opcode = read_test_config('OPCODE')['GBB_Read_From_Drive_Health_Opcode'.lower()]
lba2phy_opcode = read_test_config('OPCODE')['LBA2Phy_Opcode'.lower()]
err_inj_opcode = read_test_config('OPCODE')['Read_ERR_Inj_Opcode'.lower()]
    	
memory_health_command = f"sudo nvme admin-passthru /dev/nvme0n1 -o {gbb_opcode} --cdw10=0x2EE --cdw12=0x01 -s -r -l 0xBB8"
#lba2phy_command = f"sudo nvme admin-passthru /dev/nvme0n1 -o {lba2phy_opcode} --cdw10=0x80 --cdw12=0x78 --cdw13={lba} -s -r -l 0x30"
#err_inj_command = f"sudo nvme admin-passthru /dev/nvme0n1 -o {err_inj_opcode} --cdw10=0x11A --cdw12=0x01 -s -r -l 0x468"
 
#Execution starts from here
if __name__ == "__main__":
	try:
		cap = read_test_config('Generic')['capacity']
		cat = read_test_config('Generic')['category']
		sub = read_test_config('Generic')['sub_category']
			

		c_handler = logging.StreamHandler()
		f_handler = logging.FileHandler(os.path.join(os.getcwd(), 'results', f'{cat}_{sub}_{cap}_{date_str}.log'))


		c_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

		c_handler.setFormatter(c_format)
		f_handler.setFormatter(f_format)

		logger.addHandler(c_handler)
		logger.addHandler(f_handler)

		rERR_conf = read_test_config('ReadERR')
		dev = read_test_config('Generic')['device']
		pat = read_test_config('Generic')['pattern']
		char = "*"
		reference_GBB = 0
		start_of_test = True

		iterations = int(read_test_config('Generic')['iterations'])
		levels = rERR_conf['injection_level'].split(',')
		logger.info(f'*{char*52}')
		logger.info(f'* {char*17} Test Info Start {char*17}')
		logger.info(f'* Device choosen 			: {dev}	*')
		logger.info(f'* Drive Capacity 			: {cap}		*')
		logger.info(f'* Test Category  			: {cat}		*')
		logger.info(f'* Sub Category   			: {sub}	*')
		logger.info(f'* Read Write Pattern Choosen: {pat}		*')
		logger.info(f'**{char*15} Test Info End {char*15}****')
		gbb_opcode = read_test_config('OPCODE')['GBB_Read_From_Drive_Health_Opcode'.lower()]
		lba2phy_opcode = read_test_config('OPCODE')['LBA2Phy_Opcode'.lower()]
		err_inj_opcode = read_test_config('OPCODE')['Read_ERR_Inj_Opcode'.lower()]
				
		memory_health_command = f"sudo nvme admin-passthru {dev} -o {gbb_opcode} --cdw10=0x2EE --cdw12=0x01 -s -r -l 0xBB8"
		lba2phy_command = f"sudo nvme admin-passthru {dev} -o {lba2phy_opcode} --cdw10=0x80 --cdw12=0x78 --cdw13=0x0 -s -r -l 0x30"
		start_offset_for_error_inj = 0
		offset_change_flag = 0
		lba_offset = 14000
		
		for level in levels:
			error_level = int(level)
			reference_GBB = 0
			start_of_test = True
			
			logger.info(f"########################## Error Level : {error_level} #################################")
			for cycle in range(iterations):
				logger.info(f"------------- RFLevel{level} Iteration No : {cycle} -------------")
				offset_change_flag = offset_change_flag + 1
				if offset_change_flag == 4:
					offset_change_flag = 0
					lba_offset = lba_offset + NUM_OF_LBAs_PER_ITER
					
				#Step: 1
				logger.info(f"STEP 1 : Write operation for the iteration : {cycle}")
				ret_address = fio_readwrite_super_page(dev, cap, 'write', lba_offset, 12)

				#Step: 2
				logger.info(f"STEP 2 : Find physical address for the last LBA last written")
				l2p = run_command(lba2phy_command.split())
				#import pdb; pdb.set_trace()
				lba2phy = get_LBA2PHY_data(l2p)
				#import pdb; pdb.set_trace()

				#Step: 3
				logger.info(f"STEP 3 : Reading the Initial GBB count")
				initial_gbb_data = run_command(memory_health_command.split())
				initial_gbb = int(get_GBB_count(initial_gbb_data, failure_type="read", stage='initial'), 16)
				if start_of_test:
					reference_GBB = initial_gbb
					start_of_test = False

				#Step: 4
				logger.info(f"STEP 4 : Read Failure Error Injecting")
				error_injection(dev, lba2phy, error_level)

				#Step: 5
				logger.info(f"STEP 5 : Write operation after Error Injection")
				logger.info(f"Writing 2 Super Pages starting LBA : {ret_address[0]+1}")
				ret_address = fio_readwrite_super_page(dev, cap, 'write', ret_address[0]+1, 2)
				
				#Step: 6
				logger.info(f"STEP 6 : Read operation after Error Injection and Write")
				logger.info(f"Reading all the 14 Super Pages written in the iteration")
				ret_address = fio_readwrite_super_page(dev, cap, 'read', lba_offset, 14)
				NUM_OF_LBAs_PER_ITER = ret_address[0] + 1

				#Step: 7
				logger.info(f"STEP 7 : Drive reset")
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

				#Step: 8
				try:
					logger.info(f"STEP 8 : Read all the 14 super pages again after reset")
					logger.info("Read back the 14 super pages from the drive")
					lba,st = fio_readwrite_super_page(dev, cap, 'read', lba_offset, 14)
					if st:
						logger.info("Iteration Passed")
					else:
						logger.error("Iteration Failed")
						#break

				except Exception as e:
					logger.error("Exception occurred, during readback after resets !!!!")
					logger.error(e)
					logger.error("Test Failed")
					break
					
				#Step: 9
				logger.info(f"STEP 9 : Get the Final GBB count and compare it with initial GBB count")
				final_gbb_data = run_command(memory_health_command.split())
				#import pdb; pdb.set_trace()
				final_gbb = int(get_GBB_count(final_gbb_data, failure_type="read", stage="Final"), 16)

				if error_level < 3:
					if final_gbb == reference_GBB: 
						logger.info("GBB Pass")
					elif final_gbb > reference_GBB:
						logger.error("GBB Fail")
						logger.error(f"GBB count has increased. Initial GBB count : {reference_GBB} Final GBB count : {final_gbb}")
						break
					else:
						logger.error("GBB Fail")
						logger.error(f"Check GBB count. Initial GBB count : {reference_GBB} Final GBB count : {final_gbb}")
						break
						
				elif 7 > error_level >= 3:
					if final_gbb == reference_GBB + 1: 
						logger.info("GBB Pass")
						reference_GBB = reference_GBB + 1
					elif final_gbb == reference_GBB:
						logger.error("GBB Fail")
						logger.error(f"GBB count has not increased. Initial GBB count : {reference_GBB} Final GBB count : {final_gbb}")
						break
					elif final_gbb < reference_GBB:
						logger.error("GBB Fail")
						logger.error(f"Unexpected behaviour. Initial GBB count : {reference_GBB} Final GBB count : {final_gbb}")
						break
					else:
						logger.error("GBB Fail")
						logger.error(f"Unexpected behaviour. Initial GBB count : {reference_GBB} Final GBB count : {final_gbb}")
						break
				else:
					logger.error("Wrong Error level selected")
					break

	except Exception as e:
		logger.error("Something went wrong!!!")
		logger.error("Probably your drive might be missing. Check")
		logger.error(e)
		logger.error(f'{char*25} End of test {char*25}')



