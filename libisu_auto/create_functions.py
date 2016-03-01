#!/usr/bin/python

import os
import sys
import re

# source=sys.argv[1]#:this is meant to be the custom file manually made by
# the developer,see input.txt
IF = 'MB_SB'
hdr_enc = '/scratch/kalyvas/git_trunk/src/lib/libisu/include/libisu_msg_enc_' + IF + '_tlv.h'
hdr_dec = '/scratch/kalyvas/git_trunk/src/lib/libisu/include/libisu_msg_dec_' + IF + '_tlv.h'
src_enc = '/scratch/kalyvas/git_trunk/src/lib/libisu/src/libisu_msg_enc_' + IF + '_tlv.c'
src_dec = '/scratch/kalyvas/git_trunk/src/lib/libisu/src/libisu_msg_dec_' + IF + '_tlv.c'


def append(file_ch, function, flag=""):

    data = []
    new_data = []
    second = []
    with open(file_ch) as f:
        data = f.readlines()

    for i, line in enumerate(reversed(data)):
        if re.search(';', line):
            break
        else:
            second.append(line)

    second.reverse()

    for _ in range(i):
        data.pop()

    payload = function[7:]  # 7 is the size of the libisu_ string
    if flag == 1:  # we are encoding
        prototype = 'return_t LIBISU_encode_' + payload + \
            '(tlv_msg_hdr_t *hdr, u32 tlv_buffer_size, ' + \
            function + '_t *' + payload + ');'
    else:
        prototype = 'return_t LIBISU_decode_' + payload + \
            '(tlv_msg_hdr_t *hdr, ' + function + '_t *' + payload + ');'
    data.append('    ' + prototype + '\n')
    new_data = data + second
    f = open(file_ch, 'w')
    f.writelines(new_data)
    f.close()


def append_define(file_ch, function, flag=""):

    payload = function[7:]
    with open(file_ch, 'a') as f:
        if flag == 1:  # we are defining encoder function
            body = '\n' + 'return_t LIBISU_encode_' + payload + \
                '(tlv_msg_hdr_t *hdr, u32 tlv_buffer_size, ' + \
                function + '_t *' + payload + ')'
            body += '\n' + '{' + '\n' + '    if (LIBTLV_isu_put_opt(hdr, tlv_buffer_size, (u16)' + \
                ID + ', ' + payload + \
                    ', sizeof(' + function + '_t),TRUE)){' + '\n'
            body += '          LIBISU_INFO_("Failed to encode ' + \
                ID + '");' + '\n'
            body += '          return RETURN_NOK;'
            body += '\n' + '}'
            body += '\n' + '    return RETURN_OK;'
            body += '\n' + '}'
        else:
            body = '\n' + 'return_t LIBISU_decode_' + payload + \
                '(tlv_msg_hdr_t *hdr,' + function + '_t *' + payload + '){'
            body += '\n'
            body += '\n' + '    u16 tmp_len = 0;'
            body += '\n' + '    void *tmp_pnt = NULL;'
            body += '\n\n' + \
                '    if (LIBTLV_isu_get_param(hdr,(u16)' + \
                ID + ',&tmp_pnt,&tmp_len,TRUE) == 0) {'
            body += '\n' + '         memcpy(' + payload + ',tmp_pnt,tmp_len);'
            body += '\n' + '         return RETURN_OK;'
            body += '\n' + '     }'
            body += '\n' + '    else {'
            body += '\n' + \
                '        LIBISU_INFO_("Failed to decode ' + ID + '");'
            body += '\n' + '        return RETURN_NOK;'
            body += '\n' + '    }'
            body += '\n' + '}'
        f.write(body)


def declare_encoder():
    append(hdr_enc, function, 1)


def declare_decoder():
    append(hdr_dec, function, 0)


def define_encoder():
    append_define(src_enc, function, 1)


def define_decoder():
    append_define(src_dec, function, 0)


for line in open('input.txt'):
    line = line.split()
    ID = line[0]
    function = line[1]

    declare_encoder()
    declare_decoder()
    define_encoder()
    define_decoder()
