#!/usr/bin/python

import os
import sys
import re
import time
import random

#source=sys.argv[1]#:this is meant to be the custom file manually made by the developer,see input.txt
interface='MB_SB'
interface_endianess = {'MB_SB':'different',\
                       'SB_MB':'different',\
                       'IB_SB':'same',\
                       'SB_IB':'same',\
                       'SB_SB':'same',\
                       'MB_IB':'different',\
                       'IB_MB':'different',\
                       'IB_IB':'same'\
                       }

test_enc = '/scratch/kalyvas/git_trunk/test/unittest/lib/libisu/src/LibIsuEnc_'+interface+'_tlvs.cpp'
test_dec = '/scratch/kalyvas/git_trunk/test/unittest/lib/libisu/src/LibIsuDec_'+interface+'_tlvs.cpp'
input_file = 'unitest_caladan_input.txt'
byte_value = []
byte_buff = []



def is_same_endian(interface):

    if interface_endianess[interface] == 'same':
        return True

    return False

def handle_endian(value):

    endian_converted = value.split(',')                                                                                  
    endian_converted.reverse()
    return ','.join(endian_converted)
   

def calculate_bitfields(i,line,struct_fields,payload,bits):

    var_name = re.search('(?<= )(.+)(?= +:|:)',line).group(1).strip() 
    var_size = re.search('(\d)(?=;)',line).group(1).strip()

    def bit_worker(struct_fields,payload):
        if re.search('reserved|spare|unused',var_name):
            var_value = 0 #unused variable...
            bin_value = '0'*int(var_size)
            byte_value.insert(0,bin_value)
            exp = (payload+'.'+var_name+'='+str(var_value)+';','')
            struct_fields.append(exp)
        else:
            var_value = random.randint(0,int(var_size)**2-1) if int(var_size) != 1 else random.randint(0,1)
            bin_value = bin(var_value)[2:]#bin function spits 0bXXXXX.we only want to keep XXXXX
            byte_value.insert(0,bin_value)
            exp = (payload+'.'+var_name+'='+str(var_value)+';','')
            struct_fields.append(exp)

    if i in bits:
       # print 'Reached end of bitfield'
        global byte_value
        bit_worker(struct_fields,payload)
        hex_val = fill_bitfields(byte_value)
        byte_buff.append(hex_val)
        #print byte_value
        #print byte_buff
        #raw_input()
        byte_value = []
    else:
        bit_worker(struct_fields,payload)


def handle_large_hex(hex_value):

    #odd number of hex_value ...ie 0x1CB or OxFA2D2,etc (3,5,7,9,...) so we add a zero in front.else leave it.
    hex_value = hex_value[2:].strip('L')#put away the L indicating the LARGE number
    tmp = '0'+hex_value if len(hex_value)%2 != 0 else hex_value
    tmp1 = [tmp[i:i+2] for i in range(0, len(tmp), 2)]
    tmp2 = ['0x'+i for i in tmp1]
    tmp2.reverse()
    hex_value = ','.join(tmp2)
    return hex_value

def fill_bitfields(byte_value):
    tmp_hex_value = hex((int(''.join(byte_value),2)))
  #  print byte_value
    hex_value = tmp_hex_value[:2]+'0'+tmp_hex_value[-1].upper() if int(tmp_hex_value,16) in range(16) else tmp_hex_value[:2]+tmp_hex_value[2:].upper()
    return hex_value


def has_bitfields():

    data = tmp.readlines()
    ending_bits = []

    for i,line in enumerate(data):
        try:
            if ':' in line and i == len(data)-1:
                ending_bits.append(i)
            elif ':' in line and ':' not in data[i+1]:
                ending_bits.append(i)
        except IndexError:
            pass
    return ending_bits

def fill_values(i,line,struct_fields,payload,bits):

    if ':' in line:#bitfield
        calculate_bitfields(i,line,struct_fields,payload,bits)
   
    elif re.search('\[(\d+)\]',line) and ('reserved' in line or 'spare' in line ):#array that will be memset with zeroes
        array_name = re.search('(?= )(.+)(?=\[)',line).group(1).strip()
        array_size = re.search('(?<=\[)(\d+)(?=\])',line).group(1)
        byte_num = re.search('(?<=u)(\d+)(?=\s)',line).group(1).strip()
        hex_value = '0x00,'*((int(array_size)*(int(byte_num)/8)))
        exp = ('memset('+payload+'.'+array_name+',0,'+str(int(array_size)*(int(byte_num)/8))+');',hex_value.rstrip(','))
        struct_fields.append(exp)

    elif re.search('\[(\d+)\]',line):#ordinary array that will be filled randomly depending on the size
        array_name = re.search('(?= )(.+)(?=\[)',line).group(1).strip()
        array_size = re.search('(?<=\[)(\d+)(?=\])',line).group(1)
        byte_num = re.search('(?<=u)(\d+)(?=\s)',line).group(1)
        for i in range(int(array_size)):
            dec = random.randint(0,2**int(byte_num)-1)#alternatively we can use the hex_value formula when its a bitfield..see above...
            #hex_value = hex(dec)[:2]+hex(dec)[2:].upper()
            hex_value = handle_large_hex(hex(dec))
            exp = (payload+'.'+array_name+'['+str(i)+']='+str(dec)+';',hex_value)
            struct_fields.append(exp)

    elif 'reserved' in line or 'spare' in line:
        var_name = re.search('(?<= )(\w+)(?=;)',line).group(1).strip()   
        var_size = re.search('^u(\d+)',line).group(1).strip()
        var_value = 0
        hex_value = ('0x00,'*(int(var_size)/8)).rstrip(',')
        exp = (payload+'.'+var_name+'='+str(var_value)+';',hex_value)
        struct_fields.append(exp)     

    else:#everything else that is usually unsigned (8-bit,16-bit,32-bit,64-bit)
        var_name = re.search('(?<= )(\w+)(?=;)',line).group(1).strip()   
        var_size = re.search('^u(\d+)',line).group(1).strip()
        var_value = random.randint(0,2**int(var_size)-1)
        hex_value = handle_large_hex(hex(var_value))
        exp = (payload+'.'+var_name+'='+str(var_value)+';',hex_value)
        struct_fields.append(exp)


