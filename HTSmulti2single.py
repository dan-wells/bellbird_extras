#!/usr/bin/env python3
# (c) The contributors to Bellbird
# This code is licensed GPLv2+
# This script converts multifile HTS voices to single file HTS format
# It is a dev tool so contains minimum error checking and is slow (unoptimized)
# It is only intended to be executed a handful of times in its design life.

# Usage: HTSmulti2single dir_name_of_voice sampling_frequency frame_period alpha

import sys       # for argv
import os.path   # for directory path manipulation
import struct    # for unpacking data types on read

def convertpdfdata(vector_length,stream_size,msd,ntree,npdf,pdf_in_bindata):
    "Convert list of float pdf data from old format to new format"

    vector_segs = vector_length//stream_size
    finaldata = []  # a float list of binary data
    p = 0
    if msd == 1:
        for i in range(ntree):
            j=0
            while j<npdf[i]:
                pdf_out_bindata=[0]*(vector_length*2+1)
                for k in range(stream_size):
                    for l in range(vector_segs):
                        pdf_out_bindata[k*vector_segs+l] = pdf_in_bindata[p]
                        p += 1
                        pdf_out_bindata[k*vector_segs+vector_length+l] = pdf_in_bindata[p]
                        p += 1
                    if k == 0:
                        pdf_out_bindata[2*vector_length] = pdf_in_bindata[p]
                    p += 2
                finaldata = finaldata + pdf_out_bindata
                j += 1
    else:
        for i in range(ntree):
            j=0
            while j<npdf[i]:
                pdf_out_bindata=[0]*(vector_length*2)
                for k in range(vector_length):
                    pdf_out_bindata[k] = pdf_in_bindata[p]
                    p += 1
                    pdf_out_bindata[k+vector_length] = pdf_in_bindata[p]
                    p += 1
                finaldata = finaldata + pdf_out_bindata
                j += 1

    return finaldata

def number_of_trees(tree_file):
    "Count the number of trees in an inf file"

    if os.path.isfile(tree_file) != True:
        print('Error: unable to find :' + os.path.basename(tree_file))
        exit(1)
    with open(tree_file, 'r') as fp:
        ntree=fp.read().count('[')

    return ntree

def main():

# Define some data sizes
    size_of_int = 4    # size of int in original architecture voice was created
    size_of_float = 4  # size of float in original achitecture voice was created

# Clear data segment and initialize tracking pointer
    data_seg = b''   # this is binary data in 'bytes' format for [DATA] segment
# Note despite the existance of pointers the order of data in the data segment
# appears to matter. I was caught out on this initially.
    p_data_seg = 0 # We need to specify binary data counts so we use a counter

# Parse argv
    dirname=sys.argv[1]
    if os.path.isdir(dirname) != True:
        print("Error: unable to access directory of voice to be converted")
        exit(1)

    sampling_freq=sys.argv[2]
    frame_period=sys.argv[3]
    alpha = sys.argv[4]

# Define stream types used for output and input voice files
    if os.path.isfile(os.path.join(dirname,'lpf.pdf')):
        stream_types=['MCP','LF0','LPF']
        stream_types_file=['mgc','lf0','lpf']
    else:
        stream_types=['MCP','LF0']
        stream_types_file=['mgc','lf0']

    num_stream_types=len(stream_types)

# Read gv_off_context
    fname = os.path.join(dirname,'gv-switch.inf')
    if os.path.isfile(fname) == True:
        with open(fname, 'r') as fp:
            fdata = fp.read()
        fdata = fdata.split('{ ',1)[1] # throwaway everything before { and space
        gv_off_context = fdata.split(' }',1)[0] # throwaway everything after first space and }

# Fill use_gv list
    use_gv=[]
    for index in range(num_stream_types):
        fname = 'gv-'+stream_types_file[index]+'.pdf'
        if os.path.isfile(os.path.join(dirname,fname)) == True:
            use_gv.append(1)
        else:
            use_gv.append(0)

