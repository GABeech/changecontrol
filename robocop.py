#!/usr/bin/env python

import getpass
import argparse
import os
import sys
from subprocess import call, check_output
from datetime import datetime
import json

# ME DEBUG, ME DEBUG YOU GOOD
#import pdb


try:
    import gitlab
except ImportError:
    print 'Could not import gitlab'
    print 'It is available on pip, see https://github.com/Itxaka/pyapi-gitlab#installation'
    print 'to determine which version you need to install'
    print '  hint: might be: pip install pyapi-gitlab'
    exit()


## Globals
gl = None
change_path = None
change_id = None
basepath = os.path.join(os.path.dirname(__file__), '../..')

# Set to my private dev project for right now
# To find the project id of the project you want user the following curl command:
# curl -X GET --header "PRIVATE-TOKEN: $your_private_key" \
#   "http://gitlab.ds.stackexchange.com/api/v3/projects/$project%2F$repo"

# Production repo. You probably want to be using this one
gl_project_id = 0

def authenticate():
    global gl
    server = 'gitlab.stackexchange.com'
    try:
        auth_file = open(".gitlab_token", 'r')
    except IOError:
        print 'Error reading .gitlab_token, failing back to manual auth'
    else:
        gl = gitlab.Gitlab(server, token=auth_file.read())
        auth_file.close()
        return

    # Manual user auth
    user = getpass.getuser()
    usr_in = raw_input("Enter user name ["+ user+"]: ")
    if usr_in:
        user = usr_in
    password = getpass.getpass("Enter Password: ")
    #pdb.set_trace()
    gl = gitlab.Gitlab(server)
    gl.login(user, password)

    wpw = raw_input("Write out token? (Won't tracked by git) [Y/n]")
    if not wpw or wpw == 'Y' or wpw == 'y':
        try:
            auth_file = open(".gitlab_token", 'w')
            auth_file.write(gl.token)
            auth_file.close()
        except IOError:
            print "error writing token"



# from http://stackoverflow.com/questions/3041986/python-command-line-yes-no-input
def query_yes_no(question, default='yes'):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the suer just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {'yes': True, 'y': True, 'ye': True,
             'no':False, 'n': False}
    if default is None:
        prompt = ' [y/n] '
    elif default == 'yes':
        prompt = ' [Y/n] '
    elif default == 'no':
        prompt = ' [y/N] '
    else:
        raise ValueError('invalid default answer: ' + default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write('Please respond with "yes" or "no" '
                             '(or "y" or "n").' + "\n")

# check that we are run from master branch
def check_branch_master():
    out = check_output(['git', 'branch'])
    return any(branch.startswith('* master') for branch in out.split('\n'))

def create_change(person, system):
    if not check_branch_master():
        sys.stderr.write("Warning: not forking from master branch\n")
        if not query_yes_no("Do you stillwant to continue? ", 'no'):
            sys.exit(78) # config error

    global change_id
    change_id = person + "-" + system + "-" + datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
    global change_path
    change_path = os.path.join(basepath, passed_arg.risk_level, change_id)
    template_path = os.path.join(basepath, "template/")
    call('git checkout -b ' + change_id, shell=True)
    #call('git checkout master', shell=True)
    call("mkdir -p " + change_path + "; cp " + template_path + "/* " + change_path, shell=True)
    call('git add ' + basepath + "/*", shell=True)
    call('git commit -am\'initial commit\'', shell=True)
    call('git push --set-upstream origin ' + change_id, shell=True)



def update_metadata():
    gl_user = gl.currentuser()
    t = datetime.date
    current_date = str(t.today())

    metadata_f = open(os.path.join(change_path, "/metadata.json"), 'r+')
    data = json.load(metadata_f)
    data['request_date'] = current_date
    data['implementors'][0]['name'] = gl_user['name']
    data['implementors'][0]['email'] = gl_user['email']
    # Yes, i'm hardcoding this, no it's not good practice
    data['implementors'][0]['position'] = 'sre'

    metadata_f.write(json.dumps(data, indent=4))
    metadata_f.close()


### PROGRAM START

# Command line argument parser
arg = argparse.ArgumentParser(description="Auto Change Control Setup Robot")

arg.add_argument('-s', '--system', required=True,
                 help="This is the system that will be affected by the change")
arg.add_argument('-p', '--person', default=getpass.getuser(),
                 help="The user making the change. defaulted to: " +
                 getpass.getuser() +" just for you")
#arg.add_argument('-t', '--title', required=True, help='This is the title fo the change.')
#arg.add_argument('-l', '--labels', default='',
#                 help="Comma delimited string of labels to apply to the change")
arg.add_argument('-r', '--risk-level', required=True, choices=['routine', 'sensitive', 'major'],
                 help="The risk level of the change, limited to our approved levels")
arg.add_argument('-d', '--description', required=True,
                 help="Short description of the change")

passed_arg = arg.parse_args()
authenticate()

create_change(passed_arg.person, passed_arg.system)

#create a merge request to get the ball rolling
gl.createmergerequest(title="CCR(" + gl.currentuser()['name'] +"): " + passed_arg.description,
                      project_id=gl_project_id, sourcebranch=change_id, targetbranch='master')


# vim: set ts=4 sw=4 expandtab:
