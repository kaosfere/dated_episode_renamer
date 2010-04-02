#!/usr/bin/python

import re
import sys
import glob
import urllib
import shutil
import os.path
import optparse
import xml.dom.minidom

apikey='43B3C09FB8CACD87'
apihost='www.thetvdb.com'
apiport='80'
apipath='/api'

videopath='/av/video/television'

spacecharacter=' '
dateseperator='.'

def parse_args(): 
	parser=optparse.OptionParser()
	parser.add_option("-D", dest="delete", action="store_true", help="Delete extranous data aftermoving")
	parser.add_option("-v", dest="verbose",  action="store_true", help="Run verbosely")
	parser.add_option("-d", dest="videopath", help="Path to save renamed file to")

	(options,args)=parser.parse_args()

#	if(options.delete and not options.videopath):
#		print "You cannot delete (-D) without a target path (-d)."
#		sys.exit(1)

	if(not args):
		print "You must specify a file name."
		sys.exit(1)

	return (options, args)

class TVDB:
	def getseriesid(self, showname): 
		searchpath="GetSeries.php"
		searchstring=urllib.urlencode({'seriesname': showname})
		url="http://%s:%s%s/%s?%s" % (apihost, apiport, apipath, searchpath, searchstring)
		if(options.verbose):
			print "Fetching", url
		return urllib.urlopen(url);


class Series:
	def __init__(self):
		self.name=''
		self.seriesid=''

	def getepisodes(self):
		searchpath="%s/series/%s/all/en.xml" % (apikey, self.seriesid)
		url="http://%s:%s%s/%s" % (apihost, apiport, apipath, searchpath)
		if(options.verbose):
			print "Fetching", url
		return urllib.urlopen(url);


def doit(fullpath):
	filename=os.path.basename(fullpath)
	filepath=os.path.dirname(fullpath)
	filesplit=os.path.splitext(filename)

	regex=re.compile('(.*?)[- _\.](\d\d\d\d[- /_\.]\d\d[- /_\.]\d\d)[- /_\.](.*)')
	match=regex.match(filesplit[0]);
	if(match):
		(name, date, rest)=match.group(1, 2, 3)
		parsedname=re.sub('[\._-]', ' ', name)
		parseddate=re.sub('[/\._ ]', '-', date)
	else:
		print "Could not parse name component:",  filesplit[0]
		sys.exit(1)

	if(options.verbose):
		print "Name:", parsedname
		print "Date:", parseddate

	tvdb=TVDB()
	data=tvdb.getseriesid(parsedname);
	dom=xml.dom.minidom.parse(data)
	data=dom.firstChild;

	if (data.nodeName == 'Error'):
		print "TVDB Error: ",
		print data.firstChild.data
		sys.exit(1)
	elif (data.nodeName != 'Data'):
		print "Parser error: unknown response container.  XML follows."
		print data.toxml()
		sys.exit(1)

	seriesnodes=dom.getElementsByTagName('Series')

	if(len(seriesnodes) < 1):
		print "No series found for '%s'.  Try a different search." % (parsedname)
		sys.exit(1)
	if(len(seriesnodes) > 1 and options.verbose):
		print "Multiple series found.  Using top match."

	seriesxml=seriesnodes[0]
	seriesid=seriesxml.getElementsByTagName('seriesid')[0].firstChild.data
	seriesname=seriesxml.getElementsByTagName('SeriesName')[0].firstChild.data

	series=Series();
	series.seriesid=seriesid
	series.name=seriesname

	data=series.getepisodes()

	if(options.verbose):
		print "Parsing the DOM.  This may take a moment."

	dom=xml.dom.minidom.parse(data)

	episodes=dom.getElementsByTagName('Episode');

	for episode in episodes:
		airdate=episode.getElementsByTagName('FirstAired')[0]
		if(airdate.firstChild):
			firstair=airdate.firstChild.data
			if(firstair == parseddate):
				seasonnumber=int(episode.getElementsByTagName('SeasonNumber')[0].firstChild.data)
				episodenumber=int(episode.getElementsByTagName('EpisodeNumber')[0].firstChild.data)
				episodename=episode.getElementsByTagName('EpisodeName')[0].firstChild.data
	
				parseddate=re.sub('-', dateseperator, parseddate)

				newfilename="%s - %dx%02d (%s) - %s%s" % (seriesname, seasonnumber, episodenumber, parseddate, episodename, filesplit[1])
				destpath="%s/%s" % (videopath, seriesname)

	if(options.verbose):
		print "Old Name:", filename
		print "New Name:", newfilename

	if (not os.path.exists(destpath)):
		try:
			if(options.verbose):
				print "Making", destpath
			os.makedirs(destpath)
		except:
			print "Could not make destination path", destpath
			sys.exit(1)


	try:
		shutil.move(fullpath, "%s/%s" % (destpath, newfilename))
	except:
		print "Failed to move show to %s.  Exiting." % (destpath)
		sys.exit(1)
	
	if(options.delete):
		if(options.verbose):
			print "Deleting", filepath
		shutil.rmtree(filepath)

### MAIN ###

(options,args)=parse_args()

if(options.videopath):
	videopath=options.videopath

fullpath=args[0]

if(os.path.isdir(fullpath)):
	for extension in ('avi', 'mkv', 'mpeg', 'ts'):
		filelist=glob.glob("%s/*.%s" % (fullpath, extension))
		for file in filelist:
			doit(file)
else:
	doit(fullpath)

print "Succeeded!";

sys.exit(0)