# Fill num_windows list
    num_windows=[]
    for index in range(num_stream_types):
        wincount = 1
        fname = stream_types_file[index]+'.win'+repr(wincount)
        while True:
            if os.path.isfile(os.path.join(dirname,fname)) != True:
                break
            wincount += 1
            fname = stream_types_file[index]+'.win'+repr(wincount)
        num_windows.append(wincount-1)

# Duration files processing

# find the number of trees in duration
    fname = os.path.join(dirname,'tree-dur.inf')
    ntree = number_of_trees(fname)

# buffer into memory duration pdf file
    fname = os.path.join(dirname,"dur.pdf")
    if os.path.isfile(fname) != True:
        print('Error: unable to find dur.pdf')
        exit(1)
    with open(fname, 'rb') as fp:
        msd = struct.unpack('>i',fp.read(size_of_int))[0]
        stream_size = struct.unpack('>i',fp.read(size_of_int))[0]
        vector_length = struct.unpack('>i',fp.read(size_of_int))[0]
        npdf = []
        for index in range(ntree):
            npdf.append(struct.unpack('>i',fp.read(size_of_int))[0])
        fvalarray = fp.read()
        num_floats = (len(fvalarray))//size_of_float
        pdf_in_bindata = list(struct.unpack('>'+repr(num_floats)+'f',fvalarray))

# convert duration pdf data
    pdf_out_data=convertpdfdata(vector_length,stream_size,msd,ntree,npdf,pdf_in_bindata)

# write out duration data
    for index in range(ntree):
        data_seg = data_seg + struct.pack('<i',npdf[index])
    for fval in pdf_out_data:
        data_seg = data_seg + struct.pack('<f',fval)

# save pointer information
    dur_begin = p_data_seg
    p_data_seg += ntree*size_of_int + len(pdf_out_data)*size_of_float
    dur_end = p_data_seg-1

# write out tree-dur.inf
    tree_file = os.path.join(dirname,'tree-dur.inf')
    with open(tree_file, 'rb') as fp:
        treedata = fp.read()
    data_seg = data_seg + treedata
    dur_tree_begin = p_data_seg
    p_data_seg += len(treedata)
    dur_tree_end = p_data_seg-1 
    dur_pdf_ptrs = repr(dur_begin)+'-'+repr(dur_end)
    dur_tree_ptrs = repr(dur_tree_begin)+'-'+repr(dur_tree_end)

# write out windows files
    max_windows = max(num_windows)
    win_begin = [0]*(num_stream_types*max_windows)
    win_end   = [0]*(num_stream_types*max_windows)
    for i in range(num_stream_types):
        for j in range(num_windows[i]):
            winfile = os.path.join(dirname,stream_types_file[i]+'.win'+repr(j+1))
            if os.path.isfile(winfile) != True:
                print('Error: unable to find ' + winfile)
                exit(1)
            with open(winfile,'rb') as fp:
                windata = fp.read()
            data_seg = data_seg + windata
            win_begin[i*max_windows+j] = p_data_seg
            p_data_seg += len(windata)
            win_end[i*max_windows+j] = p_data_seg-1

