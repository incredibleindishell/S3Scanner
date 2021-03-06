#########
#
# AWS S3scanner - Scans domain names for S3 buckets
# 
# Author:  Dan Salmon (twitter.com/bltjetpack, github.com/sa7mon)
# Created: 6/19/17
# License: Creative Commons (CC BY-NC-SA 4.0))
#
#########

import argparse
import s3utils as s3
import logging
import coloredlogs
import sys


# We want to use both formatter classes, so a custom class it is
class CustomFormatter(argparse.RawTextHelpFormatter, argparse.RawDescriptionHelpFormatter):
    pass


# Instantiate the parser
parser = argparse.ArgumentParser(description='#  s3scanner - Find S3 buckets and dump!\n'
                                             '#\n'
                                             '#  Author: Dan Salmon - @bltjetpack, github.com/sa7mon\n',
                                 prog='s3scanner', formatter_class=CustomFormatter)

# Declare arguments
parser.add_argument('-o', '--out-file', required=False, dest='outFile',
                    help='Name of file to save the successfully checked buckets in (Default: buckets.txt)')
parser.add_argument('-c', '--include-closed', required=False, dest='includeClosed', action='store_true',
                    help='Include found but closed buckets in the out-file')
parser.add_argument('-r', '--default-region', dest='',
                    help='AWS region to default to (Default: us-west-1)')
parser.add_argument('-d', '--dump', required=False, dest='dump', action='store_true',
                    help='Dump all found open buckets locally')
parser.add_argument('buckets', help='Name of text file containing buckets to check')

parser.set_defaults(defaultRegion='us-west-1')
parser.set_defaults(includeClosed=False)
parser.set_defaults(outFile='./buckets.txt')
parser.set_defaults(dump=False)

# If there are no args supplied, print the full help text instead of the short usage text
if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)

# Parse the args
args = parser.parse_args()

# Create file logger
flog = logging.getLogger('s3scanner-file')
flog.setLevel(logging.DEBUG)              # Set log level for logger object

# Create file handler which logs even debug messages
fh = logging.FileHandler(args.outFile)
fh.setLevel(logging.DEBUG)

# Add the handler to logger
flog.addHandler(fh)

# Create secondary logger for logging to screen
slog = logging.getLogger('s3scanner-screen')
slog.setLevel(logging.INFO)

# Logging levels for the screen logger:
#   INFO  = found, open
#   WARN  = found, closed
#   ERROR = not found
# The levels serve no other purpose than to specify the output color

levelStyles = {
        'info': {'color': 'blue'},
        'warning': {'color': 'yellow'},
        'error': {'color': 'red'}
        }

fieldStyles = {
        'asctime': {'color': 'white'}
        }

# Use coloredlogs to add color to screen logger. Define format and styles.
coloredlogs.install(level='DEBUG', logger=slog, fmt='%(asctime)s   %(message)s',
                    level_styles=levelStyles, field_styles=fieldStyles)


with open(args.buckets, 'r') as f:
    for line in f:
        bucket = line.rstrip()            # Remove any extra whitespace
        region = args.defaultRegion

        # Determine what kind of input we're given. Options:
        #   bucket name i.e. mybucket
        #   domain name i.e. flaws.cloud
        #   full S3 url i.e. flaws.cloud.s3-us-west-2.amazonaws.com

        if ".amazonaws.com" in bucket:    # We were given a full s3 url
            bucket = bucket[:bucket.rfind(".s3")]
            region = bucket[len(bucket[:bucket.rfind(".s3")]) + 4:bucket.rfind(".amazonaws.com")]

        result = s3.checkBucket(bucket, region)

        if result[0] == 301:
            result = s3.checkBucket(bucket, result[1])

        if result[0] in [900, 404]:     # These are our 'bucket not found' codes
            slog.error(result[1])

        elif result[0] == 403:          # Found but closed bucket. Only log if user says to.
            message = "{0:>15} : {1}".format("[found] [closed]", result[1] + ":" + result[2])
            slog.warning(message)
            if args.includeClosed:      # If user supplied '--include-closed' flag, log this bucket to file
                flog.debug(result[1] + ":" + result[2])

        elif result[0] == 200:          # The only 'bucket found and open' codes
            message = "{0:<7}{1:>9} : {2}".format("[found]", "[open]", result[1] + ":" + result[2] + " - " + result[3])
            slog.info(message)
            flog.debug(result[1] + ":" + result[2])
            if args.dump:
                s3.dumpBucket(bucket, result[2])
        else:
            raise ValueError("Got back unknown code from checkBucket()")
