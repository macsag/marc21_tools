def normalizacja_100(str):
    #usuwa kropki i spacje na końcu rekordu

    if str[-1] in ('.', ' '):
        str_mid = str[:-1]
        if str_mid[-1] in ('.', ' '):
            str_out = str_mid[:-1]
        else:
            str_out = str_mid
    else:
        str_out = str
    return str_out

print(normalizacja_100("maciej sagata"))