def create_test_buffer(struct_fields,payload):
    test_buff = ''
    for i,(exp,val) in enumerate(struct_fields):
        if val and i == len(struct_fields)-1:#last line to be processed that is not bitfield
            val = ' '*22+val+'};    //'+re.search(payload+'.'+'(.+)(?=\=|,)',exp).group(1).rstrip(',0')
            test_buff += '\n'+val
        elif val:
            val = ' '*22+val+',    //'+re.search(payload+'.'+'(.+)(?=\=|,)',exp).group(1).rstrip(',0')
            test_buff += '\n'+val
        elif not val:
            try:
                if struct_fields[i+1][1]:#next element has value,ie is not a bitfield.that means we need to pop
                    val = ' '*22+byte_buff.pop(0)
                    test_buff += '\n'+val+',   //byte for bitfields'
                elif not struct_fields[i+1][1]:#next element has bitfield...pass
                    pass
            except IndexError:#we reached the last element to process and its a bitfield
                val = ' '*22+byte_buff.pop(0)
                test_buff += '\n'+val+'};    //byte for bitfields'
    print 'test buffer'
    return test_buff


def create_test_encoder(payload,hex_id_type,hex_id_length,test_buffer,struct_fields):


    with open(test_enc,'a') as f:
        body = 'TEST_FIXTURE(Libisu_enc_'+interface+'_tlvs, LibIsuEnc'+interface+'_tlvs_'+payload+'){'
        body += '\n'+'    u8 test_buff[] = {'+hex_id_type
        body += '\n'+'                     '+hex_id_length
        body += test_buffer
        body += '\n\n'+'      tlv_msg_hdr_t *hdr = (tlv_msg_hdr_t *)malloc(2000);'
        body += '\n'+'      bzero(hdr, sizeof(tlv_msg_hdr_t));'
        body += '\n'+'      u32 tlv_buffer_size = 2000;'
        body += '\n\n'+'      libisu_'+payload+'_t '+payload+';'
        body += '\n'+'      bzero(&'+payload+',sizeof('+payload+'));'
        body += '\n'+'     '+'\n'.join([' '*7+exp for exp,val in struct_fields ])
        body += '\n\n'
        body += '\n'+'      CHECK_EQUAL(RETURN_OK,LIBISU_encode_'+payload+'(hdr,tlv_buffer_size,&'+payload+'));'
        body += '\n'+'      '+'CHECK(!memcmp((u8 *)hdr + TLV_MSG_HDR_SIZE, (u8 *)test_buff,hdr->total_length));'
        body += '\n'+'      '+'free(hdr);'
        body += '\n\n}'
        f.write(body)


