# -*- coding: UTF-8 -*-

"""
Run through entire collection of lobbying reports in search of reports pertaining to certain quarters. Needs SOPR-produced xml dump unzipped to same directory.
Using legacy code. 
Todo: command line args
"""

import lxml, re, csv
import lxml.etree

from os import walk

from settings import lobby_files_path, outfile_basedir


"""
Assumes the lobby files are unzipped in this dir, something like this:
├── data
│  ├── 2012_3
│  │  ├── 2012_3_7_1.xml
│  │  ├── 2012_3_7_10.xml
...
│  ├── 2012_4
│  │  ├── 2012_4_10_1.xml
│  │  ├── 2012_4_10_10.xml
...
│  ├── 2013_1
│  │  ├── 2013_1_1_1.xml
│  │  ├── 2013_1_1_10.xml
etc.

"""

# reports will specify 'AMENDMENT', 'TERMINATION', or '(NO ACTIVITY)' following the type.
filing_types = {
    'Q1':'FIRST QUARTER',
    'Q2':'SECOND QUARTER',
    'Q3':'THIRD QUARTER',
    'Q4':'FOURTH QUARTER',
    'NEW':'NEW REGISTRATIONS'
}

# Which years do want to process? This is the year of the filing, not the year the filing was received.
# these must be strings!
years_to_handle = ['2014']
min_year = min([int(i) for i in years_to_handle])

# the keys in filing_types we care about
filings_to_handle = ['Q3']

file_types_to_handle = []
for f in filings_to_handle:
    file_types_to_handle.append(filing_types[f])



outfilename = "lobbying_" + "-".join(filings_to_handle) + "_" + "-".join(years_to_handle) + ".csv"

outfile_fullpath = outfile_basedir + "/" + outfilename


fieldnames = ['Received', 'Amount', 'Type', 'RegistrantCountry', 'RegistrantID', 'RegistrantName', 'Registrant_Description', 'Address', 'Period', 'ClientName', 'ClientID', 'Client_Description', 'SelfFiler', 'ClientState', 'Year', 'ID', 'specific_issues', 'issues']


def smart_unicode(s):
    # Could also try the below
    # but latin1 seems not to work
    # 'ascii', 'latin1', 'windows-1252',
    for enc in [ 'utf-8', 'utf-16']:
        try:
            s.decode(enc)
            return (enc)
        except UnicodeDecodeError:
            pass
    raise UnicodeDecodeError

# if it's just a mess, kill the bad characters 
# Probably should be using asciidammit        
def kill_ascii_unprintable(s):
    #a = s.decode(smart_unicode(s))
    ascii_cleaned = ''
    for i in s:
        if ord(i)<128:
            ascii_cleaned += i
    return ascii_cleaned
    

def parse_xml(xml):
#def parse_xml(xml):
    # Because the XML file may have errors that would
    # prevent it from being parsed by lxml, we split up
    # the filings into separate objects. This way if there
    # is a parsing error, it should fail on only a single 
    # filing entity, not the entire file.
    #print "Handling xml file %s" % xml
    
    xml = xml.replace("\n","")
    xml = xml.replace("\r","")
    
    encoding = smart_unicode(xml)
    print "Found encoding %s" % (encoding)
    filings = re.findall(r'<filing.*?<\/filing>', unicode(xml, encoding), re.I | re.S | re.U)
    for filing_xml in filings:
        try:
            filing = lxml.etree.fromstring(filing_xml)
        except lxml.etree.XMLSyntaxError:
            continue

        data = {'xml': filing_xml, } # Store the raw XML

        # Only keep going if this is a registration
        # or an amendment to a registration
        #if not dict(filing.items())['Type'].startswith('REGISTRATION'):
        #    continue


        this_file_type = dict(filing.items())['Type']
        year = dict(filing.items())['Year']
        
        print "file type=%s year=%s" % (this_file_type, year)
        
        handle_this = False
        for file_type in file_types_to_handle:
            if this_file_type.startswith(file_type):
                handle_this = True

        if not handle_this:
            continue
        
        if not str(year) in years_to_handle:
            continue
        
        print "handling type=%s year=%s" % (this_file_type, year)
        
        
        data.update(dict(filing.items()))

        registrant = filing.find('Registrant')
        data['registrant'] = dict(registrant.items())
        client = filing.find('Client')
        data['client'] = dict(client.items())
        issues = filing.find('Issues') or []
        data['issues'] = ";;;".join([dict(issue.items())['Code'] for issue in issues])
        
        data['specific_issues'] = ''
        data['specific_issues'] = ";;;".join([dict(issues[0].items()).get('SpecificIssue') for issue in issues])

        lobbyists = filing.find('Lobbyists')
        if lobbyists is not None:
            data['lobbyists'] = [x.attrib for x in lobbyists.iterchildren()]
        else:
            data['lobbyists'] = []

        yield data

