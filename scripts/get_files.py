import urllib2, re, zipfile
from cStringIO import StringIO

from settings import lobby_files_path, active_years


def get_zipfile_urls(year):
    url = 'http://www.senate.gov/legislative/Public_Disclosure/database_download.htm'
    page = urllib2.urlopen(url).read()
    zipfiles = re.findall(r'(%s_\d\.zip)' % year, page)
    base_url = 'http://soprweb.senate.gov/downloads/%s'
    return [base_url % filename for filename in zipfiles]
    
    



for year in active_years:
    urls = get_zipfile_urls(year)
    for url in urls:
        print url
        
        zipdata = urllib2.urlopen(url).read()
        zf = zipfile.ZipFile(StringIO(zipdata))
        for f in zf.filelist:
            print "Processing %s" % (f.filename)
            xml = zf.read(f.filename)
            filepath = lobby_files_path + "/" + f.filename
            outh = open(filepath, 'w')
            outh.write(xml)
            outh.close()
