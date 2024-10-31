"""
    This script is the main helper-file for the LOFAR Decameter Sky Survey (LoDeSS).
    LoDeSS uses a calibration strategy that requires a bright in-field calibrator.
    As the choice of in-field calibrator seems to be rather important, I wrote this
    script to help users (and with users I mean primarily me) to find suitable candidates.
    There is not a lot of data on decameter frequencies, so I added a way to make a 
    spectrum. That way, you can easily check the spectrum (so you don't pick a target)
    that's turning over
    
    --------------------------------------------

    TODO:
       - Nothing, I am done. This code is perfect.
       - Introduce new bugs, because there are no bugs in this code
    
    --------------------------------------------

    HOWTO:
       - Just run:
            python3 infield_finder.py 120+52
        Here, the code on the right is the same as the name of the pointing according 
        to the LTA.
    
       - Optional arguments:
          x --fov :  how big the image should be
          x --circlerad  :  the radius of the "guiding" circle that helps you with finding the best calibrator sources.
"""

import warnings
from astropy.utils.exceptions import AstropyDeprecationWarning
warnings.simplefilter('ignore',AstropyDeprecationWarning)

import numpy as np
import matplotlib.pyplot as plt
import sys
import os
from astropy.coordinates import SkyCoord
from astropy.wcs import WCS
import astropy.units as u
import argparse
from astroquery.vizier import Vizier
from astroquery.ipac.ned import Ned
from astroquery.simbad import Simbad
from matplotlib.patches import Circle

__author__ = "Christian Groeneveld (groeneveld@strw.leidenuniv.nl)"
__email__ = "groeneveld@strw.leidenuniv.nl"

Vizier.ROW_LIMIT = -1
targets = [ {'name' : 'CasA', 'ra' : 6.123487680622104,  'dec' : 1.0265153995604648},
            {'name' : 'CygA', 'ra' : 5.233686575770755,  'dec' : 0.7109409582180791},
            {'name' : 'TauA', 'ra' : 1.4596748493730913, 'dec' : 0.38422502335921294},
            {'name' : 'HerA', 'ra' : 4.4119087330382163, 'dec' : 0.087135562905816893},
            {'name' : 'VirA', 'ra' : 3.276086511413598,  'dec' : 0.21626589533567378},
            {'name' : 'HydraA', 'ra' : 2.4352, 'dec' : -0.21099}]


current_point = []


def detect_ateam(point):
    for target in targets:
        name = target['name']
        ra = target['ra']
        dec = target['dec']
        target_coord = SkyCoord(ra=ra,dec=dec,unit=(u.rad,u.rad))
        print(f'Separation to {name} : {target_coord.separation(point)}')

    pointgal = point.transform_to('galactic')
    print(f'Galactic Coordinates: l: {pointgal.l.value:.4f} deg     b: {pointgal.b.value:.4f} deg')
    print('------------------------------')


def fix_name(name):
    # I really hate that this is necessary. But well
    clist = ['8C','4C','3C']
    print(name)
    for c in clist:
        if c in name:
            cataloglist = name.split(c)[1].split(' ')
            name = c + next(s for s in cataloglist if s)
    if '2C' in name:
        res = Simbad.query_objectids(name)['ID']
        for i in res:
            if '3C ' in i:
                name = i
    if 'NAME' in name:
        name = name.split('NAME')[-1]
    name = name.split('G')[0]
    print(name)
    return name


def on_pick(event):
    '''
        Find the nearest point; and show the relevant radio source from NED
    '''
    artist = event.artist
    data = artist.get_offsets()
    # find brightest object near click
    selfluxes = np.array(fluxes)[event.ind]
    selected_index = event.ind[np.argmax(selfluxes)]

    coord = w.pixel_to_world(*data[selected_index])
    try:
        current_point[-1].remove()
    except:
        pass
    curpoint = axes.scatter([data[selected_index][0]],[data[selected_index][1]],color='None',edgecolor='red',s=120)
    current_point.append(curpoint)
    print(f'"({coord.ra.value}, {coord.dec.value})"')
    process_pointing(coord)

