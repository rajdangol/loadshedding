#!/usr/bin/env python3

import os, sys, json, argparse, re, time, datetime
import requests
from bs4 import BeautifulSoup

class ConnectError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return self.value

""" Scrap the routine from certain url """
def _scrapRoutine():
    # Get content from the url
    url = 'http://myrepublica.com/load-shedding.html'
    try:
        response = requests.get(url)
    except:
        raise ConnectError("Connection Error")
    if response.status_code != 200:
        raise ConnectError("Error code: "+str(response.status_code))
    # Regex to match time
    timerange = re.compile(r"[0-9]{2}:[0-9]{2}-[0-9]{2}:[0-9]{2}")
    # Get a parser for html
    extractor = BeautifulSoup(response.content, "html.parser")
    # Iterate over tr and td
    routines = []
    routine_table = extractor.select('table')[0] # Select first table
    routine_data = routine_table.find_all('tr')[1:] # Skip first row
    for tr in routine_data:
        routine = []
        td_list = tr.find_all('td')
        for td in td_list:
            text = td.get_text()
            time_list = [[[int(y) for y in z.split(':')]
                for z in x.split('-')]
                for x in timerange.findall(text)]
            if time_list:
                routine.append(time_list)
        routines.append(routine)
    return routines

""" Load the routine from file or scrap from the url """
def loadRoutine(force, freq=1):

    """ Find out how old the file is """
    def _age(fyle):
        created = os.path.getctime(fyle)
        today = time.time()
        return (today-created)/(60*60*24) #in days

    dest = os.path.expanduser("~")
    fname = dest+'/.loadshedding.routine'
    if os.path.exists(fname) and _age(fname) <= 2 and not force:
        with open(fname) as datafile:
            routines = json.load(datafile)
    else:
        try:
            routines = _scrapRoutine()
            with open(fname, 'w') as outfile:
                json.dump(routines, outfile)
        except ConnectError as e:
            if not os.path.exists(fname):
                print(e)
                exit(1)
            # print('*', end='')
            with open(fname, 'r') as datafile:
                routines = json.load(datafile)
    return routines


""" Show the status for 'relative' and 'effective' option """
def status(routines, group, relative):

    """ _prettify output for 'relative' option """
    def _prettify(tym):
        op = ''
        time = int(tym.total_seconds())
        tuples = [('s',60, 5*60), ('m', 60, 5*60), ('h', 24, 3*24),
                  ('d', 365, 50*365), ('y', 9999)]
        for t in tuples:
            tmp = time % t[1]
            if tmp and (len(t)<=2 or time < t[2]):
                op = str(tmp)+t[0]+op
            time //= t[1]
        return op

    """ _prettify output for 'effective' option """
    def _prettify2(tym):
        return tym.strftime("%H:%M")

    def _sanitize(rng):
        if rng[0]==24:
            return {"hour":23, "minute":59, "second":59}
        else:
            return {"hour":rng[0], "minute":rng[1], "second":0}

    now = datetime.datetime.now()
    week = now.isoweekday()%7+1
    routine = routines[group-1][week-1]
    for rng in routine:
        start = now.replace(**_sanitize(rng[0]))
        end = now.replace(**_sanitize(rng[1]))

        # If end is smaller than start, then it is in another day
        if end < start:
            end = end.replace(day=end.day+1)

        if now < start:
            z = _prettify(start-now) if relative else _prettify2(start)
            return z+" Y"
        elif now >= start and now <= end:
            z = _prettify(end-now) if relative else _prettify2(end)
            return z+" N"
    else:
        # Iterate over the week
        x = 0
        while x < 7:
            x += 1
            week = (week+x-1)%7 + 1
            routine = routines[group-1][week-1]
            if not routine:
                continue
            rng = routine[0]

            start = now.replace(**_sanitize(rng[0])).replace(day=now.day+x)

            z = _prettify(start-now) if relative else (_prettify2(start)
                                                       +" "+str(x))
            return z+" Y"
        return "Never"+" Y"

""" Show the status for 'more' option """
def statusMore(routines, group):
    now = datetime.datetime.now()
    routine = routines[group-1]
    week = now.isoweekday()%7+1

    op = ''
    for i, day in enumerate(routine):
        op += str(i+1) if (i+1)!=week else '*'
        op += ' '
        for rng in day:
            op += '{:02d}:{:02d}'.format(rng[0][0], rng[0][1])
            op += '-'
            op += '{:02d}:{:02d}'.format(rng[1][0], rng[1][1])
            op += ' '
        op += '\n'
    return op


def parse():
    parser = argparse.ArgumentParser("loadshedding", description=
                                     "Display loadshedding schedule.")
    parser.add_argument('-f', '--force', dest='force', help='force update',
                        action='store_const', const=True)
    parser.add_argument('-g', '--group',  dest='group', metavar='N',
                        help='force schedule update', type=int, required=True)

    optype = parser.add_mutually_exclusive_group(required=False)
    optype.add_argument('-e', '--effective', dest='relative',
                        help='show effective time',
                        action='store_const', const=False)
    optype.add_argument('-r', '--relative', dest='relative',
                        help='show remaining time',
                        action='store_const', const=True)
    optype.add_argument('-m', '--more', dest='more',
                        help='show all time',
                        action='store_const', const=True)

    return parser.parse_args()

def main():
    args = parse()
    routines = loadRoutine(args.force)

    if args.group < 1 or args.group > len(routines):
        print("Group value out of bounds.")
        exit(1)
    if args.more:
        op = statusMore(routines, args.group)
    else:
        op = status(routines, args.group, args.relative)

    print(op)
    return 0

if __name__=="__main__":
    main()
