#!/usr/bin/env python3
# (c) The contributors to Bellbird
# This code is licensed GPLv2+
# This module is to assist in bellbird lexicon encoding and decoding

import re    # for regex

def remove_c_like(symdata):
    "Remove C_like formating around data"

    for i in range(len(symdata)):
        symdata[i] = re.sub(',.*$', '', symdata[i])
        symdata[i] = re.sub(' *', '', symdata[i])
        symdata[i] = symdata[i].replace('"', '')
        symdata[i] = symdata[i].replace('\n', '')
    return symdata

def get_phonemes_rep_table(fname):
    "Read and prepare phonemes graphical representation table"

    with open(fname, 'r') as fpin:
        symdata = fpin.readlines()
    start = 0
    for i, line in enumerate(symdata):
        if 'cmu_lex_phone_table' in line:
            start = i
            break
    symdata = symdata[start+2:]
    end = 0
    for i, line in enumerate(symdata):
        if 'NULL' in line:
            end = i
            break
    symdata = symdata[:end]
    symdata = remove_c_like(symdata)
    return symdata

def get_phonemes_symdata(fname):
    "Read and prepare list of symbol data for phonemes"

    with open(fname, 'r') as fpin:
        symdata = fpin.readlines()
    start = 0
    for i, line in enumerate(symdata):
        if 'cmu_lex_phones_huff_table' in line:
            start = i
            break
    symdata = symdata[start+4:start+258]
    symdata = remove_c_like(symdata)
    for i in range(len(symdata)):
        symdata[i] = symdata[i].split('\\')
        symdata[i].pop(0)
        for j in range(len(symdata[i])):
            symdata[i][j] = int(symdata[i][j], 8) # convert from octal
    symdata.insert(0, [])

    return symdata

def get_entries_symdata(fname):
    "Read and prepare list of symbol data for entries"

    with open(fname, 'r') as fpin:
        symdata = fpin.readlines()
    start = 0
    for i, line in enumerate(symdata):
        if 'cmu_lex_entries_huff_table' in line:
            start = i
            break
    symdata = symdata[start+8:start+262]
    symdata = remove_c_like(symdata)
    symdata.insert(0, '')
    symdata.insert(0, '')

    for i in range(2, len(symdata)):
        symdata[i] = str(symdata[i])

    return symdata
