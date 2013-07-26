#!/sw64/bin/python2.7

import time
import os
import subprocess
import sys
import shutil

sys.path.append('..')
import great3

# Set which branches to test...
experiments = [
    'control',
    #'real_gal',
    #'real_psf',
    #'multiepoch',
    #'full',
]
obs_type = [
    'ground',
    'space',
]
shear_type = [
    'constant',
    #'variable',
]

root = 'test_run'
subfield_max = 2                # I keep this small so the test doesn't take too long.
data_dir = 'great3_fit_data'    # This should be set up as a sim-link to your Dropbox folder.
seed = 12345                    # Whatever.

# Clean up possible residue from previous runs.
shutil.rmtree(root, ignore_errors=True)

# Build catalogs, etc.
t1 = time.time()
great3.run(root, subfield_max=subfield_max,
           experiments=experiments, obs_type=obs_type, shear_type=shear_type,
           dir=data_dir, seed=seed, steps=['metaparameters', 'catalogs', 'config']
)
t2 = time.time()
print
print 'Time for great3.run up to config = ',t2-t1
print

# build images using galsim_yaml
dirs = []
os.chdir(root)
for exp in experiments:
    e = exp[0]
    if e == 'r': e = exp[5]
    for obs in obs_type:
        o = obs[0]
        for shear in shear_type:
            s = shear[0]
            f = e + o + s + '.yaml'
            dirs.append( os.path.join(root,exp,obs,shear) )
            t1 = time.time()
            p = subprocess.Popen(['galsim_yaml',f,'-v1'])
            p.communicate() # wait until done
            t2 = time.time()
            print
            print 'Time for galsim_yaml',f,'= ',t2-t1
            print
os.chdir('..')

# Build images using great3.run
t1 = time.time()
great3.run(root, subfield_max=subfield_max,
           experiments=experiments, obs_type=obs_type, shear_type=shear_type,
           dir=data_dir, seed=seed, steps=['images']
)
t2 = time.time()
print
print 'Time for great3.run images = ',t2-t1
print

# Check that images are the same.
print 'Checking diffs: (No output means success)'
for dir in dirs:
    for i in range(subfield_max+1):
        f1 = os.path.join(dir,'image-%03d-0.fits'%i)
        f2 = os.path.join(dir,'yaml_image-%03d-0.fits'%i)
        p = subprocess.Popen(['diff',f1,f2])
        p.communicate()

