import os

def get_ps_dirs():
    d=os.environ['GREAT3SIMS_DIR']
    ps_dir=os.path.join(d, 'inputs/shear-ps/tables')
    atmos_ps_dir=os.path.join(d, 'inputs/atmospsf/pk_math')
    opt_psf_dir = os.path.join(d, 'inputs/optical-psfs')
    return ps_dir, atmos_ps_dir, opt_psf_dir

def get_gal_dir():
    d=os.environ['GREAT3SIMS_COSMOS_DIR']
    return d

def get_run_dir(run):
    d=os.environ['GREAT3SIMS_DATA_DIR']
    d=os.path.join(d, run)
    return d

def get_data_dir(run):
    d=get_run_dir(run)
    return os.path.join(d, 'data')
