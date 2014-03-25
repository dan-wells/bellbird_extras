#!/usr/bin/env python3
# (c) The contributors to Bellbird
# This code is licensed GPLv2+
# This script decodes a Bellbird lexicon file

# Usage decodelex fname_compressed_lex fname_cmu_lex_entries.c
# Script outputs an uncompressed dictionary 'dict'

import sys     # for argv
import re      # for regex
import symbols # module for symbol table functions

def find_sym_freq(lex):
    "Finds frequency of symbols in lexicon entries"

    freq_bins= [0]*256
    for line in lex:
        for j, elmnt in enumerate(line):
            freq_bins [int(elmnt)] += 1
    return freq_bins

def get_entries_only(lex):
    "Extract only entries from lexicon"

    entries = [0]*len(lex)
    for i, line in enumerate(lex):
        try:
            start = line.index('255')
        except ValueError:
            exit(1)
        entries[i] = line[start+1:]
    return entries

def get_phonemes_only(lex):
    "Extract only phonemes from lexicon"

    phonemes = [0]*len(lex)
    for i, line in enumerate(lex):
        try:
            end = line.index('255')
        except ValueError:
            exit(1)
        phonemes[i] = line[:end]
    return phonemes

def get_lex_as_lists(fname):
    "Prepare list of lists of decimal numbers of compressed dictionary"

    with open(fname, 'rb') as fp:
        rawdata = fp.read()

    lexbyline = rawdata.splitlines(True)
    lexbyline.pop(0)    # remove comment header
    lexbyline.pop()     # remove comment on last line

# convert lexicon into utf-8 strings
    for i, line in enumerate(lexbyline):
        lexbyline[i] = line.decode("utf_8")

# remove C comments and extraneous spaces
    for i, line in enumerate(lexbyline):
        lexbyline[i] = re.sub(" \/\*.*\*\/ ","",line)
        lexbyline[i] = re.sub(" *","",lexbyline[i])

# Convert into list of lists of decimal numbers 
    for i, line in enumerate(lexbyline):
        lexbyline[i] = lexbyline[i].replace('\n','')
        lexbyline[i] = lexbyline[i].split(',')
        lexbyline[i].pop()

    return lexbyline

def decode_entries_dict(entries,symdata):
    "Decode entries given symdata to give dictionary words"

    words = []
    for i, line in enumerate(entries):
        words.append(b'')
        numofsymbols=len(line)
        j=0
        while j<numofsymbols:
            if int(line[j]) == 1:
                words[i] = words[i] + bytes((int(line[j+1]),))
                j += 2
            else:
                words[i] = words[i] + symdata[int(line[j])].encode('ascii')
                j += 1
    return words

def decode_phonemes_dict(phonemes,symdata,rep_table):
    "Decode phonemes given symbol data and representation table for a dictionary"

    phones = []
    for i, line in enumerate(phonemes):
        phones.append(b'')
        numofsymbols=len(line)
        j=numofsymbols-1
        while j>-1:  # phoneme symbols are stored in reverse order so read them backwards
            sym = symdata[int(line[j])]
            for k in range(len(sym)):
                phones[i] = phones[i] + rep_table[sym[k]].encode('utf-8') + b' '
            j -= 1
    return phones

def main():

    rep_table = symbols.get_phonemes_rep_table(sys.argv[2])
    phonemes_symdata = symbols.get_phonemes_symdata(sys.argv[2])
    entries_symdata = symbols.get_entries_symdata(sys.argv[2])

    lex = get_lex_as_lists(sys.argv[1])

    entries = get_entries_only(lex)

    phonemes = get_phonemes_only(lex)

    phones = decode_phonemes_dict(phonemes,phonemes_symdata,rep_table)
    words = decode_entries_dict(entries,entries_symdata)

#   freq_bins = find_sym_freq(phonemes)
#   print(freq_bins)

    with open('dict', 'wb') as fp:
        for i in range(len(phones)):
            fp.write(words[i])
            fp.write(bytes(':','utf-8'))
            fp.write(phones[i])
            fp.write(bytes('\n','utf-8'))

if __name__ == "__main__":
    main()