# stream pdf files processing

    stream_pdf_begin = []
    stream_pdf_end   = []
    stream_tree_begin = []
    stream_tree_end   = []
    is_msd = []
    stream_vector_length = []

    for i in range(num_stream_types):
        fname=os.path.join(dirname,'tree-'+stream_types_file[i]+'.inf')
        ntree=number_of_trees(fname)

        fname=os.path.join(dirname,stream_types_file[i]+'.pdf')
        if os.path.isfile(fname) != True:
            print('Error: unable to find ' + basename(fname))
            exit(1)
        with open(fname, 'rb') as fp:
            msd = struct.unpack('>i',fp.read(size_of_int))[0]
            stream_size = struct.unpack('>i',fp.read(size_of_int))[0]
            vector_length = struct.unpack('>i',fp.read(size_of_int))[0]
            npdf = []
            for index in range(ntree):
                npdf.append(struct.unpack('>i',fp.read(size_of_int))[0])
            fvalarray = fp.read()
            num_floats = (len(fvalarray))//size_of_float
            pdf_in_bindata = list(struct.unpack('>'+repr(num_floats)+'f',fvalarray))

        pdf_out_data=convertpdfdata(vector_length,stream_size,msd,ntree,npdf,pdf_in_bindata)

        for index in range(ntree):
            data_seg = data_seg + struct.pack('<i',npdf[index])
        for fval in pdf_out_data:
            data_seg = data_seg + struct.pack('<f',fval)

        stream_pdf_begin.append(p_data_seg)
        p_data_seg += ntree*size_of_int + len(pdf_out_data)*size_of_float
        stream_pdf_end.append(p_data_seg-1)
        is_msd.append(msd)
        stream_vector_length.append(vector_length)
        if i ==0:
            num_states = ntree

# write out stream tree files
    for i in range(num_stream_types):
        tree_file = os.path.join(dirname,'tree-'+stream_types_file[i]+'.inf')
        with open(tree_file, 'rb') as fp:
            treedata = fp.read()
        data_seg = data_seg + treedata
        stream_tree_begin.append(p_data_seg)
        p_data_seg += len(treedata)
        stream_tree_end.append(p_data_seg-1)

# gv pdf files processing

    gv_pdf_begin = []
    gv_pdf_end   = []
    gv_tree_begin = []
    gv_tree_end   = []

    for i in range(num_stream_types):
        if use_gv[i] == 1:
            fname=os.path.join(dirname,'tree-gv-'+stream_types_file[i]+'.inf')
            ntree=number_of_trees(fname)

            fname=os.path.join(dirname,'gv-'+stream_types_file[i]+'.pdf')
            if os.path.isfile(fname) != True:
                print('Error: unable to find ' + basename(fname))
                exit(1)
            with open(fname, 'rb') as fp:
                msd = struct.unpack('>i',fp.read(size_of_int))[0]
                stream_size = struct.unpack('>i',fp.read(size_of_int))[0]
                vector_length = struct.unpack('>i',fp.read(size_of_int))[0]
                print(vector_length)
                npdf = []
                for index in range(ntree):
                    npdf.append(struct.unpack('>i',fp.read(size_of_int))[0])
                fvalarray = fp.read()
                num_floats = (len(fvalarray))//size_of_float
                pdf_in_bindata = list(struct.unpack('>'+repr(num_floats)+'f',fvalarray))

            pdf_out_data=convertpdfdata(vector_length,stream_size,msd,ntree,npdf,pdf_in_bindata)

            for index in range(ntree):
                data_seg = data_seg + struct.pack('<i',npdf[index])
            for fval in pdf_out_data:
                data_seg = data_seg + struct.pack('<f',fval)

            gv_pdf_begin.append(p_data_seg)
            p_data_seg += ntree*size_of_int + len(pdf_out_data)*size_of_float
            gv_pdf_end.append(p_data_seg-1)
        else:
            gv_pdf_begin.append('')
            gv_pdf_end.append('')

# write out gv tree files
    for i in range(num_stream_types):
        if use_gv[i] == 1:
            tree_file = os.path.join(dirname,'tree-gv-'+stream_types_file[i]+'.inf')
            with open(tree_file, 'rb') as fp:
                treedata = fp.read()
            data_seg = data_seg + treedata
            gv_tree_begin.append(p_data_seg)
            p_data_seg += len(treedata)
            gv_tree_end.append(p_data_seg-1)
        else:
            gv_tree_begin.append('')
            gv_tree_end.append('')