def create_test_decoder(payload,hex_id_type,hex_id_length,id_length,test_buffer,struct_fields):

    length = 8 + 4 + int(id_length)#length here counts the header length of the tlv_msg_hdr_t,8 is the mandatory,4 is the TL,and the V
    hex_hdr_length = handle_large_hex(hex(length))
    total_length = 4 + int(id_length)#4 is the 4 bytes of T and L.So we add to this the payload (V) to find the total length
    hex_total_length = handle_large_hex(hex(total_length))
   
    if len(hex_hdr_length.split(',')) > 1:#length is so large it cannot fit in one byte only
        hex_hdr_length += ',  //header length'
    else:#most cases will be handled in here...
        hex_hdr_length = hex_hdr_length+',0x00,  //header length'


    #handle the endianness of total_length here
    #it can be applied also to hdr_length later...


    if not is_same_endian(interface) and len(hex_total_length.split(',')) > 1:
        hex_total_length = handle_endian(hex_total_length)
        hex_total_length += ', //total length'
    elif not is_same_endian(interface) and len(hex_total_length.split(',')) ==1:
        hex_total_length = '0x00,'+hex_total_length+', //total length'
    elif is_same_endian(interface) and len(hex_total_length.split(',')) > 1:
        hex_total_length += ', //total length'
    else:
        hex_total_length = hex_total_length+',0x00, //total length'
 


    tlv_msg_hdr = '{0x01,//msg_type'
    tlv_msg_hdr += '\n'+' '*27+hex_hdr_length
    tlv_msg_hdr += '\n'+' '*27+'0x00,//reserved1'
    tlv_msg_hdr += '\n'+' '*27+hex_total_length
    tlv_msg_hdr += '\n'+' '*27+'0x00,0x00,//reserved2'

    with open(test_dec,'a') as f:
        body = 'TEST_FIXTURE(Libisu_msg_dec_'+interface+'_tlvs, LibIsuMsgDec'+interface+'_tlvs_'+payload+'){'
        body += '\n'+'     u8 test_buff[] = {'+test_buffer
        body += '\n\n'+'     u8 encoded_buffer[] ='+tlv_msg_hdr
        body += '\n'+' '*27+hex_id_type
        body += '\n'+' '*27+hex_id_length
        body += ' '+test_buffer
        body += '\n\n'+'   libisu_'+payload+'_t *'+payload+' = (libisu_'+payload+'_t *)malloc(sizeof(libisu_'+payload+'_t));'
        body += '\n'+'     CHECK_EQUAL(RETURN_OK,LIBISU_decode_'+payload+'((tlv_msg_hdr_t *)encoded_buffer,'+payload+'));'
        body += '\n'+'     CHECK(!memcmp((u8 *)'+payload+', (u8 *)test_buff, sizeof(libisu_'+payload+'_t)));'
        body += '\n\n'+'   printf("DUMMY - decoded buffer: %s'+'\\'+'n", libconv_dump_to_str((u8 *)'+payload+',sizeof(libisu_'+payload+'_t)));'
        body += '\n'+'   printf("DUMMY - test buffer: %s'+'\\'+'n", libconv_dump_to_str((u8 *)test_buff,sizeof(libisu_'+payload+'_t)));'
        body += '\n'+'   free('+payload+');'
        body += '\n}\n'
        f.write(body)


def execute():

    struct_fields = []
    tmp.seek(0)
    bits = has_bitfields()
    tmp.seek(0)

    for i,line in enumerate(tmp):
        if 'TLV_ID' in line:
            line = line.split()

            id_type=re.search('---(\d+)',line[0]).group(1) #this is the T (number)of TLV
            hex_id_type =  hex(int(id_type))[:2]+'0'+hex(int(id_type))[-1].upper() if int(id_type) in range(16) else hex(int(id_type))[:2]+hex(int(id_type))[2:].upper()
            id_length=re.search('---(\d+)',line[1]).group(1)#this is the length of the payload of the TLV 
            hex_id_length = hex(int(id_length))[:2]+'0'+hex(int(id_length))[-1].upper() if int(id_length) in range(16) else hex(int(id_length))[:2]+hex(int(id_length))[2:].upper()
            hex_id_length = handle_large_hex(hex_id_length)#use case of lib_plain_buffer which occupies 1404 bytes



            #handle the endianess of TLV LENGTH here
            
            if not is_same_endian(interface) and len(hex_id_length.split(',')) > 1:#length is so large it cannot fit in one byte only
                hex_id_length = handle_endian(hex_id_length)
                hex_id_length += ',  //TLV LENGTH'

            elif not is_same_endian(interface) and len(hex_id_length.split(',')) ==1:#most cases will be handled in here...
                hex_id_length = '0x00,'+hex_id_length+',  //TLV LENGTH'
    
            elif is_same_endian(interface) and len(hex_id_length.split(',')) > 1:
                hex_id_length += ', //TLV LENGTH'
            else:
                hex_id_length = hex_id_length+',0x00, //TLV LENGTH'


            #handle the endianess of TLV_TYPE here,we should never exceed 256 TLVs per interface...
           #if we do,fix that by asking about the number of bytes it occupies.
            if not is_same_endian(interface):
                hex_id_type = '0x00,'+hex_id_type+',  //TLV TYPE'
            else:
                hex_id_type = hex_id_type+',0x00,    //TLV_TYPE'

          
            payload = re.search('libisu_(.+)---',line[1]).group(1)#this is the payload name  
            
        else:#we know that the line is not the end of the struct and is not a new line:
            line = line.strip()
            fill_values(i,line,struct_fields,payload,bits)

    print struct_fields
    #print ""
    # for i in struct_fields:
    #     print i[0]
    #     print ""
   # global byte_buff
    test_buffer = create_test_buffer(struct_fields,payload)
    create_test_encoder(payload,hex_id_type,hex_id_length,test_buffer,struct_fields)
    create_test_decoder(payload,hex_id_type,hex_id_length,id_length,test_buffer,struct_fields)
    tmp.close()
    os.remove('tmp.txt')


f = open(input_file)
line = f.readline()

try:
    print 'Hello'
    while 'THE END' not in line:
        tmp = open('tmp.txt','a+')
        for line in f:
            if 'THE END' not in line and '}' not in line:
                tmp.write(line)
            else:
                break
        print 'execution...'
        execute()    
        raw_input()
except UnboundLocalError:
    print 'End of processing...'

