from django.core.management.base import BaseCommand, CommandError
from leaderboard.models import Entry, PLACEHOLDER_SCORE, recompute_scoring
from great3.settings import installation_base
from django.core.mail import mail_admins
import logging
import numpy as np
import os
import datetime
import pytz
import codecs
import sys
sys.path.append("/home/jaz/great3-private")
import evaluate

EXPERIMENTS_DICT = { # A dictionary for translating between Joe's experiment names and Rachel's
    "Control": "control",
    "Realistic Galaxy": "real_galaxy",
    "Realistic PSF": "variable_psf",
    "Multi-epoch": "multiepoch",
    "Everything": "full"}

SCORE_LOG_FILE = os.path.join(installation_base, "results", "results.log")

# At least for now for debugging purposes, would be good to have a logfile into which the
# logger supplied to the evaluate module can store a record of the pitfalls it falls into
EVALUATE_LOG_FILE = os.path.join(installation_base, "results", "evaluation.log")
LOG_LEVEL = logging.INFO # Logging level - currently info, could set to WARN once testing is done

# Directory in which the truth catalogues are stored (and assumed unpacked!)
TRUTH_DIR = os.path.join("/great3", "beta", "truth") 
# Directory into which to store intermediate products (truth catalogues, etc.) as a hardcopy cache
# that speeds up the metric calculation
STORAGE_DIR = os.path.join(installation_base, "results", "intermediates") 

# Some things required by corr2:
CORR2_EXEC = "/usr/local/bin/corr2" # Path to executable for MJ's corr2 correlation function code
                                    # on the server

POISSON_WEIGHT = False              # Weight the aperture mass bins by their inverse poisson
                                    # variance when estimating the absolute difference metric? 
USEBINS = evaluate.USEBINS          # Take a subset of bins, ignoring extreme small and large bins?
                                    # If so, supply evaluate.USEBINS; if not, set USEBINS=None
                                    # and all bins are used (old style)

# Note the Q scores for both the constant and variable shear branches are affected by
# empricially-determined normalization factor, and (in the case of the constant branches) fiducial,
# target values of m & c biases.
#
# These numbers are stored in the great3-private/server/great3/evaluate.py module, and should be
# changed or updated there if necessary.

MAIL_SUBJECT = "[Great3] New entry {entry} by {team} on {board} scored {score}"
MAIL_MESSAGE = """Dear Great-3 People,

A new entry has been made to the Great-3 leaderboards!
It looked something like this:

Team: {team}
Method: {method}
Name: {entry}
Score: {score}
Date: {date}
Notes: {notes}

"""
class Command(BaseCommand):
    args = ''
    help = 'Checks for entries that do not have a score yet and processes them'

    def handle(self, *args, **options):
        outfile = codecs.open(SCORE_LOG_FILE, mode='a', encoding='utf-8')
        entries = Entry.objects.filter(score=PLACEHOLDER_SCORE)
        # Define a logging.Logger
        logging.basicConfig(filename=EVALUATE_LOG_FILE, level=LOG_LEVEL)
        logger = logging.getLogger(__name__)
        for entry in entries:

            print "Processing entry %s" % entry.name.encode('utf-8')
            filename = entry.get_filename()
            if not os.path.exists(filename):
                print "Filename does not exist: ", filename
                continue
            print "Computing score, loading entry filename "+str(filename)
            if entry.board.experiment not in EXPERIMENTS_DICT:
                raise ValueError("Experiment not recognised.")
            experiment = EXPERIMENTS_DICT[entry.board.experiment]
            if entry.board.space:
                obs_type = "space"
            else:
                obs_type = "ground"
            if entry.board.varying:
                shear_type = "variable"
                entry.score = evaluate.q_variable(
                    filename, experiment, obs_type, 
                    normalization={ # Explicitly set the normalization here, although this is also
                                    # the default... I'm just a bit nervous about hiding things in
                                    # defaults!
                        "ground": evaluate.NORMALIZATION_VARIABLE_GROUND,
                        "space": evaluate.NORMALIZATION_VARIABLE_SPACE}[obs_type],
                    sigma2_min={ # As above, explicitly set sigma2_min here, although this is also
                                 # the default...
                        "ground": evaluate.SIGMA2_MIN_VARIABLE_GROUND,
                        "space": evaluate.SIGMA2_MIN_VARIABLE_SPACE}[obs_type],
                    truth_dir=TRUTH_DIR,
                    storage_dir=STORAGE_DIR, logger=logger, corr2_exec=CORR2_EXEC,
                    poisson_weight=POISSON_WEIGHT, usebins=USEBINS)
            else:
                shear_type = "constant"
                (Q_c, c_plus, m_plus, c_cross, m_cross, sigc_plus, sigm_plus, sigc_cross, sigm_cross) = evaluate.q_constant(
                    filename, experiment, obs_type,  cfid=evaluate.CFID, mfid=evaluate.MFID,
                    normalization={
                        "ground": evaluate.NORMALIZATION_CONSTANT_GROUND,
                        "space": evaluate.NORMALIZATION_CONSTANT_SPACE}[obs_type],
                    just_q=False, truth_dir=TRUTH_DIR,
                    sigma2_min={ # As above, explicitly set sigma2_min here, although this is also
                                 # the default...
                        "ground": evaluate.SIGMA2_MIN_CONSTANT_GROUND,
                        "space": evaluate.SIGMA2_MIN_CONSTANT_SPACE}[obs_type],
                    storage_dir=STORAGE_DIR, logger=logger, pretty_print=False)
                entry.score = Q_c
                entry.m_plus  = m_plus
                entry.m_cross = m_cross
                entry.c_plus  = c_plus
                entry.c_cross = c_cross
                entry.delta_m_plus  = sigm_plus
                entry.delta_m_cross = sigm_cross
                entry.delta_c_plus  = sigc_plus
                entry.delta_c_cross = sigc_cross

            datestamp = datetime.datetime.utcnow().replace(tzinfo=pytz.utc).isoformat()
            outfile.write('%s\t%s\t%r\t%s\n' % (entry.name,filename,entry.score,datestamp))
            entry.save()
            if entry.board.frozen or entry.board.blind:
                subject = MAIL_SUBJECT.format(entry=entry, board=entry.board, team=entry.team, 
                    score=entry.score)
                message = MAIL_MESSAGE.format(entry=entry, board=entry.board, team=entry.team, 
                    score=entry.score, method=entry.method, notes=entry.notes, date=datestamp)
                mail_admins(subject, message, fail_silently=True)
        recompute_scoring()
        outfile.close()