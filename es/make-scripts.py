# Copyright (c) 2014, the GREAT3 executive committee (http://www.great3challenge.info/?q=contacts)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted
# provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this list of conditions
# and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice, this list of
# conditions and the following disclaimer in the documentation and/or other materials provided with
# the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors may be used to
# endorse or promote products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
# IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
# OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import sys, os
import shutil
import great3sims
from great3sims import mass_produce_utils, files

from argparse import ArgumentParser

parser=ArgumentParser(__doc__)
parser.add_argument('run',help="run to create")

args=parser.parse_args()

run=args.run

run_root = files.get_run_dir(run)
data_root = files.get_data_dir(run)

if not os.path.exists(data_root):
    os.makedirs(data_root)

# these have to match constants.py because somewhere an option
# is not being passed though, ugh
# Number of config files to be run per branch.
n_config_per_branch = 260
#n_config_per_branch = 2
# The total number of subfields is split up into n_config_per_branch config files.
subfield_min = 0
#subfield_max = 204
subfield_max = 259
#subfield_max = 1

seed = 20

# amount to increment seed for each successive branch
delta_seed = 17

# seconds between checks for programs to be done

package_only = False # only do the packaging and nothing else
do_images = True  # Make images or not?  If False with package_only also False, then just skip the
                  # image-making step: remake catalogs but do not delete files / dirs with images,
                  # then package it all up.
do_gal_images = True # Make galaxy images?  If do_images = True, then do_gal_images becomes
                     # relevant; it lets us only remake star fields if we wish (by having do_images
                     # = True, do_gal_images = False).
preload = True # preloading for real galaxy branches - irrelevant for others.

# Set which branches to test.
experiments = [
    'control',
    'real_galaxy',
]
obs_types = [
    'ground',
]
shear_types = [
    'constant',
]
branches = [ (experiment, obs_type, shear_type)
             for experiment in experiments
             for obs_type in obs_types
             for shear_type in shear_types]
n_branches = len(branches)
print "Producing images for ",n_branches," branches"

if not package_only:

    # First we set up a process for each branch.  We use a different random seed for each, and we do
    # the following steps: metaparameters, catalogs, config.  For config, there is some additional
    # juggling to do for config file names / dirs.
    prefix1 = 'g3_step1_'
    all_config_names = []
    for experiment, obs_type, shear_type in branches:
        e = experiment[0]
        o = obs_type[0]
        s = shear_type[0]

        wq_name = prefix1+e+o+s
        wq_file = os.path.join(data_root, wq_name+'.yaml')
        python_file = os.path.join(data_root, wq_name+'.py')

        print wq_file
        print python_file

        # Write out some scripts.
        mass_produce_utils.write_python_wq_script(wq_file, wq_name, data_root)
        new_config_names, new_psf_config_names, new_star_test_config_names = \
            mass_produce_utils.python_script(python_file, data_root, subfield_min, subfield_max,
                                             experiment, obs_type, shear_type,
                                             seed, n_config_per_branch, preload, my_step=1)
        if do_gal_images:
            for config_name in new_config_names:
                all_config_names.append(config_name)
        for psf_config_name in new_psf_config_names:
            all_config_names.append(psf_config_name)
        for star_test_config_name in new_star_test_config_names:
            all_config_names.append(star_test_config_name)
        seed += delta_seed

    # ESS: we just want the scripts written, we don't want to run them yet
    '''
    print "Wrote files necessary to carry out metaparameters, catalogs, and config steps"
    t1 = time.time()
    for experiment, obs_type, shear_type in branches:
        e = experiment[0]
        o = obs_type[0]
        s = shear_type[0]

        pbs_name = prefix1+e+o+s
        pbs_file = pbs_name+'.sh'
        command_str = 'qsub '+pbs_file
        p = subprocess.Popen(command_str,shell=True,close_fds=True)

    # The above command just submitted all the files to the queue.  We have to periodically poll the
    # queue to see if they are still running.
    mass_produce_utils.check_done('g3_step1', sleep_time=sleep_time)
    t2 = time.time()
    # Times are approximate since check_done only checks every N seconds for some N
    print
    print "Time for generation of metaparameters, catalogs, and config files = ",t2-t1
    print
    '''

    if do_images:
        # Then we split up into even more processes for images.
        prefix2 = 'g3_step2_'
        for config_name in all_config_names:
            file_type, _ = os.path.splitext(config_name)
            wq_file = os.path.join(data_root, prefix2 + file_type+'.yaml')
            print wq_file
            mass_produce_utils.write_galsim_wq_script(wq_file, config_name, data_root)

            '''
            command_str = 'qsub '+pbs_file
            if queue_nicely:
                mass_produce_utils.check_njobs('g3_', sleep_time=sleep_time, n_jobs=queue_nicely)
            p = subprocess.Popen(command_str, shell=True, close_fds=True)
            '''

        '''
        mass_produce_utils.check_done('g3_', sleep_time=sleep_time)
        t2 = time.time()
        # Times are approximate since check_done only checks every N seconds for some N
        print
        print "Time for generation of images = ",t2-t1
        print
        '''

# Finally, we go back to a process per branch for the final steps: star_params and packages.
prefix3 = 'g3_step3_'
for experiment, obs_type, shear_type in branches:
    e = experiment[0]
    o = obs_type[0]
    s = shear_type[0]

    pbs_name = prefix3+e+o+s
    wq_file = os.path.join(data_root, pbs_name+'.yaml')
    python_file = os.path.join(data_root, pbs_name+'.py')
    print wq_file
    print python_file

    # Write out some scripts.
    mass_produce_utils.write_python_wq_script(wq_file, pbs_name, data_root)
    mass_produce_utils.python_script(python_file, data_root, subfield_min, subfield_max, experiment,
                                     obs_type, shear_type,
                                     seed,
                                     n_config_per_branch, preload, my_step=3)
    '''
    # And then submit them
    command_str = 'qsub '+pbs_file
    p = subprocess.Popen(command_str,shell=True, close_fds=True)
    '''
'''
# The above command just submitted all the files to the queue.  We have to periodically poll the
# queue to see if they are still running.
mass_produce_utils.check_done('g3_step3', sleep_time=sleep_time)
t2 = time.time()
# Times are approximate since check_done only checks every N seconds for some N
print
print 'Time for great3sims.run star_params, packages = ',t2-t1
print
'''