def flatten_lobby_report(d):
    #print "keys: " + str(d.keys())
    
    ## in very rare cases the address is missing. No idea why. 
    address = ''
    try:
        address =d['registrant']['Address']
    except KeyError:
        print "Address missing!"
        pass
    
    specific_issues = kill_ascii_unprintable(d['specific_issues'])
    
    # These sometimes appear, which messes up excel, maybe
    specific_issues = specific_issues.replace("\n", " ")
    specific_issues = specific_issues.replace("\r", " ")
    
    report_flattened = {
    'Received':d['Received'],
    'Amount':d['Amount'],
    'Type':d['Type'],
    'RegistrantCountry':d['registrant']['RegistrantCountry'] or None,
    'RegistrantID': d['registrant']['RegistrantID'],
    'RegistrantName': kill_ascii_unprintable(d['registrant']['RegistrantName']),
    'Registrant_Description':  kill_ascii_unprintable(d['registrant']['GeneralDescription']),
    'Address': kill_ascii_unprintable(address),
    'Period':d['Period'],
    'ClientName':kill_ascii_unprintable(d['client']['ClientName']),
    'ClientID':kill_ascii_unprintable(d['client']['ClientID']),
    'Client_Description':kill_ascii_unprintable(d['client']['GeneralDescription']),
    'SelfFiler':d['client']['SelfFiler'],
    'ClientState':d['client']['ClientState'],
    'Year':d['Year'],
    'ID':d['ID'],
    'specific_issues':specific_issues,
    'issues':kill_ascii_unprintable(d['issues'])
    }
    
    
    return report_flattened
    #print "'Received':%s, 'Amount':%s, 'Type':%s, 'registrant':%s, 'Period':%s, 'ID':%s, 'client':%s, 'Year':%s" % (d['Received'], d['Amount'], d['Type'], d['registrant'], d['Period'], d['ID'], d['client'], d['Year'])
    #print d['Amount']
    


def process_file(path):
    print "handling: %s" % (path)
    
    xml = open(filepath, 'r').read()


    data = parse_xml(xml)
    results = []
    for d in data:
        results.append(flatten_lobby_report(d))
    
    return results


if __name__ == "__main__":
    
    outfile = open(outfile_fullpath, 'w')
    print "Writing results to %s" % (outfile_fullpath)
    
    outfile.write(",".join(fieldnames) +"\n")
    
    dw = csv.DictWriter(outfile, fieldnames=fieldnames, restval='', extrasaction='ignore')
    
    for (dirpath, dirnames, filenames) in walk(lobby_files_path):
        for filename in filenames:
            if filename.find(".xml") > 1:
                filepath = dirpath + "/" + filename
                # assumes original filenames, which look like '2013_1_1_13.xml'
                year = int(filename[:4])
                # ignore files if they are from *before* the first year we care about
                if year < min_year:
                    continue
                results = process_file(filepath)
            
                for result in results:
                    dw.writerow(result)