def process_pointing(coord):
    _new_name_res = True
    spectrum.clear()
    if not _new_name_res:
        '''
            Old name resolution
        '''
        simb = Simbad.query_region(coord,radius=4*u.arcmin)
        print(simb)
        namelist = simb['MAIN_ID']
        # Order of precedence in the naming convention
        namelist = list(filter(lambda x: '[' not in x, namelist)) # Prevent tagged names to 'clog up' the namelist
        name = [namelist[0]]
        name += list(filter(lambda x: "NVSS" in x,namelist))
        name += list(filter(lambda x: "8C" in x,namelist))
        name += list(filter(lambda x: "4C" in x,namelist))
        name += list(filter(lambda x: "3C" in x,namelist))
        name = name[-1]
        name = fix_name(name)
        print(name)
        spectrum.set_title(name)
    else:
        '''
            New name resolution
        '''
        nvss = Vizier.query_region(coord,catalog='VIII/65/nvss',radius=2*u.arcmin)
        nvssname = 'NVSS J' + nvss[0][0]['NVSS']
        name = Ned.query_object(nvssname)['Object Name'][0]
        print(name)
        spectrum.set_title(name)
        name = nvssname

    res = Ned.get_table(name, table='photometry')
    freq = res['Frequency']
    flxd = res['Flux Density']
    lowfreqs = freq < 5e9
    freq = freq[lowfreqs]
    flxd = flxd[lowfreqs]
    spectrum.scatter(freq,flxd,color='black')
    spectrum.loglog()
    spectrum.set_ylabel('Flux (Jy)')
    spectrum.set_xlabel('Frequency (Hz)')
    spectrum.axvspan(15e6,30e6,color='lightgreen',alpha=0.4)

    fig.canvas.draw()

def find_sources(pointing,radius):
    sources = Vizier.query_region(pointing,radius=radius,catalog='VIII/97',column_filters={'Sp':'>3'})[0]
    ra = sources['RAJ2000']
    dec = sources['DEJ2000']
    flux = list(sources['Sp'])
    coords = [SkyCoord(rasel,desel,unit=(u.hourangle,u.deg)) for rasel,desel in zip(ra,dec)]
    return coords,flux

if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument('coord', help='Coordinates of the pointing')
    args.add_argument('--fov', help='Size of the final image in degrees',default = 18,type=float)
    args.add_argument('--circlerad', help='Size of the "guiding circle"',default=5, type=float)

    parser = args.parse_args()
    crd = SkyCoord(parser.coord,unit=(u.deg,u.deg))
    detect_ateam(crd)

    w = WCS(naxis=2)
    w.wcs.crpix = [1024,1024] # for resolution of 2048pix
    w.wcs.crval = parser.coord.split('+')
    w.wcs.cdelt = [parser.fov/2048,parser.fov/2048]
    w.wcs.ctype = ["RA---SIN","DEC--SIN"]

    fig = plt.figure(figsize=(18,7))
    axes = fig.add_subplot(121,projection=w)
    axes.set_transform(w)
    axes.coords[0].set_ticks(number=10)
    axes.set_title(f'P{parser.coord}')
    axes.coords[1].set_ticks(number=10)
    axes.grid(True)
    axes.set_ylim(0,2048)
    axes.set_xlim(0,2048)

    coords,fluxes = find_sources(crd,0.5*parser.fov*u.deg)
    pixels_positions = np.array([w.world_to_pixel(coordsel) for coordsel in coords]).T
    plt.scatter(pixels_positions[0],pixels_positions[1],c=fluxes,picker=10,label = 'VLSSR points')
    plt.gca().invert_xaxis()
    cb = plt.colorbar()
    cb.set_label("Flux from VLSSR (Jy, @74MHz)")

    axes.scatter([1024],[1024],marker='X', color='orangered',s=60,picker=10,label='Pointing center')
    axes.add_artist(Circle((1024,1024),parser.circlerad/parser.fov*2048,fill=False,edgecolor='orangered',linestyle='--',label=f'Circle (radius: {parser.circlerad} deg)'))

    fig.canvas.mpl_connect('pick_event', on_pick)
    
    spectrum = fig.add_subplot(122)

    plt.show()
