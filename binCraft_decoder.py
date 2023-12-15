#!/usr/bin/python3
# -*- coding: utf-8 -*-
import struct
import math
import pandas as pd

def unpack(fmt,buff):
	vals = struct.iter_unpack(fmt, buff)
	r = []
	for val in vals:
		r.append(val[0])

	return r
def getHex(i):
	h = hex(i).split('x')[-1]
	return h
def genStr(data,start,end):
	s = ""
	i = start
	while data[i] and i < end:
		if 32 < data[i] < 127:
			s += chr(data[i])
		i += 1
	s = s.strip();
	return s
def getType(t):
	if t == 0:
		return 'adsb_icao'
	if t == 1:
		return 'adsb_icao_nt'
	if t == 2:
		return 'adsr_icao'
	if t == 3:
		return 'tisb_icao'
	if t == 4:
		return 'adsc'
	if t == 5:
		return 'mlat'
	if t == 6:
		return 'other'
	if t == 7:
		return 'mode_s'
	if t == 8:
		return 'adsb_other'
	if t == 9:
		return 'adsr_other'
	if t ==10:
		return 'tisb_trackfile'
	if t ==11:
		return 'tisb_other'
	if t ==12:
		return 'mode_ac'
	return 'unknown'

def testWqi(file,zstd_compressed=False):
	with open(file, "rb") as f:
		data = f.read()
	if zstd_compressed:
		import zstd
		data = zstd.decompress(data)
	r = {}
	buffer = data.buffer
	pass


def create_uint32_array(buffer, offset, length,type):
    # Assuming buffer is a bytes-like object
    # offset is the starting index
    # length is the number of uint32 elements

    # Calculate the end index based on the length of the array
    
    if type == 'Uint32Array':
        end_index = offset + length * 4  # 4 bytes per uint32
        sub_buffer = buffer[offset:end_index]
        array = struct.unpack(f'{length}I', sub_buffer)
    elif type == 'Int32Array':
        end_index = offset + length * 4
        sub_buffer = buffer[offset:end_index]
        array = struct.unpack(f'{length}i', sub_buffer)
    elif type == 'Uint16_array':
        end_index = offset + length * 2
        sub_buffer = buffer[offset:end_index]
        array = struct.unpack(f'{length}H', sub_buffer)
    elif type ==  "Int16Array":
        end_index = offset + length * 2
        sub_buffer = buffer[offset:end_index]
        array = struct.unpack(f'{length}h', sub_buffer)
    elif type == "Uint8Array":
        end_index = offset + length 
        sub_buffer = buffer[offset:end_index]
        array = struct.unpack(f'{length}B', sub_buffer)
    return array


