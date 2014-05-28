#!/usr/bin/env python3
# (c) The contributors to Bellbird
# This code is licensed GPLv2+
# This script encodes a Bellbird lexicon file

# Usage encodelex fname_cmu_lex_entries.c dict
# Script generates a file 'compressed-lex'

import sys     # for argv
import re      # for regex
import symbols # module of symbol table functions

def optimize_encoding(wordlen,encoding,lenencoding):
    "Optimize encoding length with slower guaranteed minimum finding method"

    num_to_test = 1
    for i in range(wordlen):
        num_to_test *= len(encoding[i])          #Will test every allowed encoding at every position
                                                 #This process contains degenerate cases
    bestlength = wordlen+1     #bestlength will be shortest number of bytes encoding (escaped bytes are 1 since not optimized)
    bestvec = []               #bestvec will be the current best vector of indexes within encoding[] to yield shortest encoding
    indexvec = []              #A counter to try every allowed combination of encoding[] during optimization
    for i in range(wordlen):
        indexvec.append(0)     #Initial position for counter
    testvec = []
    for i in range(wordlen):
        testvec.append(lenencoding[i][0])  #testvec is current combination of encoding[] to be tested

    for i in range(num_to_test):
        for j in range(wordlen):
            testvec[j] = lenencoding[j][indexvec[j]] #testvec is current combination of encoding[] to be tested
        j = 0
        count = 0
        while j< wordlen:                            #loop over j the position
            j += testvec[j]                          #step the current symbol length (this may step over other symbols)
            count += 1                               #increment byte count due to this symbol
        if count < bestlength:              #If current combination is better than previous store it
            bestlength = count
            bestvec = list(indexvec)

# This following section increments position counter so that eventually we cover all possible encoding combinations
# The algo is add with carry but with different numerical base at each position
        indexvec[wordlen-1] += 1
        for j in range(wordlen-1,0,-1):
            if indexvec[j] == len(encoding[j]):
                indexvec[j] = 0
                indexvec[j-1] += 1
            else:
                break

# Build the encoded list from the best combination found from above optimization
    encoded = []
    i=0
    while i< wordlen:
        encoded.append(encoding[i][bestvec[i]])
        i += lenencoding[i][bestvec[i]]

    return encoded

def encode_word(word,symdata):
    "Word encoding"

    wordlen = len(word)
    symdatalen = len(symdata)
    encoding = [ [] for x in range(wordlen) ]     #List of lists of possible encoding symbols at each position
    lenencoding = [ [] for x in range(wordlen) ]  #List of lists of lengths of above encoding symbols at each position
    i = 0
    while i<wordlen:                              #Loop of each position
        for j in range(2,symdatalen):             #Build encoding and lenencoding by finding allowed symbols for this position 
            sym=symdata[j]
            if word.find(sym,i,i+len(sym)) == i:
                encoding[i].append(repr(j)+',')
                lenencoding[i].append(len(sym))
        if len(encoding[i]) == 0:                 #No symbols encode this letter so fill with escaped sequence instead
            encoding_seg = []
            charbytes = word[i].encode('utf-8')
            lenchar = len(charbytes)
            for j in range(lenchar):
                encoding_seg.append(repr(1)+','+repr(charbytes[j])+',')
            encoding[i].append(''.join(encoding_seg))
            lenencoding[i].append(1)              # Escaped characters are not optimized
        i += 1

# Optimization stage
    encoded = optimize_encoding(wordlen,encoding,lenencoding)

    return encoded

def encode_phonelist(phonelist, symdata, rep_table):
    "Phoneme list encoding"

    if phonelist == ['']:
        return ['']
    phonelistlen = len(phonelist)
    symdatalen = len(symdata)
    i = 0
    while i<phonelistlen:
        for j in range(1,len(rep_table)):              #Replace phonelist with numerical ids
            if phonelist[i] == rep_table[j]:
                phonelist[i] = j
                break
        i += 1
    encoding = [ [] for x in range(phonelistlen) ]     #List of lists of possible encoding symbols at each phoneme position
    lenencoding = [ [] for x in range(phonelistlen) ]  #List of lists of lengths of above encoding symbols at each phoneme position
    i = 0
    while i<phonelistlen:                      #Loop of each phoneme position
        for j in range(1,symdatalen):          #Build encoding and lenencoding by finding allowed symbols for this phoneme position 
            sym=symdata[j]
            if phonelist[i:i+len(sym)] == sym:
                encoding[i].append(repr(j)+',')
                lenencoding[i].append(len(sym))
        i += 1

# Optimization stage
    encoded = optimize_encoding(phonelistlen,encoding,lenencoding)

    return encoded

def main():

    entries_symdata = symbols.get_entries_symdata(sys.argv[1])
    rep_table = symbols.get_phonemes_rep_table(sys.argv[1])
    phonemes_symdata = symbols.get_phonemes_symdata(sys.argv[1])
  
    with open(sys.argv[2], 'rb') as fp:
        rawdata = fp.read()

    dict = rawdata.splitlines(True)
    phone_dict = ['']*len(dict)
    for i, line in enumerate(dict):
        tmp = line.decode('utf_8')
        tmp = tmp.split(':')
        dict[i] = tmp[0]
        phone_dict[i] = tmp[1]

    bytecount = 1
    with open('compressed-lex', 'wb') as outfp:
        outfp.write(bytes('/* index to compressed data */\n','utf-8'))
        for i in range(len(dict)):
            word = dict[i]
            word = word.replace('\n','')
            tmp = encode_word(word,entries_symdata)
            encodedlineend = ' */ '+''.join(tmp)+'0,\n'
            phonelist = phone_dict[i]
            phonelist = phonelist.replace('\n','')
            phonelist = phonelist.split(' ')
            phonelist.pop()
            tmp = encode_phonelist(phonelist,phonemes_symdata,rep_table)
            encodedlinestart = '   '+''.join(reversed(tmp))+' 255, /* '
            bytecount += encodedlinestart.count(',')
            outfp.write(bytes(encodedlinestart,'utf-8')
                        +bytes(word,'utf-8')+bytes(encodedlineend,'utf-8'))
            bytecount += encodedlineend.count(',')
        outfp.write(bytes('/* num_bytes = ','utf-8') + bytes(repr(bytecount),'utf-8')+ bytes(' */\n','utf-8'))

if __name__ == "__main__":
    main()
