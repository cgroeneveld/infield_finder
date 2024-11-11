import os,sys,glob
import html as htmllib
import numpy as np
import urllib.request
import argparse
import pyperclip

def process_bibcode(bibcode,copy):
    htmlname = f'https://ui.adsabs.harvard.edu/abs/{bibcode}/exportcitation'
    encodename = htmlname.replace("&","%26")
    print(encodename)
    with urllib.request.urlopen(encodename) as response:
        html = response.read()
    htmlout = html.split(b'\n')
    # Find what to select
    tosel = False 
    out = []
    for line in htmlout:
        if b'export-textarea form-control' in line:
            tosel=True
        if b'</textarea>' in line:
            tosel=False
        if tosel:
            out.append((line+b'\n').decode("UTF-8"))

    out[0] = out[0].split('readonly="">')[1]
    if copy:
        text = htmllib.unescape(''.join(out))
        pyperclip.copy(text)
    else:
        with open('out.bib','w') as handle:
            for line in out:
                handle.write(htmllib.unescape(line))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("bibcode",default=None,nargs='?')
    parser.add_argument("--copy","-c",action='store_true',default=False)
    parser.add_argument("--paste","-p", action='store_true',default=False)
    res = parser.parse_args()

    if res.bibcode ==None and not res.paste:
        print('require either bibcode or paste')
        exit
    elif res.paste:
        bibcode = pyperclip.paste()
    else:
        bibcode = res.bibcode
    process_bibcode(bibcode,res.copy)