def binCraftReader(file,zstd_compressed=False):
	with open(file, "rb") as f:
		data = f.read()

	if zstd_compressed:
		import zstd
		data = zstd.decompress(data)

	r = {}

	#Vals
	vals = unpack('I', data)
	r['now'] = vals[0] / 1000 + vals[1] * 4294967.296
	r['global_ac_count_withpos'] = vals[3]
	r['globeIndex'] = vals[4]
	r['stride'] = vals[2]
	r['binCraftVersion'] = vals[10]
	stride = vals[2]
	del vals 

	#Bounds
	limits = unpack('h', data[20:])
	r['south'] = limits[0]
	r['west'] = limits[1]
	r['north'] = limits[2]
	r['east'] = limits[3]
	del limits

	#Aircraft
	r['aircraft'] = []
	for off in range(stride,len(data),stride):
		ac = {}

		u32 = create_uint32_array(data,off, int(stride/4),'Uint32Array')
		s32 = create_uint32_array(data,off, int(stride/4),'Int32Array')
		u16 = create_uint32_array(data,off, int(stride/2), 'Uint16_array' )
		s16 = create_uint32_array(data,off, int(stride/2), 'Int16Array')
		u8  = create_uint32_array(data,off, int(stride), 'Uint8Array')

		# ac['hex'] = format(16777215 & s32[0], '06x')
		# ac['hex'] = f"~{ac['hex']}" if t else ac['hex']

		ac['hex'] = getHex(s32[0] & ((1<<24) - 1)).zfill(6)
		ac['seen_pos'] = u16[2] / 10;
		ac['seen'] = u16[3] / 10;

		ac['lat'] = s32[2] / 1e6;
		ac['lon'] = s32[3] / 1e6;

		ac['baro_rate'] = 8 * s16[8]
		ac['geom_rate'] = 8 * s16[9]
		# ac['baro_rate'] = s16[10] * 8;
		# ac['geom_rate'] = s16[11] * 8;

		ac['alt_baro'] = 25 * s16[10] 
		ac['alt_geom'] = 25 * s16[11] 
		# ac['alt_baro'] = s16[8] * 25 
		# ac['alt_geom'] = s16[9] * 25 
		ac['nav_altitude_mcp'] = u16[12] * 4;
		ac['nav_altitude_fms'] = u16[13] * 4;
		ac['nav_qnh'] = s16[14] / 10; 
		ac['nav_heading'] = s16[15] / 90;
		ac['squawk'] = getHex(u16[16]).zfill(4)
		ac['gs'] = s16[17] / 10;
		ac['mach'] = s16[18] / 1000;
		ac['roll'] = s16[19] / 100;

		ac['track'] = s16[20] / 90;
		ac['track_rate'] = s16[21] / 100;
		ac['mag_heading'] = s16[22] / 90;
		ac['true_heading'] = s16[23] / 90;

		ac['wd'] = s16[24];
		ac['ws'] = s16[25];
		ac['oat'] = s16[26];
		ac['tat'] = s16[27];

		ac['tas'] = u16[28];
		ac['ias'] = u16[29];
		ac['rc'] = u16[30];
		ac['messages'] = u16[31];
		ac['messageRate'] = u16[31] / 10 if r['globeIndex'] and r['binCraftVersion'] >= 20220916 else u16[31]

		ac['category'] = getHex(u8[64]).upper() if u8[64] else None
		ac['nic'] = u8[65];


		ac['emergency'] = u8[67] & 15;
		ac['type'] = (u8[67] & 240) >> 4;

		ac['airground'] = u8[68] & 15;
		ac['nav_altitude_src'] = (u8[68] & 240) >> 4;

		ac['sil_type'] = u8[69] & 15;
		ac['adsb_version'] = (u8[69] & 240) >> 4;

		ac['adsr_version'] = u8[70] & 15;
		ac['tisb_version'] = (u8[70] & 240) >> 4;

		ac['nac_p'] = u8[71] & 15;
		ac['nac_v'] = (u8[71] & 240) >> 4;

		ac['sil'] = u8[72] & 3;
		ac['gva'] = (u8[72] & 12) >> 2;
		ac['sda'] = (u8[72] & 48) >> 4;
		ac['nic_a'] = (u8[72] & 64) >> 6;
		ac['nic_c'] = (u8[72] & 128) >> 7;

		ac['rssi'] = 10 * math.log10(u8[105]*u8[105]/65025 + 1.125e-5);
		ac['dbFlags'] = u16[43];
		ac['extraFlags'] = u8[106];

		ac['flight'] = genStr(u8,78,87)
		ac['t'] = genStr(u8,88,92)
		ac['r'] = genStr(u8,92,104)

		ac['receiverCount'] = u8[104];
		ac['nic_baro']      = (u8[73] & 1);
		ac['alert']        = (u8[73] & 2);
		ac['spi']           = (u8[73] & 4);

		if ac['airground'] == 1:
			ac['alt_baro'] = "ground";

		nav_modes = u8[66];
		ac['nav_modes'] = [];
		if (nav_modes & 1):
			ac['nav_modes'].append('autopilot')
		if (nav_modes & 2):
			ac['nav_modes'].append('vnav')
		if (nav_modes & 4):
			ac['nav_modes'].append('alt_hold')
		if (nav_modes & 8):
			ac['nav_modes'].append('approach')
		if (nav_modes & 16):
			ac['nav_modes'].append('lnav')
		if (nav_modes & 32):
			ac['nav_modes'].append('tcas')

		ac['type'] = getType(ac['type'])


		r['aircraft'].append(ac)

	return r


#r = testWqi(r"D:\work\Dev\地图爬取\飞机信息\outFile\1702432765.bin",True)
# c= [11]
# c = c *1000
# f =  int(108 + 108/4+1)  
# print(f/4)
# d = c[108: f]
#aa = [1,2,3,4,5,6,7,8,9,0]
#cc = aa[1:4]

# r = binCraftReader(r"D:\work\Dev\地图爬取\飞机信息\outFile\1702432765.bin",True)
# aa = r['aircraft']
# df = pd.DataFrame(aa)
# df.to_csv('D:\\aa.csv' )

# print (aa)