# Some further header information calculations (mainly pointers)
    option = ['ALPHA=' + alpha,'','']
    win_ptrs = []
    for i in range(num_stream_types):
        win_ptrs_tmp = []
        for j in range(num_windows[i]):
            win_ptrs_tmp.append(repr(win_begin[i*max_windows+j])+'-'+repr(win_end[i*max_windows+j]))
        win_ptrs_tmp1 = ','.join(win_ptrs_tmp)
        win_ptrs.append(win_ptrs_tmp1)
    stream_pdf_ptrs = []
    stream_tree_ptrs = []
    gv_pdf_ptrs = []
    gv_tree_ptrs = []
    for i in range(num_stream_types):
        stream_pdf_ptrs.append(repr(stream_pdf_begin[i])+'-'+repr(stream_pdf_end[i]))
        stream_tree_ptrs.append(repr(stream_tree_begin[i])+'-'+repr(stream_tree_end[i]))
        if use_gv[i] == 1:
            gv_pdf_ptrs.append(repr(gv_pdf_begin[i])+'-'+repr(gv_pdf_end[i]))
            gv_tree_ptrs.append(repr(gv_tree_begin[i])+'-'+repr(gv_tree_end[i]))
        else:
            gv_pdf_ptrs.append('')
            gv_tree_ptrs.append('')

# Write header data to voice file
    fp = open(dirname+'.htsvoice', 'w')

    print('[GLOBAL]', file=fp)
    print('HTS_VOICE_VERSION:1.0', file=fp)
    print('SAMPLING_FREQUENCY:' + sampling_freq, file=fp)
    print('FRAME_PERIOD:'+ frame_period, file=fp)
    print('NUM_STATES:' + repr(num_states), file=fp)
    print('NUM_STREAMS:' + repr(num_stream_types), file=fp)
    print('STREAM_TYPE:' + ','.join(stream_types), file=fp)
    print('FULLCONTEXT_FORMAT:HTS_TTS_ENG', file=fp)
    print('FULLCONTEXT_VERSION:1.0', file=fp)
    print('GV_OFF_CONTEXT:' + gv_off_context, file=fp)
    print('COMMENT:', file=fp)
    print('[STREAM]', file=fp)
    for i in range(num_stream_types):
        print('VECTOR_LENGTH[' + stream_types[i] + ']:' + repr(stream_vector_length[i]//num_windows[i]), file=fp)
    for i in range(num_stream_types):
        print('IS_MSD[' + stream_types[i] + ']:' + repr(is_msd[i]), file=fp)
    for i in range(num_stream_types):
        print('NUM_WINDOWS[' + stream_types[i] + ']:' + repr(num_windows[i]), file=fp)
    for i in range(num_stream_types):
        print('USE_GV[' + stream_types[i] + ']:' + repr(use_gv[i]), file=fp)
    for i in range(num_stream_types):
        print('OPTION[' + stream_types[i] + ']:' + option[i], file=fp)
    print('[POSITION]', file=fp)
    print('DURATION_PDF:' + dur_pdf_ptrs, file=fp)
    print('DURATION_TREE:' + dur_tree_ptrs, file=fp)
    for i in range(num_stream_types):
        print('STREAM_WIN[' + stream_types[i] + ']:' + win_ptrs[i], file=fp)
    for i in range(num_stream_types):
        print('STREAM_PDF[' + stream_types[i] + ']:' + stream_pdf_ptrs[i], file=fp)
    for i in range(num_stream_types):
        print('STREAM_TREE[' + stream_types[i] + ']:' + stream_tree_ptrs[i], file=fp)
    for i in range(num_stream_types):
        if use_gv[i] == 1:
            print('GV_PDF[' + stream_types[i] + ']:' + gv_pdf_ptrs[i], file=fp)
    for i in range(num_stream_types):
        if use_gv[i] == 1:
            print('GV_TREE[' + stream_types[i] + ']:' + gv_tree_ptrs[i], file=fp)
    print('[DATA]', file=fp)

    fp.close()

# Append data segment to header in voice file
    with open(dirname+'.htsvoice', 'a+b') as fp:
        fp.write(data_seg)

if __name__ == "__main__":
    main()
